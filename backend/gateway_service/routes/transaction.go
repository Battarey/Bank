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

	// Семантические роуты для операций
	v1.POST("/accounts/:account_id/deposit", h.Deposit)
	v1.POST("/accounts/:account_id/withdraw", h.Withdraw)
	v1.POST("/transfers", h.Transfer)

	// Унифицированный эндпоинт (для совместимости)
	v1.POST("/transactions", h.CreateTransaction)

	// История операций (только чтение)
	v1.GET("/accounts/:account_id/transactions", h.TransactionHistory)
}

// Deposit godoc
// @Summary     Пополнение счёта
// @Description Вносит средства на указанный счёт.
// @Tags        transactions
// @Security    SessionToken
// @Accept      json
// @Produce     json
// @Param       account_id path string true "UUID счёта"
// @Param       payload body map[string]interface{} true "Сумма и описание"
// @Success     200 {object} map[string]interface{}
// @Router      /api/v1/accounts/{account_id}/deposit [post]
func (h *TransactionHandler) Deposit(c echo.Context) error {
	return h.forwardWithPayload(c, "deposit")
}

// Withdraw godoc
// @Summary     Снятие наличных/со счёта
// @Description Списывает средства с указанного счёта.
// @Tags        transactions
// @Security    SessionToken
// @Accept      json
// @Produce     json
// @Param       account_id path string true "UUID счёта"
// @Param       payload body map[string]interface{} true "Сумма и описание"
// @Success     200 {object} map[string]interface{}
// @Router      /api/v1/accounts/{account_id}/withdraw [post]
func (h *TransactionHandler) Withdraw(c echo.Context) error {
	return h.forwardWithPayload(c, "withdrawal")
}

// Transfer godoc
// @Summary     Перевод средств
// @Description Перевод между двумя счетами (своими или другим клиентам).
// @Tags        transactions
// @Security    SessionToken
// @Accept      json
// @Produce     json
// @Param       payload body map[string]interface{} true "Отправитель, получатель, сумма"
// @Success     200 {object} map[string]interface{}
// @Router      /api/v1/transfers [post]
func (h *TransactionHandler) Transfer(c echo.Context) error {
	body, _ := ReadBody(c)
	data, _ := JSONToMap(body)
	if data == nil {
		data = make(map[string]interface{})
	}
	data["type"] = "transfer"
	body, _ = MapToJSON(data)

	return h.Proxy.ForwardRaw(c, http.MethodPost, "/transactions", body, "transaction", h.APIKey)
}

// Вспомогательный метод для инъекции типа и account_id
func (h *TransactionHandler) forwardWithPayload(c echo.Context, txType string) error {
	accountID := c.Param("account_id")
	body, _ := ReadBody(c)

	data, _ := JSONToMap(body)
	data["type"] = txType
	data["account_id"] = accountID
	body, _ = MapToJSON(data)

	return h.Proxy.ForwardRaw(c, http.MethodPost, "/transactions", body, "transaction", h.APIKey)
}

// CreateTransaction godoc
// @Summary     Универсальная финансовая операция
// @Tags        transactions
// @Security    SessionToken
// @Router      /api/v1/transactions [post]
func (h *TransactionHandler) CreateTransaction(c echo.Context) error {
	body, _ := ReadBody(c)
	return h.Proxy.ForwardRaw(c, http.MethodPost, "/transactions", body, "transaction", h.APIKey)
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
