# Общие утилиты (Utils)

Коллекция переиспользуемых функций и классов для обработки ошибок, нормализации данных и безопасности.

## Файловая архитектура
```
utils/
├── exceptions.py             # Иерархия бизнес-исключений (BaseBusinessError)
├── exceptions_handler.py     # Глобальный Middleware для FastAPI
├── normalize.py              # Функции очистки (нормализации) данных
├── security.py               # Утилиты хеширования и PIN-проверки
└── log_event.py              # Вспомогательный класс LogAction
```

## Система исключений (exceptions.py)

Все бизнес-ошибки сервисов наследуются от **`BaseBusinessError`**. Это гарантирует единообразные ответы API.
-   **`status_code`**: HTTP статус ошибки (напр. 400, 404).
-   **`title`**: Человекочитаемое сообщение об ошибке (напр. "Счёт не найден").

## Обработчик (exceptions_handler.py)

Глобальный обработчик для FastAPI.
-   **`setup_exception_handlers(app)`**: Регистрирует обработку `BaseBusinessError` во всем приложении.
-   Автоматически формирует JSON-ответ с кодом и сообщением.

## Нормализация (normalize.py)

| Функция            | Описание                           | Пример                         |
|--------------------|------------------------------------|--------------------------------|
| `normalize_name`   | Очистка и приведение ФИО к UPPER   | " иванов " → "ИВАНОВ"          |
| `normalize_email`  | Нижний регистр                     | "User@Mail.RU" → "user@mail.ru" |
| `normalize_phone`  | Удаление пробелов                  | "+7 999 123" → "+7999123"      |
| `digits_only`      | Очистка от нецифровых символов     | "123-456" → "123456"           |

## Безопасность (security.py)

-   Утилиты хеширования PIN-кодов через `bcrypt`.
-   Проверка PIN-попыток (Rate-limiting).
-   Timing-safe сравнение строк (`secrets.compare_digest`).

---

## Использование в сервисе
```python
from shared.utils import normalize, exceptions_handler

# Регистрация обработчика в main.py
exceptions_handler.setup_exception_handlers(app)

# Нормализация в схемax или сервисах
email = normalize.normalize_email(user_input)
```
