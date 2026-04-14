// Package config отвечает за загрузку конфигурации из переменных окружения.
package config

import (
	"log"
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
		CustomerServiceURL:    getEnvRequired("CUSTOMER_SERVICE_URL"),
		AuthServiceURL:        getEnvRequired("AUTH_SERVICE_URL"),
		AccountServiceURL:     getEnvRequired("ACCOUNT_SERVICE_URL"),
		TransactionServiceURL: getEnvRequired("TRANSACTION_SERVICE_URL"),
		CurrencyServiceURL:    getEnvRequired("CURRENCY_SERVICE_URL"),
		MetalServiceURL:       getEnvRequired("METAL_SERVICE_URL"),

		RedisSessionsURL:   getEnvRequired("REDIS_SESSIONS_URL"),
		RedisOnboardingURL: getEnvRequired("REDIS_ONBOARDING_URL"),

		InternalAPIKey:     getEnvRequired("INTERNAL_API_KEY"),
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

// getEnvRequired возвращает значение или паникует, если переменная не задана.
func getEnvRequired(key string) string {
	val := os.Getenv(key)
	if val == "" {
		log.Fatalf("Критическая ошибка: переменная окружения %s обязательна, но не задана", key)
	}
	return val
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
