package schemas

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
