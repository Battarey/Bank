package routes

import (
	"fmt"
	"net/http"

	"github.com/labstack/echo/v4"

	"gateway_service/proxy"
)

// CurrencyHandler обрабатывает маршруты валютных котировок и обмена.
type CurrencyHandler struct {
	Proxy  *proxy.ServiceClients
	APIKey string
}

// RegisterCurrencyRoutes регистрирует маршруты валютных операций в API Gateway.
func (h *CurrencyHandler) RegisterCurrencyRoutes(e *echo.Echo) {
	v1 := e.Group("/api/v1/currencies")

	v1.GET("/rates", h.GetRates)                        // Список всех курсов
	v1.GET("/rates/:base/:target", h.GetPairRate)       // Курс конкретной пары
	v1.POST("/exchange", h.Exchange)                     // Обмен между счетами
}

// GetRates godoc
// @Summary     Все курсы валют
// @Description Возвращает котировки всех валют относительно базовой (RUB по умолчанию).
// @Tags        currencies
// @Produce     json
// @Param       base query string false "Базовая валюта (ISO 4217)"
// @Success     200 {object} map[string]interface{}
// @Router      /api/v1/currencies/rates [get]
func (h *CurrencyHandler) GetRates(c echo.Context) error {
	base := c.QueryParam("base")
	if base == "" {
		base = "RUB"
	}
	path := fmt.Sprintf("/rates?base=%s", base)
	return h.Proxy.ForwardRaw(c, http.MethodGet, path, nil, "currency", h.APIKey)
}

// GetPairRate godoc
// @Summary     Курс валютной пары
// @Description Возвращает точный курс обмена между двумя валютами.
// @Tags        currencies
// @Produce     json
// @Param       base path string true "Базовая валюта"
// @Param       target path string true "Целевая валюта"
// @Success     200 {object} map[string]interface{}
// @Router      /api/v1/currencies/rates/{base}/{target} [get]
func (h *CurrencyHandler) GetPairRate(c echo.Context) error {
	base := c.Param("base")
	target := c.Param("target")
	path := fmt.Sprintf("/rates/%s/%s", base, target)
	return h.Proxy.ForwardRaw(c, http.MethodGet, path, nil, "currency", h.APIKey)
}

// Exchange godoc
// @Summary     Обмен валюты
// @Description Конвертирует средства между двумя валютными счетами пользователя.
// @Tags        currencies
// @Security    SessionToken
// @Accept      json
// @Produce     json
// @Param       payload body schemas.ExchangeRequest true "Данные обмена"
// @Success     200 {object} map[string]interface{}
// @Router      /api/v1/currencies/exchange [post]
func (h *CurrencyHandler) Exchange(c echo.Context) error {
	body, _ := ReadBody(c)
	return h.Proxy.ForwardRaw(c, http.MethodPost, "/exchange", body, "currency", h.APIKey)
}
