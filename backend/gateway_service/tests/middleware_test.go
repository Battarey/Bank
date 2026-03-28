package tests

import (
	"context"
	"net/http"
	"net/http/httptest"
	"testing"

	"github.com/labstack/echo/v4"
	"github.com/stretchr/testify/assert"

	"gateway_service/middleware"
	redisClient "gateway_service/redis"
)

func TestIsPublic(t *testing.T) {
	tests := []struct {
		path   string
		method string
		want   bool
	}{
		{"/", "GET", true},
		{"/health", "GET", true},
		{"/docs/index.html", "GET", true},
		{"/users/start", "POST", true},
		{"/currency/rates", "GET", true},
		{"/auth/login", "POST", false}, // auth/login-pin is public, but not /auth/login
		{"/auth/login-pin", "POST", true},
		{"/users/me", "GET", false},
		{"/users/me/account/123", "GET", true}, // publicSegment
		{"/any", "OPTIONS", true},             // OPTIONS is always public
	}

	for _, tt := range tests {
		got := middleware.IsPublic(tt.path, tt.method)
		assert.Equal(t, tt.want, got, "path: %s, method: %s", tt.path, tt.method)
	}
}

func TestAuthMiddleware(t *testing.T) {
	redisURL := "redis://redis_test:6379/0"
	if _, err := redisClient.NewSessionsClient(redisURL); err != nil {
		redisURL = "redis://localhost:6379/0"
	}
	
	sessions, err := redisClient.NewSessionsClient(redisURL)
	if err != nil {
		t.Skip("Redis недоступен для теста AuthMiddleware")
	}
	defer sessions.Close()

	e := echo.New()
	handler := middleware.AuthMiddleware(sessions)(func(c echo.Context) error {
		return c.String(http.StatusOK, "OK")
	})

	t.Run("Public path", func(t *testing.T) {
		req := httptest.NewRequest(http.MethodGet, "/health", nil)
		rec := httptest.NewRecorder()
		c := e.NewContext(req, rec)
		
		err := handler(c)
		assert.NoError(t, err)
		assert.Equal(t, http.StatusOK, rec.Code)
	})

	t.Run("Missing token", func(t *testing.T) {
		req := httptest.NewRequest(http.MethodGet, "/users/me", nil)
		rec := httptest.NewRecorder()
		c := e.NewContext(req, rec)
		
		err := handler(c)
		assert.NoError(t, err)
		assert.Equal(t, http.StatusUnauthorized, rec.Code)
		assert.Contains(t, rec.Body.String(), "X-Session-Token")
	})

	t.Run("Invalid token", func(t *testing.T) {
		req := httptest.NewRequest(http.MethodGet, "/users/me", nil)
		req.Header.Set("X-Session-Token", "invalid-token")
		rec := httptest.NewRecorder()
		c := e.NewContext(req, rec)
		
		err := handler(c)
		assert.NoError(t, err)
		assert.Equal(t, http.StatusUnauthorized, rec.Code)
	})

	t.Run("Valid token - PIN required", func(t *testing.T) {
		token := "valid-token-no-pin"
		userID := "user-123"
		ctx := context.Background()
		sessions.SaveToken(ctx, token, userID, map[string]string{"has_pin": "false"}, redisClient.DefaultSessionTTL)
		defer sessions.DeleteToken(ctx, token)

		req := httptest.NewRequest(http.MethodGet, "/users/me", nil)
		req.Header.Set("X-Session-Token", token)
		rec := httptest.NewRecorder()
		c := e.NewContext(req, rec)
		
		err := handler(c)
		assert.NoError(t, err)
		assert.Equal(t, http.StatusForbidden, rec.Code)
		assert.Contains(t, rec.Body.String(), "PIN")
	})

	t.Run("Valid token - Success", func(t *testing.T) {
		token := "valid-token-with-pin"
		userID := "user-456"
		ctx := context.Background()
		sessions.SaveToken(ctx, token, userID, map[string]string{"has_pin": "true"}, redisClient.DefaultSessionTTL)
		defer sessions.DeleteToken(ctx, token)

		req := httptest.NewRequest(http.MethodGet, "/users/me", nil)
		req.Header.Set("X-Session-Token", token)
		rec := httptest.NewRecorder()
		c := e.NewContext(req, rec)
		
		err := handler(c)
		assert.NoError(t, err)
		assert.Equal(t, http.StatusOK, rec.Code)
		assert.Equal(t, userID, c.Get("user_id"))
	})
}
