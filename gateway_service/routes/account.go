package routes

import (
	"fmt"
	"net/http"

	"github.com/labstack/echo/v4"

	"gateway_service/proxy"
)

// AccountHandler обрабатывает маршруты account_service.
type AccountHandler struct {
	Proxy  *proxy.ServiceClients
	APIKey string
}

// RegisterAccountRoutes регистрирует маршруты банковских счетов.
func (h *AccountHandler) RegisterAccountRoutes(e *echo.Echo) {
	e.POST("/accounts", h.openAccount)
	e.GET("/accounts", h.listAccounts)
	e.GET("/accounts/:account_id", h.getAccount)
	e.POST("/accounts/:account_id/close", h.closeAccount)
	e.POST("/accounts/:account_id/freeze", h.freezeAccount)
	e.POST("/accounts/:account_id/unfreeze", h.unfreezeAccount)
}

// openAccount godoc
// @Summary     Открыть новый счёт
// @Description Создаёт банковский счёт указанного типа и валюты для текущего пользователя.
// @Tags        accounts
// @Security    SessionToken
// @Accept      json
// @Produce     json
// @Param       payload body schemas.OpenAccountRequest true "Тип и валюта счёта"
// @Success     201 {object} map[string]interface{}
// @Failure     401 {object} map[string]string
// @Failure     409 {object} map[string]string
// @Router      /accounts [post]
func (h *AccountHandler) openAccount(c echo.Context) error {
	body, _ := readBody(c)
	return h.Proxy.ForwardRaw(c, http.MethodPost, "/accounts", body, "account", h.APIKey)
}

// listAccounts godoc
// @Summary     Список счетов
// @Description Возвращает все счета текущего пользователя.
// @Tags        accounts
// @Security    SessionToken
// @Produce     json
// @Success     200 {object} map[string]interface{}
// @Failure     401 {object} map[string]string
// @Router      /accounts [get]
func (h *AccountHandler) listAccounts(c echo.Context) error {
	return h.Proxy.ForwardRaw(c, http.MethodGet, "/accounts", nil, "account", h.APIKey)
}

// getAccount godoc
// @Summary     Детали счёта
// @Description Возвращает данные конкретного счёта.
// @Tags        accounts
// @Security    SessionToken
// @Produce     json
// @Param       account_id path string true "UUID счёта"
// @Success     200 {object} map[string]interface{}
// @Failure     401 {object} map[string]string
// @Failure     404 {object} map[string]string
// @Router      /accounts/{account_id} [get]
func (h *AccountHandler) getAccount(c echo.Context) error {
	accountID := c.Param("account_id")
	path := fmt.Sprintf("/accounts/%s", accountID)
	return h.Proxy.ForwardRaw(c, http.MethodGet, path, nil, "account", h.APIKey)
}

// closeAccount godoc
// @Summary     Закрыть счёт
// @Description Закрывает банковский счёт. Баланс должен быть 0.
// @Tags        accounts
// @Security    SessionToken
// @Produce     json
// @Param       account_id path string true "UUID счёта"
// @Success     200 {object} map[string]interface{}
// @Failure     401 {object} map[string]string
// @Failure     409 {object} map[string]string
// @Router      /accounts/{account_id}/close [post]
func (h *AccountHandler) closeAccount(c echo.Context) error {
	accountID := c.Param("account_id")
	path := fmt.Sprintf("/accounts/%s/close", accountID)
	return h.Proxy.ForwardRaw(c, http.MethodPost, path, nil, "account", h.APIKey)
}

// freezeAccount godoc
// @Summary     Заморозить счёт
// @Description Замораживает счёт. Исходящие операции блокируются, входящие — разрешены.
// @Tags        accounts
// @Security    SessionToken
// @Produce     json
// @Param       account_id path string true "UUID счёта"
// @Success     200 {object} map[string]interface{}
// @Failure     401 {object} map[string]string
// @Router      /accounts/{account_id}/freeze [post]
func (h *AccountHandler) freezeAccount(c echo.Context) error {
	accountID := c.Param("account_id")
	path := fmt.Sprintf("/accounts/%s/freeze", accountID)
	return h.Proxy.ForwardRaw(c, http.MethodPost, path, nil, "account", h.APIKey)
}

// unfreezeAccount godoc
// @Summary     Разморозить счёт
// @Description Размораживает счёт. Доступно только если заморозка инициирована пользователем.
// @Tags        accounts
// @Security    SessionToken
// @Produce     json
// @Param       account_id path string true "UUID счёта"
// @Success     200 {object} map[string]interface{}
// @Failure     401 {object} map[string]string
// @Router      /accounts/{account_id}/unfreeze [post]
func (h *AccountHandler) unfreezeAccount(c echo.Context) error {
	accountID := c.Param("account_id")
	path := fmt.Sprintf("/accounts/%s/unfreeze", accountID)
	return h.Proxy.ForwardRaw(c, http.MethodPost, path, nil, "account", h.APIKey)
}
