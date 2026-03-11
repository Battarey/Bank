package routes



import (
	"fmt"
	"net/http"

	"github.com/labstack/echo/v4"

	"gateway_service/proxy"
)

// MetalHandler обрабатывает маршруты metal_service.
type MetalHandler struct {
	Proxy  *proxy.ServiceClients
	APIKey string
}

// RegisterMetalRoutes регистрирует маршруты драгоценных металлов.
func (h *MetalHandler) RegisterMetalRoutes(e *echo.Echo) {
	e.GET("/metals/rates", h.getMetalRates)
}

// getMetalRates godoc
// @Summary     Цены на металлы
// @Description Возвращает цены на драгоценные металлы (за грамм).
// @Tags        metals
// @Produce     json
// @Param       base query string false "Базовая валюта (по умолчанию RUB)" default(RUB)
// @Success     200 {object} map[string]interface{}
// @Router      /metals/rates [get]
func (h *MetalHandler) getMetalRates(c echo.Context) error {
	base := c.QueryParam("base")
	if base == "" {
		base = "RUB"
	}
	path := fmt.Sprintf("/metals/rates?base=%s", base)
	return h.Proxy.ForwardRaw(c, http.MethodGet, path, nil, "metal", h.APIKey)
}
