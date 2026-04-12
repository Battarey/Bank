#!/bin/bash
set -e

# Пути внутри контейнера:
# /app - корень backend
# /infra_audit - примонтированная папка с конфигами

echo "--- 🛠️ Установка инструментов аудита ---"
pip install --no-cache-dir -r /infra_audit/requirements.txt

# Временно копируем pyproject.toml в корень проекта, чтобы инструменты нашли его автоматически
cp /infra_audit/pyproject.toml /app/pyproject.toml

# Функция для очистки при выходе
cleanup() {
    rm -f /app/pyproject.toml
}
trap cleanup EXIT

printf "\n--- 🧹 Ruff: Проверка стиля и импортов ---\n"
ruff check .

printf "\n--- 🎨 Ruff: Проверка форматирования ---\n"
ruff format . --check

printf "\n--- 🦅 Vulture: Поиск мертвого кода ---\n"
vulture .

printf "\n--- 📦 Deptry: Аудит зависимостей по сервисам ---\n"
SERVICES="account_service auth_service currency_service customer_service gateway_service log_service metal_service notification_service security_service transaction_service"

for service in $SERVICES; do
    if [ -d "$service" ]; then
        printf "\n🔍 Проверка $service...\n"
        deptry "$service" --requirements-files "$service/requirements.txt"
    fi
done

printf "\n✅ Аудит завершен!\n"
