package tests

import (
	"os"
	"testing"

	"github.com/stretchr/testify/assert"

	"gateway_service/config"
)

func TestLoad(t *testing.T) {
	os.Setenv("GATEWAY_PORT", "9999")
	os.Setenv("INTERNAL_API_KEY", "secret")
	os.Setenv("CORS_ALLOWED_ORIGINS", "http://a.com,http://b.com")

	cfg := config.Load()
	assert.Equal(t, "9999", cfg.Port)
	assert.Equal(t, "secret", cfg.InternalAPIKey)
	assert.Contains(t, cfg.CORSAllowedOrigins, "http://a.com")
	assert.Contains(t, cfg.CORSAllowedOrigins, "http://b.com")
}
