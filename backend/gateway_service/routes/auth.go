package routes

import (
	"fmt"
	"net/http"

	"github.com/labstack/echo/v4"

	"gateway_service/proxy"
	redisClient "gateway_service/redis"
	_ "gateway_service/schemas"
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

	// Публичные (вход и восстановление)
	v1.POST("/sessions", h.Login)                               // Создать сессию (Вход)
	v1.POST("/sessions/quick", h.QuickLogin)                     // Быстрый вход по PIN
	v1.POST("/auth/unlock-codes", h.RequestUnlock)               // Запросить код восстановления
	v1.POST("/auth/unlock-codes/verifications", h.ConfirmUnlock) // Восстановление и смена PIN

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
// @Description В случае успеха возвращает сессионный токен (JWT) и токен привязки (Refresh Token).
// @Tags        sessions
// @Accept      json
// @Produce     json
// @Param       payload body schemas.LoginPinRequest true "Номер телефона (+7...) и 4-значный PIN"
// @Success     201 {object} schemas.LoginResponse "Успешная авторизация"
// @Failure     400 {object} schemas.ValidationErrorResponse "Ошибка валидации входных данных"
// @Failure     401 {object} schemas.UnauthorizedErrorResponse "Неверный логин или пароль"
// @Failure     403 {object} schemas.AuthBlockedErrorResponse "Доступ запрещён (аккаунт заблокирован)"
// @Failure     404 {object} schemas.NotFoundErrorResponse "Пользователь не найден"
// @Failure     423 {object} schemas.AuthCooldownErrorResponse "Временная блокировка (AuthCooldown)"
// @Router      /api/v1/sessions [post]
func (h *AuthHandler) Login(c echo.Context) error {
	body, err := ReadBody(c)
	if err != nil {
		return echo.NewHTTPError(http.StatusBadRequest, map[string]string{
			"detail": "Ошибка чтения тела запроса.",
		})
	}
	return h.Proxy.ForwardRaw(c, http.MethodPost, "/sessions", body, "auth", h.APIKey)
}

// quickLogin godoc
// @Summary     Быстрый вход (по PIN)
// @Description Повторный вход в приложение с использованием токена привязки и PIN-кода.
// @Description Позволяет войти без ввода номера телефона. Токен привязки обновляется при каждом входе.
// @Tags        sessions
// @Accept      json
// @Produce     json
// @Param       payload body schemas.QuickLoginRequest true "Токен привязки и 4-значный PIN"
// @Success     201 {object} schemas.LoginResponse "Успешная авторизация"
// @Failure     400 {object} schemas.ValidationErrorResponse "Ошибка валидации данных"
// @Failure     403 {object} schemas.AuthInvalidCodeErrorResponse "Неверный PIN или токен привязки"
// @Router      /api/v1/sessions/quick [post]
func (h *AuthHandler) QuickLogin(c echo.Context) error {
	body, err := ReadBody(c)
	if err != nil {
		return echo.NewHTTPError(http.StatusBadRequest, map[string]string{
			"detail": "Ошибка чтения тела запроса.",
		})
	}
	return h.Proxy.ForwardRaw(c, http.MethodPost, "/sessions/quick", body, "auth", h.APIKey)
}

// requestUnlock godoc
// @Summary     Запросить код восстановления доступа
// @Description Отправляет 6-значный одноразовый код на Email пользователя, привязанный к номеру телефона.
// @Description Код необходим для сброса блокировки или смены забытого PIN.
// @Tags        auth-recovery
// @Accept      json
// @Produce     json
// @Param       payload body schemas.RequestUnlockRequest true "Номер телефона, привязанный к аккаунту"
// @Success     201 {object} schemas.SuccessResponse "Код успешно отправлен на Email"
// @Failure     400 {object} schemas.ValidationErrorResponse "Некорректный формат телефона"
// @Failure     404 {object} schemas.NotFoundErrorResponse "Пользователь не найден"
// @Router      /api/v1/auth/unlock-codes [post]
func (h *AuthHandler) RequestUnlock(c echo.Context) error {
	body, err := ReadBody(c)
	if err != nil {
		return echo.NewHTTPError(http.StatusBadRequest, map[string]string{
			"detail": "Ошибка чтения тела запроса.",
		})
	}
	return h.Proxy.ForwardRaw(c, http.MethodPost, "/unlock-codes", body, "auth", h.APIKey)
}

// confirmUnlock godoc
// @Summary     Подтвердить восстановление и сменить PIN
// @Description Проверяет код из письма и устанавливает новый PIN-код для входа в аккаунт.
// @Description После успешного сброса статус аккаунта меняется на 'active'.
// @Tags        auth-recovery
// @Accept      json
// @Produce     json
// @Param       payload body schemas.UnlockRequest true "Телефон, код из письма и новый PIN"
// @Success     200 {object} schemas.SuccessResponse "Доступ успешно восстановлен"
// @Failure     400 {object} schemas.ValidationErrorResponse "Ошибка формата данных"
// @Failure     403 {object} schemas.AuthInvalidCodeErrorResponse "Неверный или просроченный код"
// @Failure     404 {object} schemas.NotFoundErrorResponse "Пользователь не найден"
// @Router      /api/v1/auth/unlock-codes/verifications [post]
func (h *AuthHandler) ConfirmUnlock(c echo.Context) error {
	body, err := ReadBody(c)
	if err != nil {
		return echo.NewHTTPError(http.StatusBadRequest, map[string]string{
			"detail": "Ошибка чтения тела запроса.",
		})
	}
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
// @Failure     401 {object} schemas.UnauthorizedErrorResponse "Сессия невалидна или отсутствует токен"
// @Router      /api/v1/auth/pins [put]
func (h *AuthHandler) SetPin(c echo.Context) error {
	body, err := ReadBody(c)
	if err != nil {
		return echo.NewHTTPError(http.StatusBadRequest, map[string]string{
			"detail": "Ошибка чтения тела запроса.",
		})
	}

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
		err = h.Sessions.UpdateTokenData(c.Request().Context(), token, map[string]string{
			"has_pin": "true",
		})
		if err != nil {
			c.Logger().Errorf("Ошибка обновления данных сессии (has_pin) в Redis: %v", err)
		}
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
// @Failure     401 {object} schemas.UnauthorizedErrorResponse "Токен уже недействителен"
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
// @Failure     401 {object} schemas.UnauthorizedErrorResponse "Необходима авторизация"
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
// @Failure     401 {object} schemas.UnauthorizedErrorResponse "Необходима авторизация"
// @Router      /api/v1/auth/self-block [post]
func (h *AuthHandler) SelfBlock(c echo.Context) error {
	return h.Proxy.ForwardRaw(c, http.MethodPost, "/sessions/me/block", nil, "auth", h.APIKey)
}
