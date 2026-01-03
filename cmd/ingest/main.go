package main

import (
	"context"
	"encoding/base64"
	"encoding/json"
	"log"
	"net/http"
	"strings"

	"github.com/aws/aws-lambda-go/events"
	"github.com/aws/aws-lambda-go/lambda"
	"github.com/aws/aws-sdk-go-v2/service/sqs"
	"github.com/google/uuid"

	"memory-machine/internal/config"
	"memory-machine/internal/models"
)

func main() {
	lambda.Start(handleRequest)
}

func handleRequest(ctx context.Context, req events.APIGatewayV2HTTPRequest) (events.APIGatewayV2HTTPResponse, error) {
	settings, err := config.Load(ctx)
	if err != nil {
		log.Printf("configuration error: %v", err)
		return errorResponse(http.StatusInternalServerError, "internal configuration error"), nil
	}

	body := req.Body
	if req.IsBase64Encoded {
		decoded, decodeErr := base64.StdEncoding.DecodeString(req.Body)
		if decodeErr != nil {
			return errorResponse(http.StatusBadRequest, "invalid base64 body"), nil
		}
		body = string(decoded)
	}

	contentType := strings.ToLower(strings.TrimSpace(strings.Split(req.Headers["content-type"], ";")[0]))

	var message models.InternalMessage
	switch contentType {
	case "application/json":
		var payload models.JSONIngestRequest
		if err := json.Unmarshal([]byte(body), &payload); err != nil {
			return errorResponse(http.StatusBadRequest, "invalid JSON payload"), nil
		}
		if payload.TenantID == "" || payload.Text == "" {
			return errorResponse(http.StatusBadRequest, "tenant_id and text are required"), nil
		}
		logID := payload.LogID
		if logID == "" {
			logID = uuid.NewString()
		}
		message = models.NewInternalMessage(payload.TenantID, logID, "json_upload", payload.Text)
	case "text/plain":
		tenant := req.Headers["x-tenant-id"]
		if tenant == "" {
			return errorResponse(http.StatusBadRequest, "missing X-Tenant-ID header"), nil
		}
		message = models.NewInternalMessage(tenant, uuid.NewString(), "text_upload", body)
	default:
		return errorResponse(http.StatusBadRequest, "unsupported Content-Type. Use application/json or text/plain."), nil
	}

	client := sqs.NewFromConfig(settings.AWSConfig)
	messageBody, _ := json.Marshal(message)
	_, err = client.SendMessage(ctx, &sqs.SendMessageInput{
		QueueUrl:    &settings.SQSQueueURL,
		MessageBody: stringPtr(string(messageBody)),
	})
	if err != nil {
		log.Printf("failed to enqueue message: %v", err)
		return errorResponse(http.StatusInternalServerError, "failed to enqueue message"), nil
	}

	resp := models.EnqueueResponse{
		Status:   "enqueued",
		TenantID: message.TenantID,
		LogID:    message.LogID,
	}
	payload, _ := json.Marshal(resp)

	return events.APIGatewayV2HTTPResponse{
		StatusCode: http.StatusAccepted,
		Body:       string(payload),
		Headers: map[string]string{
			"content-type": "application/json",
		},
	}, nil
}

func errorResponse(code int, msg string) events.APIGatewayV2HTTPResponse {
	body, _ := json.Marshal(map[string]string{"error": msg})
	return events.APIGatewayV2HTTPResponse{
		StatusCode: code,
		Body:       string(body),
		Headers: map[string]string{
			"content-type": "application/json",
		},
	}
}

func stringPtr(s string) *string {
	return &s
}

