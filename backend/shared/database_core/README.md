# Database Core

Асинхронное подключение к PostgreSQL через SQLAlchemy. Предоставляет engine, фабрику сессий и FastAPI-зависимость для получения транзакционной сессии.

## Файловая архитектура
```
database_core/
├── db.py          # Engine, SessionLocal, get_session()
└── env.py         # Чтение DATABASE_URL из окружения
```

## Экспорт

### `env.py`

| Символ                       | Тип          | Описание                                  |
|------------------------------|--------------|-------------------------------------------|
| `POSTGRES_CORE_DATABASE_URL` | `Final[str]` | URL базы данных, прочитанный из окружения |

### `db.py`

| Символ         | Тип                                    | Описание                                                     |
|----------------|----------------------------------------|--------------------------------------------------------------|
| `engine`       | `AsyncEngine`                          | Асинхронный движок SQLAlchemy                                |
| `SessionLocal` | `async_sessionmaker[AsyncSession]`     | Фабрика сессий (`autoflush=False`, `expire_on_commit=False`) |
| `get_session`  | `AsyncGenerator[AsyncSession, None]`   | FastAPI Depends — открывает и закрывает сессию               |

