"""Unit tests for the SQS worker Lambda handler.

This module tests the worker's log processing logic, including:
- Data transformation and redaction
- DynamoDB persistence
- Idempotency and duplicate handling
- End-to-end event processing
"""

import pytest
from botocore.exceptions import ClientError

import app.worker_handler as worker
from app.models import InternalMessage


class FakeDynamo:
    """Minimal DynamoDB stub capturing writes.
    
    This mock DynamoDB client simulates the conditional write behavior
    used for idempotency, allowing tests to verify duplicate detection
    without actual AWS infrastructure.
    """

    def __init__(self) -> None:
        """Initialize empty in-memory item store."""
        self.items = {}

    def put_item(self, TableName: str, Item: dict, ConditionExpression: str) -> None:
        """Simulate DynamoDB put_item with conditional write.
        
        Stores items keyed by (tenant_id, log_id) and raises
        ConditionalCheckFailedException if the item already exists,
        mimicking the actual DynamoDB behavior.
        
        Args:
            TableName: Target table name (recorded but not used)
            Item: DynamoDB item in low-level format (e.g., {"S": "value"})
            ConditionExpression: Condition string (recorded but not evaluated)
            
        Raises:
            ClientError: When attempting to write duplicate item
        """
        key = (Item["tenant_id"]["S"], Item["log_id"]["S"])
        if key in self.items:
            # Simulate DynamoDB conditional check failure for duplicates
            raise ClientError(
                {"Error": {"Code": "ConditionalCheckFailedException", "Message": ""}},
                "PutItem",
            )
        self.items[key] = {"Item": Item, "TableName": TableName, "Condition": ConditionExpression}


@pytest.fixture(autouse=True)
def deterministic_processing(monkeypatch: pytest.MonkeyPatch) -> None:
    """Avoid random crashes and sleep during tests.
    
    This fixture ensures tests run quickly and deterministically by:
    - Disabling simulated random crashes (return 0.99 > 0.05 threshold)
    - Skipping simulated processing delays (no-op sleep function)
    
    Applied automatically to all tests in this module via autouse=True.
    """
    monkeypatch.setattr(worker.random, "random", lambda: 0.99)
    monkeypatch.setattr(worker.time, "sleep", lambda _seconds: None)


def test_process_message_writes_redacted_text(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that phone numbers are redacted and data is persisted correctly.
    
    Verifies that:
    - Phone patterns (XXX-XXXX) are replaced with [REDACTED]
    - Original text is preserved in the database
    - Modified text contains the redaction
    - Conditional expression is properly set for idempotency
    """
    fake_dynamo = FakeDynamo()
    # Create minimal settings object (using type() for simplicity in tests)
    settings = type("S", (), {"dynamodb_table_name": "tenant-logs"})
    message = InternalMessage(
        tenant_id="acme",
        log_id="123",
        source="text_upload",
        text="Call 555-0199 soon",
    )

    # Process the message
    worker.process_message(message, settings, {"dynamodb": fake_dynamo})

    # Verify both original and redacted text are stored
    stored = fake_dynamo.items[(message.tenant_id, message.log_id)]["Item"]
    assert stored["original_text"]["S"] == "Call 555-0199 soon"
    assert stored["modified_data"]["S"] == "Call [REDACTED] soon"
    
    # Verify idempotency condition was applied
    assert (
        fake_dynamo.items[(message.tenant_id, message.log_id)]["Condition"]
        == "attribute_not_exists(tenant_id) AND attribute_not_exists(log_id)"
    )


def test_process_message_is_idempotent(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that duplicate messages are handled gracefully (idempotency).
    
    Verifies that:
    - First processing succeeds and writes to DynamoDB
    - Second processing of same message is detected as duplicate
    - No duplicate entries are created in the database
    - The function returns successfully without raising errors
    
    This is crucial for handling Lambda retries and SQS redeliveries.
    """
    fake_dynamo = FakeDynamo()
    settings = type("S", (), {"dynamodb_table_name": "tenant-logs"})
    message = InternalMessage(
        tenant_id="acme",
        log_id="123",
        source="text_upload",
        text="Repeat 555-0199",
    )

    # Process the same message twice
    worker.process_message(message, settings, {"dynamodb": fake_dynamo})
    worker.process_message(message, settings, {"dynamodb": fake_dynamo})

    # Verify only one item was persisted (no duplicates)
    assert len(fake_dynamo.items) == 1


def test_handler_processes_records(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test end-to-end Lambda handler processing of SQS event.
    
    Verifies that:
    - Handler correctly extracts messages from SQS event format
    - Messages are deserialized and validated
    - Processing logic is invoked correctly
    - Results are persisted to DynamoDB
    
    This integration test ensures the handler properly orchestrates
    all components of the worker Lambda.
    """
    fake_dynamo = FakeDynamo()
    settings = type("S", (), {"aws_region": "us-east-1", "dynamodb_table_name": "tenant-logs"})
    
    # Create a message and wrap it in SQS event format
    message = InternalMessage(
        tenant_id="tenant",
        log_id="abc",
        source="json_upload",
        text="Process me 555-0199",
    )
    event = {"Records": [{"body": message.json()}]}

    # Mock configuration and client initialization
    monkeypatch.setattr(worker, "get_worker_settings", lambda: settings)
    monkeypatch.setattr(worker, "get_clients", lambda _settings: {"dynamodb": fake_dynamo})

    # Invoke the Lambda handler
    worker.handler(event, None)

    # Verify the message was successfully processed and persisted
    assert ("tenant", "abc") in fake_dynamo.items
