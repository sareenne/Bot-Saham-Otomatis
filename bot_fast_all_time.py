import os
import requests

def main():
    # Ambil dari GitHub Secrets
    tg_token = os.getenv("TG_TOKEN")
    chat_id = os.getenv("TG_CHAT_ID")

    print("TOKEN ADA?", bool(tg_token))
    print("CHAT_ID ADA?", bool(chat_id))

    if not tg_token or not chat_id:
        print("ERROR: Token atau Chat ID tidak terbaca")
        return

    url = f"https://api.telegram.org/bot{tg_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": "TEST BERHASIL: Telegram dari GitHub Actions"
    }

    try:
        response = requests.post(url, data=payload, timeout=10)
        print("STATUS CODE:", response.status_code)
        print("RESPONSE:", response.text)
    except Exception as e:
        print("REQUEST ERROR:", e)

if __name__ == "__main__":
    main()
