"""FastAPI application exposing the /ingest endpoint.

This module implements a serverless log ingestion service that accepts logs via HTTP,
validates them, and enqueues them to SQS for asynchronous processing by worker Lambdas.

The service supports two ingestion formats:
1. JSON (application/json) - Structured log data with tenant_id, text, and optional log_id
2. Plain text (text/plain) - Raw text logs with tenant identification via X-Tenant-ID header

All ingested logs are enqueued to SQS and processed asynchronously, allowing the API
to return quickly (202 Accepted) without waiting for processing to complete.
"""

from __future__ import annotations

import logging
import uuid
from typing import Optional

import boto3
from botocore.exceptions import BotoCoreError, ClientError
from fastapi import Depends, FastAPI, Header, HTTPException, Request, status
from mangum import Mangum

from app.config import Settings, get_settings
from app.models import EnqueueResponse, InternalMessage, JsonIngestRequest, build_internal_message

# Configure logging format for Lambda CloudWatch integration
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger(__name__)

# Initialize FastAPI application
app = FastAPI(title="Log Ingestion Service", version="1.0.0")


def get_sqs_client(settings: Settings) -> boto3.client:
    """Instantiate an SQS client for the configured region.
    
    This function is designed to be dependency-injected and can be easily mocked
    in tests to avoid actual AWS calls.
    
    Args:
        settings: Application settings containing AWS region configuration
        
    Returns:
        boto3.client: Configured SQS client for the specified region
    """
    return boto3.client("sqs", region_name=settings.aws_region)


@app.post(
    "/ingest",
    response_model=EnqueueResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Ingest a log",
)
async def ingest(
    request: Request,
    x_tenant_id: Optional[str] = Header(default=None, convert_underscores=False),
    settings: Settings = Depends(get_settings),
) -> EnqueueResponse:
    """
    Ingest logs in JSON or plain text form and enqueue them onto SQS.
    
    This endpoint accepts logs in two formats:
    - application/json: Expects tenant_id and text fields, optional log_id
    - text/plain: Expects X-Tenant-ID header for tenant identification
    
    The endpoint performs minimal validation and immediately enqueues the log
    to SQS for asynchronous processing, returning a 202 Accepted response.
    
    Args:
        request: FastAPI request object containing the log payload
        x_tenant_id: Optional tenant identifier from X-Tenant-ID header (for text/plain)
        settings: Injected application settings
        
    Returns:
        EnqueueResponse: Contains status, tenant_id, log_id, and SQS request_id
        
    Raises:
        HTTPException 400: Invalid payload, missing headers, or unsupported content type
        HTTPException 500: Failed to enqueue message to SQS
    """
    # Extract and normalize Content-Type header, ignoring charset and other parameters
    content_type = request.headers.get("content-type", "").split(";")[0].strip().lower()

    # Handle JSON payload format (structured log data)
    if content_type == "application/json":
        try:
            payload = await request.json()
            json_request = JsonIngestRequest(**payload)
        except Exception as exc:  # Broad exception to provide clean 400 response
            logger.warning("Invalid JSON payload: %s", exc)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid JSON payload",
            ) from exc

        # Generate UUID for log_id if not provided by client
        log_id = json_request.log_id or str(uuid.uuid4())
        message = build_internal_message(
            tenant_id=json_request.tenant_id,
            log_id=log_id,
            source="json_upload",
            text=json_request.text,
        )
    # Handle plain text payload format (raw log text)
    elif content_type == "text/plain":
        # Validate required X-Tenant-ID header for tenant identification
        if not x_tenant_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Missing X-Tenant-ID header",
            )

        # Read raw body bytes and decode to UTF-8, replacing invalid characters
        body_bytes = await request.body()
        text_body = body_bytes.decode("utf-8", errors="replace")
        
        # Always generate a new UUID for plain text uploads
        message = build_internal_message(
            tenant_id=x_tenant_id,
            log_id=str(uuid.uuid4()),
            source="text_upload",
            text=text_body,
        )
    else:
        # Reject unsupported content types
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported Content-Type. Use application/json or text/plain.",
        )

    # Initialize SQS client and send the message to the queue
    sqs_client = get_sqs_client(settings)
    try:
        response = sqs_client.send_message(
            QueueUrl=settings.sqs_queue_url,
            MessageBody=message.to_queue_body(),
        )
        logger.info(
            "Enqueued message tenant_id=%s log_id=%s request_id=%s",
            message.tenant_id,
            message.log_id,
            response.get("ResponseMetadata", {}).get("RequestId"),
        )
    except (BotoCoreError, ClientError) as exc:
        # Log the error and return 500 if SQS enqueue fails
        logger.exception("Failed to enqueue message: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to enqueue message",
        ) from exc

    # Return non-blocking response immediately once message is safely enqueued
    # Actual processing happens asynchronously in worker Lambda
    return EnqueueResponse(
        status="enqueued",
        tenant_id=message.tenant_id,
        log_id=message.log_id,
        request_id=response.get("ResponseMetadata", {}).get("RequestId"),
    )


# Mangum adapter enables FastAPI to run as an AWS Lambda function
# This is the handler that API Gateway invokes
handler = Mangum(app)
