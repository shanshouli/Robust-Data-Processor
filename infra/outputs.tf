output "api_invoke_url" {
  description = "Invoke URL for the ingest API."
  value       = aws_apigatewayv2_stage.ingest_stage.invoke_url
}

output "sqs_queue_url" {
  description = "URL of the ingestion SQS queue."
  value       = aws_sqs_queue.log_ingest_queue.id
}

output "dynamodb_table_name" {
  description = "Name of the DynamoDB table storing processed logs."
  value       = aws_dynamodb_table.tenant_logs.name
}

