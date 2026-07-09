from app.services.telegram import send_telegram_notification


def test_telegram_notification_is_simulated_without_credentials(monkeypatch):
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.delenv("TELEGRAM_CHAT_ID", raising=False)

    sent, status, error = send_telegram_notification("Mensaje de prueba")

    assert sent is True
    assert status == "simulated"
    assert error is None


def test_telegram_notification_sends_with_configured_credentials(monkeypatch):
    captured = {}

    class FakeResponse:
        status_code = 200
        text = "ok"

    def fake_post(url, json, timeout):
        captured["url"] = url
        captured["json"] = json
        captured["timeout"] = timeout
        return FakeResponse()

    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "bot-token")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "global-chat")
    monkeypatch.setattr("app.services.telegram.requests.post", fake_post)

    sent, status, error = send_telegram_notification("Mensaje de prueba", chat_id="user-chat")

    assert sent is True
    assert status == "sent"
    assert error is None
    assert captured["url"] == "https://api.telegram.org/botbot-token/sendMessage"
    assert captured["json"] == {
        "chat_id": "user-chat",
        "text": "Mensaje de prueba",
        "parse_mode": "Markdown",
    }
    assert captured["timeout"] == 10


def test_telegram_notification_reports_api_failure(monkeypatch):
    class FakeResponse:
        status_code = 400
        text = "bad request"

    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "bot-token")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "global-chat")
    monkeypatch.setattr(
        "app.services.telegram.requests.post",
        lambda url, json, timeout: FakeResponse(),
    )

    sent, status, error = send_telegram_notification("Mensaje de prueba")

    assert sent is False
    assert status == "failed"
    assert error == "400 - bad request"
