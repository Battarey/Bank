package schemas

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
	Amount string `json:"amount" example:"1000.50" validate:"required"`
}

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
	Balance string `json:"balance" example:"15000.50"`
	// Текущее состояние счёта
	Status string `json:"status" example:"active" enums:"active,frozen,closed"`
	// Дата и время открытия счета (ISO 8601)
	CreatedAt string `json:"created_at" example:"2023-10-27T10:00:00Z" format:"date-time"`
}

// ── Specific Account Errors ───────────────────────────────────────────

// AccountNotFoundError ошибка: счёт не найден или не принадлежит пользователю
type AccountNotFoundError struct {
	Type   string `json:"type" example:"AccountNotFound"`
	Title  string `json:"title" example:"Счёт не найден"`
	Status int    `json:"status" example:"404"`
	Detail string `json:"detail" example:"Счёт с указанным ID не найден или доступ к нему запрещён"`
}

// AccountLimitReachedError ошибка: превышен лимит счетов данного типа/валюты
type AccountLimitReachedError struct {
	Type   string `json:"type" example:"AccountLimitReached"`
	Title  string `json:"title" example:"Лимит счетов превышен"`
	Status int    `json:"status" example:"403"`
	Detail string `json:"detail" example:"Вы достигли максимального количества активных счетов для данной валюты"`
}

// AccountNotOpenError ошибка: счёт не в статусе open (невозможно выполнить операцию)
type AccountNotOpenError struct {
	Type   string `json:"type" example:"AccountNotOpen"`
	Title  string `json:"title" example:"Счёт недоступен"`
	Status int    `json:"status" example:"422"`
	Detail string `json:"detail" example:"Операция невозможна, так как счёт не активен (закрыт или в процессе открытия)"`
}

// AccountNonZeroBalanceError ошибка: на счёте есть остаток (невозможно закрыть)
type AccountNonZeroBalanceError struct {
	Type   string `json:"type" example:"AccountNonZeroBalance"`
	Title  string `json:"title" example:"Баланс не нулевой"`
	Status int    `json:"status" example:"409"`
	Detail string `json:"detail" example:"Невозможно закрыть счёт с положительным балансом. Сначала выведите средства"`
}

// AccountFrozenError ошибка: счёт заморожен (все расходные операции запрещены)
type AccountFrozenError struct {
	Type   string `json:"type" example:"AccountFrozen"`
	Title  string `json:"title" example:"Счёт заморожен"`
	Status int    `json:"status" example:"403"`
	Detail string `json:"detail" example:"Операция отклонена: счёт временно заблокирован банком или владельцем"`
}

// AccountConflictError ошибка 409: попытка совершить действие, несовместимое с текущим статусом (например, заморозить уже замороженный счёт)
type AccountConflictError struct {
	Type   string `json:"type" example:"AccountConflict"`
	Title  string `json:"title" example:"Конфликт статуса"`
	Status int    `json:"status" example:"409"`
	Detail string `json:"detail" example:"Операция невозможна из-за текущего состояния счёта"`
}

// UnfreezeNotAllowedError ошибка: разморозка запрещена (счёт заморожен системой)
type UnfreezeNotAllowedError struct {
	Type   string `json:"type" example:"UnfreezeNotAllowed"`
	Title  string `json:"title" example:"Разморозка запрещена"`
	Status int    `json:"status" example:"403"`
	Detail string `json:"detail" example:"Вы не можете самостоятельно разморозить этот счёт, обратитесь в поддержку"`
}

// AccountErrorResponse устаревшая общая структура (оставлена для обратной совместимости во время рефакторинга)
type AccountErrorResponse struct {
	Type    string                 `json:"type" example:"AccountFrozen"`
	Title   string                 `json:"title" example:"Счёт заморожен"`
	Status  int                    `json:"status" example:"403"`
	Detail  string                 `json:"detail" example:"Операция невозможна: счёт временно заблокирован банком"`
	Details map[string]interface{} `json:"details,omitempty" swaggertype:"object"`
}
