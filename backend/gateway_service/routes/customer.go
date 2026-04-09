package routes

import (
	"crypto/rand"
	"encoding/base64"
	"fmt"
	"net/http"

	"github.com/labstack/echo/v4"

	redisClient "gateway_service/redis"
	"gateway_service/proxy"
)

// CustomerHandler обрабатывает маршруты онбординга (регистрации) и профиля клиента.
type CustomerHandler struct {
	Proxy      *proxy.ServiceClients
	Sessions   redisClient.SessionStore
	Onboarding redisClient.OnboardingStore
	APIKey     string
}

// RegisterCustomerRoutes регистрирует маршруты клиента в API Gateway.
func (h *CustomerHandler) RegisterCustomerRoutes(e *echo.Echo) {
	v1 := e.Group("/api/v1")

	// Онбординг (Публичные эндпоинты с X-Onboarding-Token)
	v1.POST("/onboarding", h.StartOnboarding)                    // Шаг 0: Старт
	v1.POST("/onboarding/personal-data", h.SubmitPersonalData)   // Шаг 1: ФИО
	v1.POST("/onboarding/passport", h.SubmitPassport)             // Шаг 2: Паспорт
	v1.POST("/onboarding/identifiers", h.SubmitIdentifiers)       // Шаг 3: ИНН/СНИЛС
	v1.POST("/onboarding/contacts", h.SubmitContacts)             // Шаг 4: Контакты
	v1.POST("/onboarding/email/send", h.SendEmailCode)             // Верификация 1: Отправка
	v1.POST("/onboarding/email/verify", h.VerifyEmailCode)         // Верификация 2: Проверка
	v1.POST("/onboarding/completion", h.CompleteOnboarding)       // Завершение

	// Управление профилем (Требуется сессия X-Session-Token)
	v1.PATCH("/customers/me/personal-data", h.UpdatePersonalData) // Смена ФИО
	v1.PUT("/customers/me/passport", h.ReplacePassport)           // Новый паспорт
	v1.PATCH("/customers/me/contacts", h.UpdateContacts)           // Смена Email/тел
	v1.DELETE("/customers/me", h.DeleteAccount)                    // Удаление (soft delete)
}

// resolveOnboarding извлекает userID из onboarding-токена.
func (h *CustomerHandler) resolveOnboarding(c echo.Context) (string, error) {
	token := c.Request().Header.Get("X-Onboarding-Token")
	if token == "" {
		return "", echo.NewHTTPError(http.StatusUnauthorized, "Заголовок X-Onboarding-Token отсутствует.")
	}

	userID, err := h.Onboarding.LoadOnboardingToken(c.Request().Context(), token)
	if err != nil {
		return "", echo.NewHTTPError(http.StatusInternalServerError, "Ошибка верификации токена.")
	}
	if userID == "" {
		return "", echo.NewHTTPError(http.StatusUnauthorized, "Невалидный или просроченный токен.")
	}

	// Обновляем TTL токена при активности
	_ = h.Onboarding.TouchOnboardingToken(c.Request().Context(), token, redisClient.DefaultOnboardingTTL)

	return userID, nil
}

// ── Онбординг ──────────────────────────────────────────────────────────

// StartOnboarding godoc
// @Summary     Начать регистрацию
// @Description Создаёт временный профиль и выдаёт X-Onboarding-Token для прохождения шагов.
// @Tags        onboarding
// @Accept      json
// @Produce     json
// @Success     201 {object} map[string]interface{}
// @Router      /api/v1/onboarding [post]
func (h *CustomerHandler) StartOnboarding(c echo.Context) error {
	respData, statusCode, err := ForwardAndParse(c, h.Proxy, http.MethodPost, "/onboarding", nil, "customer", h.APIKey)
	if err != nil {
		return err
	}

	if statusCode >= 400 {
		return c.JSON(statusCode, respData)
	}

	userID, ok := respData["user_id"].(string)
	if !ok {
		// Если по какой-то причине ID нет, логируем и возвращаем ошибку
		return echo.NewHTTPError(http.StatusInternalServerError, "ID пользователя отсутствует в ответе сервиса.")
	}
	token, _ := redisClient.GenerateToken()

	_ = h.Onboarding.SaveOnboardingToken(c.Request().Context(), token, userID, redisClient.DefaultOnboardingTTL)

	return c.JSON(http.StatusCreated, map[string]interface{}{
		"onboarding_token": token,
		"status":           "started",
	})
}

// OnboardingStep — хелпер для проксирования шагов регистрации.
func (h *CustomerHandler) OnboardingStep(c echo.Context, subPath string) error {
	userID, err := h.resolveOnboarding(c)
	if err != nil {
		return err
	}

	body, _ := ReadBody(c)
	path := fmt.Sprintf("/onboarding/%s/%s", userID, subPath)
	return h.Proxy.ForwardRaw(c, http.MethodPost, path, body, "customer", h.APIKey)
}

// SubmitPersonalData godoc
// @Summary     Шаг 1: ФИО
// @Tags        onboarding
// @Router      /api/v1/onboarding/personal-data [post]
func (h *CustomerHandler) SubmitPersonalData(c echo.Context) error {
	return h.OnboardingStep(c, "personal-data")
}

