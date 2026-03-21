package tests

import (
	"context"
	"testing"
	"time"

	"github.com/stretchr/testify/assert"

	redisClient "gateway_service/redis"
)

func TestOnboardingClient(t *testing.T) {
	redisURL := "redis://redis_test:6379/11"
	o, err := redisClient.NewOnboardingClient(redisURL)
	if err != nil {
		t.Skip("Redis недоступен")
	}
	defer o.Close()

	ctx := context.Background()
	token := "onb-1"
	userID := "u1"

	t.Run("SaveLoadTouchDelete", func(t *testing.T) {
		err := o.SaveOnboardingToken(ctx, token, userID, time.Minute)
		assert.NoError(t, err)

		id, err := o.LoadOnboardingToken(ctx, token)
		assert.NoError(t, err)
		assert.Equal(t, userID, id)

		err = o.TouchOnboardingToken(ctx, token, time.Hour)
		assert.NoError(t, err)

		err = o.DeleteOnboardingToken(ctx, token)
		assert.NoError(t, err)

		id, _ = o.LoadOnboardingToken(ctx, token)
		assert.Empty(t, id)
	})

	t.Run("GenerateToken", func(t *testing.T) {
		tok, err := redisClient.GenerateToken()
		assert.NoError(t, err)
		assert.NotEmpty(t, tok)
	})
}
