package routes

import (
	"fmt"
	"net/http"

	"github.com/labstack/echo/v4"

	"gateway_service/proxy"
)

// MetalHandler обрабатывает маршруты котировок драгоценных металлов.
type MetalHandler struct {
	Proxy  *proxy.ServiceClients
	APIKey string
}

// RegisterMetalRoutes регистрирует маршруты металлов в API Gateway.
func (h *MetalHandler) RegisterMetalRoutes(e *echo.Echo) {
	v1 := e.Group("/api/v1/metals")

	v1.GET("/rates", h.GetMetalRates) // Получение актуальных цен на золото, серебро и т.д.
}

// GetMetalRates godoc
// @Summary     Котировки металлов
// @Description Возвращает текущие банковские цены на драгоценные металлы (за грамм).
// @Tags        metals
// @Produce     json
// @Param       base query string false "Валюта цены (RUB по умолчанию)"
// @Success     200 {object} map[string]interface{}
// @Router      /api/v1/metals/rates [get]
func (h *MetalHandler) GetMetalRates(c echo.Context) error {
	base := c.QueryParam("base")
	if base == "" {
		base = "RUB"
	}
	// Внутренний путь остается /metals/rates (см. metal_service/main.py)
	path := fmt.Sprintf("/metals/rates?base=%s", base)
	return h.Proxy.ForwardRaw(c, http.MethodGet, path, nil, "metal", h.APIKey)
}
