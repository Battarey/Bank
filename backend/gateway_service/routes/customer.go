// Package routes содержит маршруты Gateway → внутренние сервисы.
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

// CustomerHandler обрабатывает маршруты customer_service.
type CustomerHandler struct {
	Proxy      *proxy.ServiceClients
	Sessions   *redisClient.SessionsClient
	Onboarding *redisClient.OnboardingClient
	APIKey     string
}

// RegisterCustomerRoutes регистрирует маршруты онбординга и обновления данных.
func (h *CustomerHandler) RegisterCustomerRoutes(e *echo.Echo) {
	// Онбординг (публичный + onboarding-токен)
	e.POST("/users/start", h.StartOnboarding)
	e.POST("/users/me/account/personal-data", h.SubmitPersonalData)
	e.POST("/users/me/account/passport", h.SubmitPassport)
	e.POST("/users/me/account/identifiers", h.SubmitIdentifiers)
	e.POST("/users/me/account/contacts", h.SubmitContacts)
	e.POST("/users/me/account/send-email-code", h.SendEmailCode)
	e.POST("/users/me/account/verify-email", h.VerifyEmail)
	e.POST("/users/me/account/finalize", h.FinalizeOnboarding)

	// Обновление данных (сессия)
	e.PATCH("/users/me/personal-data", h.UpdatePersonalData)
	e.PUT("/users/me/passport", h.ReplacePassport)
	e.PATCH("/users/me/contacts", h.UpdateContacts)
	e.DELETE("/users/me", h.DeleteAccount)
}

// resolveOnboarding проверяет X-Onboarding-Token и возвращает userID.
func (h *CustomerHandler) resolveOnboarding(c echo.Context) (string, error) {
	token := c.Request().Header.Get("X-Onboarding-Token")
	if token == "" {
		return "", echo.NewHTTPError(http.StatusUnauthorized, "Заголовок X-Onboarding-Token обязателен.")
	}

	userID, err := h.Onboarding.LoadOnboardingToken(c.Request().Context(), token)
	if err != nil {
		return "", echo.NewHTTPError(http.StatusInternalServerError, "Ошибка проверки онбординг-токена.")
	}
	if userID == "" {
		return "", echo.NewHTTPError(http.StatusUnauthorized, "Onboarding-токен невалиден или истёк.")
	}

	// Скользящая экспирация
	_ = h.Onboarding.TouchOnboardingToken(c.Request().Context(), token, redisClient.DefaultOnboardingTTL)

	return userID, nil
}



// ── Онбординг ──────────────────────────────────────────────────────────

// startOnboarding godoc
// @Summary     Начать регистрацию
// @Description Создаёт нового пользователя и возвращает onboarding_token для прохождения шагов регистрации.
// @Tags        onboarding
// @Accept      json
// @Produce     json
// @Success     201 {object} map[string]interface{} "onboarding_token + status"
// @Failure     500 {object} map[string]string
// @Router      /users/start [post]
func (h *CustomerHandler) StartOnboarding(c echo.Context) error {
	body, _ := ReadBody(c)

	svc := h.Proxy
	respData, statusCode, err := ForwardAndParse(c, svc, http.MethodPost, "/users/start", body, "customer", h.APIKey)
	if err != nil {
		return err
	}

	if statusCode >= 400 {
		return c.JSON(statusCode, respData)
	}

	userID, _ := respData["user_id"].(string)

	token, err := redisClient.GenerateToken()
	if err != nil {
		return c.JSON(http.StatusInternalServerError, map[string]string{
			"detail": "Ошибка генерации токена.",
		})
	}
	err = h.Onboarding.SaveOnboardingToken(c.Request().Context(), token, userID, redisClient.DefaultOnboardingTTL)
	if err != nil {
		return c.JSON(http.StatusInternalServerError, map[string]string{
			"detail": "Ошибка сохранения токена.",
		})
	}

	return c.JSON(http.StatusCreated, map[string]interface{}{
		"onboarding_token": token,
		"status":           respData["status"],
	})
}

// onboardingStep — общий обработчик для шагов онбординга.
func (h *CustomerHandler) OnboardingStep(c echo.Context, subPath string) error {
	userID, err := h.resolveOnboarding(c)
	if err != nil {
		he, ok := err.(*echo.HTTPError)
		if ok {
			return c.JSON(he.Code, map[string]string{"detail": fmt.Sprint(he.Message)})
		}
		return err
	}

	body, _ := ReadBody(c)
	path := fmt.Sprintf("/users/%s/account/%s", userID, subPath)
	return h.Proxy.ForwardRaw(c, http.MethodPost, path, body, "customer", h.APIKey)
}

