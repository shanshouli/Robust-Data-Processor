"""Unit tests for the FastAPI ingestion endpoint.

This module tests the /ingest endpoint with both JSON and text/plain formats,
covering success cases, validation errors, and edge cases.
"""

import json

import pytest
from fastapi.testclient import TestClient

import app.main as main
from app.config import Settings


class DummySQS:
    """In-memory SQS stub used for tests.
    
    This mock SQS client captures all send_message calls in memory,
    allowing tests to verify that messages are properly enqueued
    without making actual AWS API calls.
    """

    def __init__(self) -> None:
        """Initialize empty message list."""
        self.sent = []

    def send_message(self, QueueUrl: str, MessageBody: str) -> dict:
        """Record the message and return a mock SQS response.
        
        Args:
            QueueUrl: The queue URL (recorded but not used in tests)
            MessageBody: The message body to enqueue
            
        Returns:
            dict: Mock SQS response with fake RequestId
        """
        self.sent.append({"QueueUrl": QueueUrl, "MessageBody": MessageBody})
        return {"ResponseMetadata": {"RequestId": "req-123"}}


@pytest.fixture
def client_with_mocks() -> tuple[TestClient, DummySQS]:
    """Provide a TestClient with mocked settings and SQS client.
    
    This fixture sets up the FastAPI test client with:
    - Mock SQS client to avoid actual AWS calls
    - Test configuration with dummy AWS settings
    - Proper cleanup after test execution
    
    Yields:
        tuple: (TestClient for making requests, DummySQS for verification)
    """
    # Create mock SQS client
    dummy_sqs = DummySQS()
    
    # Create test settings (no actual AWS credentials needed)
    settings = Settings(
        aws_region="us-east-1",
        sqs_queue_url="https://sqs.example.com/queue",
        dynamodb_table_name="tenant-logs",
    )
    
    # Override dependencies to inject mocks
    original_get_sqs_client = main.get_sqs_client
    main.get_sqs_client = lambda _settings: dummy_sqs  # type: ignore[assignment]
    main.app.dependency_overrides[main.get_settings] = lambda: settings

    # Create test client
    client = TestClient(main.app)
    yield client, dummy_sqs

    # Cleanup: restore original dependencies
    main.app.dependency_overrides = {}
    main.get_sqs_client = original_get_sqs_client


def test_ingest_json_success(client_with_mocks: tuple[TestClient, DummySQS]) -> None:
    """Test successful JSON log ingestion with all fields provided.
    
    Verifies that:
    - The API returns 202 Accepted
    - Response contains correct tenant_id and log_id
    - Message is properly enqueued to SQS with correct format
    """
    client, dummy_sqs = client_with_mocks

    # Submit a JSON log with tenant_id, text, and explicit log_id
    payload = {"tenant_id": "acme", "text": "hello", "log_id": "abc"}
    resp = client.post("/ingest", json=payload)

    # Verify HTTP response
    assert resp.status_code == 202
    body = resp.json()
    assert body["tenant_id"] == "acme"
    assert body["log_id"] == "abc"

    # Verify message was enqueued to SQS
    assert len(dummy_sqs.sent) == 1
    message = json.loads(dummy_sqs.sent[0]["MessageBody"])
    assert message["source"] == "json_upload"
    assert message["tenant_id"] == "acme"
    assert message["log_id"] == "abc"


def test_ingest_text_plain_success(client_with_mocks: tuple[TestClient, DummySQS]) -> None:
    """Test successful plain text log ingestion with X-Tenant-ID header.
    
    Verifies that:
    - The API accepts text/plain content type
    - Tenant ID is extracted from X-Tenant-ID header
    - A log_id is auto-generated when not provided
    - Message is properly enqueued with source=text_upload
    """
    client, dummy_sqs = client_with_mocks

    # Submit plain text log with tenant ID in header
    resp = client.post(
        "/ingest",
        data="User 555-0199 accessed",
        headers={"Content-Type": "text/plain", "X-Tenant-ID": "beta"},
    )

    # Verify HTTP response
    assert resp.status_code == 202
    body = resp.json()
    assert body["tenant_id"] == "beta"
    assert body["log_id"]  # Auto-generated UUID

    # Verify message was enqueued to SQS with correct source type
    assert len(dummy_sqs.sent) == 1
    message = json.loads(dummy_sqs.sent[0]["MessageBody"])
    assert message["source"] == "text_upload"
    assert message["tenant_id"] == "beta"


def test_ingest_missing_tenant_header_returns_400(
    client_with_mocks: tuple[TestClient, DummySQS]
) -> None:
    """Test that plain text ingestion without X-Tenant-ID header fails.
    
    Verifies that:
    - The API returns 400 Bad Request when X-Tenant-ID is missing
    - Error message is descriptive
    - No message is enqueued to SQS (prevents processing invalid data)
    """
    client, dummy_sqs = client_with_mocks

    # Attempt to submit plain text without required X-Tenant-ID header
    resp = client.post(
        "/ingest",
        data="missing header",
        headers={"Content-Type": "text/plain"},
    )

    # Verify error response
    assert resp.status_code == 400
    assert resp.json()["detail"] == "Missing X-Tenant-ID header"
    
    # Verify no message was enqueued
    assert dummy_sqs.sent == []