// SubmitPassport godoc
// @Summary     Шаг 2: Паспорт
// @Tags        onboarding
// @Router      /api/v1/onboarding/passport [post]
func (h *CustomerHandler) SubmitPassport(c echo.Context) error {
	return h.OnboardingStep(c, "passport")
}

// SubmitIdentifiers godoc
// @Summary     Шаг 3: ИНН/СНИЛС
// @Tags        onboarding
// @Router      /api/v1/onboarding/identifiers [post]
func (h *CustomerHandler) SubmitIdentifiers(c echo.Context) error {
	return h.OnboardingStep(c, "identifiers")
}

// SubmitContacts godoc
// @Summary     Шаг 4: Контакты
// @Tags        onboarding
// @Router      /api/v1/onboarding/contacts [post]
func (h *CustomerHandler) SubmitContacts(c echo.Context) error {
	return h.OnboardingStep(c, "contacts")
}

// SendEmailCode godoc
// @Summary     Отправить код на Email
// @Tags        onboarding
// @Router      /api/v1/onboarding/email/send [post]
func (h *CustomerHandler) SendEmailCode(c echo.Context) error {
	return h.OnboardingStep(c, "email/send")
}

// VerifyEmailCode godoc
// @Summary     Подтвердить Email кодом
// @Tags        onboarding
// @Router      /api/v1/onboarding/email/verify [post]
func (h *CustomerHandler) VerifyEmailCode(c echo.Context) error {
	return h.OnboardingStep(c, "email/verify")
}

// CompleteOnboarding godoc
// @Summary     Завершение регистрации
// @Description Переносит данные из черновиков в основной профиль и активирует аккаунт.
// @Tags        onboarding
// @Router      /api/v1/onboarding/completion [post]
func (h *CustomerHandler) CompleteOnboarding(c echo.Context) error {
	userID, err := h.resolveOnboarding(c)
	if err != nil {
		return err
	}

	onbToken := c.Request().Header.Get("X-Onboarding-Token")
	path := fmt.Sprintf("/onboarding/%s/completion", userID)
	
	respData, statusCode, fwdErr := ForwardAndParse(c, h.Proxy, http.MethodPost, path, nil, "customer", h.APIKey)
	if fwdErr != nil {
		return fwdErr
	}

	if statusCode >= 400 {
		return c.JSON(statusCode, respData)
	}

	// Очистка onboarding-данных
	if onbToken != "" {
		_ = h.Onboarding.DeleteOnboardingToken(c.Request().Context(), onbToken)
	}

	// Генерируем сессию, чтобы пользователь сразу был залогинен
	sessionToken, _ := redisClient.GenerateToken()
	_ = h.Sessions.SaveToken(c.Request().Context(), sessionToken, userID, nil, redisClient.DefaultSessionTTL)

	// Добавляем токен в ответ
	respData["session_token"] = sessionToken

	return c.JSON(http.StatusOK, respData)
}

// ── Профиль пользователя ───────────────────────────────────────────────

// UpdatePersonalData godoc
// @Summary     Обновить ФИО
// @Tags        customers
// @Security    SessionToken
// @Router      /api/v1/customers/me/personal-data [patch]
func (h *CustomerHandler) UpdatePersonalData(c echo.Context) error {
	body, _ := ReadBody(c)
	return h.Proxy.ForwardRaw(c, http.MethodPatch, "/users/personal-data", body, "customer", h.APIKey)
}

// ReplacePassport godoc
// @Summary     Сменить паспорт
// @Tags        customers
// @Security    SessionToken
// @Router      /api/v1/customers/me/passport [put]
func (h *CustomerHandler) ReplacePassport(c echo.Context) error {
	body, _ := ReadBody(c)
	return h.Proxy.ForwardRaw(c, http.MethodPut, "/users/passport", body, "customer", h.APIKey)
}

// UpdateContacts godoc
// @Summary     Сменить контакты
// @Tags        customers
// @Security    SessionToken
// @Router      /api/v1/customers/me/contacts [patch]
func (h *CustomerHandler) UpdateContacts(c echo.Context) error {
	body, _ := ReadBody(c)
	return h.Proxy.ForwardRaw(c, http.MethodPatch, "/users/contacts", body, "customer", h.APIKey)
}

// DeleteAccount godoc
// @Summary     Удалить профиль
// @Description Помечает профиль как удалённый и завершает все активные сессии.
// @Tags        customers
// @Security    SessionToken
// @Router      /api/v1/customers/me [delete]
func (h *CustomerHandler) DeleteAccount(c echo.Context) error {
	respData, statusCode, err := ForwardAndParse(c, h.Proxy, http.MethodDelete, "/users/me", nil, "customer", h.APIKey)
	if err != nil {
		return err
	}

	if statusCode >= 400 {
		return c.JSON(statusCode, respData)
	}

	// Принудительный логаут со всех устройств после удаления
	if userID, ok := c.Get("user_id").(string); ok && userID != "" {
		_ = h.Sessions.RevokeAll(c.Request().Context(), userID)
	}

	return c.JSON(http.StatusOK, respData)
}

// ── Утилиты ────────────────────────────────────────────────────────────

func generateSessionToken() string {
	b := make([]byte, 32)
	_, _ = rand.Read(b)
	return base64.RawURLEncoding.EncodeToString(b)
}
