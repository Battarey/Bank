package tests

import (
	"context"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"

	"github.com/labstack/echo/v4"
	"github.com/stretchr/testify/assert"

	"gateway_service/proxy"
	redisClient "gateway_service/redis"
	"gateway_service/routes"
)

func TestCustomerHandler(t *testing.T) {
	redisURL := "redis://redis_test:6379/2"
	sessions, _ := redisClient.NewSessionsClient(redisURL)
	onboarding, _ := redisClient.NewOnboardingClient(redisURL)
	if sessions == nil || onboarding == nil {
		t.Skip("Redis недоступен")
	}
	defer sessions.Close()
	defer onboarding.Close()

	ts := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		if strings.Contains(r.URL.Path, "/users/start") {
			w.WriteHeader(http.StatusCreated)
			json.NewEncoder(w).Encode(map[string]string{"user_id": "u1", "status": "started"})
		} else if strings.Contains(r.URL.Path, "/finalize") {
			w.WriteHeader(http.StatusOK)
			json.NewEncoder(w).Encode(map[string]string{"status": "ok", "message": "welcome"})
		} else {
			w.WriteHeader(http.StatusOK)
			json.NewEncoder(w).Encode(map[string]string{"status": "step_ok"})
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
		req := httptest.NewRequest(http.MethodPost, "/users/start", strings.NewReader(`{"phone":"1"}`))
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
		onboarding.SaveOnboardingToken(context.Background(), token, "u1", redisClient.DefaultOnboardingTTL)
		defer onboarding.DeleteOnboardingToken(context.Background(), token)

		steps := []struct {
			name string
			fn   func(echo.Context) error
		}{
			{"personal-data", h.SubmitPersonalData},
			{"passport", h.SubmitPassport},
			{"identifiers", h.SubmitIdentifiers},
			{"contacts", h.SubmitContacts},
			{"send-email-code", h.SendEmailCode},
			{"verify-email", h.VerifyEmail},
		}

		for _, step := range steps {
			t.Run(step.name, func(t *testing.T) {
				req := httptest.NewRequest(http.MethodPost, "/", strings.NewReader(`{"data":"test"}`))
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

	t.Run("UpdateMethods", func(t *testing.T) {
		updates := []struct {
			name string
			fn   func(echo.Context) error
		}{
			{"UpdatePersonalData", h.UpdatePersonalData},
			{"ReplacePassport", h.ReplacePassport},
			{"UpdateContacts", h.UpdateContacts},
		}

		for _, up := range updates {
			t.Run(up.name, func(t *testing.T) {
				req := httptest.NewRequest(http.MethodPost, "/", strings.NewReader(`{"data":"test"}`))
				rec := httptest.NewRecorder()
				c := e.NewContext(req, rec)
				err := up.fn(c)
				assert.NoError(t, err)
				assert.Equal(t, http.StatusOK, rec.Code)
			})
		}
	})

	t.Run("FinalizeOnboarding", func(t *testing.T) {
		token := "onb-token-finalize"
		onboarding.SaveOnboardingToken(context.Background(), token, "u1", redisClient.DefaultOnboardingTTL)

		req := httptest.NewRequest(http.MethodPost, "/users/me/account/finalize", nil)
		req.Header.Set("X-Onboarding-Token", token)
		rec := httptest.NewRecorder()
		c := e.NewContext(req, rec)
		
		err := h.FinalizeOnboarding(c)
		assert.NoError(t, err)
		assert.Equal(t, http.StatusOK, rec.Code)
		assert.Contains(t, rec.Body.String(), "session_token")
	})

	t.Run("DeleteAccount", func(t *testing.T) {
		req := httptest.NewRequest(http.MethodDelete, "/users/me", nil)
		rec := httptest.NewRecorder()
		c := e.NewContext(req, rec)
		c.Set("user_id", "u1")
		
		err := h.DeleteAccount(c)
		assert.NoError(t, err)
		assert.Equal(t, http.StatusOK, rec.Code)
	})
}
