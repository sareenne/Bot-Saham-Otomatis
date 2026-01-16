import yfinance as yf
import os
from datetime import datetime
from telegram.ext import Updater, MessageHandler, Filters
from telegram import ParseMode

TOKEN = os.getenv("TELEGRAM_TOKEN")

# ===== HELPER =====
def ema(series, p):
    return series.ewm(span=p, adjust=False).mean()

def confidence(p):
    if p >= 5: return "A", "⭐⭐⭐⭐⭐"
    if p >= 3: return "B", "⭐⭐⭐⭐☆"
    return "C", "⭐⭐⭐☆☆"

def default_mode():
    jam = datetime.now().hour + datetime.now().minute / 60
    if 9 <= jam < 11.5 or 13.5 <= jam < 15:
        return "SCALPING"
    return "SWING"

# ===== ANALISA =====
def analyze(kode):
    df = yf.download(kode + ".JK", period="6mo", interval="1d", progress=False)
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

    avg_val = (df["Close"] * df["Volume"]).tail(20).mean()
    hasil = {}

    # ===== BAGGER =====
    p = 0
    if avg_val >= 25e9: p += 1
    if last["ema20"] > last["ema50"] > last["ema100"]: p += 1
    if abs(last["Close"] - last["ema50"]) / last["ema50"] <= 0.05: p += 1
    if all(prev5["Volume"].values[i] < prev5["Volume"].values[i+1] for i in range(4)): p += 1
    if (prev10["Close"].iloc[-1] - prev10["Close"].iloc[0]) / prev10["Close"].iloc[0] <= 0.15: p += 1

    if p >= 3:
        g,s = confidence(p)
        hasil["BAGGER"] = {
            "entry": last["Close"],
            "tp": last["Close"] * 1.30,
            "sl": last["Close"] * 0.93,
            "grade": g, "star": s,
            "note": "Akumulasi kuat, trend menengah baru mulai"
        }

    # ===== SWING =====
    p = 0
    if avg_val >= 20e9: p += 1
    if last["ema20"] > last["ema50"]: p += 1
    if abs(last["Close"] - last["ema20"]) / last["ema20"] <= 0.03: p += 1
    if last["Volume"] > last["vol_ma20"] * 1.5: p += 1
    if (prev3["Close"].iloc[-1] - prev3["Close"].iloc[0]) / prev3["Close"].iloc[0] <= 0.07: p += 1

    if p >= 3:
        g,s = confidence(p)
        hasil["SWING"] = {
            "entry": last["Close"],
            "tp": last["Close"] * 1.06,
            "sl": last["Close"] * 0.97,
            "grade": g, "star": s,
            "note": "Momentum awal, cocok 2–5 hari"
        }

    # ===== SCALPING =====
    p = 0
    if avg_val >= 50e9: p += 1
    if last["Volume"] > last["vol_ma20"]: p += 1
    if last["Close"] > last["ema20"]: p += 1

    if p >= 2:
        g,s = confidence(p)
        hasil["SCALPING"] = {
            "entry": last["Close"],
            "tp": last["Close"] * 1.01,
            "sl": last["Close"] * 0.995,
            "grade": g, "star": s,
            "note": "Likuid tinggi, cocok intraday"
        }

    if not hasil:
        return None, "Tidak ada setup layak saat ini"

    return hasil, None

# ===== TELEGRAM HANDLER =====
def handle(update, context):
    parts = update.message.text.upper().split()
    kode = parts[0]
    harga_beli = float(parts[1]) if len(parts) == 2 else None

    hasil, error = analyze(kode)
    if error:
        update.message.reply_text(f"❌ *{kode}*\n{error}", parse_mode=ParseMode.MARKDOWN)
        return

    default = default_mode()
    prioritas = ["BAGGER","SWING","SCALPING"]
    utama = default if default in hasil else next(m for m in prioritas if m in hasil)

    msg = f"📊 *{kode}*\n\n"
    msg += "MODE VALID:\n"
    for m in hasil:
        msg += f"- {m}\n"

    msg += f"\nRekomendasi: *{utama}* {hasil[utama]['star']} ({hasil[utama]['grade']})\n"

    if harga_beli:
        tp = harga_beli * (hasil[utama]["tp"] / hasil[utama]["entry"])
        sl = harga_beli * (hasil[utama]["sl"] / hasil[utama]["entry"])
        msg += f"\nPosisi kamu: `{harga_beli:.0f}`\nTP: `{tp:.0f}`\nSL: `{sl:.0f}`"
    else:
        for m,d in hasil.items():
            msg += f"\n{m}\nEntry `{d['entry']:.0f}` | TP `{d['tp']:.0f}` | SL `{d['sl']:.0f}`"

    msg += f"\n\n_{hasil[utama]['note']}_"
    update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)

def main():
    up = Updater(TOKEN, use_context=True)
    up.dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, handle))
    up.start_polling()
    up.idle()

if __name__ == "__main__":
    main()
