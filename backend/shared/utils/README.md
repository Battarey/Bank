# Utils

Переиспользуемые утилиты нормализации данных. Используются в `customer_service` (онбординг и обновление данных).

## Файловая архитектура
```
utils/
├── __init__.py
├── normalize.py     # Функции нормализации ФИО, email, телефона, ИНН/СНИЛС
└── README.md
```

## Экспорт (`normalize.py`)

| Функция            | Сигнатура                     | Описание                        |
|--------------------|-------------------------------|---------------------------------|
| `normalize_name`   | `(str \| None) → str \| None` | `.strip().upper()` (ФИО)        |
| `normalize_email`  | `(str) → str`                 | `.lower()`                      |
| `normalize_phone`  | `(str) → str`                 | Удаление пробелов               |
| `digits_only`      | `(str) → str`                 | Только цифры (ИНН, СНИЛС)       |

## Кто использует

| Модуль                                 | Функции                                                               |
|----------------------------------------|-----------------------------------------------------------------------|
| `customer_service/create_account`      | `normalize_name`, `normalize_email`, `normalize_phone`, `digits_only` |
| `customer_service/update_user_data`    | `normalize_name`, `normalize_email`, `normalize_phone`                |

## Использование

```python
from shared.utils.normalize import normalize_name, normalize_email, normalize_phone, digits_only

name = normalize_name("  иванов  ")     # "ИВАНОВ"
email = normalize_email("User@Mail.RU") # "user@mail.ru"
phone = normalize_phone("+7 999 123 45 67")  # "+79991234567"
inn = digits_only("1234-5678-9012")     # "123456789012"
```
