package routes

import (
	"fmt"
	"net/http"

	"github.com/labstack/echo/v4"

	"gateway_service/proxy"
	redisClient "gateway_service/redis"
)

// AuthHandler обрабатывает маршруты аутентификации и управления доступом.
type AuthHandler struct {
	Proxy    *proxy.ServiceClients
	Sessions *redisClient.SessionsClient
	APIKey   string
}

// RegisterAuthRoutes регистрирует маршруты аутентификации в API Gateway.
func (h *AuthHandler) RegisterAuthRoutes(e *echo.Echo) {
	// Группа API v1
	v1 := e.Group("/api/v1")

	// Публичные (вход и разблокировка)
	v1.POST("/sessions", h.Login)             // Создать сессию (Вход)
	v1.POST("/auth/unlock-codes", h.RequestUnlock)         // Запросить код
	v1.POST("/auth/unlock-codes/verifications", h.ConfirmUnlock) // Подтверждение разблокировки

	// Защищённые (управление сессиями и PIN)
	v1.PUT("/auth/pins", h.SetPin)                         // Обновить PIN
	v1.DELETE("/sessions/current", h.Logout)             // Выход (текущая)
	v1.DELETE("/sessions", h.LogoutAll)                  // Выход (все устройства)
	v1.POST("/auth/self-block", h.SelfBlock)             // Самоблокировка
}

// ── Публичные ──────────────────────────────────────────────────────────

// login godoc
// @Summary     Вход в приложение
// @Description Аутентификация по номеру телефона и PIN-коду. Возвращает сессионный токен.
// @Tags        sessions
// @Accept      json
// @Produce     json
// @Param       payload body schemas.LoginPinRequest true "Данные для входа"
// @Success     201 {object} map[string]interface{}
// @Failure     401 {object} map[string]string
// @Router      /api/v1/sessions [post]
func (h *AuthHandler) Login(c echo.Context) error {
	body, _ := ReadBody(c)
	return h.Proxy.ForwardRaw(c, http.MethodPost, "/sessions", body, "auth", h.APIKey)
}

// requestUnlock godoc
// @Summary     Запросить код разблокировки
// @Description Отправляет временный код на email пользователя для восстановления доступа.
// @Tags        auth-unlock
// @Accept      json
// @Produce     json
// @Param       payload body schemas.RequestUnlockRequest true "Email пользователя"
// @Success     201 {object} map[string]interface{}
// @Router      /api/v1/auth/unlock-codes [post]
func (h *AuthHandler) RequestUnlock(c echo.Context) error {
	body, _ := ReadBody(c)
	return h.Proxy.ForwardRaw(c, http.MethodPost, "/unlock-codes", body, "auth", h.APIKey)
}

// confirmUnlock godoc
// @Summary     Подтвердить разблокировку
// @Description Проверяет код и разблокирует учетную запись пользователя.
// @Tags        auth-unlock
// @Accept      json
// @Produce     json
// @Param       payload body schemas.UnlockRequest true "Данные для разблокировки"
// @Success     200 {object} map[string]interface{}
// @Router      /api/v1/auth/unlock-codes/verifications [post]
func (h *AuthHandler) ConfirmUnlock(c echo.Context) error {
	body, _ := ReadBody(c)
	return h.Proxy.ForwardRaw(c, http.MethodPost, "/unlock-codes/verifications", body, "auth", h.APIKey)
}

// ── Защищённые ─────────────────────────────────────────────────────────

// setPin godoc
// @Summary     Обновить PIN-код
// @Description Устанавливает или изменяет секретный PIN для входа в приложение.
// @Tags        auth
// @Security    SessionToken
// @Accept      json
// @Produce     json
// @Param       payload body schemas.SetPinRequest true "Новый PIN"
// @Success     200 {object} map[string]interface{}
// @Router      /api/v1/auth/pins [put]
func (h *AuthHandler) SetPin(c echo.Context) error {
	body, _ := ReadBody(c)

	respData, statusCode, err := ForwardAndParse(c, h.Proxy, http.MethodPut, "/pins", body, "auth", h.APIKey)
	if err != nil {
		return c.JSON(http.StatusBadGateway, map[string]string{
			"detail": fmt.Sprintf("Ошибка проксирования: %v", err),
		})
	}

	if statusCode >= 400 {
		return c.JSON(statusCode, respData)
	}

	// Обновляем состояние сессии в Redis: PIN установлен
	token := c.Request().Header.Get("X-Session-Token")
	if token != "" {
		_ = h.Sessions.UpdateTokenData(c.Request().Context(), token, map[string]string{
			"has_pin": "true",
		})
	}

	return c.JSON(statusCode, respData)
}

// logout godoc
// @Summary     Выход (текущая сессия)
// @Description Удаляет текущий сессионный токен.
// @Tags        sessions
// @Security    SessionToken
// @Produce     json
// @Success     200 {object} map[string]interface{}
// @Router      /api/v1/sessions/current [delete]
func (h *AuthHandler) Logout(c echo.Context) error {
	return h.Proxy.ForwardRaw(c, http.MethodDelete, "/sessions/current", nil, "auth", h.APIKey)
}

// logoutAll godoc
// @Summary     Выход со всех устройств
// @Description Аннулирует все активные сессии текущего пользователя.
// @Tags        sessions
// @Security    SessionToken
// @Produce     json
// @Success     200 {object} map[string]interface{}
// @Router      /api/v1/sessions [delete]
func (h *AuthHandler) LogoutAll(c echo.Context) error {
	return h.Proxy.ForwardRaw(c, http.MethodDelete, "/sessions", nil, "auth", h.APIKey)
}

// selfBlock godoc
// @Summary     Самоблокировка клиента
// @Description Блокирует доступ к аккаунту и замораживает все счета по инициативе пользователя.
// @Tags        auth
// @Security    SessionToken
// @Produce     json
// @Success     200 {object} map[string]interface{}
// @Router      /api/v1/auth/self-block [post]
func (h *AuthHandler) SelfBlock(c echo.Context) error {
	return h.Proxy.ForwardRaw(c, http.MethodPost, "/sessions/me/block", nil, "auth", h.APIKey)
}
