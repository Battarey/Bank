// Package redis реализует работу с Redis для сессий и онбординга.
package redis

import (
	"context"
	"time"

	"github.com/redis/go-redis/v9"
)

// DefaultSessionTTL — время жизни сессионного токена (30 минут).
const DefaultSessionTTL = 30 * time.Minute

// SessionsClient предоставляет операции с сессионными токенами в Redis.
type SessionsClient struct {
	rdb *redis.Client
}

// NewSessionsClient создаёт клиент Redis для сессий.
func NewSessionsClient(redisURL string) (*SessionsClient, error) {
	opts, err := redis.ParseURL(redisURL)
	if err != nil {
		return nil, err
	}
	return &SessionsClient{rdb: redis.NewClient(opts)}, nil
}

// Close закрывает соединение с Redis.
func (s *SessionsClient) Close() error {
	return s.rdb.Close()
}

// Ping проверяет доступность Redis.
func (s *SessionsClient) Ping(ctx context.Context) error {
	return s.rdb.Ping(ctx).Err()
}

func sessionTokenKey(token string) string {
	return "session:token:" + token
}

func userSessionsKey(userID string) string {
	return "session:user:" + userID
}

// SaveToken сохраняет сессионный токен в Redis.
func (s *SessionsClient) SaveToken(ctx context.Context, token, userID string, payload map[string]string, ttl time.Duration) error {
	values := map[string]interface{}{"user_id": userID}
	for k, v := range payload {
		values[k] = v
	}

	pipe := s.rdb.Pipeline()
	pipe.HSet(ctx, sessionTokenKey(token), values)
	pipe.Expire(ctx, sessionTokenKey(token), ttl)
	pipe.SAdd(ctx, userSessionsKey(userID), token)
	pipe.Expire(ctx, userSessionsKey(userID), ttl)
	_, err := pipe.Exec(ctx)
	return err
}

// LoadToken возвращает данные сессии по токену.
func (s *SessionsClient) LoadToken(ctx context.Context, token string) (map[string]string, error) {
	data, err := s.rdb.HGetAll(ctx, sessionTokenKey(token)).Result()
	if err != nil {
		return nil, err
	}
	if len(data) == 0 {
		return nil, nil
	}
	return data, nil
}

// TouchToken продлевает TTL токена и множества сессий пользователя.
func (s *SessionsClient) TouchToken(ctx context.Context, token, userID string, ttl time.Duration) error {
	pipe := s.rdb.Pipeline()
	pipe.Expire(ctx, sessionTokenKey(token), ttl)
	pipe.Expire(ctx, userSessionsKey(userID), ttl)
	_, err := pipe.Exec(ctx)
	return err
}

// UpdateTokenData обновляет поля хеша сессионного токена.
func (s *SessionsClient) UpdateTokenData(ctx context.Context, token string, data map[string]string) error {
	values := make(map[string]interface{}, len(data))
	for k, v := range data {
		values[k] = v
	}
	return s.rdb.HSet(ctx, sessionTokenKey(token), values).Err()
}

// DeleteToken удаляет токен и его привязку к пользователю.
func (s *SessionsClient) DeleteToken(ctx context.Context, token string) error {
	data, err := s.LoadToken(ctx, token)
	if err != nil || data == nil {
		return err
	}

	userID := data["user_id"]
	pipe := s.rdb.Pipeline()
	pipe.Del(ctx, sessionTokenKey(token))
	pipe.SRem(ctx, userSessionsKey(userID), token)
	_, err = pipe.Exec(ctx)
	return err
}

// RevokeAll удаляет все активные токены пользователя.
func (s *SessionsClient) RevokeAll(ctx context.Context, userID string) error {
	tokens, err := s.rdb.SMembers(ctx, userSessionsKey(userID)).Result()
	if err != nil || len(tokens) == 0 {
		return err
	}

	keys := make([]string, 0, len(tokens)+1)
	for _, t := range tokens {
		keys = append(keys, sessionTokenKey(t))
	}
	keys = append(keys, userSessionsKey(userID))
	return s.rdb.Del(ctx, keys...).Err()
}
