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
	e.GET("/currency/rates", h.getRates)
	e.GET("/currency/rates/:base/:target", h.getPairRate)
	e.POST("/currency/exchange", h.exchange)
}

// getRates godoc
// @Summary     Все курсы валют
// @Description Возвращает курсы всех валют относительно базовой.
// @Tags        currency
// @Produce     json
// @Param       base query string false "Базовая валюта (по умолчанию RUB)" default(RUB)
// @Success     200 {object} map[string]interface{}
// @Router      /currency/rates [get]
func (h *CurrencyHandler) getRates(c echo.Context) error {
	base := c.QueryParam("base")
	if base == "" {
		base = "RUB"
	}
	path := fmt.Sprintf("/rates?base=%s", base)
	return h.Proxy.ForwardRaw(c, http.MethodGet, path, nil, "currency", h.APIKey)
}

// getPairRate godoc
// @Summary     Курс валютной пары
// @Description Возвращает курс конкретной валютной пары.
// @Tags        currency
// @Produce     json
// @Param       base path string true "Базовая валюта (RUB, USD, EUR)"
// @Param       target path string true "Целевая валюта (RUB, USD, EUR)"
// @Success     200 {object} map[string]interface{}
// @Router      /currency/rates/{base}/{target} [get]
func (h *CurrencyHandler) getPairRate(c echo.Context) error {
	base := c.Param("base")
	target := c.Param("target")
	path := fmt.Sprintf("/rates/%s/%s", base, target)
	return h.Proxy.ForwardRaw(c, http.MethodGet, path, nil, "currency", h.APIKey)
}

// exchange godoc
// @Summary     Обменять валюту между счетами
// @Description Конвертирует валюту между банковскими счетами (RUB/USD/EUR).
// @Tags        currency
// @Security    SessionToken
// @Accept      json
// @Produce     json
// @Param       payload body schemas.ExchangeRequest true "Данные обмена"
// @Success     200 {object} map[string]interface{}
// @Failure     401 {object} map[string]string
// @Router      /currency/exchange [post]
func (h *CurrencyHandler) exchange(c echo.Context) error {
	body, _ := readBody(c)
	return h.Proxy.ForwardRaw(c, http.MethodPost, "/exchange", body, "currency", h.APIKey)
}
