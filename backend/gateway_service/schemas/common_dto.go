package schemas

// ErrorResponse базовая структура ошибки (RFC 7807)
type ErrorResponse struct {
	Type    string                 `json:"type" example:"BaseBusinessError"`
	Title   string                 `json:"title" example:"Ошибка бизнес-логики"`
	Status  int                    `json:"status" example:"400"`
	Detail  string                 `json:"detail" example:"Описание ошибки"`
	Details map[string]interface{} `json:"details,omitempty" swaggertype:"object"`
}

// UnauthorizedErrorResponse ошибка: не указан или невалиден токен сессии
type UnauthorizedErrorResponse struct {
	Type   string `json:"type" example:"Unauthorized"`
	Title  string `json:"title" example:"Не авторизован"`
	Status int    `json:"status" example:"401"`
	Detail string `json:"detail" example:"Для доступа к ресурсу необходимо войти в систему"`
}

// ForbiddenErrorResponse ошибка: доступ запрещён (недостаточно прав или заблокирован)
type ForbiddenErrorResponse struct {
	Type   string `json:"type" example:"Forbidden"`
	Title  string `json:"title" example:"Доступ запрещён"`
	Status int    `json:"status" example:"403"`
	Detail string `json:"detail" example:"У вас нет прав для выполнения этой операции"`
}

// NotFoundErrorResponse ошибка: запрашиваемый ресурс не найден
type NotFoundErrorResponse struct {
	Type   string `json:"type" example:"ResourceNotFound"`
	Title  string `json:"title" example:"Ресурс не найден"`
	Status int    `json:"status" example:"404"`
	Detail string `json:"detail" example:"Запрашиваемый объект (счёт, транзакция, профиль) не существует"`
}

// ConflictErrorResponse ошибка: конфликт состояния (например, объект уже существует)
type ConflictErrorResponse struct {
	Type   string `json:"type" example:"Conflict"`
	Title  string `json:"title" example:"Конфликт данных"`
	Status int    `json:"status" example:"409"`
	Detail string `json:"detail" example:"Операция невозможна из-за текущего состояния ресурса"`
}

// ValidationErrorResponse ошибка валидации входных данных
type ValidationErrorResponse struct {
	Type    string                 `json:"type" example:"ValidationError"`
	Title   string                 `json:"title" example:"Ошибка валидации"`
	Status  int                    `json:"status" example:"400"`
	Detail  string                 `json:"detail" example:"Некорректное значение одного или нескольких полей запроса"`
	Details map[string]interface{} `json:"details,omitempty" swaggertype:"object"`
}

// BadGatewayErrorResponse ошибка 502 (проблема с внешним сервисом)
type BadGatewayErrorResponse struct {
	Type   string `json:"type" example:"BadGateway"`
	Title  string `json:"title" example:"Внешний сервис недоступен"`
	Status int    `json:"status" example:"502"`
	Detail string `json:"detail" example:"Не удалось получить данные от внешнего поставщика (курсы валют, котировки металлов)"`
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

// HealthErrorResponse описание ошибки при недоступности зависимостей
type HealthErrorResponse struct {
	// Статус ошибки ('error')
	Status string `json:"status" example:"error"`
	// Детальное описание проблемы
	Detail string `json:"detail" example:"Redis (sessions) non-responsive"`
}
