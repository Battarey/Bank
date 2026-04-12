package routes

import (
	"net/http"

	"github.com/labstack/echo/v4"
	"gateway_service/schemas"
)

// Health godoc
// @Summary     Проверка состояния системы
// @Description Возвращает статус 'ok', если Gateway запущен и готов принимать запросы.
// @Tags        system
// @Produce     json
// @Success     200 {object} schemas.HealthResponse "Система работает нормально"
// @Router      /health [get]
func Health(c echo.Context) error {
	return c.JSON(http.StatusOK, schemas.HealthResponse{Status: "ok"})
}
