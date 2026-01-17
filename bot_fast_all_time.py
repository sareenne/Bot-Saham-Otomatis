import yfinance as yf
import pandas as pd
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
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": text,
        "parse_mode": "HTML"
    }
    requests.post(url, data=payload, timeout=10)

def fast_all_time_signal(df):
    if df is None or df.empty or len(df) < 25:
        return False, "Data kosong"

    df['ma5'] = df['Close'].rolling(MA_FAST).mean()
    df['ma20'] = df['Close'].rolling(MA_SLOW).mean()
    df['avg_vol'] = df['Volume'].rolling(20).mean()
    df['recent_high'] = df['High'].rolling(LOOKBACK_HIGH).max()

    last = df.iloc[-1]
    prev_high = df['recent_high'].shift(1).iloc[-1]

    if not (PRICE_MIN <= last['Close'] <= PRICE_MAX):
        return False, "Harga di luar range"

    if last['High'] <= prev_high:
        return False, "Tidak break high"

    if last['Volume'] <= last['avg_vol'] * VOL_MULTIPLIER:
        return False, "Volume tidak spike"

    if not (last['Close'] > last['ma5'] > last['ma20']):
        return False, "MA belum align"

    body = abs(last['Close'] - last['Open'])
    rng = last['High'] - last['Low']
    if rng == 0 or body < rng * 0.4:
        return False, "Candle lemah"

    return True, "VALID"

def main():
    # === TEST MESSAGE (PASTI MASUK TELEGRAM) ===
    send_telegram("✅ <b>FAST ALL TIME BOT AKTIF</b>\nBot berhasil dijalankan di GitHub Actions.")

    hasil = []

    for kode in SAHAM_LIST:
        try:
            df = yf.download(
                kode,
                period=PERIOD,
                interval=TIMEFRAME,
                auto_adjust=True,_
