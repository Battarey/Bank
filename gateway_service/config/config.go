// Package config отвечает за загрузку конфигурации из переменных окружения.
package config

import (
	"os"
	"strings"
)

// Config хранит настройки gateway_service.
type Config struct {
	// URL-ы внутренних сервисов
	CustomerServiceURL    string
	AuthServiceURL        string
	AccountServiceURL     string
	TransactionServiceURL string
	CurrencyServiceURL    string
	MetalServiceURL       string

	// Redis
	RedisSessionsURL    string
	RedisOnboardingURL  string

	// Безопасность
	InternalAPIKey     string
	CORSAllowedOrigins []string

	// Сервер
	Port string
}

// Load загружает конфигурацию из переменных окружения.
func Load() *Config {
	return &Config{
		CustomerServiceURL:    getEnv("CUSTOMER_SERVICE_URL", "http://customer_service:8000"),
		AuthServiceURL:        getEnv("AUTH_SERVICE_URL", "http://auth_service:8000"),
		AccountServiceURL:     getEnv("ACCOUNT_SERVICE_URL", "http://account_service:8000"),
		TransactionServiceURL: getEnv("TRANSACTION_SERVICE_URL", "http://transaction_service:8000"),
		CurrencyServiceURL:    getEnv("CURRENCY_SERVICE_URL", "http://currency_service:8000"),
		MetalServiceURL:       getEnv("METAL_SERVICE_URL", "http://metal_service:8000"),

		RedisSessionsURL:   getEnv("REDIS_SESSIONS_URL", "redis://redis_sessions:6379/0"),
		RedisOnboardingURL: getEnv("REDIS_ONBOARDING_URL", "redis://redis_onboarding:6379/0"),

		InternalAPIKey:     getEnv("INTERNAL_API_KEY", ""),
		CORSAllowedOrigins: parseCORSOrigins(getEnv("CORS_ALLOWED_ORIGINS", "")),

		Port: getEnv("GATEWAY_PORT", "8000"),
	}
}

// getEnv возвращает значение переменной окружения или fallback.
func getEnv(key, fallback string) string {
	if val := os.Getenv(key); val != "" {
		return val
	}
	return fallback
}

// parseCORSOrigins разбивает строку origins через запятую.
func parseCORSOrigins(raw string) []string {
	if raw == "" {
		return []string{}
	}
	parts := strings.Split(raw, ",")
	origins := make([]string, 0, len(parts))
	for _, p := range parts {
		if trimmed := strings.TrimSpace(p); trimmed != "" {
			origins = append(origins, trimmed)
		}
	}
	return origins
}
