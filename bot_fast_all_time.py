import yfinance as yf
import requests
from config_fast import *

SAHAM_LIST = [
    "KOKA.JK",
    "BACA.JK",
    "BAPA.JK",
    "SDMU.JK",
    "CRSN.JK",
]

def send_telegram(text):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        payload = {
            "chat_id": CHAT_ID,
            "text": text
        }
        requests.post(url, data=payload, timeout=10)
    except Exception as e:
        print("Telegram error:", e)

def main():
    # TEST MESSAGE – PASTI TERKIRIM
    send_telegram("FAST ALL TIME BOT: START")

    for kode in SAHAM_LIST:
        try:
            df = yf.download(
                kode,
                period="10d",
                interval="1d",
                progress=False
            )

            if df is None or df.empty:
                print(kode, "DATA KOSONG")
                continue

            last_close = df["Close"].iloc[-1]
            print(kode, "OK | Close:", last_close)

        except Exception as e:
            print("ERROR DATA", kode, e)

    send_telegram("FAST ALL TIME BOT: SELESAI SCAN")

if __name__ == "__main__":
    main()
