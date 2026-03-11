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
	"/auth/login-pin":      true,
	"/auth/request-unlock": true,
	"/auth/unlock":         true,
}

// Префиксы публичных путей.
var publicPrefixes = []string{
	"/users/start",
	"/currency/rates",
	"/metals/rates",
	"/docs/",
}

// Подстроки, по которым путь считается публичным (шаги онбординга).
var publicSegments = []string{
	"/users/me/account/",
}

// Пути, доступные авторизованным пользователям без PIN.
var pinExemptPaths = map[string]bool{
	"/auth/set-pin":    true,
	"/auth/logout":     true,
	"/auth/logout-all": true,
}

// isPublic определяет, является ли запрос публичным.
func isPublic(path, method string) bool {
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
func AuthMiddleware(sessions *redisClient.SessionsClient) echo.MiddlewareFunc {
	return func(next echo.HandlerFunc) echo.HandlerFunc {
		return func(c echo.Context) error {
			path := c.Request().URL.Path
			method := c.Request().Method

			if isPublic(path, method) {
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
