# Metal Service

Внутренний сервис драгоценных металлов. Предоставляет актуальные цены на золото (XAU), серебро (XAG), платину (XPT) и палладий (XPD) через Metals.Dev API. Ничего не сохраняется в БД.

## Структура

```
metal_service/
├── main.py              # Точка входа FastAPI, подключение роутеров
├── metal_client.py      # Клиент Metals.Dev API, кэширование
├── exceptions.py        # Исключения сервиса (MetalError, RateUnavailable)
├── rates/               # Модуль просмотра цен на металлы
├── tests/               # Тесты
├── Dockerfile
└── requirements.txt
```

## Функциональность

- `GET /metals/rates?base=RUB` — цены всех металлов за грамм в указанной валюте

## Ценообразование

Цены получаются из Metals.Dev API (`/v1/latest`):
- Запрос с параметром `unit=g` — API сразу возвращает цену за 1 грамм
- Поддерживаемые металлы: gold → XAU, silver → XAG, platinum → XPT, palladium → XPD

## Конфигурация

Сервис использует внешние API для получения цен на металлы.

Подробное описание:
- **[Интеграция с Metals.Dev API](../../infra/docs/external_integrations.md#1-metalsdev-api-metal-service)**
- **[Справочник переменных окружения](../../infra/env/README.md)**
