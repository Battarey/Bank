"""Репозиторий для хранения событий безопасности в MongoDB."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from shared.bootstrap import get_container
from shared.mongodb_core import get_mongodb

logger = logging.getLogger("security_service")


def get_mongo_repo() -> SecurityEventRepository:
    """Зависимость для получения репозитория событий безопасности."""
    settings = get_container().settings
    return SecurityEventRepository(collection_name=settings.SECURITY_COLLECTION)


class SecurityEventRepository:
    """Репозиторий для работы с журналом событий безопасности (AML)."""

    def __init__(self, collection_name: str):
        self.db = get_mongodb()
        self.collection_name = collection_name

    async def save_event(
        self,
        *,
        account_id: str,
        rule: str,
        details: dict[str, Any],
        action: str,
        threshold: str | None = None,
        actual: str | None = None,
    ) -> None:
        """Сохранить событие безопасности.

        Args:
            account_id: ID счёта.
            rule: Сработавшее правило.
            details: Подробности срабатывания.
            action: Предпринятое действие.
            threshold: Пороговое значение.
            actual: Фактическое значение.
        """
        doc = {
            "account_id": account_id,
            "rule": rule,
            "details": details,
            "action": action,
            "threshold": threshold,
            "actual": actual,
            "created_at": datetime.now(UTC),
        }
        try:
            await self.db[self.collection_name].insert_one(doc)
            logger.info(
                "Security event saved: rule=%s, account=%s, action=%s",
                rule,
                account_id,
                action,
            )
        except Exception:
            logger.exception(
                "Не удалось сохранить событие безопасности в MongoDB: rule=%s",
                rule,
            )
