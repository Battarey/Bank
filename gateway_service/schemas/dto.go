// Package schemas содержит DTO (Data Transfer Objects) для генерации Swagger/OpenAPI спецификации.
// Эти структуры используются ТОЛЬКО для документации, чтобы Swagger UI мог генерировать
// правильные примеры запросов (auto-fill) с нужными полями и типами.
// Сама валидация по-прежнему происходит на стороне Python-микросервисов.
package schemas

// ── Auth & Onboarding ──────────────────────────────────────────────────

// LoginPinRequest запрос на вход по PIN-коду
type LoginPinRequest struct {
	Phone string `json:"phone" example:"+79991234567" format:"phone"`
	Pin   string `json:"pin" example:"1234"`
}

// SetPinRequest запрос на установку PIN-кода
type SetPinRequest struct {
	Pin string `json:"pin" example:"1234"`
}

// RequestUnlockRequest запрос на отправку кода разблокировки
type RequestUnlockRequest struct {
	Email string `json:"email" example:"user@example.com" format:"email"`
}

// UnlockRequest запрос на разблокировку аккаунта
type UnlockRequest struct {
	Email string `json:"email" example:"user@example.com" format:"email"`
	Code  string `json:"code" example:"123456"`
}

// VerifyEmailRequest запрос на проверку email
type VerifyEmailRequest struct {
	Code string `json:"code" example:"123456"`
}

// ── Personal Data (Customer) ──────────────────────────────────────────

// PersonalDataPayload запрос на сохранение персональных данных (Шаг 1)
type PersonalDataPayload struct {
	FirstName  string `json:"first_name" example:"Иван"`
	LastName   string `json:"last_name" example:"Иванов"`
	MiddleName string `json:"middle_name,omitempty" example:"Иванович"`
	BirthDate  string `json:"birth_date" example:"1990-01-01" format:"date"`
	Gender     string `json:"gender" example:"M" enums:"M,F"`
}

// PersonalDataUpdate запрос на обновление имени
type PersonalDataUpdate struct {
	FirstName  string `json:"first_name,omitempty" example:"Петр"`
	LastName   string `json:"last_name,omitempty" example:"Петров"`
	MiddleName string `json:"middle_name,omitempty" example:"Петрович"`
}

// PassportPayload запрос на сохранение паспорта (Шаг 2)
type PassportPayload struct {
	Series              string `json:"series" example:"1234"`
	Number              string `json:"number" example:"567890"`
	IssuedBy            string `json:"issued_by" example:"ГУ МВД России"`
	IssuedAt            string `json:"issued_at" example:"2010-01-01" format:"date"`
	DivisionCode        string `json:"division_code" example:"123-456"`
	RegistrationAddress string `json:"registration_address" example:"г. Москва, ул. Пушкина"`
	ExpirationDate      string `json:"expiration_date" example:"2030-01-01" format:"date"`
}

// IdentifiersPayload запрос на сохранение ИНН и СНИЛС (Шаг 3)
type IdentifiersPayload struct {
	Inn   string `json:"inn" example:"123456789012"`
	Snils string `json:"snils" example:"12345678900"`
}

// ContactsPayload запрос на сохранение контактов (Шаг 4)
type ContactsPayload struct {
	Email string `json:"email" example:"user@example.com" format:"email"`
	Phone string `json:"phone" example:"+79991234567" format:"phone"`
}

// ContactsUpdate запрос на обновление контактов
type ContactsUpdate struct {
	Email string `json:"email,omitempty" example:"new@example.com" format:"email"`
	Phone string `json:"phone,omitempty" example:"+79990001122" format:"phone"`
}

// ── Accounts & Transactions ───────────────────────────────────────────

// OpenAccountRequest запрос на открытие счёта
type OpenAccountRequest struct {
	Type     string `json:"type" example:"checking" enums:"checking,savings,credit,deposit"`
	Currency string `json:"currency" example:"RUB" enums:"RUB,USD,EUR"`
}

// AmountPayload запрос с суммой (пополнение, снятие)
type AmountPayload struct {
	Amount float64 `json:"amount" example:"1000.50"`
}

// TransferRequest запрос на перевод средств
type TransferRequest struct {
	ToAccountID string  `json:"to_account_id" example:"550e8400-e29b-41d4-a716-446655440000" format:"uuid"`
	Amount      float64 `json:"amount" example:"500.00"`
	Description string  `json:"description,omitempty" example:"Перевод другу"`
}

// ── Currency Exchange ─────────────────────────────────────────────────

// ExchangeRequest запрос на обмен валюты
type ExchangeRequest struct {
	FromAccountID string  `json:"from_account_id" example:"from-uuid-here" format:"uuid"`
	ToAccountID   string  `json:"to_account_id" example:"to-uuid-here" format:"uuid"`
	Amount        float64 `json:"amount" example:"100.00"`
}
