package tests

import (
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"

	"github.com/labstack/echo/v4"
	"github.com/stretchr/testify/assert"

	"gateway_service/proxy"
	"gateway_service/routes"
)

func TestForwardAndParse(t *testing.T) {
	ts := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(map[string]interface{}{"id": "123", "status": "ok"})
	}))
	defer ts.Close()

	sc := proxy.NewServiceClients(map[string]string{
		"test": ts.URL,
	})
	defer sc.Close()

	e := echo.New()
	req := httptest.NewRequest(http.MethodGet, "/test", nil)
	rec := httptest.NewRecorder()
	c := e.NewContext(req, rec)
	c.Set("user_id", "u1")

	parsed, status, err := routes.ForwardAndParse(c, sc, "GET", "/info", nil, "test", "key")
	assert.NoError(t, err)
	assert.Equal(t, http.StatusOK, status)
	assert.Equal(t, "123", parsed["id"])
	assert.Equal(t, "ok", parsed["status"])
}

func TestForwardAndParseNonJSON(t *testing.T) {
	ts := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Write([]byte("plain text error"))
	}))
	defer ts.Close()

	sc := proxy.NewServiceClients(map[string]string{
		"test": ts.URL,
	})
	defer sc.Close()

	e := echo.New()
	req := httptest.NewRequest(http.MethodGet, "/test", nil)
	c := e.NewContext(req, httptest.NewRecorder())

	parsed, _, _ := routes.ForwardAndParse(c, sc, "GET", "/err", nil, "test", "key")
	assert.Equal(t, "plain text error", parsed["detail"])
}
