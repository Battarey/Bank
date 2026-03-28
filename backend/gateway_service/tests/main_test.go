package tests

import (
	"testing"

	"github.com/stretchr/testify/assert"

	"gateway_service/app"
	"gateway_service/config"
	"gateway_service/proxy"
)

func TestSetupApp(t *testing.T) {
	cfg := &config.Config{
		CORSAllowedOrigins: []string{"*"},
		InternalAPIKey:     "test",
	}
	
	e := app.SetupApp(cfg, nil, nil, proxy.NewServiceClients(nil))
	assert.NotNil(t, e)
	
	// Проверяем наличие нескольких роутов
	routes := e.Routes()
	assert.NotEmpty(t, routes)
	
	foundHealth := false
	for _, r := range routes {
		if r.Path == "/health" {
			foundHealth = true
			break
		}
	}
	assert.True(t, foundHealth)
}
