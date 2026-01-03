package main

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"log"
	"math/rand"
	"regexp"
	"time"

	"github.com/aws/aws-lambda-go/events"
	"github.com/aws/aws-lambda-go/lambda"
	"github.com/aws/aws-sdk-go-v2/service/dynamodb"
	"github.com/aws/aws-sdk-go-v2/service/dynamodb/types"

	"memory-machine/internal/config"
	"memory-machine/internal/models"
)

var phonePattern = regexp.MustCompile(`\b\d{3}-\d{4}\b`)

func main() {
	rand.Seed(time.Now().UnixNano())
	lambda.Start(handleSQSEvent)
}

func handleSQSEvent(ctx context.Context, event events.SQSEvent) error {
	settings, err := config.Load(ctx)
	if err != nil {
		log.Printf("configuration error: %v", err)
		return err
	}
	db := dynamodb.NewFromConfig(settings.AWSConfig)

	for _, record := range event.Records {
		if err := processRecord(ctx, db, settings, record); err != nil {
			return err
		}
	}
	return nil
}

func processRecord(ctx context.Context, db *dynamodb.Client, settings config.Settings, record events.SQSMessage) error {
	var message models.InternalMessage
	if err := json.Unmarshal([]byte(record.Body), &message); err != nil {
		return fmt.Errorf("invalid message body: %w", err)
	}

	// Simulate crash with 5% probability for resilience testing.
	if rand.Float64() < 0.05 {
		return errors.New("simulated worker crash")
	}

	// Simulate heavy processing proportional to payload size.
	sleepDuration := time.Duration(len(message.Text)) * 50 * time.Millisecond
	time.Sleep(sleepDuration)

	redacted := phonePattern.ReplaceAllString(message.Text, "[REDACTED]")
	processedAt := time.Now().UTC().Format(time.RFC3339)

	item := map[string]types.AttributeValue{
		"tenant_id":     &types.AttributeValueMemberS{Value: message.TenantID},
		"log_id":        &types.AttributeValueMemberS{Value: message.LogID},
		"source":        &types.AttributeValueMemberS{Value: message.Source},
		"original_text": &types.AttributeValueMemberS{Value: message.Text},
		"modified_data": &types.AttributeValueMemberS{Value: redacted},
		"processed_at":  &types.AttributeValueMemberS{Value: processedAt},
	}

	_, err := db.PutItem(ctx, &dynamodb.PutItemInput{
		TableName:           stringPtr(settings.DynamoDBTableName),
		Item:                item,
		ConditionExpression: stringPtr("attribute_not_exists(tenant_id) AND attribute_not_exists(log_id)"),
	})
	if err != nil {
		var cfe *types.ConditionalCheckFailedException
		if errors.As(err, &cfe) {
			log.Printf("duplicate detected tenant_id=%s log_id=%s", message.TenantID, message.LogID)
			return nil
		}
		return fmt.Errorf("dynamodb put error: %w", err)
	}

	log.Printf("persisted tenant_id=%s log_id=%s processed_at=%s", message.TenantID, message.LogID, processedAt)
	return nil
}

func stringPtr(s string) *string {
	return &s
}

