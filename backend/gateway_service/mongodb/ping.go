// Package mongodb предоставляет инструменты для работы с MongoDB в Gateway Service.
package mongodb

import (
	"context"
	"fmt"
	"time"

	"go.mongodb.org/mongo-driver/mongo"
	"go.mongodb.org/mongo-driver/mongo/options"
	"go.mongodb.org/mongo-driver/mongo/readpref"
)

// MongoStore интерфейс для проверки здоровья MongoDB.
type MongoStore interface {
	Ping(ctx context.Context) error
	Close() error
}

// Client обертка над mongo.Client для проверки работоспособности.
type Client struct {
	client *mongo.Client
}

// NewClient создает новый клиент MongoDB.
func NewClient(uri string) (*Client, error) {
	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()

	client, err := mongo.Connect(ctx, options.Client().ApplyURI(uri))
	if err != nil {
		return nil, fmt.Errorf("failed to connect to mongodb: %w", err)
	}

	return &Client{client: client}, nil
}

// Ping проверяет доступность базы данных.
func (c *Client) Ping(ctx context.Context) error {
	if c.client == nil {
		return fmt.Errorf("mongo client is not initialized")
	}
	// Используем Read Preference Primary для проверки доступности узла записи
	return c.client.Ping(ctx, readpref.Primary())
}

// Close закрывает соединение с MongoDB.
func (c *Client) Close() error {
	if c.client == nil {
		return nil
	}
	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()
	return c.client.Disconnect(ctx)
}
