package tests

import (
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"

	"github.com/labstack/echo/v4"
	"github.com/stretchr/testify/assert"

	"gateway_service/proxy"
)

func TestForwardRequest(t *testing.T) {
	// Создаем тестовый сервер для имитации внутреннего сервиса
	ts := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		assert.Equal(t, "application/json", r.Header.Get("Content-Type"))
		assert.Equal(t, "test-api-key", r.Header.Get("X-Internal-Key"))
		assert.Equal(t, "test-user-id", r.Header.Get("X-User-ID"))

		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusOK)
		json.NewEncoder(w).Encode(map[string]string{"result": "success"})
	}))
	defer ts.Close()

	sc := proxy.NewServiceClients(map[string]string{
		"test": ts.URL,
	})
	defer sc.Close()

	e := echo.New()
	req := httptest.NewRequest(http.MethodPost, "/proxy", nil)
	rec := httptest.NewRecorder()
	c := e.NewContext(req, rec)
	c.Set("user_id", "test-user-id")

	err := sc.ForwardRequest(c, http.MethodPost, "/internal", map[string]string{"foo": "bar"}, "test", "test-api-key")
	assert.NoError(t, err)
	assert.Equal(t, http.StatusOK, rec.Code)

	var resp map[string]string
	json.Unmarshal(rec.Body.Bytes(), &resp)
	assert.Equal(t, "success", resp["result"])
}

func TestForwardRaw(t *testing.T) {
	ts := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusCreated)
		w.Write([]byte("raw-ok"))
	}))
	defer ts.Close()

	sc := proxy.NewServiceClients(map[string]string{
		"test": ts.URL,
	})
	defer sc.Close()

	e := echo.New()
	req := httptest.NewRequest(http.MethodPut, "/proxy", nil)
	rec := httptest.NewRecorder()
	c := e.NewContext(req, rec)

	err := sc.ForwardRaw(c, http.MethodPut, "/raw", []byte(`{"a":1}`), "test", "key")
	assert.NoError(t, err)
	assert.Equal(t, http.StatusCreated, rec.Code)
	assert.Equal(t, "raw-ok", rec.Body.String())
}

func TestForwardUnknownService(t *testing.T) {
	sc := proxy.NewServiceClients(map[string]string{})
	e := echo.New()
	req := httptest.NewRequest(http.MethodGet, "/", nil)
	rec := httptest.NewRecorder()
	c := e.NewContext(req, rec)

	err := sc.ForwardRequest(c, "GET", "/", nil, "unknown", "key")
	assert.Error(t, err)
	
	he, ok := err.(*echo.HTTPError)
	assert.True(t, ok)
	assert.Equal(t, http.StatusInternalServerError, he.Code)
}

func TestForwardCreateRequestError(t *testing.T) {
	ts := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {}))
	defer ts.Close()
	
	sc := proxy.NewServiceClients(map[string]string{
		"test": ts.URL,
	})
	defer sc.Close()

	e := echo.New()
	req := httptest.NewRequest(http.MethodGet, "/", nil)
	rec := httptest.NewRecorder()
	c := e.NewContext(req, rec)

	// Некорректный метод вызовет ошибку создания HTTP-запроса
	err := sc.ForwardRaw(c, " INVALID METHOD ", "/test", nil, "test", "key")
	assert.Error(t, err)
	
	he, ok := err.(*echo.HTTPError)
	assert.True(t, ok)
	assert.Equal(t, http.StatusInternalServerError, he.Code)
}

func TestForwardNetworkError(t *testing.T) {
	badSc := proxy.NewServiceClients(map[string]string{
		"bad": "http://invalid-dns-name-xyz.local",
	})
	defer badSc.Close()

	e := echo.New()
	req := httptest.NewRequest(http.MethodGet, "/test", nil)
	rec := httptest.NewRecorder()
	c := e.NewContext(req, rec)

	err := badSc.ForwardRaw(c, http.MethodGet, "/test", nil, "bad", "key")
	assert.Error(t, err)
	
	he, ok := err.(*echo.HTTPError)
	assert.True(t, ok)
	assert.Equal(t, http.StatusBadGateway, he.Code)
}