// submitPersonalData godoc
// @Summary     Шаг 1: Персональные данные
// @Description Сохраняет ФИО, дату рождения и пол клиента.
// @Tags        onboarding
// @Security    OnboardingToken
// @Accept      json
// @Produce     json
// @Param       payload body schemas.PersonalDataPayload true "Персональные данные"
// @Success     201 {object} map[string]interface{}
// @Failure     401 {object} map[string]string
// @Router      /users/me/account/personal-data [post]
func (h *CustomerHandler) SubmitPersonalData(c echo.Context) error {
	return h.OnboardingStep(c, "personal-data")
}

// submitPassport godoc
// @Summary     Шаг 2: Паспортные данные
// @Description Сохраняет серию, номер, кем выдан и прочие паспортные сведения.
// @Tags        onboarding
// @Security    OnboardingToken
// @Accept      json
// @Produce     json
// @Param       payload body schemas.PassportPayload true "Паспортные данные"
// @Success     201 {object} map[string]interface{}
// @Failure     401 {object} map[string]string
// @Router      /users/me/account/passport [post]
func (h *CustomerHandler) SubmitPassport(c echo.Context) error {
	return h.OnboardingStep(c, "passport")
}

// submitIdentifiers godoc
// @Summary     Шаг 3: ИНН и СНИЛС
// @Description Сохраняет идентификаторы налогоплательщика и социального страхования.
// @Tags        onboarding
// @Security    OnboardingToken
// @Accept      json
// @Produce     json
// @Param       payload body schemas.IdentifiersPayload true "ИНН и СНИЛС"
// @Success     201 {object} map[string]interface{}
// @Failure     401 {object} map[string]string
// @Router      /users/me/account/identifiers [post]
func (h *CustomerHandler) SubmitIdentifiers(c echo.Context) error {
	return h.OnboardingStep(c, "identifiers")
}

// submitContacts godoc
// @Summary     Шаг 4: Контактные данные
// @Description Сохраняет email и номер телефона клиента.
// @Tags        onboarding
// @Security    OnboardingToken
// @Accept      json
// @Produce     json
// @Param       payload body schemas.ContactsPayload true "Контактные данные"
// @Success     201 {object} map[string]interface{}
// @Failure     401 {object} map[string]string
// @Router      /users/me/account/contacts [post]
func (h *CustomerHandler) SubmitContacts(c echo.Context) error {
	return h.OnboardingStep(c, "contacts")
}

// sendEmailCode godoc
// @Summary     Отправить код на email
// @Description Отправляет 6-значный код подтверждения на email из шага 4 (contacts).
// @Tags        onboarding
// @Security    OnboardingToken
// @Produce     json
// @Success     200 {object} map[string]interface{}
// @Failure     401 {object} map[string]string
// @Router      /users/me/account/send-email-code [post]
func (h *CustomerHandler) SendEmailCode(c echo.Context) error {
	return h.OnboardingStep(c, "send-email-code")
}

// verifyEmail godoc
// @Summary     Подтвердить email
// @Description Проверяет 6-значный код. После успешной верификации можно вызывать finalize.
// @Tags        onboarding
// @Security    OnboardingToken
// @Accept      json
// @Produce     json
// @Param       payload body schemas.VerifyEmailRequest true "Код верификации"
// @Success     200 {object} map[string]interface{}
// @Failure     401 {object} map[string]string
// @Router      /users/me/account/verify-email [post]
func (h *CustomerHandler) VerifyEmail(c echo.Context) error {
	return h.OnboardingStep(c, "verify-email")
}

