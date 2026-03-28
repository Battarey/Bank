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
	e.POST("/accounts", h.OpenAccount)
	e.GET("/accounts", h.ListAccounts)
	e.GET("/accounts/:account_id", h.GetAccount)
	e.POST("/accounts/:account_id/close", h.CloseAccount)
	e.POST("/accounts/:account_id/freeze", h.FreezeAccount)
	e.POST("/accounts/:account_id/unfreeze", h.UnfreezeAccount)
}

// OpenAccount godoc
func (h *AccountHandler) OpenAccount(c echo.Context) error {
	body, _ := ReadBody(c)
	return h.Proxy.ForwardRaw(c, http.MethodPost, "/accounts", body, "account", h.APIKey)
}

// ListAccounts godoc
func (h *AccountHandler) ListAccounts(c echo.Context) error {
	return h.Proxy.ForwardRaw(c, http.MethodGet, "/accounts", nil, "account", h.APIKey)
}

// GetAccount godoc
func (h *AccountHandler) GetAccount(c echo.Context) error {
	accountID := c.Param("account_id")
	path := fmt.Sprintf("/accounts/%s", accountID)
	return h.Proxy.ForwardRaw(c, http.MethodGet, path, nil, "account", h.APIKey)
}

// CloseAccount godoc
func (h *AccountHandler) CloseAccount(c echo.Context) error {
	accountID := c.Param("account_id")
	path := fmt.Sprintf("/accounts/%s/close", accountID)
	return h.Proxy.ForwardRaw(c, http.MethodPost, path, nil, "account", h.APIKey)
}

// FreezeAccount godoc
func (h *AccountHandler) FreezeAccount(c echo.Context) error {
	accountID := c.Param("account_id")
	path := fmt.Sprintf("/accounts/%s/freeze", accountID)
	return h.Proxy.ForwardRaw(c, http.MethodPost, path, nil, "account", h.APIKey)
}

// UnfreezeAccount godoc
func (h *AccountHandler) UnfreezeAccount(c echo.Context) error {
	accountID := c.Param("account_id")
	path := fmt.Sprintf("/accounts/%s/unfreeze", accountID)
	return h.Proxy.ForwardRaw(c, http.MethodPost, path, nil, "account", h.APIKey)
}
