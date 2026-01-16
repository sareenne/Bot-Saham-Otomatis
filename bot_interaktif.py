import yfinance as yf
import pandas as pd
import os
from datetime import datetime
from telegram.ext import Updater, MessageHandler, Filters
from telegram import ParseMode

TOKEN = os.getenv("TELEGRAM_TOKEN")

# ================= HELPER =================
def ema(series, period):
    return series.ewm(span=period, adjust=False).mean()

def confidence_score(points):
    if points >= 5:
        return "A", "⭐⭐⭐⭐⭐"
    if points >= 3:
        return "B", "⭐⭐⭐⭐☆"
    return "C", "⭐⭐⭐☆☆"

def default_mode_by_time():
    jam = datetime.now().hour + datetime.now().minute / 60
    if 9 <= jam < 11.5:
        return "SCALPING"
    if 11.5 <= jam < 13.5:
        return "SWING"
    if 13.5 <= jam < 15:
        return "SCALPING"
    if 15 <= jam < 18:
        return "SWING"
    return "BAGGER"

# ================= CORE ANALYSIS =================
def analisa_saham(kode):
    ticker = kode.upper() + ".JK"
    df = yf.download(ticker, period="6mo", interval="1d", progress=False)

    if df.empty or len(df) < 120:
        return None, "Data tidak cukup / kode salah"

    df["ema20"] = ema(df["Close"], 20)
    df["ema50"] = ema(df["Close"], 50)
    df["ema100"] = ema(df["Close"], 100)
    df["vol_ma20"] = df["Volume"].rolling(20).mean()

    last = df.iloc[-1]
    prev3 = df.iloc[-4:-1]
    prev5 = df.iloc[-6:-1]
    prev10 = df.iloc[-11:-1]

    avg_value = (df["Close"] * df["Volume"]).tail(20).mean()
    hasil = {}

    # ================= BAGGER =================
    points = 0
    vol_acc = all(prev5["Volume"].values[i] < prev5["Volume"].values[i+1] for i in range(4))
    price_10d = (prev10["Close"].iloc[-1] - prev10["Close"].iloc[0]) / prev10["Close"].iloc[0]
    near_ema50 = abs(last["Close"] - last["ema50"]) / last["ema50"] <= 0.05

    if avg_value >= 25e9: points += 1
    if last["ema20"] > last["ema50"] > last["ema100"]: points += 1
    if near_ema50: points += 1
    if vol_acc: points += 1
    if price_10d <= 0.15: points += 1

    if points >= 3:
        grade, star = confidence_score(points)
        entry = last["Close"]
        hasil["BAGGER"] = {
            "entry": entry, "tp": entry * 1.30, "sl": entry * 0.93,
            "grade": grade, "star": star,
            "note": "Akumulasi kuat & trend menengah baru mulai"
        }

    # ================= SWING =================
    points = 0
    price_3d = (prev3["Close"].iloc[-1] - prev3["Close"].iloc[0]) / prev3["Close"].iloc[0]
    near_ema20 = abs(last["Close"] - last["ema20"]) / last["ema20"] <= 0.03

    if avg_value >= 20e9: points += 1
    if last["ema20"] > last["ema50"]: points += 1
    if near_ema20: points += 1
    if last["Volume"] > last["vol_ma20"] * 1.5: points += 1
    if price_3d <= 0.07: points += 1

    if points >= 3:
        grade, star = confidence_score(points)
        entry = last["Close"]
        hasil["SWING"] = {
            "entry": entry, "tp": entry * 1.06, "sl": entry * 0.97,
            "grade": grade, "star": star,
            "note": "Momentum awal, cocok swing 2–5 hari"
        }

    # ================= SCALPING =================
    points = 0
    if avg_value >= 50e9: points += 1
    if last["Volume"] > last["vol_ma20"]: points += 1
    if last["Close"] > last["ema20"]: points += 1

    if points >= 2:
        grade, star = confidence_score(points)
        entry = last["Close"]
        hasil["SCALPING"] = {
            "entry": entry, "tp": entry * 1.01, "sl": entry * 0.995,
            "grade": grade, "star": star,
            "note": "Likuid tinggi, cocok intraday"
        }

    if not hasil:
        return None, "Tidak direkomendasikan"

    return hasil, None

# ================= HANDLER =================
def handle_message(update, context):
    kode = update.message.text.strip().upper()
    hasil, error = analisa_saham(kode)

    if error:
        update.message.reply_text(f"❌ *{kode}*\n{error}", parse_mode=ParseMode.MARKDOWN)
        return

    default_mode = default_mode_by_time()
    priority = ["BAGGER", "SWING", "SCALPING"]
    utama = default_mode if default_mode in hasil else next(m for m in priority if m in hasil)

    pesan = f"📊 *{kode}*\n\n✅ *MODE VALID:*\n"
    for m in hasil:
        icon = "🔥" if m == "BAGGER" else "🟡" if m == "SWING" else "🔵"
        pesan += f"{icon} {m}\n"

    pesan += f"\n⏰ Default jam sekarang: *{default_mode}*\n"
    pesan += f"⭐ *Rekomendasi utama:* {utama} | {hasil[utama]['star']} ({hasil[utama]['grade']})\n\n"

    for m, d in hasil.items():
        icon = "🔥" if m == "BAGGER" else "🟡" if m == "SWING" else "🔵"
        pesan += (
            f"──────────────\n"
            f"{icon} *{m}*\n"
            f"Entry : `{d['entry']:.0f}`\n"
            f"TP    : `{d['tp']:.0f}`\n"
            f"SL    : `{d['sl']:.0f}`\n"
        )

    pesan += f"\n📌 _{hasil[utama]['note']}_"
    update.message.reply_text(pesan, parse_mode=ParseMode.MARKDOWN)

# ================= MAIN =================
def main():
    updater = Updater(TOKEN, use_context=True)
    updater.dispatcher.add_handler(
        MessageHandler(Filters.text & ~Filters.command, handle_message)
    )
    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()
