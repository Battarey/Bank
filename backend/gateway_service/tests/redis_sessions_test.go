package tests

import (
	"context"
	"testing"
	"time"

	"github.com/stretchr/testify/assert"

	redisClient "gateway_service/redis"
)

func TestSessionsClient(t *testing.T) {
	redisURL := "redis://redis_test:6379/10"
	s, err := redisClient.NewSessionsClient(redisURL)
	if err != nil {
		t.Skip("Redis недоступен")
	}
	defer s.Close()

	ctx := context.Background()
	token := "test-token"
	userID := "u1"
	payload := map[string]string{"foo": "bar"}

	t.Run("Ping", func(t *testing.T) {
		err := s.Ping(ctx)
		assert.NoError(t, err)
	})

	t.Run("SaveAndLoad", func(t *testing.T) {
		err := s.SaveToken(ctx, token, userID, payload, time.Minute)
		assert.NoError(t, err)

		data, err := s.LoadToken(ctx, token)
		assert.NoError(t, err)
		assert.Equal(t, userID, data["user_id"])
		assert.Equal(t, "bar", data["foo"])
	})

	t.Run("Touch", func(t *testing.T) {
		err := s.TouchToken(ctx, token, userID, time.Hour)
		assert.NoError(t, err)
	})

	t.Run("Update", func(t *testing.T) {
		err := s.UpdateTokenData(ctx, token, map[string]string{"foo": "baz"})
		assert.NoError(t, err)
		data, _ := s.LoadToken(ctx, token)
		assert.Equal(t, "baz", data["foo"])
	})

	t.Run("Delete", func(t *testing.T) {
		err := s.DeleteToken(ctx, token)
		assert.NoError(t, err)
		data, _ := s.LoadToken(ctx, token)
		assert.Nil(t, data)
	})

	t.Run("RevokeAll", func(t *testing.T) {
		s.SaveToken(ctx, "t1", userID, nil, time.Minute)
		s.SaveToken(ctx, "t2", userID, nil, time.Minute)
		err := s.RevokeAll(ctx, userID)
		assert.NoError(t, err)
		d1, _ := s.LoadToken(ctx, "t1")
		assert.Nil(t, d1)
	})
}
