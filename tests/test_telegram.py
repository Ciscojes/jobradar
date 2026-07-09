from app.services.telegram import get_recent_telegram_chats, send_telegram_notification


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


def test_get_recent_telegram_chats_returns_private_chats(monkeypatch):
    class FakeResponse:
        status_code = 200

        def json(self):
            return {
                "ok": True,
                "result": [
                    {
                        "message": {
                            "chat": {
                                "id": 1463980165,
                                "type": "private",
                                "first_name": "Jesus",
                                "last_name": "Granados",
                                "username": "jesus",
                            }
                        }
                    },
                    {
                        "message": {
                            "chat": {
                                "id": -100,
                                "type": "group",
                                "title": "Grupo",
                            }
                        }
                    },
                ],
            }

    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "bot-token")
    monkeypatch.setattr(
        "app.services.telegram.requests.get",
        lambda url, params, timeout: FakeResponse(),
    )

    chats, error = get_recent_telegram_chats()

    assert error is None
    assert chats == [
        {
            "id": 1463980165,
            "name": "Jesus Granados",
            "username": "jesus",
        }
    ]


def test_get_recent_telegram_chats_reports_missing_configuration(monkeypatch):
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)

    chats, error = get_recent_telegram_chats()

    assert chats == []
    assert error == "Telegram no está configurado en el servidor."
