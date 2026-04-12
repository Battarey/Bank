// Package schemas содержит DTO (Data Transfer Objects) для генерации Swagger/OpenAPI спецификации.
// Эти структуры используются ТОЛЬКО для документации, чтобы Swagger UI мог генерировать
// правильные примеры запросов (auto-fill) с нужными полями и типами.
// Сама валидация по-прежнему происходит на стороне Python-микросервисов.
package schemas

// ── Auth & Onboarding ──────────────────────────────────────────────────

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

// ── Personal Data (Customer) ──────────────────────────────────────────

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

// ── Accounts & Transactions ───────────────────────────────────────────

// OpenAccountRequest параметры запроса на открытие нового банковского счёта
type OpenAccountRequest struct {
	// Тип счёта: checking (расчётный), savings (накопительный), credit (кредитный), deposit (вклад)
	Type string `json:"type" example:"checking" enums:"checking,savings,credit,deposit" validate:"required"`
	// Валюта счёта (ISO 4217)
	Currency string `json:"currency" example:"RUB" enums:"RUB,USD,EUR" validate:"required"`
}

// AmountPayload стандартный запрос с указанием суммы денежных средств
type AmountPayload struct {
	// Сумма операции (положительное число)
	Amount float64 `json:"amount" example:"1000.50" minimum:"0.01" validate:"required"`
}

// TransferRequest параметры для межбанковского или внутреннего перевода
type TransferRequest struct {
	// ID счёта получателя (UUID)
	ToAccountID string `json:"to_account_id" example:"550e8400-e29b-41d4-a716-446655440000" format:"uuid" validate:"required"`
	// Сумма перевода
	Amount float64 `json:"amount" example:"500.00" minimum:"0.01" validate:"required"`
	// Назначение платежа (комментарий для получателя)
	Description string `json:"description,omitempty" example:"Перевод другу"`
}

// CreateTransactionRequest универсальный запрос на создание финансовой операции
type CreateTransactionRequest struct {
	// Вид операции
	Type string `json:"type" example:"deposit" enums:"deposit,withdrawal,transfer" validate:"required"`
	// ID основного счёта (UUID)
	AccountID string `json:"account_id" example:"550e8400-e29b-41d4-a716-446655440001" format:"uuid" validate:"required"`
	// ID счёта получателя (только для переводов)
	ToAccountID string `json:"to_account_id,omitempty" example:"550e8400-e29b-41d4-a716-446655440002" format:"uuid"`
	// Сумма операции
	Amount float64 `json:"amount" example:"1000.00" minimum:"0.01" validate:"required"`
	// Описание/комментарий
	Description string `json:"description,omitempty" example:"Пополнение через банкомат"`
}

// ── Общие ответы ──────────────────────────────────────────────────────

// ErrorResponse универсальная структура ответа при возникновении ошибки
type ErrorResponse struct {
	// Подробное сообщение об ошибке для разработчика и пользователя
	Detail string `json:"detail" example:"Неверный PIN-код или формат данных"`
}

// SuccessResponse подтверждает успешное выполнение операции без возврата данных
type SuccessResponse struct {
	// Статус успеха (обычно 'success')
	Status string `json:"status" example:"success"`
}

// HealthResponse содержит информацию о текущем состоянии работоспособности шлюза
type HealthResponse struct {
	// Статус доступности ('ok')
	Status string `json:"status" example:"ok"`
}

// ── Auth & Onboarding ──────────────────────────────────────────────────

// LoginResponse данные, возвращаемые после успешного входа
type LoginResponse struct {
	// Сессионный токен (JWT), необходим для авторизации последующих запросов
	SessionToken string `json:"session_token" example:"eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."`
	// Текущий статус аккаунта в системе
	Status string `json:"status" example:"active"`
	// Признак наличия установленного PIN-кода (false - если нужно установить впервые)
	HasPin bool `json:"has_pin" example:"true"`
}

// OnboardingStartResponse содержит токен для прохождения процесса регистрации
type OnboardingStartResponse struct {
	// Токен процесса регистрации, передается в заголовке X-Onboarding-Token
	OnboardingToken string `json:"onboarding_token" example:"onb_550e8400-e29b-41d4-a716-446655440000"`
	// Текущий статус онбординга
	Status string `json:"status" example:"started"`
}

// ── Accounts & Transactions ───────────────────────────────────────────

