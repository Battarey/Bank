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

## Переменные окружения

| Переменная            | Описание                                      |
|-----------------------|-----------------------------------------------|
| `INTERNAL_API_KEY`    | Ключ внутренней авторизации                   |
| `METALS_DEV_API_KEY`  | API-ключ Metals.Dev                           |
| `METALS_DEV_BASE_URL` | Базовый URL API (`https://api.metals.dev/v1`) |
