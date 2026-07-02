import os
import requests

def send_telegram_notification(text: str) -> bool:
    """
    Envía un mensaje de notificación a un chat de Telegram usando el bot configurado en .env.
    Si no está configurado, imprime el mensaje en consola de forma limpia para desarrollo.
    """
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")

    if not bot_token or not chat_id or bot_token == "tu_token" or chat_id == "tu_chat_id":
        print(f"\n[TELEGRAM SIMULADO]\n{text}\n--------------------")
        return True

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "Markdown"
    }

    try:
        response = requests.post(url, json=payload, timeout=10)
        if response.status_code == 200:
            return True
        else:
            print(f"Error al enviar notificación de Telegram: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"Exception al conectar con API de Telegram: {e}")
        return False
