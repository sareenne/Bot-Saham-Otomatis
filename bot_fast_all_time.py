import os
import requests
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta

# === ENV TELEGRAM ===
TG_TOKEN = os.getenv("TG_TOKEN")
CHAT_ID = os.getenv("TG_CHAT_ID")

# === SAHAM SCAN (BISA DITAMBAH) ===
SAHAM_LIST = [
    "BAPA.JK",
    "BACA.JK",
    "KOKA.JK",
    "SDMU.JK",
    "CRSN.JK"
]

def send_telegram(text):
    url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": text
    }
    requests.post(url, data=payload, timeout=10)

def analisa_fast_all_time(df):
    if df is None or len(df) < 25:
        return False, {}

    df["ma5"] = df["Close"].rolling(5).mean()
    df["ma20"] = df["Close"].rolling(20).mean()
    df["avg_vol"] = df["Volume"].rolling(20).mean()
    df["high_5"] = df["High"].rolling(5).max()

    last = df.iloc[-1]
    prev_high = df["high_5"].shift(1).iloc[-1]

    body = abs(last["Close"] - last["Open"])
    rng = last["High"] - last["Low"]

    alasan = []

    if last["High"] > prev_high:
        alasan.append("Break High 5 candle")
    else:
        return False, {}

    if last["Volume"] > last["avg_vol"] * 1.5:
        alasan.append("Volume Spike")
    else:
        return False, {}

    if last["Close"] > last["ma5"] > last["ma20"]:
        alasan.append("MA 5 > MA 20")
    else:
        return False, {}

    if rng > 0 and body >= rng * 0.5:
        alasan.append("Candle kuat")
    else:
        return False, {}

    return True, {
        "harga": round(last["Close"], 2),
        "alasan": alasan
    }

def main():
    hasil = []

    for kode in SAHAM_LIST:
        try:
            df = yf.download(
                kode,
                period="5d",
                interval="15m",
                progress=False
            )

            valid, info = analisa_fast_all_time(df)

            if valid:
                msg = (
                    "🚀 FAST ALL TIME – SCALPING\n\n"
                    f"Kode   : {kode.replace('.JK','')}\n"
                    f"Harga  : {info['harga']}\n"
                    f"Waktu  : {datetime.now().strftime('%H:%M WIB')}\n\n"
                    "Analisa:\n"
                    + "\n".join([f"✔ {a}" for a in info["alasan"]]) +
                    "\n\nRencana:\n"
                    "🎯 TP : +2% – +4%\n"
                    "🛑 CL : -1%\n"
                    "⏱ Intraday only"
                )
                send_telegram(msg)
                hasil.append(kode)

        except Exception as e:
            print("ERROR", kode, e)

    if not hasil:
        send_telegram(
            "ℹ️ FAST ALL TIME\n\n"
            "Tidak ada saham lolos analisa\n"
            "Sesi pagi (09.00 – 10.30)"
        )

if __name__ == "__main__":
    main()
