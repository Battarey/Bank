package routes

import (
	"crypto/rand"
	"encoding/base64"
	"fmt"
	"net/http"

	"github.com/labstack/echo/v4"

	redisClient "gateway_service/redis"
	"gateway_service/proxy"
	_ "gateway_service/schemas"
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
	v1.GET("/customers/me", h.GetProfile)                         // Получить профиль
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
	err = h.Onboarding.TouchOnboardingToken(c.Request().Context(), token, redisClient.DefaultOnboardingTTL)
	if err != nil {
		// Логируем ошибку, но не прерываем запрос, так как это не критично для текущего шага
		c.Logger().Errorf("Ошибка продления TTL onboarding-токена: %v", err)
	}

	return userID, nil
}

// ── Онбординг ──────────────────────────────────────────────────────────

// StartOnboarding godoc
// @Summary     Начать регистрацию (Шаг 0)
// @Description Инициирует процесс создания нового клиента.
// @Description Создаёт временный профиль и выдаёт X-Onboarding-Token для прохождения последующих шагов.
// @Tags        onboarding
// @Accept      json
// @Produce     json
// @Success     201 {object} schemas.OnboardingStartResponse "Регистрация начата"
// @Failure     500 {object} schemas.ErrorResponse "Внутренняя ошибка сервиса"
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
	token, err := redisClient.GenerateToken()
	if err != nil {
		return echo.NewHTTPError(http.StatusInternalServerError, "Ошибка генерации токена регистрации.")
	}

	err = h.Onboarding.SaveOnboardingToken(c.Request().Context(), token, userID, redisClient.DefaultOnboardingTTL)
	if err != nil {
		return echo.NewHTTPError(http.StatusInternalServerError, "Ошибка сохранения сессии регистрации.")
	}

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

	body, err := ReadBody(c)
	if err != nil {
		return echo.NewHTTPError(http.StatusBadRequest, map[string]string{
			"detail": "Ошибка чтения тела запроса.",
		})
	}
	path := fmt.Sprintf("/onboarding/%s/%s", userID, subPath)
	return h.Proxy.ForwardRaw(c, http.MethodPost, path, body, "customer", h.APIKey)
}

// SubmitPersonalData godoc
// @Summary     Шаг 1: ФИО и дата рождения
// @Description Сохраняет базовые анкетные данные во временный профиль.
// @Description Требует заголовок X-Onboarding-Token.
// @Tags        onboarding
// @Security    OnboardingToken
// @Accept      json
// @Produce     json
// @Param       payload body schemas.PersonalDataPayload true "Анкетные данные"
// @Success     200 {object} schemas.SuccessResponse "Данные сохранены"
// @Failure     400 {object} schemas.ValidationErrorResponse "Ошибка валидации входных данных"
// @Failure     401 {object} schemas.OnboardingNotFoundErrorResponse "Сессия регистрации не найдена (OnboardingNotFound)"
// @Router      /api/v1/onboarding/personal-data [post]
func (h *CustomerHandler) SubmitPersonalData(c echo.Context) error {
	return h.OnboardingStep(c, "personal-data")
}

// SubmitPassport godoc
// @Summary     Шаг 2: Паспортные данные
// @Description Сохраняет данные паспорта РФ.
// @Description Требует заголовок X-Onboarding-Token.
// @Tags        onboarding
// @Security    OnboardingToken
// @Accept      json
// @Produce     json
// @Param       payload body schemas.PassportPayload true "Данные паспорта"
// @Success     200 {object} schemas.SuccessResponse "Данные сохранены"
// @Failure     400 {object} schemas.ValidationErrorResponse "Ошибка валидации паспортных данных"
// @Failure     401 {object} schemas.OnboardingNotFoundErrorResponse "Сессия регистрации не найдена (OnboardingNotFound)"
// @Router      /api/v1/onboarding/passport [post]
func (h *CustomerHandler) SubmitPassport(c echo.Context) error {
	return h.OnboardingStep(c, "passport")
}

// SubmitIdentifiers godoc
// @Summary     Шаг 3: ИНН и СНИЛС
// @Description Сохраняет государственные идентификаторы.
// @Description Требует заголовок X-Onboarding-Token.
// @Tags        onboarding
// @Security    OnboardingToken
// @Accept      json
// @Produce     json
// @Param       payload body schemas.IdentifiersPayload true "ИНН и СНИЛС"
// @Success     200 {object} schemas.SuccessResponse "Данные сохранены"
// @Failure     400 {object} schemas.ValidationErrorResponse "Ошибка валидации форматов"
// @Failure     401 {object} schemas.OnboardingNotFoundErrorResponse "Сессия регистрации не найдена"
// @Failure     409 {object} schemas.OnboardingConflictErrorResponse "ИНН или СНИЛС уже используются (OnboardingConflict)"
// @Router      /api/v1/onboarding/identifiers [post]
func (h *CustomerHandler) SubmitIdentifiers(c echo.Context) error {
	return h.OnboardingStep(c, "identifiers")
}

