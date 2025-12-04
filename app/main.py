"""FastAPI application exposing the /ingest endpoint."""

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

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(title="Log Ingestion Service", version="1.0.0")


def get_sqs_client(settings: Settings) -> boto3.client:
    """Instantiate an SQS client for the configured region."""
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

    - application/json expects tenant_id and text fields, optional log_id
    - text/plain expects X-Tenant-ID header
    """
    content_type = request.headers.get("content-type", "").split(";")[0].strip().lower()

    if content_type == "application/json":
        try:
            payload = await request.json()
            json_request = JsonIngestRequest(**payload)
        except Exception as exc:  # broad to return a clean 400
            logger.warning("Invalid JSON payload: %s", exc)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid JSON payload",
            ) from exc

        log_id = json_request.log_id or str(uuid.uuid4())
        message = build_internal_message(
            tenant_id=json_request.tenant_id,
            log_id=log_id,
            source="json_upload",
            text=json_request.text,
        )
    elif content_type == "text/plain":
        if not x_tenant_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Missing X-Tenant-ID header",
            )

        body_bytes = await request.body()
        text_body = body_bytes.decode("utf-8", errors="replace")
        message = build_internal_message(
            tenant_id=x_tenant_id,
            log_id=str(uuid.uuid4()),
            source="text_upload",
            text=text_body,
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported Content-Type. Use application/json or text/plain.",
        )

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
        logger.exception("Failed to enqueue message: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to enqueue message",
        ) from exc

    return EnqueueResponse(
        status="enqueued",
        tenant_id=message.tenant_id,
        log_id=message.log_id,
        request_id=response.get("ResponseMetadata", {}).get("RequestId"),
    )


handler = Mangum(app)

