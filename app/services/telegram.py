import logging
import os

import requests

logger = logging.getLogger(__name__)


def send_telegram_notification(text: str, chat_id: str | None = None) -> tuple[bool, str, str | None]:
    """
    Envía un mensaje de notificación a un chat de Telegram usando el bot configurado en .env.
    Si se pasa `chat_id` (canal de un usuario concreto) se usa ese; si no, cae al
    TELEGRAM_CHAT_ID global del .env (modo legacy de un solo canal).
    Si no hay bot configurado, simula el envío imprimiendo en consola (útil en desarrollo).

    Devuelve una tupla (enviado, status, error) donde status es "sent", "simulated" o "failed".
    """
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    resolved_chat_id = chat_id or os.getenv("TELEGRAM_CHAT_ID")

    if not bot_token or not resolved_chat_id or bot_token == "tu_token" or resolved_chat_id == "tu_chat_id":
        logger.info("Telegram notification simulated")
        return True, "simulated", None

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": resolved_chat_id,
        "text": text,
        "parse_mode": "Markdown"
    }

    try:
        response = requests.post(url, json=payload, timeout=10)
        if response.status_code == 200:
            return True, "sent", None
        else:
            error = f"{response.status_code} - {response.text}"
            logger.warning("Telegram notification failed: %s", error)
            return False, "failed", error
    except Exception as e:
        logger.exception("Telegram API connection failed: %s", e)
        return False, "failed", str(e)
