# Repository Layer

Слой репозиториев отвечает за непосредственное взаимодействие с базой данных PostgreSQL через SQLAlchemy.

## Состав
- `currency.py`: Репозиторий для работы со счетами (`BankAccount`) и транзакциями.

## Особенности
- Использует `FOR UPDATE` для атомарной блокировки записей во время обмена, предотвращая Race Conditions.
- Сортировка ID при блокировке нескольких счетов для исключения Deadlocks.
- Наследуется от `shared.database_core.base_repository.BaseRepository`.
