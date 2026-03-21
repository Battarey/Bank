package routes

import (
	"fmt"
	"net/http"

	"github.com/labstack/echo/v4"

	"gateway_service/proxy"
)

// CurrencyHandler обрабатывает маршруты currency_service.
type CurrencyHandler struct {
	Proxy  *proxy.ServiceClients
	APIKey string
}

// RegisterCurrencyRoutes регистрирует маршруты валютных операций.
func (h *CurrencyHandler) RegisterCurrencyRoutes(e *echo.Echo) {
	e.GET("/currency/rates", h.GetRates)
	e.GET("/currency/rates/:base/:target", h.GetPairRate)
	e.POST("/currency/exchange", h.Exchange)
}

// GetRates godoc
func (h *CurrencyHandler) GetRates(c echo.Context) error {
	base := c.QueryParam("base")
	if base == "" {
		base = "RUB"
	}
	path := fmt.Sprintf("/rates?base=%s", base)
	return h.Proxy.ForwardRaw(c, http.MethodGet, path, nil, "currency", h.APIKey)
}

// GetPairRate godoc
func (h *CurrencyHandler) GetPairRate(c echo.Context) error {
	base := c.Param("base")
	target := c.Param("target")
	path := fmt.Sprintf("/rates/%s/%s", base, target)
	return h.Proxy.ForwardRaw(c, http.MethodGet, path, nil, "currency", h.APIKey)
}

// Exchange godoc
func (h *CurrencyHandler) Exchange(c echo.Context) error {
	body, _ := ReadBody(c)
	return h.Proxy.ForwardRaw(c, http.MethodPost, "/exchange", body, "currency", h.APIKey)
}
