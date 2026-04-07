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

func TestCustomerHandler(t *testing.T) {
	// Используем моки
	sessions := NewMockSessionStore()
	onboarding := NewMockOnboardingStore()
	defer sessions.Close()
	defer onboarding.Close()

	ts := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		if strings.Contains(r.URL.Path, "/onboarding") && r.Method == http.MethodPost {
			w.WriteHeader(http.StatusCreated)
			json.NewEncoder(w).Encode(map[string]string{"client_id": "u1", "status": "started"})
		} else {
			w.WriteHeader(http.StatusOK)
			json.NewEncoder(w).Encode(map[string]string{"status": "ok"})
		}
	}))
	defer ts.Close()

	sc := proxy.NewServiceClients(map[string]string{
		"customer": ts.URL,
	})
	defer sc.Close()

	h := &routes.CustomerHandler{
		Proxy:      sc,
		Sessions:   sessions,
		Onboarding: onboarding,
		APIKey:     "key",
	}

	e := echo.New()
	h.RegisterCustomerRoutes(e)

	t.Run("StartOnboarding", func(t *testing.T) {
		req := httptest.NewRequest(http.MethodPost, "/api/v1/onboarding", strings.NewReader(`{"phone":"1"}`))
		req.Header.Set("Content-Type", "application/json")
		rec := httptest.NewRecorder()
		c := e.NewContext(req, rec)
		
		err := h.StartOnboarding(c)
		assert.NoError(t, err)
		assert.Equal(t, http.StatusCreated, rec.Code)
		assert.Contains(t, rec.Body.String(), "onboarding_token")
	})

	t.Run("OnboardingStep", func(t *testing.T) {
		token := "onb-token"
		onboarding.SaveOnboardingToken(context.Background(), token, "u1", 15*time.Minute)
		defer onboarding.DeleteOnboardingToken(context.Background(), token)

		steps := []struct {
			name string
			fn   func(echo.Context) error
		}{
			{"personal-data", h.SubmitPersonalData},
			{"passport", h.SubmitPassport},
			{"identifiers", h.SubmitIdentifiers},
			{"contacts", h.SubmitContacts},
		}

		for _, step := range steps {
			t.Run(step.name, func(t *testing.T) {
				req := httptest.NewRequest(http.MethodPost, "/api/v1/onboarding/"+step.name, strings.NewReader(`{"data":"test"}`))
				req.Header.Set("X-Onboarding-Token", token)
				req.Header.Set("Content-Type", "application/json")
				rec := httptest.NewRecorder()
				c := e.NewContext(req, rec)
				err := step.fn(c)
				assert.NoError(t, err)
				assert.Equal(t, http.StatusOK, rec.Code)
			})
		}
	})

	t.Run("CompleteOnboarding", func(t *testing.T) {
		token := "onb-token-finalize"
		onboarding.SaveOnboardingToken(context.Background(), token, "u1", 15*time.Minute)

		req := httptest.NewRequest(http.MethodPost, "/api/v1/onboarding/completion", nil)
		req.Header.Set("X-Onboarding-Token", token)
		rec := httptest.NewRecorder()
		c := e.NewContext(req, rec)
		
		err := h.CompleteOnboarding(c)
		assert.NoError(t, err)
		assert.Equal(t, http.StatusOK, rec.Code)
	})

	t.Run("DeleteAccount", func(t *testing.T) {
		req := httptest.NewRequest(http.MethodDelete, "/api/v1/customers/me", nil)
		rec := httptest.NewRecorder()
		c := e.NewContext(req, rec)
		c.Set("user_id", "u1")
		
		err := h.DeleteAccount(c)
		assert.NoError(t, err)
		assert.Equal(t, http.StatusOK, rec.Code)
	})
}
