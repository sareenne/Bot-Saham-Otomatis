import requests
from config_fast import *

def main():
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": "TEST FINAL: cek koneksi Telegram dari GitHub Actions"
    }

    r = requests.post(url, data=payload)

    print("STATUS CODE :", r.status_code)
    print("RESPONSE    :", r.text)

    # paksa gagal kalau Telegram tidak OK
    if r.status_code != 200:
        raise Exception("Telegram send failed")

if __name__ == "__main__":
    main()