// SubmitContacts godoc
// @Summary     Шаг 4: Контакты (Email/Телефон)
// @Description Сохраняет контактные данные для связи и уведомлений.
// @Description Требует заголовок X-Onboarding-Token.
// @Tags        onboarding
// @Security    OnboardingToken
// @Accept      json
// @Produce     json
// @Param       payload body schemas.ContactsPayload true "Email и Телефон"
// @Success     200 {object} schemas.SuccessResponse "Данные сохранены"
// @Failure     400 {object} schemas.ValidationErrorResponse "Ошибка валидации контактов"
// @Failure     401 {object} schemas.OnboardingNotFoundErrorResponse "Сессия регистрации не найдена"
// @Failure     409 {object} schemas.OnboardingConflictErrorResponse "Email или телефон уже используются (OnboardingConflict)"
// @Router      /api/v1/onboarding/contacts [post]
func (h *CustomerHandler) SubmitContacts(c echo.Context) error {
	return h.OnboardingStep(c, "contacts")
}

// SendEmailCode godoc
// @Summary     Запросить Email-подтверждение
// @Description Отправляет проверочный код на Email, указанный на предыдущем шаге.
// @Description Требует заголовок X-Onboarding-Token.
// @Tags        onboarding
// @Security    OnboardingToken
// @Produce     json
// @Success     200 {object} schemas.SuccessResponse "Код успешно отправлен"
// @Failure     401 {object} schemas.OnboardingNotFoundErrorResponse "Сессия регистрации не найдена"
// @Failure     429 {object} schemas.OnboardingTooManyRequestsErrorResponse "Слишком частые запросы кода"
// @Router      /api/v1/onboarding/email/send [post]
func (h *CustomerHandler) SendEmailCode(c echo.Context) error {
	return h.OnboardingStep(c, "email/send")
}

// VerifyEmailCode godoc
// @Summary     Подтвердить Email
// @Description Проверяет 6-значный код, отправленный на почту.
// @Description Требует заголовок X-Onboarding-Token.
// @Tags        onboarding
// @Security    OnboardingToken
// @Accept      json
// @Produce     json
// @Param       payload body schemas.VerifyEmailRequest true "Код подтверждения"
// @Success     200 {object} schemas.SuccessResponse "Email подтвержден"
// @Failure     400 {object} schemas.ValidationErrorResponse "Неверный или просроченный код подтверждения"
// @Failure     401 {object} schemas.OnboardingNotFoundErrorResponse "Сессия регистрации не найдена"
// @Router      /api/v1/onboarding/email/verify [post]
func (h *CustomerHandler) VerifyEmailCode(c echo.Context) error {
	return h.OnboardingStep(c, "email/verify")
}

// CompleteOnboarding godoc
// @Summary     Завершение регистрации
// @Description Переносит данные из временного хранилища в основной профиль и активирует аккаунт.
// @Description В ответе возвращается сессионный токен для немедленного входа.
// @Tags        onboarding
// @Security    OnboardingToken
// @Produce     json
// @Success     200 {object} schemas.LoginResponse "Регистрация успешно завершена"
// @Failure     400 {object} schemas.OnboardingInvalidStepErrorResponse "Не все шаги регистрации пройдены"
// @Failure     401 {object} schemas.OnboardingNotFoundErrorResponse "Сессия регистрации не найдена"
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
		err = h.Onboarding.DeleteOnboardingToken(c.Request().Context(), onbToken)
		if err != nil {
			c.Logger().Errorf("Ошибка удаления onboarding-токена: %v", err)
		}
	}

	// Генерируем сессию, чтобы пользователь сразу был залогинен
	sessionToken, err := redisClient.GenerateToken()
	if err != nil {
		return echo.NewHTTPError(http.StatusInternalServerError, "Ошибка генерации сессионного токена.")
	}
	err = h.Sessions.SaveToken(c.Request().Context(), sessionToken, userID, nil, redisClient.DefaultSessionTTL)
	if err != nil {
		return echo.NewHTTPError(http.StatusInternalServerError, "Ошибка сохранения сессии пользователя.")
	}

	// Добавляем токен в ответ
	respData["session_token"] = sessionToken

	return c.JSON(http.StatusOK, respData)
}

