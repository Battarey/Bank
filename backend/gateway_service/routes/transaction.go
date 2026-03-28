package routes

import (
	"fmt"
	"net/http"

	"github.com/labstack/echo/v4"

	"gateway_service/proxy"
)

// TransactionHandler обрабатывает маршруты transaction_service.
type TransactionHandler struct {
	Proxy  *proxy.ServiceClients
	APIKey string
}

// RegisterTransactionRoutes регистрирует маршруты транзакций.
func (h *TransactionHandler) RegisterTransactionRoutes(e *echo.Echo) {
	e.POST("/accounts/:account_id/deposit", h.Deposit)
	e.POST("/accounts/:account_id/withdraw", h.Withdraw)
	e.POST("/accounts/:account_id/transfer", h.Transfer)
	e.GET("/accounts/:account_id/transactions", h.TransactionHistory)
}

// Deposit godoc
func (h *TransactionHandler) Deposit(c echo.Context) error {
	accountID := c.Param("account_id")
	body, _ := ReadBody(c)
	path := fmt.Sprintf("/accounts/%s/deposit", accountID)
	return h.Proxy.ForwardRaw(c, http.MethodPost, path, body, "transaction", h.APIKey)
}

// Withdraw godoc
func (h *TransactionHandler) Withdraw(c echo.Context) error {
	accountID := c.Param("account_id")
	body, _ := ReadBody(c)
	path := fmt.Sprintf("/accounts/%s/withdraw", accountID)
	return h.Proxy.ForwardRaw(c, http.MethodPost, path, body, "transaction", h.APIKey)
}

// Transfer godoc
func (h *TransactionHandler) Transfer(c echo.Context) error {
	accountID := c.Param("account_id")
	body, _ := ReadBody(c)
	path := fmt.Sprintf("/accounts/%s/transfer", accountID)
	return h.Proxy.ForwardRaw(c, http.MethodPost, path, body, "transaction", h.APIKey)
}

// TransactionHistory godoc
func (h *TransactionHandler) TransactionHistory(c echo.Context) error {
	accountID := c.Param("account_id")

	queryString := c.QueryString()
	path := fmt.Sprintf("/accounts/%s/transactions", accountID)
	if queryString != "" {
		path += "?" + queryString
	}
	return h.Proxy.ForwardRaw(c, http.MethodGet, path, nil, "transaction", h.APIKey)
}