// AccountDTO полная детальная информация о банковском счёте
type AccountDTO struct {
	// Уникальный идентификатор счёта (UUID)
	ID string `json:"id" example:"550e8400-e29b-41d4-a716-446655440000" format:"uuid"`
	// ID владельца счёта
	UserID string `json:"user_id" example:"user-uuid" format:"uuid"`
	// Тип продукта
	Type string `json:"type" example:"checking" enums:"checking,savings,credit,deposit"`
	// Валюта (ISO 4217)
	Currency string `json:"currency" example:"RUB" enums:"RUB,USD,EUR"`
	// Доступный остаток средств
	Balance float64 `json:"balance" example:"15000.50"`
	// Текущее состояние счёта
	Status string `json:"status" example:"active" enums:"active,frozen,closed"`
	// Дата и время открытия счета (ISO 8601)
	CreatedAt string `json:"created_at" example:"2023-10-27T10:00:00Z" format:"date-time"`
}

// TransactionDTO подробная запись о движении денежных средств
type TransactionDTO struct {
	// Уникальный идентификатор операции (UUID)
	ID string `json:"id" example:"tx-uuid" format:"uuid"`
	// Тип финансового действия
	Type string `json:"type" example:"transfer" enums:"deposit,withdrawal,transfer,exchange"`
	// ID счёта, по которому прошла операция
	AccountID string `json:"account_id" example:"acc-uuid" format:"uuid"`
	// ID счёта контр-агента (только для переводов и обмена)
	ToAccountID string `json:"to_account_id,omitempty" example:"target-acc-uuid" format:"uuid"`
	// Сумма операции
	Amount float64 `json:"amount" example:"500.00"`
	// Валюта операции
	Currency string `json:"currency" example:"RUB"`
	// Назначение платежа или техническое описание
	Description string `json:"description" example:"Перевод другу"`
	// Текущий статус проводки
	Status string `json:"status" example:"completed" enums:"pending,completed,failed,blocked"`
	// Точное время совершения операции (ISO 8601)
	Timestamp string `json:"timestamp" example:"2023-10-27T10:05:00Z" format:"date-time"`
}

// ── Currency & Metals ─────────────────────────────────────────────────

// ExchangeRequest запрос на моментальный обмен валюты между счетами пользователя
type ExchangeRequest struct {
	// ID счёта списания (UUID)
	FromAccountID string `json:"from_account_id" example:"550e8400-e29b-41d4-a716-446655440001" format:"uuid" validate:"required"`
	// ID счёта зачисления (UUID)
	ToAccountID string `json:"to_account_id" example:"550e8400-e29b-41d4-a716-446655440002" format:"uuid" validate:"required"`
	// Сумма в валюте списания
	Amount float64 `json:"amount" example:"100.00" minimum:"0.01" validate:"required"`
}

// ExchangeRatesResponse содержит актуальную информацию о валютном рынке
type ExchangeRatesResponse struct {
	// Базовая валюта, относительно которой считаются курсы
	Base string `json:"base" example:"RUB"`
	// Время последнего обновления котировок (ISO 8601)
	LastUpdated string `json:"last_updated" example:"2023-10-27T10:00:00Z"`
	// Таблица курсов (Ключ - код валюты, значение - цена за 1 ед. базы)
	Rates map[string]float64 `json:"rates" example:"USD:0.0108,EUR:0.0102"`
}

// ExchangeRatePairResponse содержит курс для конкретной пары валют
type ExchangeRatePairResponse struct {
	// Валюта, которую отдаем
	Base string `json:"base" example:"RUB"`
	// Валюта, которую получаем
	Target string `json:"target" example:"USD"`
	// Значение курса (сколько target дают за 1 base)
	Rate float64 `json:"rate" example:"0.0108"`
	// Время обновления
	LastUpdated string `json:"last_updated" example:"2023-10-27T10:00:00Z"`
}

// MetalPriceDTO представляет рыночную стоимость драгоценного металла
type MetalPriceDTO struct {
	// Код металла (XAU - золото, XAG - серебро, XPT - платина, XPD - палладий)
	Metal string `json:"metal" example:"XAU" enums:"XAU,XAG,XPT,XPD"`
	// Текущая стоимость за единицу (грамм)
	Price float64 `json:"price" example:"5850.40"`
	// Единица измерения (всегда 'gram')
	Unit string `json:"unit" example:"gram"`
	// Валюта стоимости
	Currency string `json:"currency" example:"RUB"`
}

// MetalRatesResponse агрегированный ответ со списком всех котировок металлов
type MetalRatesResponse struct {
	// Время формирования котировок
	Timestamp string `json:"timestamp" example:"2023-10-27T10:00:00Z"`
	// Валюта оценки
	Base string `json:"base" example:"RUB"`
	// Список цен на поддерживаемые металлы
	Rates []MetalPriceDTO `json:"rates"`
}
