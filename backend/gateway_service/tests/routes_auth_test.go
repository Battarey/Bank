package tests

import (
	"context"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
	"time"

	"github.com/labstack/echo/v4"
	"github.com/stretchr/testify/assert"

	"gateway_service/proxy"
	"gateway_service/routes"
)

func TestAuthHandler(t *testing.T) {
	// Используем мок вместо реального Redis
	sessions := NewMockSessionStore()
	defer sessions.Close()

	// Тестовый сервер для имитации auth_service
	ts := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		if r.URL.Path == "/sessions" && r.Method == http.MethodPost {
			w.WriteHeader(http.StatusOK)
			json.NewEncoder(w).Encode(map[string]string{"session_token": "ok"})
		} else if r.URL.Path == "/pins" && r.Method == http.MethodPut {
			w.WriteHeader(http.StatusOK)
			json.NewEncoder(w).Encode(map[string]string{"status": "pin_set"})
		} else {
			w.WriteHeader(http.StatusOK)
			json.NewEncoder(w).Encode(map[string]string{"status": "ok"})
		}
	}))
	defer ts.Close()

	sc := proxy.NewServiceClients(map[string]string{
		"auth": ts.URL,
	})
	defer sc.Close()

	h := &routes.AuthHandler{
		Proxy:    sc,
		Sessions: sessions,
		APIKey:   "test-key",
	}

	e := echo.New()
	h.RegisterAuthRoutes(e)

	t.Run("Login", func(t *testing.T) {
		req := httptest.NewRequest(http.MethodPost, "/api/v1/sessions", strings.NewReader(`{"phone":"1","pin":"1"}`))
		req.Header.Set("Content-Type", "application/json")
		rec := httptest.NewRecorder()
		c := e.NewContext(req, rec)
		
		err := h.Login(c)
		assert.NoError(t, err)
		assert.Equal(t, http.StatusOK, rec.Code)
	})

	t.Run("SetPin", func(t *testing.T) {
		token := "test-token"
		sessions.SaveToken(context.Background(), token, "u1", map[string]string{"has_pin": "false"}, 30*time.Minute)

		req := httptest.NewRequest(http.MethodPut, "/api/v1/auth/pins", strings.NewReader(`{"pin":"1234"}`))
		req.Header.Set("Content-Type", "application/json")
		req.Header.Set("X-Session-Token", token)
		rec := httptest.NewRecorder()
		c := e.NewContext(req, rec)
		c.Set("user_id", "u1")

		err := h.SetPin(c)
		assert.NoError(t, err)
		assert.Equal(t, http.StatusOK, rec.Code)

		// Проверяем, что в Mock-хранилище обновилось has_pin
		data, _ := sessions.LoadToken(context.Background(), token)
		assert.Equal(t, "true", data["has_pin"])
	})

	t.Run("Logout", func(t *testing.T) {
		req := httptest.NewRequest(http.MethodDelete, "/api/v1/sessions/current", nil)
		rec := httptest.NewRecorder()
		c := e.NewContext(req, rec)
		
		err := h.Logout(c)
		assert.NoError(t, err)
		assert.Equal(t, http.StatusOK, rec.Code)
	})

	t.Run("RequestUnlock", func(t *testing.T) {
		req := httptest.NewRequest(http.MethodPost, "/api/v1/auth/unlock-codes", strings.NewReader(`{"email":"a@b.c"}`))
		rec := httptest.NewRecorder()
		c := e.NewContext(req, rec)
		err := h.RequestUnlock(c)
		assert.NoError(t, err)
		assert.Equal(t, http.StatusOK, rec.Code)
	})

	t.Run("LogoutAll", func(t *testing.T) {
		req := httptest.NewRequest(http.MethodDelete, "/api/v1/sessions", nil)
		rec := httptest.NewRecorder()
		c := e.NewContext(req, rec)
		err := h.LogoutAll(c)
		assert.NoError(t, err)
		assert.Equal(t, http.StatusOK, rec.Code)
	})

	t.Run("SelfBlock", func(t *testing.T) {
		req := httptest.NewRequest(http.MethodPost, "/api/v1/auth/self-block", nil)
		rec := httptest.NewRecorder()
		c := e.NewContext(req, rec)
		err := h.SelfBlock(c)
		assert.NoError(t, err)
		assert.Equal(t, http.StatusOK, rec.Code)
	})
}