// finalizeOnboarding godoc
// @Summary     Завершить регистрацию
// @Description Переносит данные из черновиков в БД, выдаёт сессионный токен и удаляет onboarding-токен.
// @Tags        onboarding
// @Security    OnboardingToken
// @Produce     json
// @Success     200 {object} map[string]interface{} "status + message + session_token + user_id"
// @Failure     401 {object} map[string]string
// @Router      /users/me/account/finalize [post]
func (h *CustomerHandler) FinalizeOnboarding(c echo.Context) error {
	userID, err := h.resolveOnboarding(c)
	if err != nil {
		he, ok := err.(*echo.HTTPError)
		if ok {
			return c.JSON(he.Code, map[string]string{"detail": fmt.Sprint(he.Message)})
		}
		return err
	}

	onbToken := c.Request().Header.Get("X-Onboarding-Token")

	path := fmt.Sprintf("/users/%s/account/finalize", userID)
	respData, statusCode, fwdErr := ForwardAndParse(c, h.Proxy, http.MethodPost, path, nil, "customer", h.APIKey)
	if fwdErr != nil {
		return fwdErr
	}

	if statusCode >= 400 {
		return c.JSON(statusCode, respData)
	}

	// Удаляем onboarding-токен
	if onbToken != "" {
		_ = h.Onboarding.DeleteOnboardingToken(c.Request().Context(), onbToken)
	}

	// Генерируем сессионный токен
	sessionToken := generateSessionToken()
	err = h.Sessions.SaveToken(c.Request().Context(), sessionToken, userID, map[string]string{
		"has_pin": "false",
	}, redisClient.DefaultSessionTTL)
	if err != nil {
		return c.JSON(http.StatusInternalServerError, map[string]string{
			"detail": "Ошибка создания сессии.",
		})
	}

	return c.JSON(http.StatusOK, map[string]interface{}{
		"status":        respData["status"],
		"message":       respData["message"],
		"session_token": sessionToken,
		"user_id":       userID,
	})
}

// ── Обновление данных пользователя ─────────────────────────────────────

// updatePersonalData godoc
// @Summary     Обновить персональные данные
// @Description Частичное обновление ФИО. Дата рождения и пол неизменяемы.
// @Tags        user-update
// @Security    SessionToken
// @Accept      json
// @Produce     json
// @Param       payload body schemas.PersonalDataUpdate true "Данные для обновления"
// @Success     200 {object} map[string]interface{}
// @Failure     401 {object} map[string]string
// @Router      /users/me/personal-data [patch]
func (h *CustomerHandler) UpdatePersonalData(c echo.Context) error {
	body, _ := ReadBody(c)
	return h.Proxy.ForwardRaw(c, http.MethodPatch, "/users/personal-data", body, "customer", h.APIKey)
}

// replacePassport godoc
// @Summary     Заменить паспортные данные
// @Description Полная замена паспортных данных (все поля обязательны).
// @Tags        user-update
// @Security    SessionToken
// @Accept      json
// @Produce     json
// @Param       payload body schemas.PassportPayload true "Паспортные данные"
// @Success     200 {object} map[string]interface{}
// @Failure     401 {object} map[string]string
// @Router      /users/me/passport [put]
func (h *CustomerHandler) ReplacePassport(c echo.Context) error {
	body, _ := ReadBody(c)
	return h.Proxy.ForwardRaw(c, http.MethodPut, "/users/passport", body, "customer", h.APIKey)
}

// updateContacts godoc
// @Summary     Обновить контактные данные
// @Description Частичное обновление email и/или телефона.
// @Tags        user-update
// @Security    SessionToken
// @Accept      json
// @Produce     json
// @Param       payload body schemas.ContactsUpdate true "Контактные данные"
// @Success     200 {object} map[string]interface{}
// @Failure     401 {object} map[string]string
// @Router      /users/me/contacts [patch]
func (h *CustomerHandler) UpdateContacts(c echo.Context) error {
	body, _ := ReadBody(c)
	return h.Proxy.ForwardRaw(c, http.MethodPatch, "/users/contacts", body, "customer", h.APIKey)
}

// deleteAccount godoc
// @Summary     Удалить аккаунт
// @Description Soft delete: статус → deleted, счета заморожены, все сессии отозваны. Данные сохраняются.
// @Tags        user-update
// @Security    SessionToken
// @Produce     json
// @Success     200 {object} map[string]interface{}
// @Failure     401 {object} map[string]string
// @Router      /users/me [delete]
func (h *CustomerHandler) DeleteAccount(c echo.Context) error {
	respData, statusCode, err := ForwardAndParse(c, h.Proxy, http.MethodDelete, "/users/delete", nil, "customer", h.APIKey)
	if err != nil {
		return err
	}

	if statusCode >= 400 {
		return c.JSON(statusCode, respData)
	}

	if userID, ok := c.Get("user_id").(string); ok && userID != "" {
		_ = h.Sessions.RevokeAll(c.Request().Context(), userID)
	}

	return c.JSON(statusCode, respData)
}

// ── Утилиты ────────────────────────────────────────────────────────────

// generateSessionToken генерирует случайный URL-safe сессионный токен.
func generateSessionToken() string {
	b := make([]byte, 32)
	_, _ = rand.Read(b)
	return base64.RawURLEncoding.EncodeToString(b)
}
