




## Файловая архитектура
```
shared
├── database_core/               # Логика для подключения к основной БД
├── models/                      # Pydantic модели
├── redis_onboarding/            # Логика redis для работы с черновиками данных до попадания в основную БД
├── redis_sessions/              # Логика redis для работы с пользовательскими сессиями
└── schemas/                     # Pydantic схемы
```

