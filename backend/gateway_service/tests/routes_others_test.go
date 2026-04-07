package tests

import (
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"

	"github.com/labstack/echo/v4"
	"github.com/stretchr/testify/assert"

	"gateway_service/proxy"
	"gateway_service/routes"
)

func TestOtherHandlers(t *testing.T) {
	ts := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusOK)
		json.NewEncoder(w).Encode(map[string]string{"status": "ok"})
	}))
	defer ts.Close()

	sc := proxy.NewServiceClients(map[string]string{
		"account":     ts.URL,
		"transaction": ts.URL,
		"currency":    ts.URL,
		"metal":       ts.URL,
	})
	defer sc.Close()

	e := echo.New()

	t.Run("AccountHandler", func(t *testing.T) {
		h := &routes.AccountHandler{Proxy: sc, APIKey: "key"}
		
		methods := []struct {
			name   string
			fn     func(echo.Context) error
			params map[string]string
		}{
			{"open", h.OpenAccount, nil},
			{"list", h.ListAccounts, nil},
			{"get", h.GetAccount, map[string]string{"account_id": "a1"}},
			{"close", h.CloseAccount, map[string]string{"account_id": "a1"}},
			{"suspend", h.SuspendAccount, map[string]string{"account_id": "a1"}},
			{"resume", h.ResumeAccount, map[string]string{"account_id": "a1"}},
		}

		for _, m := range methods {
			t.Run(m.name, func(t *testing.T) {
				req := httptest.NewRequest(http.MethodGet, "/api/v1/accounts", nil)
				rec := httptest.NewRecorder()
				c := e.NewContext(req, rec)
				for k, v := range m.params {
					c.SetParamNames(k)
					c.SetParamValues(v)
				}
				err := m.fn(c)
				assert.NoError(t, err)
				assert.Equal(t, http.StatusOK, rec.Code)
			})
		}
	})

	t.Run("TransactionHandler", func(t *testing.T) {
		h := &routes.TransactionHandler{Proxy: sc, APIKey: "key"}

		methods := []struct {
			name   string
			fn     func(echo.Context) error
			params map[string]string
		}{
			{"create", h.CreateTransaction, nil},
			{"history", h.TransactionHistory, map[string]string{"account_id": "a1"}},
		}

		for _, m := range methods {
			t.Run(m.name, func(t *testing.T) {
				req := httptest.NewRequest(http.MethodPost, "/api/v1/transactions", strings.NewReader(`{"amount":10}`))
				req.Header.Set("Content-Type", "application/json")
				rec := httptest.NewRecorder()
				c := e.NewContext(req, rec)
				for k, v := range m.params {
					c.SetParamNames(k)
					c.SetParamValues(v)
				}
				err := m.fn(c)
				assert.NoError(t, err)
				assert.Equal(t, http.StatusOK, rec.Code)
			})
		}
	})

	t.Run("CurrencyHandler", func(t *testing.T) {
		h := &routes.CurrencyHandler{Proxy: sc, APIKey: "key"}
		req := httptest.NewRequest(http.MethodGet, "/api/v1/currency/rates", nil)
		rec := httptest.NewRecorder()
		c := e.NewContext(req, rec)
		err := h.GetRates(c)
		assert.NoError(t, err)
		assert.Equal(t, http.StatusOK, rec.Code)
	})

	t.Run("MetalHandler", func(t *testing.T) {
		h := &routes.MetalHandler{Proxy: sc, APIKey: "key"}
		req := httptest.NewRequest(http.MethodGet, "/api/v1/metals/rates", nil)
		rec := httptest.NewRecorder()
		c := e.NewContext(req, rec)
		err := h.GetMetalRates(c)
		assert.NoError(t, err)
		assert.Equal(t, http.StatusOK, rec.Code)
	})
}
