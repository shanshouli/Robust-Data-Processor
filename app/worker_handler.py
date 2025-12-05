"""SQS-triggered worker Lambda that processes ingested logs.

This module implements the asynchronous log processing worker that:
1. Receives log messages from SQS queue
2. Performs data transformation and redaction (e.g., masking phone numbers)
3. Persists processed logs to DynamoDB with idempotency guarantees
4. Handles failures with automatic retry via SQS dead-letter queue

The worker simulates heavy processing workload and includes deliberate failure
injection for testing retry mechanisms and system resilience.
"""

from __future__ import annotations

import json
import logging
import random
import re
import time
from datetime import datetime, timezone
from typing import Any, Dict, List

import boto3
from botocore.exceptions import BotoCoreError, ClientError

from app.config import WorkerSettings, get_worker_settings
from app.models import InternalMessage

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)

# Regular expression to detect simple phone number patterns (e.g., 555-0199)
PHONE_PATTERN = re.compile(r"\b\d{3}-\d{4}\b")


def redact_text(text: str) -> str:
    """Mask simple phone-like patterns with [REDACTED].
    
    This function provides basic PII redaction by identifying and masking
    phone numbers in the format XXX-XXXX. In production, this could be
    extended to handle more complex patterns and additional PII types.
    
    Args:
        text: Original log text potentially containing phone numbers
        
    Returns:
        str: Text with phone numbers replaced by [REDACTED]
    """
    return PHONE_PATTERN.sub("[REDACTED]", text)


def get_clients(settings: WorkerSettings) -> Dict[str, Any]:
    """Initialize AWS service clients.
    
    Creates and returns a dictionary of AWS service clients needed for
    log processing. Currently only DynamoDB is required, but this pattern
    allows easy addition of other services (S3, SNS, etc.).
    
    Args:
        settings: Application settings containing AWS configuration
        
    Returns:
        Dict[str, Any]: Dictionary mapping service names to client objects
    """
    dynamodb = boto3.client("dynamodb", region_name=settings.aws_region)
    return {"dynamodb": dynamodb}


def process_message(message: InternalMessage, settings: WorkerSettings, clients: Dict[str, Any]) -> None:
    """Simulate heavy processing and persist results to DynamoDB.
    
    This function represents the core log processing logic:
    1. Simulates potential failures (for testing retry mechanisms)
    2. Performs CPU-intensive work (simulated via sleep)
    3. Applies data transformations (redaction)
    4. Persists results to DynamoDB with idempotency guarantees
    
    The function uses a conditional write to ensure each log is processed
    exactly once, even if the Lambda is invoked multiple times due to retries.
    
    Args:
        message: Normalized log message from SQS
        settings: Application settings
        clients: Dictionary of AWS service clients
        
    Raises:
        RuntimeError: Randomly simulated crashes (5% probability)
        ClientError: DynamoDB errors (except ConditionalCheckFailedException for duplicates)
        BotoCoreError: AWS SDK errors
    """
    # Simulated crash with 5% probability to exercise retry behavior and DLQ routing
    # In production, this would be replaced with actual error handling
    if random.random() < 0.05:
        logger.error("Simulated worker crash for log_id=%s", message.log_id)
        raise RuntimeError("Simulated worker crash")

    # Simulate heavy processing time proportional to payload size
    # This demonstrates backpressure and auto-scaling behavior
    time.sleep(0.05 * len(message.text))
    
    # Apply redaction transformations to protect PII
    modified_text = redact_text(message.text)

    # Prepare DynamoDB item with processed data
    processed_at = datetime.now(timezone.utc).isoformat()
    item = {
        "tenant_id": {"S": message.tenant_id},
        "log_id": {"S": message.log_id},
        "source": {"S": message.source},
        "original_text": {"S": message.text},
        "modified_data": {"S": modified_text},
        "processed_at": {"S": processed_at},
    }

    try:
        # Attempt to write the processed log to DynamoDB
        # The conditional expression ensures idempotency: the write only succeeds
        # if no item with the same tenant_id + log_id already exists
        clients["dynamodb"].put_item(
            TableName=settings.dynamodb_table_name,
            Item=item,
            # Conditional put enforces idempotency on composite key (tenant_id, log_id)
            # This prevents duplicate processing even if the Lambda is retried
            ConditionExpression="attribute_not_exists(tenant_id) AND attribute_not_exists(log_id)",
        )
        logger.info(
            "Persisted log tenant_id=%s log_id=%s processed_at=%s",
            message.tenant_id,
            message.log_id,
            processed_at,
        )
    except ClientError as exc:
        # Handle duplicate detection gracefully (expected behavior for retries)
        if exc.response["Error"]["Code"] == "ConditionalCheckFailedException":
            logger.warning(
                "Duplicate detected, skipping persist tenant_id=%s log_id=%s",
                message.tenant_id,
                message.log_id,
            )
            # Return successfully since the log was already processed
            return
        # Propagate other ClientErrors for retry handling
        logger.exception("Failed to write to DynamoDB: %s", exc)
        raise
    except BotoCoreError as exc:
        # Propagate AWS SDK errors for retry handling
        logger.exception("AWS client error: %s", exc)
        raise


def handler(event: Dict[str, Any], context: Any) -> None:
    """Lambda entrypoint for SQS events.
    
    This function is invoked by AWS Lambda when messages are available in the SQS queue.
    It processes each message in the batch, handling deserialization, validation,
    and processing errors.
    
    Error Handling Strategy:
    - Any exception raised will cause the entire batch to be retried
    - After max retries, failed messages move to the dead-letter queue (DLQ)
    - Idempotency guarantees prevent duplicate processing on retries
    
    Args:
        event: Lambda event containing SQS message batch under "Records" key
        context: Lambda context object (unused but required by Lambda signature)
        
    Raises:
        Exception: Any processing error, triggering SQS retry mechanism
    """
    # Load configuration and initialize AWS clients
    settings = get_worker_settings()
    clients = get_clients(settings)

    # Extract SQS records from the event (batch can contain multiple messages)
    records: List[Dict[str, Any]] = event.get("Records", [])
    
    # Process each message in the batch
    for record in records:
        try:
            # Deserialize the message body from JSON
            body = json.loads(record["body"])
            
            # Parse and validate the internal message structure
            message = InternalMessage.parse_obj(body)
            
            logger.info(
                "Processing message tenant_id=%s log_id=%s", message.tenant_id, message.log_id
            )
            
            # Perform actual log processing and persistence
            process_message(message, settings, clients)
            
        except Exception as exc:
            # Log the error and re-raise to trigger SQS retry mechanism
            # Lambda will mark this batch as failed, and SQS will retry based on queue config
            logger.exception("Error processing record: %s", exc)
            raise
