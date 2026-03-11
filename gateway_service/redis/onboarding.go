package redis

import (
	"context"
	"crypto/rand"
	"encoding/base64"
	"time"

	"github.com/redis/go-redis/v9"
)

// DefaultOnboardingTTL — время жизни onboarding-токена (15 минут).
const DefaultOnboardingTTL = 15 * time.Minute

// OnboardingClient предоставляет операции с onboarding-токенами в Redis.
type OnboardingClient struct {
	rdb *redis.Client
}

// NewOnboardingClient создаёт клиент Redis для онбординга.
func NewOnboardingClient(redisURL string) (*OnboardingClient, error) {
	opts, err := redis.ParseURL(redisURL)
	if err != nil {
		return nil, err
	}
	return &OnboardingClient{rdb: redis.NewClient(opts)}, nil
}

// Close закрывает соединение с Redis.
func (o *OnboardingClient) Close() error {
	return o.rdb.Close()
}

func onboardingTokenKey(token string) string {
	return "onboarding:token:" + token
}

// GenerateToken генерирует случайный URL-safe токен (аналог secrets.token_urlsafe(32)).
func GenerateToken() (string, error) {
	b := make([]byte, 32)
	if _, err := rand.Read(b); err != nil {
		return "", err
	}
	return base64.RawURLEncoding.EncodeToString(b), nil
}

// SaveOnboardingToken сохраняет onboarding-токен → userID в Redis.
func (o *OnboardingClient) SaveOnboardingToken(ctx context.Context, token, userID string, ttl time.Duration) error {
	return o.rdb.Set(ctx, onboardingTokenKey(token), userID, ttl).Err()
}

// LoadOnboardingToken возвращает userID по onboarding-токену.
// Возвращает пустую строку, если токен не найден или истёк.
func (o *OnboardingClient) LoadOnboardingToken(ctx context.Context, token string) (string, error) {
	val, err := o.rdb.Get(ctx, onboardingTokenKey(token)).Result()
	if err == redis.Nil {
		return "", nil
	}
	return val, err
}

// TouchOnboardingToken продлевает TTL onboarding-токена (скользящая экспирация).
func (o *OnboardingClient) TouchOnboardingToken(ctx context.Context, token string, ttl time.Duration) error {
	return o.rdb.Expire(ctx, onboardingTokenKey(token), ttl).Err()
}

// DeleteOnboardingToken удаляет onboarding-токен.
func (o *OnboardingClient) DeleteOnboardingToken(ctx context.Context, token string) error {
	return o.rdb.Del(ctx, onboardingTokenKey(token)).Err()
}
