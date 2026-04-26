# Bank Project

Проект представляет собой банковское веб-приложение.

Backend построен на базе микросервисов с использованием FastAPI и Go.

## Структура проекта

Проект организован в виде монорепозитория:

*   **[`backend/`](./backend/)**: Весь код бэкенда, включая микросервисы, базы данных, миграции и инфраструктуру Docker.
*   **[`docs/`](./docs/)**: Документация проекта.
*   **[`infra/`](./infra/)**: Инфраструктура проекта.
*   **[`research/`](./research/)**: Для хранения заметок, документов и результаты исследования.

## Стек технологий

*   **Backend**: Python 3.12 (FastAPI), Go 1.23 (Gateway)
*   **Databases**: PostgreSQL, Redis, MongoDB, ClickHouse
*   **Infrastructure**: Docker, RabbitMQ, Locust (Load Testing)

---

## Подробное описание:
*  Backend — **[Код и архитектура](./backend/README.md)**.
*  Архитектурные паттерны бэкенда — **[Patterns.md](./backend/Patterns.md)**.
*  Инфраструктура и стандарты — **[README инфраструктуры](./infra/README.md)**.
*  Research — **[README исследования](./research/README.md)**.

В общем: 


