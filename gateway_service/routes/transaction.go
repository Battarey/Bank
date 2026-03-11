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
	e.POST("/accounts/:account_id/deposit", h.deposit)
	e.POST("/accounts/:account_id/withdraw", h.withdraw)
	e.POST("/accounts/:account_id/transfer", h.transfer)
	e.GET("/accounts/:account_id/transactions", h.transactionHistory)
}

// deposit godoc
// @Summary     Пополнить счёт
// @Description Вносит средства на указанный счёт.
// @Tags        transactions
// @Security    SessionToken
// @Accept      json
// @Produce     json
// @Param       account_id path string true "UUID счёта"
// @Param       payload body schemas.AmountPayload true "Сумма пополнения"
// @Success     200 {object} map[string]interface{}
// @Failure     401 {object} map[string]string
// @Router      /accounts/{account_id}/deposit [post]
func (h *TransactionHandler) deposit(c echo.Context) error {
	accountID := c.Param("account_id")
	body, _ := readBody(c)
	path := fmt.Sprintf("/accounts/%s/deposit", accountID)
	return h.Proxy.ForwardRaw(c, http.MethodPost, path, body, "transaction", h.APIKey)
}

// withdraw godoc
// @Summary     Снять со счёта
// @Description Списывает средства со счёта текущего пользователя.
// @Tags        transactions
// @Security    SessionToken
// @Accept      json
// @Produce     json
// @Param       account_id path string true "UUID счёта"
// @Param       payload body schemas.AmountPayload true "Сумма снятия"
// @Success     200 {object} map[string]interface{}
// @Failure     401 {object} map[string]string
// @Router      /accounts/{account_id}/withdraw [post]
func (h *TransactionHandler) withdraw(c echo.Context) error {
	accountID := c.Param("account_id")
	body, _ := readBody(c)
	path := fmt.Sprintf("/accounts/%s/withdraw", accountID)
	return h.Proxy.ForwardRaw(c, http.MethodPost, path, body, "transaction", h.APIKey)
}

// transfer godoc
// @Summary     Перевести между счетами
// @Description Переводит средства с указанного счёта на другой (свой или чужой).
// @Tags        transactions
// @Security    SessionToken
// @Accept      json
// @Produce     json
// @Param       account_id path string true "UUID счёта-отправителя"
// @Param       payload body schemas.TransferRequest true "Данные перевода"
// @Success     200 {object} map[string]interface{}
// @Failure     401 {object} map[string]string
// @Router      /accounts/{account_id}/transfer [post]
func (h *TransactionHandler) transfer(c echo.Context) error {
	accountID := c.Param("account_id")
	body, _ := readBody(c)
	path := fmt.Sprintf("/accounts/%s/transfer", accountID)
	return h.Proxy.ForwardRaw(c, http.MethodPost, path, body, "transaction", h.APIKey)
}

// transactionHistory godoc
// @Summary     История операций
// @Description Возвращает историю операций по счёту с пагинацией и фильтрами.
// @Tags        transactions
// @Security    SessionToken
// @Produce     json
// @Param       account_id path string true "UUID счёта"
// @Param       limit query int false "Кол-во записей (по умолчанию 20)" default(20)
// @Param       offset query int false "Смещение" default(0)
// @Param       type query string false "Тип операции: deposit | withdrawal | transfer"
// @Param       direction query string false "Направление: incoming | outgoing"
// @Success     200 {object} map[string]interface{}
// @Failure     401 {object} map[string]string
// @Router      /accounts/{account_id}/transactions [get]
func (h *TransactionHandler) transactionHistory(c echo.Context) error {
	accountID := c.Param("account_id")

	queryString := c.QueryString()
	path := fmt.Sprintf("/accounts/%s/transactions", accountID)
	if queryString != "" {
		path += "?" + queryString
	}
	return h.Proxy.ForwardRaw(c, http.MethodGet, path, nil, "transaction", h.APIKey)
}
