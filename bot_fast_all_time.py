import yfinance as yf
import pandas as pd
import requests
from config_fast import *

SAHAM_LIST = [
    "KOKA.JK","BACA.JK","BAPA.JK","SDMU.JK","CRSN.JK",
    # tambahkan saham lain sesuai kebutuhan
]

def send_telegram(msg):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    data = {"chat_id": CHAT_ID, "text": msg}
    requests.post(url, data=data)

def fast_all_time_signal(df):
    if len(df) < 25:
        return False

    df['ma5'] = df['Close'].rolling(MA_FAST).mean()
    df['ma20'] = df['Close'].rolling(MA_SLOW).mean()
    recent_high = df['High'].rolling(LOOKBACK_HIGH).max()

    price = df['Close'].iloc[-1]
    volume = df['Volume'].iloc[-1]
    avg_vol = df['Volume'].rolling(20).mean().iloc[-1]

    candle_body = abs(df['Close'].iloc[-1] - df['Open'].iloc[-1])
    candle_range = df['High'].iloc[-1] - df['Low'].iloc[-1]

    signal = (
        PRICE_MIN <= price <= PRICE_MAX and
        df['High'].iloc[-1] > recent_high.shift(1).iloc[-1] and
        volume > avg_vol * VOL_MULTIPLIER and
        price > df['ma5'].iloc[-1] and
        df['ma5'].iloc[-1] > df['ma20'].iloc[-1] and
        candle_body >= candle_range * 0.6
    )

    return signal

def main():
    for kode
