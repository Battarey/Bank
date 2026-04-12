package routes

import (
	"fmt"
	"net/http"

	"github.com/labstack/echo/v4"

	"gateway_service/proxy"
)

// AccountHandler обрабатывает маршруты управления банковскими счетами.
type AccountHandler struct {
	Proxy  *proxy.ServiceClients
	APIKey string
}

// RegisterAccountRoutes регистрирует маршруты для работы со счетами в API Gateway.
func (h *AccountHandler) RegisterAccountRoutes(e *echo.Echo) {
	v1 := e.Group("/api/v1")

	v1.POST("/accounts", h.OpenAccount)              // Открыть новый счёт
	v1.GET("/accounts", h.ListAccounts)             // Список всех счетов пользователя
	v1.GET("/accounts/:account_id", h.GetAccount)    // Информация о конкретном счёте
	v1.DELETE("/accounts/:account_id", h.CloseAccount) // Закрыть счёт (архивировать)

	// Приостановка/возобновление обслуживания (вместо freeze)
	v1.POST("/accounts/:account_id/suspensions", h.SuspendAccount)   // Приостановить обслуживание
	v1.DELETE("/accounts/:account_id/suspensions", h.ResumeAccount) // Возобновить обслуживание
}

// OpenAccount godoc
// @Summary     Открыть счёт
// @Description Создаёт новый банковский счёт для текущего пользователя (RUB, USD, EUR).
// @Description Доступные типы: checking, savings, credit, deposit.
// @Tags        accounts
// @Security    SessionToken
// @Accept      json
// @Produce     json
// @Param       payload body schemas.OpenAccountRequest true "Тип счёта и валюта"
// @Success     201 {object} schemas.AccountDTO "Счёт успешно создан"
// @Failure     400 {object} schemas.ErrorResponse "Неверные параметры (валюта или тип)"
// @Failure     401 {object} schemas.ErrorResponse "Не авторизован"
// @Router      /api/v1/accounts [post]
func (h *AccountHandler) OpenAccount(c echo.Context) error {
	body, _ := ReadBody(c)
	return h.Proxy.ForwardRaw(c, http.MethodPost, "/accounts", body, "account", h.APIKey)
}

// ListAccounts godoc
// @Summary     Список счетов
// @Description Возвращает список всех активных, замороженных и архивных счетов текущего пользователя.
// @Tags        accounts
// @Security    SessionToken
// @Produce     json
// @Success     200 {object} []schemas.AccountDTO "Список счетов"
// @Failure     401 {object} schemas.ErrorResponse "Не авторизован"
// @Router      /api/v1/accounts [get]
func (h *AccountHandler) ListAccounts(c echo.Context) error {
	return h.Proxy.ForwardRaw(c, http.MethodGet, "/accounts", nil, "account", h.APIKey)
}

// GetAccount godoc
// @Summary     Детали счёта
// @Description Возвращает подробную информацию о конкретном банковском счёте, включая баланс и статус.
// @Tags        accounts
// @Security    SessionToken
// @Produce     json
// @Param       account_id path string true "UUID счёта" format(uuid)
// @Success     200 {object} schemas.AccountDTO "Информация о счёте"
// @Failure     401 {object} schemas.ErrorResponse "Не авторизован"
// @Failure     404 {object} schemas.ErrorResponse "Счёт не найден"
// @Router      /api/v1/accounts/{account_id} [get]
func (h *AccountHandler) GetAccount(c echo.Context) error {
	accountID := c.Param("account_id")
	path := fmt.Sprintf("/accounts/%s", accountID)
	return h.Proxy.ForwardRaw(c, http.MethodGet, path, nil, "account", h.APIKey)
}

// CloseAccount godoc
// @Summary     Закрыть счёт
// @Description Переводит счёт в статус 'closed'. Проводки по нему становятся невозможны.
// @Description Счёт может быть закрыт только при нулевом балансе.
// @Tags        accounts
// @Security    SessionToken
// @Produce     json
// @Param       account_id path string true "UUID счёта" format(uuid)
// @Success     200 {object} schemas.SuccessResponse "Счёт успешно закрыт"
// @Failure     400 {object} schemas.ErrorResponse "Нельзя закрыть счёт с ненулевым балансом"
// @Failure     404 {object} schemas.ErrorResponse "Счёт не найден"
// @Router      /api/v1/accounts/{account_id} [delete]
func (h *AccountHandler) CloseAccount(c echo.Context) error {
	accountID := c.Param("account_id")
	path := fmt.Sprintf("/accounts/%s", accountID)
	return h.Proxy.ForwardRaw(c, http.MethodDelete, path, nil, "account", h.APIKey)
}

// SuspendAccount godoc
// @Summary     Приостановить обслуживание (Заморозка)
// @Description Временно блокирует любые расходные операции по счёту.
// @Tags        accounts
// @Security    SessionToken
// @Produce     json
// @Param       account_id path string true "UUID счёта" format(uuid)
// @Success     200 {object} schemas.SuccessResponse "Счёт успешно заморожен"
// @Failure     404 {object} schemas.ErrorResponse "Счёт не найден"
// @Router      /api/v1/accounts/{account_id}/suspensions [post]
func (h *AccountHandler) SuspendAccount(c echo.Context) error {
	accountID := c.Param("account_id")
	path := fmt.Sprintf("/accounts/%s/suspensions", accountID)
	return h.Proxy.ForwardRaw(c, http.MethodPost, path, nil, "account", h.APIKey)
}

// ResumeAccount godoc
// @Summary     Возобновить обслуживание (Разморозка)
// @Description Снимает временную блокировку со счёта, восстанавливая возможность проведения операций.
// @Tags        accounts
// @Security    SessionToken
// @Produce     json
// @Param       account_id path string true "UUID счёта" format(uuid)
// @Success     200 {object} schemas.SuccessResponse "Счёт успешно разморожен"
// @Failure     403 {object} schemas.ErrorResponse "Нет прав на разморозку (если заморожен системой)"
// @Router      /api/v1/accounts/{account_id}/suspensions [delete]
func (h *AccountHandler) ResumeAccount(c echo.Context) error {
	accountID := c.Param("account_id")
	path := fmt.Sprintf("/accounts/%s/suspensions", accountID)
	return h.Proxy.ForwardRaw(c, http.MethodDelete, path, nil, "account", h.APIKey)
}
