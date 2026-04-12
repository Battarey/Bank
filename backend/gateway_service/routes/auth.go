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
	Sessions redisClient.SessionStore
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
// @Description Аутентификация по номеру телефона и PIN-коду. 
// @Description В случае успеха возвращает сессионный токен, который нужно передавать в заголовке X-Session-Token.
// @Tags        sessions
// @Accept      json
// @Produce     json
// @Param       payload body schemas.LoginPinRequest true "Номер телефона (+7...) и 4-значный PIN"
// @Success     201 {object} schemas.LoginResponse "Успешная авторизация"
// @Failure     400 {object} schemas.ErrorResponse "Неверный формат входных данных"
// @Failure     401 {object} schemas.ErrorResponse "Неверный телефон или PIN-код"
// @Failure     423 {object} schemas.ErrorResponse "Аккаунт временно заблокирован из-за перебора PIN"
// @Router      /api/v1/sessions [post]
func (h *AuthHandler) Login(c echo.Context) error {
	body, _ := ReadBody(c)
	return h.Proxy.ForwardRaw(c, http.MethodPost, "/sessions", body, "auth", h.APIKey)
}

// requestUnlock godoc
// @Summary     Запросить код разблокировки
// @Description Отправляет 6-значный одноразовый код на привязанный Email пользователя.
// @Description Код необходим для сброса блокировки после неверного ввода PIN.
// @Tags        auth-unlock
// @Accept      json
// @Produce     json
// @Param       payload body schemas.RequestUnlockRequest true "Email, привязанный к аккаунту"
// @Success     201 {object} schemas.SuccessResponse "Код успешно отправлен"
// @Failure     400 {object} schemas.ErrorResponse "Некорректный Email"
// @Failure     404 {object} schemas.ErrorResponse "Пользователь с таким Email не найден"
// @Router      /api/v1/auth/unlock-codes [post]
func (h *AuthHandler) RequestUnlock(c echo.Context) error {
	body, _ := ReadBody(c)
	return h.Proxy.ForwardRaw(c, http.MethodPost, "/unlock-codes", body, "auth", h.APIKey)
}

// confirmUnlock godoc
// @Summary     Подтвердить разблокировку
// @Description Проверяет код из письма и разблокирует учетную запись пользователя.
// @Description После разблокировки пользователь сможет снова войти по своему PIN.
// @Tags        auth-unlock
// @Accept      json
// @Produce     json
// @Param       payload body schemas.UnlockRequest true "Email и 6-значный код"
// @Success     200 {object} schemas.SuccessResponse "Аккаунт успешно разблокирован"
// @Failure     400 {object} schemas.ErrorResponse "Неверный или просроченный код"
// @Router      /api/v1/auth/unlock-codes/verifications [post]
func (h *AuthHandler) ConfirmUnlock(c echo.Context) error {
	body, _ := ReadBody(c)
	return h.Proxy.ForwardRaw(c, http.MethodPost, "/unlock-codes/verifications", body, "auth", h.APIKey)
}

// ── Защищённые ─────────────────────────────────────────────────────────

// setPin godoc
// @Summary     Обновить PIN-код
// @Description Устанавливает новый или изменяет существующий 4-значный PIN-код.
// @Description Операция доступна только аутентифицированным пользователям.
// @Tags        auth
// @Security    SessionToken
// @Accept      json
// @Produce     json
// @Param       payload body schemas.SetPinRequest true "Новый 4-значный PIN"
// @Success     200 {object} schemas.SuccessResponse "PIN успешно изменен"
// @Failure     401 {object} schemas.ErrorResponse "Сессия невалидна или отсутствует токен"
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
// @Description Удаляет текущий сессионный токен из хранилища Redis.
// @Description После этого токен станет недействительным для всех последующих запросов.
// @Tags        sessions
// @Security    SessionToken
// @Produce     json
// @Success     200 {object} schemas.SuccessResponse "Выход успешно выполнен"
// @Failure     401 {object} schemas.ErrorResponse "Токен уже недействителен"
// @Router      /api/v1/sessions/current [delete]
func (h *AuthHandler) Logout(c echo.Context) error {
	return h.Proxy.ForwardRaw(c, http.MethodDelete, "/sessions/current", nil, "auth", h.APIKey)
}

// logoutAll godoc
// @Summary     Выход со всех устройств
// @Description Аннулирует ВСЕ активные сессии текущего пользователя.
// @Description Полезно в случае компрометации одного из устройств.
// @Tags        sessions
// @Security    SessionToken
// @Produce     json
// @Success     200 {object} schemas.SuccessResponse "Все сессии завершены"
// @Failure     401 {object} schemas.ErrorResponse "Необходима авторизация"
// @Router      /api/v1/sessions [delete]
func (h *AuthHandler) LogoutAll(c echo.Context) error {
	return h.Proxy.ForwardRaw(c, http.MethodDelete, "/sessions", nil, "auth", h.APIKey)
}

// selfBlock godoc
// @Summary     Самоблокировка клиента
// @Description Полностью блокирует доступ к аккаунту и замораживает все счета.
// @Description ВНИМАНИЕ: Для разблокировки потребуется обращение в поддержку или использование email-кода.
// @Tags        auth
// @Security    SessionToken
// @Produce     json
// @Success     200 {object} schemas.SuccessResponse "Аккаунт успешно заблокирован"
// @Failure     401 {object} schemas.ErrorResponse "Необходима авторизация"
// @Router      /api/v1/auth/self-block [post]
func (h *AuthHandler) SelfBlock(c echo.Context) error {
	return h.Proxy.ForwardRaw(c, http.MethodPost, "/sessions/me/block", nil, "auth", h.APIKey)
}
