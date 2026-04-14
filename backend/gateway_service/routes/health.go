package routes

import (
	"net/http"

	"github.com/labstack/echo/v4"
	"gateway_service/redis"
	"gateway_service/schemas"
)

// HealthHandler хранит зависимости для проверки здоровья системы.
type HealthHandler struct {
	Sessions   redis.SessionStore
	Onboarding redis.OnboardingStore
}

// Health godoc
// @Summary     Проверка состояния системы
// @Description Возвращает статус 'ok', если Gateway и его зависимости (Redis) доступны.
// @Tags        system
// @Produce     json
// @Success     200 {object} schemas.HealthResponse "Система работает нормально"
// @Failure     503 {object} schemas.HealthErrorResponse "Одна из зависимостей недоступна"
// @Router      /health [get]
func (h *HealthHandler) Health(c echo.Context) error {
	ctx := c.Request().Context()

	// Проверка Redis сессий
	if err := h.Sessions.Ping(ctx); err != nil {
		return c.JSON(http.StatusServiceUnavailable, schemas.HealthErrorResponse{
			Status: "error",
			Detail: "Redis (sessions) non-responsive",
		})
	}

	// Проверка Redis онбординга
	if err := h.Onboarding.Ping(ctx); err != nil {
		return c.JSON(http.StatusServiceUnavailable, schemas.HealthErrorResponse{
			Status: "error",
			Detail: "Redis (onboarding) non-responsive",
		})
	}

	return c.JSON(http.StatusOK, schemas.HealthResponse{Status: "ok"})
}
