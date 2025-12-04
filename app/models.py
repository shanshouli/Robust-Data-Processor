"""Pydantic models for requests and internal messaging."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal, Optional

from pydantic import BaseModel, Field


class JsonIngestRequest(BaseModel):
    """Request body for JSON ingestion."""

    tenant_id: str = Field(..., description="Tenant identifier")
    text: str = Field(..., description="Log body text")
    log_id: Optional[str] = Field(None, description="Optional log identifier")


class InternalMessage(BaseModel):
    """Normalized message stored on SQS."""

    tenant_id: str
    log_id: str
    source: Literal["json_upload", "text_upload"]
    text: str
    received_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC timestamp when the ingestion service received the log",
    )

    def to_queue_body(self) -> str:
        """Serialize the message to JSON with ISO timestamps."""
        return self.json()


class EnqueueResponse(BaseModel):
    """Response returned after enqueueing a log."""

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
    """Factory helper for creating a normalized internal message."""
    return InternalMessage(
        tenant_id=tenant_id,
        log_id=log_id,
        source=source,
        text=text,
    )

