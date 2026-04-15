from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from shared.schemas import NotificationPayload, NotificationTask


@pytest.mark.asyncio
@patch("notification_service.service.send_email", AsyncMock())
@patch("notification_service.service.get_template")
async def test_process_notification_success(mock_get_template, notification_service, mock_repo):
	"""Успешная обработка уведомления — рендеринг, отправка и сохранение."""
	task = NotificationTask(
		type="test_type", payload=NotificationPayload(to="test@example.com", variables={"name": "Test User"})
	)

	mock_template = MagicMock()
	mock_template.render.return_value = ("Subject", "Body", None)
	mock_get_template.return_value = mock_template

	await notification_service.process_notification(task)

	# Проверка вызова шаблонизатора
	mock_get_template.assert_called_once_with("test_type")
	mock_template.render.assert_called_once_with({"name": "Test User"})

	# Проверка сохранения в БД
	mock_repo.save.assert_awaited_once_with(
		msg_type="test_type",
		to="test@example.com",
		subject="Subject",
		body="Body",
		variables={"name": "Test User"},
		status="sent",
	)


@pytest.mark.asyncio
@patch("notification_service.service.send_email")
@patch("notification_service.service.get_template")
async def test_process_notification_error(mock_get_template, mock_send_email, notification_service, mock_repo):
	"""Ошибка при обработке (например, SMTP) — уведомление помечается как проваленное."""
	task = NotificationTask(
		type="test_type", payload=NotificationPayload(to="test@example.com", variables={"name": "Test User"})
	)

	mock_template = MagicMock()
	mock_template.render.return_value = ("Subject", "Body", None)
	mock_get_template.return_value = mock_template

	# SMTP бросает исключение
	mock_send_email.side_effect = Exception("SMTP error")

	await notification_service.process_notification(task)

	# Проверка сохранения ошибки в БД
	mock_repo.save.assert_awaited_once_with(
		msg_type="test_type",
		to="test@example.com",
		subject="",
		body="",
		variables={"name": "Test User"},
		status="failed",
		error="SMTP error",
	)
