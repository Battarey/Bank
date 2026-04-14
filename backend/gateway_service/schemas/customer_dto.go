package schemas

// PersonalDataPayload содержит основные анкетные данные клиента (Шаг 1 регистрации)
type PersonalDataPayload struct {
	// Имя клиента
	FirstName string `json:"first_name" example:"Иван" validate:"required"`
	// Фамилия клиента
	LastName string `json:"last_name" example:"Иванов" validate:"required"`
	// Отчество клиента (при наличии)
	MiddleName string `json:"middle_name,omitempty" example:"Иванович"`
	// Дата рождения в формате ГГГГ-ММ-ДД
	BirthDate string `json:"birth_date" example:"1990-01-01" format:"date" validate:"required"`
	// Пол клиента (M - мужской, F - женский)
	Gender string `json:"gender" example:"M" enums:"M,F" validate:"required"`
}

// PersonalDataUpdate содержит поля для частичного обновления ФИО
type PersonalDataUpdate struct {
	// Новое имя
	FirstName string `json:"first_name,omitempty" example:"Петр"`
	// Новая фамилия
	LastName string `json:"last_name,omitempty" example:"Петров"`
	// Новое отчество
	MiddleName string `json:"middle_name,omitempty" example:"Петрович"`
}

// PassportPayload содержит данные паспорта гражданина РФ (Шаг 2 регистрации)
type PassportPayload struct {
	// Серия паспорта (4 цифры)
	Series string `json:"series" example:"1234" minLength:"4" maxLength:"4" validate:"required"`
	// Номер паспорта (6 цифр)
	Number string `json:"number" example:"567890" minLength:"6" maxLength:"6" validate:"required"`
	// Кем выдан документ
	IssuedBy string `json:"issued_by" example:"ГУ МВД России" validate:"required"`
	// Дата выдачи
	IssuedAt string `json:"issued_at" example:"2010-01-01" format:"date" validate:"required"`
	// Код подразделения (000-000)
	DivisionCode string `json:"division_code" example:"123-456" validate:"required"`
	// Адрес постоянной регистрации
	RegistrationAddress string `json:"registration_address" example:"г. Москва, ул. Пушкина" validate:"required"`
	// Дата окончания действия (если применимо)
	ExpirationDate string `json:"expiration_date" example:"2030-01-01" format:"date"`
}

// IdentifiersPayload содержит государственные номера ИНН и СНИЛС (Шаг 3 регистрации)
type IdentifiersPayload struct {
	// ИНН (12 цифр для физлиц)
	Inn string `json:"inn" example:"123456789012" minLength:"12" maxLength:"12" validate:"required"`
	// СНИЛС (11 цифр)
	Snils string `json:"snils" example:"12345678900" minLength:"11" maxLength:"11" validate:"required"`
}

// ContactsPayload содержит контактную информацию клиента (Шаг 4 регистрации)
type ContactsPayload struct {
	// Основной Email
	Email string `json:"email" example:"user@example.com" format:"email" validate:"required"`
	// Номер телефона
	Phone string `json:"phone" example:"+79991234567" format:"phone" validate:"required"`
}

// ContactsUpdate содержит поля для обновления контактных данных
type ContactsUpdate struct {
	// Новый Email
	Email string `json:"email,omitempty" example:"new@example.com" format:"email"`
	// Новый номер телефона
	Phone string `json:"phone,omitempty" example:"+79990001122" format:"phone"`
}

// CustomerProfileDTO агрегированная информация о профиле клиента (личный кабинет)
type CustomerProfileDTO struct {
	// Уникальный идентификатор пользователя (UUID)
	ID string `json:"id" example:"user-uuid" format:"uuid"`
	// Статус учетной записи
	Status string `json:"status" example:"active" enums:"active,blocked,deleted"`
	// Анкетные данные (ФИО, ДР, Пол)
	PersonalData PersonalDataPayload `json:"personal_data"`
	// Паспортные данные
	Passport PassportPayload `json:"passport"`
	// ИНН и СНИЛС
	Identifiers IdentifiersPayload `json:"identifiers"`
	// Контактные данные
	Contacts ContactsPayload `json:"contacts"`
}

// OnboardingErrorResponse базовая ошибка в процессе регистрации (будет заменена на специфичные)
type OnboardingErrorResponse struct {
	Type    string                 `json:"type" example:"OnboardingError"`
	Title   string                 `json:"title" example:"Ошибка регистрации"`
	Status  int                    `json:"status" example:"400"`
	Detail  string                 `json:"detail" example:"Произошла ошибка при обработке данных онбординга"`
	Details map[string]interface{} `json:"details,omitempty" swaggertype:"object"`
}

// OnboardingNotFoundErrorResponse ошибка 401/404 (сессия не найдена)
type OnboardingNotFoundErrorResponse struct {
	Type   string `json:"type" example:"OnboardingNotFound"`
	Title  string `json:"title" example:"Черновик не найден"`
	Status int    `json:"status" example:"401"`
	Detail string `json:"detail" example:"Сессия регистрации истекла или заголовок X-Onboarding-Token отсутствует"`
}

// OnboardingConflictErrorResponse ошибка 409 (данные уже заняты)
type OnboardingConflictErrorResponse struct {
	Type   string `json:"type" example:"OnboardingConflict"`
	Title  string `json:"title" example:"Данные уже используются"`
	Status int    `json:"status" example:"409"`
	Detail string `json:"detail" example:"Пользователь с таким Email, ИНН или СНИЛС уже зарегистрирован в системе"`
}

// OnboardingTooManyRequestsErrorResponse ошибка 429 (лимит запросов кода)
type OnboardingTooManyRequestsErrorResponse struct {
	Type   string `json:"type" example:"OnboardingRateLimit"`
	Title  string `json:"title" example:"Слишком много запросов"`
	Status int    `json:"status" example:"429"`
	Detail string `json:"detail" example:"Вы слишком часто запрашиваете код подтверждения. Пожалуйста, подождите 2 минуты."`
}

// OnboardingInvalidStepErrorResponse ошибка 400 (нарушена последовательность)
type OnboardingInvalidStepErrorResponse struct {
	Type   string `json:"type" example:"OnboardingInvalidStep"`
	Title  string `json:"title" example:"Неверный шаг"`
	Status int    `json:"status" example:"400"`
	Detail string `json:"detail" example:"Невозможно выполнить этот шаг (например, завершить регистрацию), так как не все предыдущие данные заполнены"`
}

// OnboardingStartResponse содержит токен для прохождения процесса регистрации
type OnboardingStartResponse struct {
	// Токен процесса регистрации, передается в заголовке X-Onboarding-Token
	OnboardingToken string `json:"onboarding_token" example:"onb_550e8400-e29b-41d4-a716-446655440000"`
	// Текущий статус онбординга
	Status string `json:"status" example:"started"`
}
