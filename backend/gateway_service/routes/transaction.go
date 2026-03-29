package routes

import (
	"fmt"
	"net/http"

	"github.com/labstack/echo/v4"

	"gateway_service/proxy"
)

// TransactionHandler обрабатывает маршруты финансовых операций и истории.
type TransactionHandler struct {
	Proxy  *proxy.ServiceClients
	APIKey string
}

// RegisterTransactionRoutes регистрирует маршруты транзакций в API Gateway.
func (h *TransactionHandler) RegisterTransactionRoutes(e *echo.Echo) {
	v1 := e.Group("/api/v1")

	// Операции по конкретному счету
	v1.POST("/accounts/:account_id/deposit", h.Deposit)       // Пополнение
	v1.POST("/accounts/:account_id/withdrawal", h.Withdrawal) // Снятие (обновленный путь)
	v1.POST("/accounts/:account_id/transfer", h.Transfer)     // Перевод другому клиенту
	v1.GET("/accounts/:account_id/transactions", h.TransactionHistory) // История операций
}

// Deposit godoc
// @Summary     Пополнить счёт
// @Description Вносит указанную сумму на банковский счёт текущего пользователя.
// @Tags        transactions
// @Security    SessionToken
// @Accept      json
// @Produce     json
// @Param       account_id path string true "UUID счёта"
// @Param       payload body schemas.DepositRequest true "Данные пополнения"
// @Success     200 {object} map[string]interface{}
// @Router      /api/v1/accounts/{account_id}/deposit [post]
func (h *TransactionHandler) Deposit(c echo.Context) error {
	accountID := c.Param("account_id")
	body, _ := ReadBody(c)
	path := fmt.Sprintf("/accounts/%s/deposit", accountID)
	return h.Proxy.ForwardRaw(c, http.MethodPost, path, body, "transaction", h.APIKey)
}

// Withdrawal godoc
// @Summary     Снять средства
// @Description Списывает указанную сумму с банковского счёта пользователя.
// @Tags        transactions
// @Security    SessionToken
// @Accept      json
// @Produce     json
// @Param       account_id path string true "UUID счёта"
// @Param       payload body schemas.WithdrawRequest true "Данные снятия"
// @Success     200 {object} map[string]interface{}
// @Router      /api/v1/accounts/{account_id}/withdrawal [post]
func (h *TransactionHandler) Withdrawal(c echo.Context) error {
	accountID := c.Param("account_id")
	body, _ := ReadBody(c)
	path := fmt.Sprintf("/accounts/%s/withdrawal", accountID)
	return h.Proxy.ForwardRaw(c, http.MethodPost, path, body, "transaction", h.APIKey)
}

// Transfer godoc
// @Summary     Перевод средств
// @Description Переводит деньги между счетами разных клиентов банка.
// @Tags        transactions
// @Security    SessionToken
// @Accept      json
// @Produce     json
// @Param       account_id path string true "UUID исходного счёта"
// @Param       payload body schemas.TransferRequest true "Данные перевода"
// @Success     200 {object} map[string]interface{}
// @Router      /api/v1/accounts/{account_id}/transfer [post]
func (h *TransactionHandler) Transfer(c echo.Context) error {
	accountID := c.Param("account_id")
	body, _ := ReadBody(c)
	path := fmt.Sprintf("/accounts/%s/transfer", accountID)
	return h.Proxy.ForwardRaw(c, http.MethodPost, path, body, "transaction", h.APIKey)
}

// TransactionHistory godoc
// @Summary     История транзакций
// @Description Возвращает список всех операций по конкретному счёту с поддержкой фильтрации.
// @Tags        transactions
// @Security    SessionToken
// @Produce     json
// @Param       account_id path string true "UUID счёта"
// @Param       type query string false "Тип (deposit|withdrawal|transfer|exchange)"
// @Param       limit query int false "Количество записей"
// @Success     200 {object} []map[string]interface{}
// @Router      /api/v1/accounts/{account_id}/transactions [get]
func (h *TransactionHandler) TransactionHistory(c echo.Context) error {
	accountID := c.Param("account_id")

	queryString := c.QueryString()
	path := fmt.Sprintf("/accounts/%s/transactions", accountID)
	if queryString != "" {
		path += "?" + queryString
	}
	return h.Proxy.ForwardRaw(c, http.MethodGet, path, nil, "transaction", h.APIKey)
}
