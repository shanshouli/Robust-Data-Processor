package config

import (
	"context"
	"fmt"
	"os"

	"github.com/aws/aws-sdk-go-v2/aws"
	"github.com/aws/aws-sdk-go-v2/config"
)

// Settings holds resolved configuration and shared AWS config.
type Settings struct {
	AWSConfig         aws.Config
	SQSQueueURL       string
	DynamoDBTableName string
}

// Load reads environment variables and AWS configuration.
func Load(ctx context.Context) (Settings, error) {
	awsCfg, err := config.LoadDefaultConfig(ctx)
	if err != nil {
		return Settings{}, fmt.Errorf("load AWS config: %w", err)
	}

	sqsURL := os.Getenv("SQS_QUEUE_URL")
	if sqsURL == "" {
		return Settings{}, fmt.Errorf("missing SQS_QUEUE_URL")
	}

	tableName := os.Getenv("DYNAMODB_TABLE_NAME")
	if tableName == "" {
		return Settings{}, fmt.Errorf("missing DYNAMODB_TABLE_NAME")
	}

	return Settings{
		AWSConfig:         awsCfg,
		SQSQueueURL:       sqsURL,
		DynamoDBTableName: tableName,
	}, nil
}

