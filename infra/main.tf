terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

locals {
  ingest_zip = "${path.module}/../dist/ingest-go.zip"
  worker_zip = "${path.module}/../dist/worker-go.zip"
  common_tags = {
    Project = var.project_name
  }
}

resource "aws_sqs_queue" "log_ingest_dlq" {
  name = "${var.project_name}-ingest-dlq"

  tags = local.common_tags
}

resource "aws_sqs_queue" "log_ingest_queue" {
  name                       = "${var.project_name}-ingest"
  visibility_timeout_seconds = 300
  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.log_ingest_dlq.arn
    maxReceiveCount     = 5
  })

  tags = local.common_tags
}

resource "aws_dynamodb_table" "tenant_logs" {
  name         = "${var.project_name}-tenant-logs"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "tenant_id"
  range_key    = "log_id"

  attribute {
    name = "tenant_id"
    type = "S"
  }

  attribute {
    name = "log_id"
    type = "S"
  }

  tags = local.common_tags
}

data "aws_iam_policy_document" "lambda_assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "ingest_role" {
  name               = "${var.project_name}-ingest-role"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume.json
  tags               = local.common_tags
}

resource "aws_iam_role" "worker_role" {
  name               = "${var.project_name}-worker-role"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume.json
  tags               = local.common_tags
}

data "aws_iam_policy_document" "ingest_policy" {
  statement {
    actions   = ["sqs:SendMessage"]
    resources = [aws_sqs_queue.log_ingest_queue.arn]
  }

  statement {
    actions = [
      "logs:CreateLogGroup",
      "logs:CreateLogStream",
      "logs:PutLogEvents",
    ]
    resources = ["arn:aws:logs:*:*:*"]
  }
}

resource "aws_iam_role_policy" "ingest_policy" {
  role   = aws_iam_role.ingest_role.id
  policy = data.aws_iam_policy_document.ingest_policy.json
}

data "aws_iam_policy_document" "worker_policy" {
  statement {
    actions = [
      "sqs:ReceiveMessage",
      "sqs:DeleteMessage",
      "sqs:ChangeMessageVisibility",
      "sqs:GetQueueAttributes",
      "sqs:GetQueueUrl",
    ]
    resources = [aws_sqs_queue.log_ingest_queue.arn]
  }

  statement {
    actions   = ["dynamodb:PutItem"]
    resources = [aws_dynamodb_table.tenant_logs.arn]
  }

  statement {
    actions = [
      "logs:CreateLogGroup",
      "logs:CreateLogStream",
      "logs:PutLogEvents",
    ]
    resources = ["arn:aws:logs:*:*:*"]
  }
}

resource "aws_iam_role_policy" "worker_policy" {
  role   = aws_iam_role.worker_role.id
  policy = data.aws_iam_policy_document.worker_policy.json
}

resource "aws_lambda_function" "ingest" {
  function_name = "${var.project_name}-ingest"
  filename      = local.ingest_zip
  source_code_hash = filebase64sha256(local.ingest_zip)
  role              = aws_iam_role.ingest_role.arn
  handler           = "bootstrap"
  runtime           = "provided.al2023"
  timeout           = 10
  memory_size       = 256

  environment {
    variables = {
      SQS_QUEUE_URL        = aws_sqs_queue.log_ingest_queue.id
      DYNAMODB_TABLE_NAME  = aws_dynamodb_table.tenant_logs.name
    }
  }

  tags = local.common_tags
}

resource "aws_lambda_function" "worker" {
  function_name = "${var.project_name}-worker"
  filename      = local.worker_zip
  source_code_hash = filebase64sha256(local.worker_zip)
  role              = aws_iam_role.worker_role.arn
  handler           = "bootstrap"
  runtime           = "provided.al2023"
  timeout           = 300
  memory_size       = 256

  environment {
    variables = {
      DYNAMODB_TABLE_NAME = aws_dynamodb_table.tenant_logs.name
    }
  }

  tags = local.common_tags
}

resource "aws_apigatewayv2_api" "ingest_api" {
  name          = "${var.project_name}-api"
  protocol_type = "HTTP"
  tags          = local.common_tags
}

resource "aws_apigatewayv2_integration" "ingest_integration" {
  api_id                 = aws_apigatewayv2_api.ingest_api.id
  integration_type       = "AWS_PROXY"
  integration_method     = "POST"
  integration_uri        = aws_lambda_function.ingest.invoke_arn
  payload_format_version = "2.0"
}

resource "aws_apigatewayv2_route" "ingest_route" {
  api_id    = aws_apigatewayv2_api.ingest_api.id
  route_key = "POST /ingest"
  target    = "integrations/${aws_apigatewayv2_integration.ingest_integration.id}"
}

resource "aws_apigatewayv2_stage" "ingest_stage" {
  api_id      = aws_apigatewayv2_api.ingest_api.id
  name        = "$default"
  auto_deploy = true
  tags        = local.common_tags
}

resource "aws_lambda_permission" "apigw_invoke" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.ingest.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.ingest_api.execution_arn}/*/*"
}

resource "aws_lambda_event_source_mapping" "worker_sqs_mapping" {
  event_source_arn = aws_sqs_queue.log_ingest_queue.arn
  function_name    = aws_lambda_function.worker.arn
  batch_size       = 5
}

