package schemas

// LoginPinRequest запрос на вход по PIN-коду
type LoginPinRequest struct {
	// Номер телефона в международном формате (+7...)
	Phone string `json:"phone" example:"+79991234567" format:"phone" validate:"required"`
	// Секретный 4-значный код доступа
	Pin string `json:"pin" example:"1234" minLength:"4" maxLength:"4" validate:"required"`
}

// SetPinRequest запрос на установку или смену PIN-кода
type SetPinRequest struct {
	// Новый 4-значный секретный код
	Pin string `json:"pin" example:"1234" minLength:"4" maxLength:"4" validate:"required"`
}

// RequestUnlockRequest запрос на отправку кода разблокировки на Email
type RequestUnlockRequest struct {
	// Email, привязанный к профилю клиента
	Email string `json:"email" example:"user@example.com" format:"email" validate:"required"`
}

// UnlockRequest запрос на разблокировку аккаунта после неверных попыток ввода PIN
type UnlockRequest struct {
	// Email, привязанный к профилю клиента
	Email string `json:"email" example:"user@example.com" format:"email" validate:"required"`
	// 6-значный код подтверждения из Email-письма
	Code string `json:"code" example:"123456" minLength:"6" maxLength:"6" validate:"required"`
}

// VerifyEmailRequest запрос на подтверждение Email-адреса в процессе регистрации
type VerifyEmailRequest struct {
	// 6-значный одноразовый код подтверждения
	Code string `json:"code" example:"123456" minLength:"6" maxLength:"6" validate:"required"`
}

// AuthErrorResponse базовая ошибка аутентификации (будет заменена на специфичные)
type AuthErrorResponse struct {
	Type    string                 `json:"type" example:"AuthError"`
	Title   string                 `json:"title" example:"Ошибка аутентификации"`
	Status  int                    `json:"status" example:"401"`
	Detail  string                 `json:"detail" example:"Неверные учетные данные"`
	Details map[string]interface{} `json:"details,omitempty" swaggertype:"object"`
}

// AuthCooldownErrorResponse ошибка 423 (временная блокировка после попыток)
type AuthCooldownErrorResponse struct {
	Type   string `json:"type" example:"AuthCooldown"`
	Title  string `json:"title" example:"Временная блокировка"`
	Status int    `json:"status" example:"423"`
	Detail string `json:"detail" example:"Слишком много попыток входа. Попробуйте через 5 минут или воспользуйтесь кодом разблокировки."`
}

// AuthInvalidCodeErrorResponse ошибка 403 (неверный код из письма)
type AuthInvalidCodeErrorResponse struct {
	Type   string `json:"type" example:"AuthInvalidCode"`
	Title  string `json:"title" example:"Неверный код"`
	Status int    `json:"status" example:"403"`
	Detail string `json:"detail" example:"Код разблокировки неверен или истек"`
}

// AuthBlockedErrorResponse ошибка 403 (аккаунт заблокирован по безопасности)
type AuthBlockedErrorResponse struct {
	Type   string `json:"type" example:"AuthBlocked"`
	Title  string `json:"title" example:"Аккаунт заблокирован"`
	Status int    `json:"status" example:"403"`
	Detail string `json:"detail" example:"Доступ к аккаунту заблокирован по соображениям безопасности"`
}

// LoginResponse данные, возвращаемые после успешного входа
type LoginResponse struct {
	// Сессионный токен (JWT), необходим для авторизации последующих запросов
	SessionToken string `json:"session_token" example:"eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."`
	// Текущий статус аккаунта в системе
	Status string `json:"status" example:"active"`
	// Признак наличия установленного PIN-кода (false - если нужно установить впервые)
	HasPin bool `json:"has_pin" example:"true"`
}
