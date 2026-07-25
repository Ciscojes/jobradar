import base64
import hashlib
import hmac
import logging
import os
import secrets
import time
from typing import Any

import requests

from ..config import get_settings

logger = logging.getLogger(__name__)
PLACEHOLDER_VALUES = {"", "tu_token", "tu_chat_id"}
TELEGRAM_LINK_TTL_SECONDS = 600


def _sign_token(payload: str) -> str:
    digest = hmac.new(
        get_settings().secret_key.encode("utf-8"),
        payload.encode("utf-8"),
        hashlib.sha256,
    ).digest()[:12]
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")


def _create_compact_token(payload: str) -> str:
    encoded = base64.urlsafe_b64encode(payload.encode("utf-8")).rstrip(b"=").decode("ascii")
    return f"{encoded}{_sign_token(encoded)}"


def _read_compact_token(token: str) -> str | None:
    if len(token) <= 16:
        return None
    encoded, signature = token[:-16], token[-16:]
    if not hmac.compare_digest(signature, _sign_token(encoded)):
        return None
    try:
        padding = "=" * (-len(encoded) % 4)
        return base64.urlsafe_b64decode(encoded + padding).decode("utf-8")
    except (ValueError, UnicodeDecodeError):
        return None


def _token_is_fresh(timestamp: str) -> bool:
    try:
        age = int(time.time()) - int(timestamp)
    except ValueError:
        return False
    return -30 <= age <= TELEGRAM_LINK_TTL_SECONDS


def create_telegram_link_token(user_id: int) -> str:
    payload = f"link|{user_id}|{int(time.time())}|{secrets.token_urlsafe(4)}"
    return _create_compact_token(payload)


def verify_telegram_link_token(token: str, user_id: int) -> bool:
    payload = _read_compact_token(token)
    if payload is None:
        return False
    try:
        prefix, token_user_id, timestamp, _nonce = payload.split("|", 3)
    except ValueError:
        return False
    return (
        prefix == "link"
        and token_user_id == str(user_id)
        and _token_is_fresh(timestamp)
    )


def create_telegram_channel_token(user_id: int, chat_id: str) -> str:
    return _create_compact_token(f"channel|{user_id}|{chat_id}|{int(time.time())}")


def verify_telegram_channel_token(token: str, user_id: int, chat_id: str) -> bool:
    payload = _read_compact_token(token)
    if payload is None:
        return False
    try:
        prefix, token_user_id, token_chat_id, timestamp = payload.split("|", 3)
    except ValueError:
        return False
    return (
        prefix == "channel"
        and token_user_id == str(user_id)
        and token_chat_id == str(chat_id)
        and _token_is_fresh(timestamp)
    )


def _get_bot_token() -> str | None:
    bot_token = (os.getenv("TELEGRAM_BOT_TOKEN") or "").strip()
    return None if bot_token in PLACEHOLDER_VALUES else bot_token


def send_telegram_notification(text: str, chat_id: str | None = None) -> tuple[bool, str, str | None]:
    """
    Envía un mensaje de notificación a un chat de Telegram usando el bot configurado en .env.
    Si se pasa `chat_id` (canal de un usuario concreto) se usa ese; si no, cae al
    TELEGRAM_CHAT_ID global del .env (modo legacy de un solo canal).
    Si no hay bot configurado, simula el envío imprimiendo en consola (útil en desarrollo).

    Devuelve una tupla (enviado, status, error) donde status es "sent", "simulated" o "failed".
    """
    bot_token = _get_bot_token()
    resolved_chat_id = (chat_id or os.getenv("TELEGRAM_CHAT_ID") or "").strip()

    if not bot_token or resolved_chat_id in PLACEHOLDER_VALUES:
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
    except Exception as exc:
        logger.exception("Telegram API connection failed: %s", exc)
        return False, "failed", str(exc)


def get_recent_telegram_chats(
    link_token: str,
    limit: int = 100,
) -> tuple[list[dict[str, Any]], str | None]:
    """
    Devuelve chats privados recientes que enviaron mensajes al bot oficial.
    El token nunca sale del servidor; el dashboard solo recibe chat_id y nombre.
    """
    bot_token = _get_bot_token()
    if not bot_token:
        return [], "Telegram no está configurado en el servidor."

    url = f"https://api.telegram.org/bot{bot_token}/getUpdates"
    try:
        response = requests.get(url, params={"limit": limit, "timeout": 0}, timeout=10)
    except Exception as exc:
        logger.exception("Telegram getUpdates connection failed: %s", exc)
        return [], str(exc)

    if response.status_code != 200:
        return [], f"{response.status_code} - {response.text}"

    data = response.json()
    chats: dict[int, dict[str, Any]] = {}
    for update in data.get("result", []):
        message = update.get("message") or update.get("edited_message") or {}
        if (message.get("text") or "").strip() != f"/start {link_token}":
            continue
        chat = message.get("chat") or {}
        chat_id = chat.get("id")
        if not chat_id or chat.get("type") != "private":
            continue

        full_name = " ".join(
            value
            for value in [chat.get("first_name"), chat.get("last_name")]
            if value
        )
        chats[int(chat_id)] = {
            "id": int(chat_id),
            "name": full_name or chat.get("username") or str(chat_id),
            "username": chat.get("username"),
        }

    return list(chats.values()), None
