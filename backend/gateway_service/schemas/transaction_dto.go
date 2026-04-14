package schemas

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

// TransactionErrorResponse ошибка при выполнении транзакции (бизнес-логика)
type TransactionErrorResponse struct {
	Type    string                 `json:"type" example:"InsufficientFunds"`
	Title   string                 `json:"title" example:"Недостаточно средств"`
	Status  int                    `json:"status" example:"422"`
	Detail  string                 `json:"detail" example:"На счёте недостаточно средств для совершения перевода"`
	Details map[string]interface{} `json:"details,omitempty" swaggertype:"object"`
}

// AccountFrozenErrorResponse ошибка 403 (счет заморожен)
type AccountFrozenErrorResponse struct {
	Type   string `json:"type" example:"AccountFrozen"`
	Title  string `json:"title" example:"Счёт заморожен"`
	Status int    `json:"status" example:"403"`
	Detail string `json:"detail" example:"Операция невозможна, так как счёт временно заморожен или заблокирован"`
}

// SecurityViolationErrorResponse ошибка 403 (отклонено антифродом/безопасностью)
type SecurityViolationErrorResponse struct {
	Type   string `json:"type" example:"SecurityViolation"`
	Title  string `json:"title" example:"Операция отклонена"`
	Status int    `json:"status" example:"403"`
	Detail string `json:"detail" example:"Операция отклонена системой безопасности банка. Обратитесь в поддержку."`
}

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


