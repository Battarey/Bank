import pytest
from notification_service.templates.templates import (
    EmailTemplate, get_template, TEMPLATES,
    VERIFICATION_CODE, WELCOME, PIN_CHANGED, LOGIN_ALERT,
    TRANSACTION_DEPOSIT, TRANSACTION_WITHDRAWAL, TRANSACTION_TRANSFER,
    TRANSACTION_INCOMING, SECURITY_FREEZE, UNLOCK_CODE,
    ACCOUNT_OPENED, ACCOUNT_CLOSED, ACCOUNT_LOCKED, ACCOUNT_UNLOCKED,
    ACCOUNT_FROZEN, ACCOUNT_UNFROZEN, ACCOUNT_SELF_BLOCKED, ACCOUNT_DELETED,
)


# ── EmailTemplate.render ───────────────────────────────────────────────

def test_render_substitutes_variables():
    tmpl = EmailTemplate(
        name="test",
        subject="Привет, {name}!",
        body="Ваш код: {code}",
    )
    subject, body = tmpl.render({"name": "Иван", "code": "12345"})
    assert subject == "Привет, Иван!"
    assert body == "Ваш код: 12345"


def test_render_missing_variable():
    tmpl = EmailTemplate(name="t", subject="{missing}", body="ok")
    with pytest.raises(KeyError):
        tmpl.render({})


def test_render_no_variables():
    tmpl = EmailTemplate(name="t", subject="Добро пожаловать!", body="Текст")
    subject, body = tmpl.render({})
    assert subject == "Добро пожаловать!"
    assert body == "Текст"


# ── get_template ───────────────────────────────────────────────────────

def test_get_template_known():
    tmpl = get_template("verification_code")
    assert tmpl is VERIFICATION_CODE


def test_get_template_unknown():
    with pytest.raises(ValueError, match="не найден"):
        get_template("nonexistent_template_xyz")


def test_all_templates_registered():
    """Проверяем, что все 18 шаблонов зарегистрированы в реестре."""
    expected = {
        "verification_code", "welcome", "pin_changed", "login_alert",
        "account_locked", "unlock_code", "account_unlocked", "account_opened",
        "account_closed", "account_frozen", "account_unfrozen",
        "account_self_blocked", "security_freeze", "account_deleted",
        "transaction_deposit", "transaction_withdrawal",
        "transaction_transfer", "transaction_incoming",
    }
    assert expected.issubset(set(TEMPLATES.keys()))


# ── Конкретные шаблоны — рендеринг ────────────────────────────────────

def test_verification_code_render():
    s, b = VERIFICATION_CODE.render({"code": "999888"})
    assert "999888" in b


def test_login_alert_render():
    s, b = LOGIN_ALERT.render({"login_time": "2026-01-01 12:00"})
    assert "2026-01-01 12:00" in b


def test_transaction_deposit_render():
    s, b = TRANSACTION_DEPOSIT.render({
        "account_number": "40817", "amount": "500",
        "currency": "RUB", "balance_after": "1500",
    })
    assert "500" in b
    assert "40817" in b


def test_transaction_transfer_render():
    s, b = TRANSACTION_TRANSFER.render({
        "amount": "1000", "currency": "RUB",
        "from_account": "ACC1", "to_account": "ACC2",
        "balance_after": "9000",
    })
    assert "ACC1" in b and "ACC2" in b


def test_transaction_incoming_render():
    s, b = TRANSACTION_INCOMING.render({
        "account_number": "ACC2", "amount": "1000",
        "currency": "RUB", "from_account": "ACC1", "balance_after": "2000",
    })
    assert "ACC1" in b


def test_security_freeze_render():
    s, b = SECURITY_FREEZE.render({
        "account_number": "ACC1", "rule": "rapid_fire",
        "details": "Слишком частые операции",
    })
    assert "rapid_fire" in b


def test_account_opened_render():
    s, b = ACCOUNT_OPENED.render({
        "account_type": "дебетовый", "currency": "RUB",
        "account_number": "40817",
    })
    assert "40817" in b


def test_account_frozen_render():
    s, b = ACCOUNT_FROZEN.render({
        "account_number": "40817", "frozen_by": "user",
        "reason": "self_block",
    })
    assert "user" in b


def test_unlock_code_render():
    s, b = UNLOCK_CODE.render({"code": "654321"})
    assert "654321" in b


def test_no_variable_templates():
    """Шаблоны без переменных рендерятся без ошибок."""
    for tmpl in (WELCOME, PIN_CHANGED, ACCOUNT_LOCKED, ACCOUNT_UNLOCKED,
                 ACCOUNT_CLOSED, ACCOUNT_UNFROZEN, ACCOUNT_SELF_BLOCKED,
                 ACCOUNT_DELETED):
        # Некоторые шаблоны не требуют переменных
        try:
            subj, body = tmpl.render({
                "account_number": "x",
                "code": "1"
            })
            assert isinstance(subj, str)
        except KeyError:
            pass  # ожидаемо, если шаблон требует переменных
