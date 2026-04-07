package tests

import (
	"net/http"
	"net/http/httptest"
	"testing"

	"github.com/labstack/echo/v4"
	"github.com/stretchr/testify/assert"

	"gateway_service/app"
	"gateway_service/config"
	"gateway_service/proxy"
)

func TestGlobalCORS(t *testing.T) {
	cfg := &config.Config{
		CORSAllowedOrigins: []string{"http://example.com"},
	}
	// Мы можем передать nil для redis-клиентов, если этот тест их не вызывает
	e := app.SetupApp(cfg, nil, nil, nil)

	req := httptest.NewRequest(http.MethodOptions, "/health", nil)
	req.Header.Set(echo.HeaderOrigin, "http://example.com")
	req.Header.Set(echo.HeaderAccessControlRequestMethod, http.MethodGet)
	rec := httptest.NewRecorder()

	e.ServeHTTP(rec, req)

	assert.Equal(t, http.StatusNoContent, rec.Code)
	assert.Equal(t, "http://example.com", rec.Header().Get(echo.HeaderAccessControlAllowOrigin))
}

func TestHeaderSpoofingProtection(t *testing.T) {
	// 1. Создаем бэкенд, который проверит, что получил от Gateway
	ts := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		// Бэкенд НЕ должен получить X-User-ID, который прислал клиент напрямую на публичный путь
		userID := r.Header.Get("X-User-ID")
		assert.Empty(t, userID, "X-User-ID must be empty for public routes even if sent by client")
		
		assert.Equal(t, "gateway-internal-key", r.Header.Get("X-Internal-Key"))
		
		w.WriteHeader(http.StatusOK)
		w.Write([]byte(`{"status":"ok"}`))
	}))
	defer ts.Close()

	cfg := &config.Config{
		InternalAPIKey: "gateway-internal-key",
	}
	// Мапим "валюты" на наш тестовый сервер
	services := proxy.NewServiceClients(map[string]string{
		"currency": ts.URL,
	})
	defer services.Close()

	e := app.SetupApp(cfg, nil, nil, services)

	// Делаем запрос на публичный эндпоинт и пытаемся подменить X-User-ID
	req := httptest.NewRequest(http.MethodGet, "/api/v1/currencies/rates", nil)
	req.Header.Set("X-User-ID", "spoofed-user-id")
	rec := httptest.NewRecorder()

	e.ServeHTTP(rec, req)
	assert.Equal(t, http.StatusOK, rec.Code)
}

func TestPanicRecovery(t *testing.T) {
	e := app.SetupApp(&config.Config{}, nil, nil, nil)
	
	// Используем путь, который считается публичным в AuthMiddleware
	e.GET("/api/v1/onboarding/panic", func(c echo.Context) error {
		panic("intentional panic for testing recover middleware")
	})

	req := httptest.NewRequest(http.MethodGet, "/api/v1/onboarding/panic", nil)
	rec := httptest.NewRecorder()

	// Middleware Recover должен поймать панику и вернуть 500
	assert.NotPanics(t, func() {
		e.ServeHTTP(rec, req)
	})
	assert.Equal(t, http.StatusInternalServerError, rec.Code)
}

func TestFullInternalFlow(t *testing.T) {
	// Проверка того, что для авторизованных запросов X-User-ID берется из Echo Context (из сессии)
	ts := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		assert.Equal(t, "authorized-user-id", r.Header.Get("X-User-ID"))
		w.WriteHeader(http.StatusOK)
	}))
	defer ts.Close()

	sc := proxy.NewServiceClients(map[string]string{"account": ts.URL})
	e := echo.New()
	
	// Имитируем состояние после AuthMiddleware (user_id в контексте)
	req := httptest.NewRequest(http.MethodGet, "/accounts/me", nil)
	rec := httptest.NewRecorder()
	c := e.NewContext(req, rec)
	c.Set("user_id", "authorized-user-id")

	// Вызываем Forward через прокси напрямую (имитация логики хендлера)
	err := sc.ForwardRequest(c, "GET", "/", nil, "account", "secret")
	assert.NoError(t, err)
	assert.Equal(t, http.StatusOK, rec.Code)
}
