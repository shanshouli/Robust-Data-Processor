"""Pydantic models for requests and internal messaging.

This module defines all data models used throughout the log ingestion pipeline:
- Request models for API input validation
- Internal message format for SQS queue communication
- Response models for API output serialization
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal, Optional

from pydantic import BaseModel, Field


class JsonIngestRequest(BaseModel):
    """Request body for JSON ingestion.
    
    This model validates incoming JSON payloads sent to the /ingest endpoint.
    It ensures required fields are present and properly formatted.
    
    Attributes:
        tenant_id: Unique identifier for the tenant/organization submitting the log
        text: The actual log content/body to be processed
        log_id: Optional client-provided identifier; auto-generated if omitted
    """

    tenant_id: str = Field(..., description="Tenant identifier")
    text: str = Field(..., description="Log body text")
    log_id: Optional[str] = Field(None, description="Optional log identifier")


class InternalMessage(BaseModel):
    """Normalized message stored on SQS.
    
    This model represents the standardized internal format for all logs,
    regardless of how they were submitted (JSON or plain text). This ensures
    the worker Lambda can process all messages uniformly.
    
    Attributes:
        tenant_id: Tenant identifier extracted from request
        log_id: Unique log identifier (client-provided or auto-generated)
        source: Indicates the ingestion method used (json_upload or text_upload)
        text: The raw log content to be processed
        received_at: UTC timestamp automatically set when the log was received
    """

    tenant_id: str
    log_id: str
    source: Literal["json_upload", "text_upload"]
    text: str
    received_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC timestamp when the ingestion service received the log",
    )

    def to_queue_body(self) -> str:
        """Serialize the message to JSON with ISO timestamps.
        
        Converts the message to a JSON string suitable for SQS message body.
        Pydantic automatically handles datetime serialization to ISO format.
        
        Returns:
            str: JSON-encoded message body
        """
        return self.json()


class EnqueueResponse(BaseModel):
    """Response returned after enqueueing a log.
    
    This model defines the API response structure for successful log ingestion.
    The 202 Accepted status indicates the log has been queued for processing.
    
    Attributes:
        status: Always "enqueued" to indicate successful queueing
        tenant_id: Echo back the tenant identifier for client verification
        log_id: The log identifier (useful for tracking and debugging)
        request_id: Optional AWS request ID from SQS for troubleshooting
    """

    status: str
    tenant_id: str
    log_id: str
    request_id: Optional[str] = None


def build_internal_message(
    *,
    tenant_id: str,
    log_id: str,
    source: Literal["json_upload", "text_upload"],
    text: str,
) -> InternalMessage:
    """Factory helper for creating a normalized internal message.
    
    This function provides a consistent way to construct InternalMessage objects,
    ensuring all required fields are provided and the received_at timestamp is
    automatically set.
    
    Args:
        tenant_id: Tenant identifier
        log_id: Unique log identifier
        source: Upload method (json_upload or text_upload)
        text: Raw log content
        
    Returns:
        InternalMessage: Fully constructed message ready for SQS enqueueing
    """
    return InternalMessage(
        tenant_id=tenant_id,
        log_id=log_id,
        source=source,
        text=text,
    )

