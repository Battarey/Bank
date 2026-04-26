# Сценарии использования (Business Flows)

В этом разделе представлены детальные схемы прохождения данных через систему для ключевых бизнес-процессов.

## 1. Процесс финансовой транзакции (Перевод)

Схема показывает путь запроса на перевод средств между счетами, включая проверки безопасности и асинхронное уведомление участников.

```mermaid
sequenceDiagram
    participant C as Клиент
    participant GW as Go Gateway
    participant TS as Transaction Service
    participant SS as Security Service
    participant DB as Postgres (Core)
    participant RMQ as RabbitMQ
    participant LS as Log/Notif Services

    C->>GW: POST /transactions/transfer (token, amount)
    GW->>GW: Валидация токена и PIN-gate
    GW->>TS: Пересылка запроса (Internal Key)
    
    activate TS
    TS->>DB: SELECT FOR UPDATE (Блокировка счетов)
    TS->>TS: Проверка баланса и лимитов
    
    TS->>SS: GET /check_transaction (AML Check)
    SS-->>TS: Результат проверки (Safe / Violation)
    
    alt Если AML нарушение
        TS->>DB: UPDATE account SET status='frozen'
        TS-->>GW: 403 Security Violation
        GW-->>C: Ошибка безопасности
    else Если все в порядке
        TS->>DB: UPDATE balances (Списание/Зачисление)
        TS->>DB: INSERT transactions (Запись лога)
        TS->>TS: Регистрация событий в UoW
        TS->>DB: COMMIT
        TS->>RMQ: Publish Events (Log, Notification)
        TS-->>GW: 201 Created
        deactivate TS
        GW-->>C: Успешный перевод
        
        RMQ-->>LS: Потребление событий
        LS->>LS: Отправка Email / Запись в ClickHouse
    end
```

## 2. Пошаговая регистрация (KYC Onboarding)

Процесс регистрации разделен на этапы для удобства пользователя. Промежуточное состояние хранится в Redis.

```mermaid
sequenceDiagram
    participant C as Клиент
    participant GW as Go Gateway
    participant CS as Customer Service
    participant R as Redis (Onboarding)
    participant DB as Postgres (Core)

    C->>GW: POST /onboarding/step1 (ФИО, почта)
    GW->>CS: Пересылка запроса
    CS->>R: JSON.SET onboarding:{id} (Шаг 1)
    CS-->>C: 200 OK (id сессии регистрации)

    C->>GW: POST /onboarding/step2 (Паспортные данные)
    GW->>CS: Пересылка запроса
    CS->>R: JSON.ARRAPPEND onboarding:{id} (Шаг 2)
    CS-->>C: 200 OK

    C->>GW: POST /onboarding/complete
    GW->>CS: Завершение регистрации
    CS->>R: JSON.GET onboarding:{id}
    CS->>DB: INSERT clients, INSERT accounts (Finalize)
    CS->>R: DEL onboarding:{id}
    CS-->>C: 201 Created (Доступ в банк открыт)
```

## 3. Мониторинг и Аудит

Все действия пользователей в системе проходят через "дуальную запись":
1.  **Синхронно**: Обновление баланса в Postgres Core для гарантированной точности.
2.  **Асинхронно**: Через RabbitMQ событие попадает в `Log Service`, который сохраняет данные в **ClickHouse** для бизнес-аналитики и в **Postgres History** для юридического аудита.
