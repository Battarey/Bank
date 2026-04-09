// Package middleware реализует HTTP-middleware для аутентификации.
package middleware

import (
	"net/http"
	"strings"

	"github.com/labstack/echo/v4"

	redisClient "gateway_service/redis"
)

// Публичные пути, не требующие авторизации.
var publicPaths = map[string]bool{
	"/":             true,
	"/health":       true,
	"/docs":         true,
	"/docs/":        true,
	"/openapi.json": true,
	"/redoc":        true,
	"/favicon.ico":  true,
	"/api/v1/sessions":            true,
	"/api/v1/auth/unlock-codes":   true,
	"/api/v1/auth/unlock-codes/verifications": true,
}

// Префиксы публичных путей.
var publicPrefixes = []string{
	"/api/v1/onboarding",
	"/api/v1/currencies/rates",
	"/api/v1/metals/rates",
	"/docs/",
}

// Подстроки, по которым путь считается публичным.
var publicSegments = []string{}

var pinExemptPaths = map[string]bool{
	"/api/v1/auth/pins":            true,
	"/api/v1/sessions/current":     true,
	"/api/v1/sessions":             true,
}

// IsPublic определяет, является ли запрос публичным.
func IsPublic(path, method string) bool {
	if method == http.MethodOptions {
		return true
	}
	if publicPaths[path] {
		return true
	}
	for _, prefix := range publicPrefixes {
		if strings.HasPrefix(path, prefix) {
			return true
		}
	}
	for _, seg := range publicSegments {
		if strings.Contains(path, seg) {
			return true
		}
	}
	return false
}

// AuthMiddleware проверяет X-Session-Token и реализует PIN-gate.
func AuthMiddleware(sessions redisClient.SessionStore) echo.MiddlewareFunc {
	return func(next echo.HandlerFunc) echo.HandlerFunc {
		return func(c echo.Context) error {
			path := c.Request().URL.Path
			method := c.Request().Method

			if IsPublic(path, method) {
				return next(c)
			}

			token := c.Request().Header.Get("X-Session-Token")
			if token == "" {
				return c.JSON(http.StatusUnauthorized, map[string]string{
					"detail": "Отсутствует заголовок X-Session-Token.",
				})
			}

			sessionData, err := sessions.LoadToken(c.Request().Context(), token)
			if err != nil {
				return c.JSON(http.StatusInternalServerError, map[string]string{
					"detail": "Ошибка проверки сессии.",
				})
			}
			if sessionData == nil {
				return c.JSON(http.StatusUnauthorized, map[string]string{
					"detail": "Сессионный токен недействителен или истёк.",
				})
			}

			userID := sessionData["user_id"]

			// Скользящая экспирация: продлеваем TTL при каждом запросе
			_ = sessions.TouchToken(c.Request().Context(), token, userID, redisClient.DefaultSessionTTL)

			// Сохраняем user_id в контексте Echo
			c.Set("user_id", userID)

			// PIN-gate: без PIN доступны только set-pin, logout, logout-all
			hasPin := sessionData["has_pin"]
			if hasPin != "true" && !pinExemptPaths[path] {
				return c.JSON(http.StatusForbidden, map[string]string{
					"detail": "Необходимо установить PIN-код. POST /auth/set-pin",
				})
			}

			return next(c)
		}
	}
}
