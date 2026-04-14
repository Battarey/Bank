package routes

import (
	"fmt"
	"net/http"

	"github.com/labstack/echo/v4"

	"gateway_service/proxy"
	_ "gateway_service/schemas"
)

// CurrencyHandler обрабатывает маршруты валютных котировок и обмена.
type CurrencyHandler struct {
	Proxy  *proxy.ServiceClients
	APIKey string
}

// RegisterCurrencyRoutes регистрирует маршруты валютных операций в API Gateway.
func (h *CurrencyHandler) RegisterCurrencyRoutes(e *echo.Echo) {
	v1 := e.Group("/api/v1/currencies")
	v1_root := e.Group("/api/v1")

	v1.GET("/rates", h.GetRates)                  // Список всех курсов
	v1.GET("/rates/:base/:target", h.GetPairRate) // Курс конкретной пары

	// Конвертация валют (вынесено на уровень /api/v1/)
	v1_root.POST("/currency-conversions", h.Convert)
}

// GetRates godoc
// @Summary     Все курсы валют
// @Description Возвращает котировки всех поддерживаемых валют относительно базовой (RUB по умолчанию).
// @Description Кэшируется на стороне сервиса на 5 минут.
// @Tags        currencies
// @Produce     json
// @Param       base query string false "Базовая валюта (ISO 4217)" default(RUB)
// @Success     200 {object} schemas.ExchangeRatesResponse "Таблица курсов"
// @Failure     502 {object} schemas.BadGatewayErrorResponse "Внешний API котировок недоступен"
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
// @Description Возвращает точный курс обмена между двумя конкретными валютами (например, RUB/USD).
// @Tags        currencies
// @Produce     json
// @Param       base path string true "Базовая валюта (откуда)" example(RUB)
// @Param       target path string true "Целевая валюта (куда)" example(USD)
// @Success     200 {object} schemas.ExchangeRatePairResponse "Точный курс пары"
// @Failure     404 {object} schemas.NotFoundErrorResponse "Валюта не поддерживается"
// @Router      /api/v1/currencies/rates/{base}/{target} [get]
func (h *CurrencyHandler) GetPairRate(c echo.Context) error {
	base := c.Param("base")
	target := c.Param("target")
	path := fmt.Sprintf("/rates/%s/%s", base, target)
	return h.Proxy.ForwardRaw(c, http.MethodGet, path, nil, "currency", h.APIKey)
}

// Convert godoc
// @Summary     Конвертировать валюту (Обмен)
// @Description Безопасно переводит средства между двумя валютными счетами одного владельца.
// @Description Типы счетов должны совпадать (например, с текущего RUB на текущий USD).
// @Tags        currencies
// @Security    SessionToken
// @Accept      json
// @Produce     json
// @Param       payload body schemas.ExchangeRequest true "Параметры обмена"
// @Success     200 {object} schemas.TransactionDTO "Обмен успешно выполнен"
// @Failure     400 {object} schemas.TransactionErrorResponse "Недостаточно средств или неверные счета"
// @Failure     401 {object} schemas.UnauthorizedErrorResponse "Не авторизован"
// @Router      /api/v1/currency-conversions [post]
func (h *CurrencyHandler) Convert(c echo.Context) error {
	body, err := ReadBody(c)
	if err != nil {
		return echo.NewHTTPError(http.StatusBadRequest, map[string]string{
			"detail": "Ошибка чтения тела запроса.",
		})
	}
	return h.Proxy.ForwardRaw(c, http.MethodPost, "/currency-conversions", body, "currency", h.APIKey)
}
