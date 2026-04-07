package tests

import (
	"context"
	"net/http"
	"net/http/httptest"
	"testing"
	"time"

	"github.com/labstack/echo/v4"
	"github.com/stretchr/testify/assert"

	"gateway_service/middleware"
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
		{"/users/start", "POST", false}, // old path
		{"/api/v1/onboarding", "POST", true},
		{"/api/v1/currencies/rates", "GET", true},
		{"/auth/login", "POST", false},
		{"/api/v1/auth/login-pin", "POST", true},
		{"/users/me", "GET", false},
		{"/api/v1/users/me/account/123", "GET", true},
		{"/any", "OPTIONS", true},
	}

	for _, tt := range tests {
		got := middleware.IsPublic(tt.path, tt.method)
		assert.Equal(t, tt.want, got, "path: %s, method: %s", tt.path, tt.method)
	}
}

func TestAuthMiddleware(t *testing.T) {
	// Используем мок вместо реального Redis
	sessions := NewMockSessionStore()
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
		req := httptest.NewRequest(http.MethodGet, "/api/v1/customers/me", nil)
		rec := httptest.NewRecorder()
		c := e.NewContext(req, rec)
		
		err := handler(c)
		assert.NoError(t, err)
		assert.Equal(t, http.StatusUnauthorized, rec.Code)
		assert.Contains(t, rec.Body.String(), "X-Session-Token")
	})

	t.Run("Invalid token", func(t *testing.T) {
		req := httptest.NewRequest(http.MethodGet, "/api/v1/customers/me", nil)
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
		sessions.SaveToken(ctx, token, userID, map[string]string{"has_pin": "false"}, 30*time.Minute)

		req := httptest.NewRequest(http.MethodGet, "/api/v1/customers/me", nil)
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
		sessions.SaveToken(ctx, token, userID, map[string]string{"has_pin": "true"}, 30*time.Minute)

		req := httptest.NewRequest(http.MethodGet, "/api/v1/customers/me", nil)
		req.Header.Set("X-Session-Token", token)
		rec := httptest.NewRecorder()
		c := e.NewContext(req, rec)
		
		err := handler(c)
		assert.NoError(t, err)
		assert.Equal(t, http.StatusOK, rec.Code)
		assert.Equal(t, userID, c.Get("user_id"))
	})
}
