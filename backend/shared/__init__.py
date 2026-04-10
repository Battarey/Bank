"""Shared library for Bank monorepo."""

# Мы не импортируем здесь models и schemas автоматически,
# чтобы не тянуть тяжелые зависимости (SQLAlchemy) в сервисы без БД.
