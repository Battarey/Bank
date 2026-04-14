package routes

import (
	"fmt"
	"net/http"

	"github.com/labstack/echo/v4"

	"gateway_service/proxy"
	_ "gateway_service/schemas"
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
// @Summary     Котировки драгоценных металлов
// @Description Возвращает текущие банковские цены на золото (XAU), серебро (XAG), платину (XPT) и палладий (XPD).
// @Description Цены указаны за 1 грамм в выбранной валюте.
// @Tags        metals
// @Produce     json
// @Param       base query string false "Валюта цены (ISO 4217)" default(RUB)
// @Success     200 {object} schemas.MetalRatesResponse "Список актуальных котировок"
// @Failure     401 {object} schemas.UnauthorizedErrorResponse "Не авторизован"
// @Failure     404 {object} schemas.NotFoundErrorResponse "Валюта не поддерживается"
// @Failure     502 {object} schemas.BadGatewayErrorResponse "Внешний источник цен недоступен"
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
