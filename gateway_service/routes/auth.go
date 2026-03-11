package routes

import (
	"fmt"
	"net/http"

	"github.com/labstack/echo/v4"

	"gateway_service/proxy"
	redisClient "gateway_service/redis"
)

// AuthHandler обрабатывает маршруты auth_service.
type AuthHandler struct {
	Proxy    *proxy.ServiceClients
	Sessions *redisClient.SessionsClient
	APIKey   string
}

// RegisterAuthRoutes регистрирует маршруты аутентификации.
func (h *AuthHandler) RegisterAuthRoutes(e *echo.Echo) {
	// Публичные
	e.POST("/auth/login-pin", h.loginPin)
	e.POST("/auth/request-unlock", h.requestUnlock)
	e.POST("/auth/unlock", h.unlock)

	// Защищённые (middleware уже проверяет сессию)
	e.POST("/auth/set-pin", h.setPin)
	e.POST("/auth/logout", h.logout)
	e.POST("/auth/logout-all", h.logoutAll)
	e.POST("/auth/self-block", h.selfBlock)
}

// ── Публичные ──────────────────────────────────────────────────────────

// loginPin godoc
// @Summary     Вход по PIN-коду
// @Description Аутентификация по номеру телефона и PIN-коду. Возвращает сессионный токен.
// @Tags        auth
// @Accept      json
// @Produce     json
// @Param       payload body schemas.LoginPinRequest true "Телефон и PIN"
// @Success     200 {object} map[string]interface{}
// @Failure     401 {object} map[string]string
// @Router      /auth/login-pin [post]
func (h *AuthHandler) loginPin(c echo.Context) error {
	body, _ := readBody(c)
	return h.Proxy.ForwardRaw(c, http.MethodPost, "/login-pin", body, "auth", h.APIKey)
}

// requestUnlock godoc
// @Summary     Запросить код разблокировки
// @Description Отправляет код разблокировки на email, привязанный к аккаунту.
// @Tags        auth
// @Accept      json
// @Produce     json
// @Param       payload body schemas.RequestUnlockRequest true "Данные для запроса"
// @Success     200 {object} map[string]interface{}
// @Router      /auth/request-unlock [post]
func (h *AuthHandler) requestUnlock(c echo.Context) error {
	body, _ := readBody(c)
	return h.Proxy.ForwardRaw(c, http.MethodPost, "/request-unlock", body, "auth", h.APIKey)
}

// unlock godoc
// @Summary     Разблокировать аккаунт
// @Description Проверяет код и разблокирует аккаунт.
// @Tags        auth
// @Accept      json
// @Produce     json
// @Param       payload body schemas.UnlockRequest true "Код разблокировки"
// @Success     200 {object} map[string]interface{}
// @Router      /auth/unlock [post]
func (h *AuthHandler) unlock(c echo.Context) error {
	body, _ := readBody(c)
	return h.Proxy.ForwardRaw(c, http.MethodPost, "/unlock", body, "auth", h.APIKey)
}

// ── Защищённые ─────────────────────────────────────────────────────────

// setPin godoc
// @Summary     Установить / сменить PIN
// @Description Устанавливает или обновляет PIN-код текущего пользователя.
// @Tags        auth
// @Security    SessionToken
// @Accept      json
// @Produce     json
// @Param       payload body schemas.SetPinRequest true "PIN-код"
// @Success     200 {object} map[string]interface{}
// @Failure     401 {object} map[string]string
// @Router      /auth/set-pin [post]
func (h *AuthHandler) setPin(c echo.Context) error {
	body, _ := readBody(c)

	respData, statusCode, err := forwardAndParse(c, h.Proxy, http.MethodPost, "/set-pin", body, "auth", h.APIKey)
	if err != nil {
		return c.JSON(http.StatusBadGateway, map[string]string{
			"detail": fmt.Sprintf("Ошибка пересылки: %v", err),
		})
	}

	if statusCode >= 400 {
		return c.JSON(statusCode, respData)
	}

	// Обновляем сессию: PIN теперь установлен
	token := c.Request().Header.Get("X-Session-Token")
	if token != "" {
		_ = h.Sessions.UpdateTokenData(c.Request().Context(), token, map[string]string{
			"has_pin": "true",
		})
	}

	return c.JSON(statusCode, respData)
}

// logout godoc
// @Summary     Выход
// @Description Завершает текущий сеанс (удаляет сессионный токен).
// @Tags        auth
// @Security    SessionToken
// @Produce     json
// @Success     200 {object} map[string]interface{}
// @Failure     401 {object} map[string]string
// @Router      /auth/logout [post]
func (h *AuthHandler) logout(c echo.Context) error {
	return h.Proxy.ForwardRaw(c, http.MethodPost, "/logout", nil, "auth", h.APIKey)
}

// logoutAll godoc
// @Summary     Выход со всех устройств
// @Description Завершает все активные сеансы пользователя.
// @Tags        auth
// @Security    SessionToken
// @Produce     json
// @Success     200 {object} map[string]interface{}
// @Failure     401 {object} map[string]string
// @Router      /auth/logout-all [post]
func (h *AuthHandler) logoutAll(c echo.Context) error {
	return h.Proxy.ForwardRaw(c, http.MethodPost, "/logout-all", nil, "auth", h.APIKey)
}

// selfBlock godoc
// @Summary     Самоблокировка аккаунта
// @Description Блокирует аккаунт по запросу владельца. Замораживает все счета и завершает все сеансы.
// @Tags        auth
// @Security    SessionToken
// @Produce     json
// @Success     200 {object} map[string]interface{}
// @Failure     401 {object} map[string]string
// @Router      /auth/self-block [post]
func (h *AuthHandler) selfBlock(c echo.Context) error {
	return h.Proxy.ForwardRaw(c, http.MethodPost, "/self-block", nil, "auth", h.APIKey)
}
