"""SQS-triggered worker Lambda that processes ingested logs."""

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

from app.config import Settings, get_settings
from app.models import InternalMessage

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)

PHONE_PATTERN = re.compile(r"\b\d{3}-\d{4}\b")


def redact_text(text: str) -> str:
    """Mask simple phone-like patterns."""
    return PHONE_PATTERN.sub("[REDACTED]", text)


def get_clients(settings: Settings) -> Dict[str, Any]:
    """Initialize AWS service clients."""
    dynamodb = boto3.client("dynamodb", region_name=settings.aws_region)
    return {"dynamodb": dynamodb}


def process_message(message: InternalMessage, settings: Settings, clients: Dict[str, Any]) -> None:
    """Simulate heavy processing and persist results to DynamoDB."""
    # Simulated crash with small probability to exercise retry behavior.
    if random.random() < 0.05:
        logger.error("Simulated worker crash for log_id=%s", message.log_id)
        raise RuntimeError("Simulated worker crash")

    time.sleep(0.05 * len(message.text))
    modified_text = redact_text(message.text)

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
        clients["dynamodb"].put_item(
            TableName=settings.dynamodb_table_name,
            Item=item,
            ConditionExpression="attribute_not_exists(tenant_id) AND attribute_not_exists(log_id)",
        )
        logger.info(
            "Persisted log tenant_id=%s log_id=%s processed_at=%s",
            message.tenant_id,
            message.log_id,
            processed_at,
        )
    except ClientError as exc:
        if exc.response["Error"]["Code"] == "ConditionalCheckFailedException":
            logger.warning(
                "Duplicate detected, skipping persist tenant_id=%s log_id=%s",
                message.tenant_id,
                message.log_id,
            )
            return
        logger.exception("Failed to write to DynamoDB: %s", exc)
        raise
    except BotoCoreError as exc:
        logger.exception("AWS client error: %s", exc)
        raise


def handler(event: Dict[str, Any], context: Any) -> None:
    """Lambda entrypoint for SQS events."""
    settings = get_settings()
    clients = get_clients(settings)

    records: List[Dict[str, Any]] = event.get("Records", [])
    for record in records:
        try:
            body = json.loads(record["body"])
            message = InternalMessage.parse_obj(body)
            logger.info(
                "Processing message tenant_id=%s log_id=%s", message.tenant_id, message.log_id
            )
            process_message(message, settings, clients)
        except Exception as exc:  # let Lambda/SQS handle retries
            logger.exception("Error processing record: %s", exc)
            raise
