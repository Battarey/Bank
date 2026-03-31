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

	// Унифицированный эндпоинт для всех типов операций
	v1.POST("/transactions", h.CreateTransaction)

	// История операций (только чтение)
	v1.GET("/accounts/:account_id/transactions", h.TransactionHistory)
}

// CreateTransaction godoc
// @Summary     Выполнить финансовую операцию
// @Description Создаёт новую транзакцию (пополнение, снятие или перевод). Тип определяется полем 'type' в JSON-теле.
// @Tags        transactions
// @Security    SessionToken
// @Accept      json
// @Produce     json
// @Param       payload body schemas.TransactionCreateRequest true "Данные операции"
// @Success     200 {object} map[string]interface{}
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