// ── Профиль пользователя ───────────────────────────────────────────────
//
// GetProfile godoc
// @Summary     Получить профиль клиента
// @Description Возвращает полную агрегированную информацию о текущем пользователе (ФИО, Паспорт, Контакты и т.д.).
// @Tags        customers
// @Security    SessionToken
// @Produce     json
// @Success     200 {object} schemas.CustomerProfileDTO "Полный профиль пользователя"
// @Failure     401 {object} schemas.UnauthorizedErrorResponse "Необходима авторизация (Invalid Session)"
// @Failure     404 {object} schemas.NotFoundErrorResponse "Профиль не найден (UpdateDataNotFound)"
// @Router      /api/v1/customers/me [get]
func (h *CustomerHandler) GetProfile(c echo.Context) error {
	return h.Proxy.ForwardRaw(c, http.MethodGet, "/users/me", nil, "customer", h.APIKey)
}

// UpdatePersonalData godoc
// @Summary     Обновить ФИО
// @Description Позволяет изменить имя, фамилию или отчество.
// @Tags        customers
// @Security    SessionToken
// @Accept      json
// @Produce     json
// @Param       payload body schemas.PersonalDataUpdate true "Новые анкетные данные"
// @Success     200 {object} schemas.SuccessResponse "Данные успешно обновлены"
// @Failure     401 {object} schemas.UnauthorizedErrorResponse "Необходима авторизация"
// @Router      /api/v1/customers/me/personal-data [patch]
func (h *CustomerHandler) UpdatePersonalData(c echo.Context) error {
	body, err := ReadBody(c)
	if err != nil {
		return echo.NewHTTPError(http.StatusBadRequest, map[string]string{
			"detail": "Ошибка чтения тела запроса.",
		})
	}
	return h.Proxy.ForwardRaw(c, http.MethodPatch, "/users/personal-data", body, "customer", h.APIKey)
}

// ReplacePassport godoc
// @Summary     Смена паспорта
// @Description Обновляет паспортные данные пользователя (например, при замене документа).
// @Tags        customers
// @Security    SessionToken
// @Accept      json
// @Produce     json
// @Param       payload body schemas.PassportPayload true "Новые паспортные данные"
// @Success     200 {object} schemas.SuccessResponse "Паспорт успешно обновлен"
// @Router      /api/v1/customers/me/passport [put]
func (h *CustomerHandler) ReplacePassport(c echo.Context) error {
	body, err := ReadBody(c)
	if err != nil {
		return echo.NewHTTPError(http.StatusBadRequest, map[string]string{
			"detail": "Ошибка чтения тела запроса.",
		})
	}
	return h.Proxy.ForwardRaw(c, http.MethodPut, "/users/passport", body, "customer", h.APIKey)
}

// UpdateContacts godoc
// @Summary     Смена контактных данных
// @Description Позволяет обновить Email или номер телефона.
// @Tags        customers
// @Security    SessionToken
// @Accept      json
// @Produce     json
// @Param       payload body schemas.ContactsUpdate true "Новые контакты"
// @Success     200 {object} schemas.SuccessResponse "Контакты успешно обновлены"
// @Failure     401 {object} schemas.UnauthorizedErrorResponse "Необходима авторизация"
// @Failure     409 {object} schemas.ConflictErrorResponse "Контактные данные уже заняты (UpdateDataConflict)"
// @Router      /api/v1/customers/me/contacts [patch]
func (h *CustomerHandler) UpdateContacts(c echo.Context) error {
	body, err := ReadBody(c)
	if err != nil {
		return echo.NewHTTPError(http.StatusBadRequest, map[string]string{
			"detail": "Ошибка чтения тела запроса.",
		})
	}
	return h.Proxy.ForwardRaw(c, http.MethodPatch, "/users/contacts", body, "customer", h.APIKey)
}

// DeleteAccount godoc
// @Summary     Удалить профиль клиента
// @Description Помечает профиль как удалённый (Soft Delete) и завершает все активные сессии.
// @Tags        customers
// @Security    SessionToken
// @Produce     json
// @Success     200 {object} schemas.SuccessResponse "Профиль успешно удален"
// @Failure     401 {object} schemas.UnauthorizedErrorResponse "Необходима авторизация"
// @Failure     404 {object} schemas.NotFoundErrorResponse "Аккаунт не найден (AccountNotFound)"
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
		err = h.Sessions.RevokeAll(c.Request().Context(), userID)
		if err != nil {
			c.Logger().Errorf("Ошибка аннулирования сессий при удалении аккаунта: %v", err)
		}
	}

	return c.JSON(http.StatusOK, respData)
}
