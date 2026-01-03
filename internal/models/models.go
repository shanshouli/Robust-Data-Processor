package models

import (
	"time"
)

// JSONIngestRequest matches the JSON ingest payload.
type JSONIngestRequest struct {
	TenantID string `json:"tenant_id"`
	Text     string `json:"text"`
	LogID    string `json:"log_id,omitempty"`
}

// InternalMessage is the normalized structure sent to SQS.
type InternalMessage struct {
	TenantID   string    `json:"tenant_id"`
	LogID      string    `json:"log_id"`
	Source     string    `json:"source"`
	Text       string    `json:"text"`
	ReceivedAt time.Time `json:"received_at"`
}

// EnqueueResponse is returned after enqueueing a message.
type EnqueueResponse struct {
	Status   string `json:"status"`
	TenantID string `json:"tenant_id"`
	LogID    string `json:"log_id"`
}

// NewInternalMessage builds a normalized message with a UTC timestamp.
func NewInternalMessage(tenantID, logID, source, text string) InternalMessage {
	return InternalMessage{
		TenantID:   tenantID,
		LogID:      logID,
		Source:     source,
		Text:       text,
		ReceivedAt: time.Now().UTC(),
	}
}

