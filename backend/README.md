# Банковская Платформа (Backend)

![Python 3.12](https://img.shields.io/badge/python-3.12-blue.png)
![FastAPI](https://img.shields.io/badge/FastAPI-0.109+-009688.png)
![Architecture: Clean/Layered](https://img.shields.io/badge/Architecture-Clean%2FLayered-blueviolet.png)
![Go 1.23](https://img.shields.io/badge/go-1.23-00ADD8.png)

Централизованная банковская экосистема, построенная на микросервисной архитектуре. Система реализует современные архитектурные паттерны: **Domain-Driven Design (DDD)**, **Unit of Work**, **CQRS** и **Event-Driven Architecture (EDA)**.

## Файловая архитектура

```text
backend/
├── account_service/      # Жизненный цикл банковских счетов
├── auth_service/         # Аутентификация, сессии и безопасность
├── currency_service/     # Валютные котировки и конвертация
├── customer_service/     # Управление профилями клиентов (KYC)
├── gateway_service/      # API Gateway (Go / Echo)
├── log_service/          # Централизованный аудит и аналитика
├── notification_service/ # Система уведомлений (Email)
├── security_service/     # Антифрод-мониторинг и AML
├── metal_service/        # Котировки драгоценных металлов
├── shared/               # Ядро инфраструктуры (DB, RabbitMQ, Utils)
├── migrations/           # Управление схемами баз данных
├── README.md             # Общий обзор системы
└── Patterns.md           # Архитектурные стандарты и паттерны
```

## Технологический Стек

-   **Языки**: Go 1.23 (Gateway), Python 3.12 (Бизнес-логика).
-   **Фреймворки**: Echo (Go), FastAPI (Python).
-   **Хранилища**: 
    - PostgreSQL 17 (Core & History)
    - Redis Stack (Sessions & Onboarding)
    - MongoDB 7 (Logs)
    - ClickHouse 24 (Analytics)
-   **Брокер**: RabbitMQ 3.13.
-   **Контейнеризация**: Docker, Docker Compose.

---

## Архитектура Системы

```mermaid
graph TD
    Client[Клиент] --> GW[Gateway Service :8000]
    
    subgraph "Бизнес-Сервисы (Python)"
        GW --> Auth[Auth Service]
        GW --> Cust[Customer Service]
        GW --> Acc[Account Service]
        GW --> Trans[Transaction Service]
        GW --> Curr[Currency Service]
    end
    
    subgraph "Инфраструктура Данных"
        Acc & Trans & Auth --> PG_CORE[(PostgreSQL Core)]
        Cust --> Redis_ON[(Redis Onboarding)]
        Auth --> Redis_SESS[(Redis Sessions)]
    end
    
    subgraph "Событийная Модель (EDA)"
        Acc & Trans & Auth -- Domain Events --> RMQ[RabbitMQ]
        RMQ -- notifications --> Notif[Notification Service]
        RMQ -- logs --> LogS[Log Service]
    end
    
    Notif --> SMTP[Gmail SMTP]
    Notif --> MongoDB[(MongoDB Log)]
    LogS --> PG_HIST[(PostgreSQL History)]
    LogS --> CH[(ClickHouse Analytics)]
    
    Trans -- AML Check --> Sec[Security Service]
```

---

## Описание Сервисов

### 1. Gateway Service (Go)
Единая точка входа. Выполняет маршрутизацию, динамическую валидацию UUID, проверку сессий в Redis и блокировку по PIN-коду. Обеспечивает безопасность внутренних вызовов через инъекцию `X-Internal-Key`.

### 2. Account Service
Управление жизненным циклом счетов. Реализует логику генерации 20-значных номеров по банковскому стандарту, управление лимитами по валютам и каскадные блокировки аккаунтов.

### 3. Transaction Service
Финансовое ядро системы. Гарантирует атомарность операций через паттерн Unit of Work, предотвращает взаимные блокировки (Deadlocks) и обеспечивает идемпотентность платежей.

### 4. Auth Service
Сервис безопасности и контроля доступа. Отвечает за bcrypt-хеширование PIN-кодов, управление жизненным циклом сессий в Redis и автоматическую блокировку при признаках Brute-force.

### 5. Customer Service
Управление данными пользователей и KYC. Реализует пошаговый онбординг с сохранением промежуточных состояний в Redis Stack и шифрованием персональных данных (PII).

### 6. Security Service (AML/CFT)
Выполняет превентивный анализ транзакций по набору правил (Large Tx, Rapid Fire, Structuring). Позволяет автоматически замораживать счета при обнаружении подозрительной активности.

### 7. Notification & Log Services
Асинхронные потребители событий. `Notification` обеспечивает коммуникацию с клиентом, а `Log` реализует дуальную запись для аудита (Postgres) и бизнес-аналитики (ClickHouse).

---

## Безопасность

Проект реализует многоуровневую систему защиты:
1.  **Transport**: Изоляция сервисов во внутренней Docker-сети.
2.  **Authentication**: Проверка `X-Session-Token` на уровне Middleware.
3.  **Authorization**: Доступ к финансовым операциям защищен PIN-gate.
4.  **Integrity**: Межсервисное взаимодействие валидируется через `X-Internal-Key`.

---

## Документация
- **[Инфраструктура и запуск](../infra/README.md)**
- **[Архитектурные паттерны](./Patterns.md)**
- **[API & AML Стандарты](../infra/docs/api_standards.md)**
