from uuid import uuid4

import pytest

from log_service.core.schemas import LogEvent, LogPayload


@pytest.mark.asyncio
async def test_process_log_success(log_service, mock_postgres_repo, mock_clickhouse_repo):
	"""Успешная обработка лога — запись в оба хранилища."""
	payload = LogPayload(
		user_id=uuid4(),
		action="test_action",
		service="test_service",
		details="test_details",
	)
	event = LogEvent(type="test_type", payload=payload)

	await log_service.process_log(event)

	mock_postgres_repo.save_action.assert_awaited_once_with(payload)
	mock_clickhouse_repo.save_event.assert_awaited_once_with("test_type", payload)


@pytest.mark.asyncio
async def test_process_log_one_fails(log_service, mock_postgres_repo, mock_clickhouse_repo):
	"""Ошибка в одном из хранилищ не прерывает запись в другое."""
	payload = LogPayload(
		user_id=uuid4(),
		action="test_action",
		service="test_service",
	)
	event = LogEvent(type="test_type", payload=payload)

	mock_postgres_repo.save_action.side_effect = Exception("DB error")

	await log_service.process_log(event)

	mock_postgres_repo.save_action.assert_awaited_once()
	mock_clickhouse_repo.save_event.assert_awaited_once()
