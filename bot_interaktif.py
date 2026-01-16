import yfinance as yf
import os
from datetime import datetime
from telegram.ext import Updater, MessageHandler, Filters
from telegram import ParseMode

TOKEN = os.getenv("TELEGRAM_TOKEN")

# ================= HELPER =================
def ema(series, p):
    return series.ewm(span=p, adjust=False).mean()

def confidence(p):
    if p >= 5:
        return "A", "⭐⭐⭐⭐⭐"
    if p >= 3:
        return "B", "⭐⭐⭐⭐☆"
    return "C", "⭐⭐⭐☆☆"

def default_mode():
    jam = datetime.now().hour + datetime.now().minute / 60
    if 9 <= jam < 11.5 or 13.5 <= jam < 15:
        return "SCALPING"
    return "SWING"

# ================= ANALISA =================
def analyze(kode):
    ticker = kode.upper() + ".JK"
    df = yf.download(ticker, period="6mo", interval="1d", progress=False)

    if df.empty or len(df) < 120:
        return None, "Data tidak cukup / kode salah"

    df["ema20"] = ema(df["Close"], 20)
    df["ema50"] = ema(df["Close"], 50)
    df["ema100"] = ema(df["Close"], 100)
    df["vol_ma20"] = df["Volume"].rolling(20).mean()

    last = df.iloc[-1]

    # === SEMUA DIJADIKAN FLOAT (AMAN) ===
    close = float(last["Close"])
    ema20 = float(last["ema20"])
    ema50 = float(last["ema50"])
    ema100 = float(last["ema100"])
    volume = float(last["Volume"])
    vol_ma20 = float(last["vol_ma20"])

    # nilai transaksi rata-rata (scalar)
    avg_value = float((df["Close"] * df["Volume"]).tail(20).mean())

    hasil = {}

    # ===== BAGGER =====
    p = 0
    if avg_value >= 25_000_000_000:
        p += 1
    if ema20 > ema50 and ema50 > ema100:
        p += 1
    if abs(close - ema50) / ema50 <= 0.05:
        p += 1

    # cek volume naik TANPA all() / loop Series
    vol5 = df["Volume"].tail(5).values
    if vol5[4] > vol5[3] > vol5[2] > vol5[1] > vol5[0]:
        p += 1

    # harga 10 hari masih konsolidasi
    close10 = df["Close"].tail(10).values
    if (close10[-1] - close10[0]) / close10[0] <= 0.15:
        p += 1

    if p >= 3:
        g, s = confidence(p)
        hasil["BAGGER"] = {
            "entry": close,
            "tp": close * 1.30,
            "sl": close * 0.93,
            "grade": g,
            "star": s,
            "note": "Akumulasi kuat, trend menengah baru mulai"
        }

    # ===== SWING (2–5 HARI) =====
    p = 0
    if avg_value >= 20_000_000_000:
        p += 1
    if ema20 > ema50:
        p += 1
    if abs(close - ema20) / ema20 <= 0.03:
        p += 1
    if volume > vol_ma20 * 1.5:
        p += 1

    close3 = df["Close"].tail(3).values
    if (close3[-1] - close3[0]) / close3[0] <= 0.07:
        p += 1

    if p >= 3:
        g, s = confidence(p)
        hasil["SWING"] = {
            "entry": close,
            "tp": close * 1.06,
            "sl": close * 0.97,
            "grade": g,
            "star": s,
            "note": "Momentum awal, cocok 2–5 hari"
        }

    # ===== SCALPING =====
    p = 0
    if avg_value >= 50_000_000_000:
        p += 1
    if volume > vol_ma20:
        p += 1
    if close > ema20:
        p += 1

    if p >= 2:
        g, s = confidence(p)
        hasil["SCALPING"] = {
            "entry": close,
            "tp": close * 1.01,
            "sl": close * 0.995,
            "grade": g,
            "star": s,
            "note": "Likuid tinggi, cocok intraday"
        }

    if not hasil:
        return None, "Tidak ada setup layak saat ini"

    return hasil, None

# ================= TELEGRAM HANDLER =================
def handle(update, context):
    parts = update.message.text.strip().upper().split()
    kode = parts[0]
    harga_beli = float(parts[1]) if len(parts) == 2 else None

    hasil, error = analyze(kode)
    if error:
        update.message.reply_text(f"❌ *{kode}*\n{error}", parse_mode=ParseMode.MARKDOWN)
        return

    default = default_mode()
    prioritas = ["BAGGER", "SWING", "SCALPING"]
    utama = default if default in hasil else next(m for m in prioritas if m in hasil)

    msg = f"📊 *{kode}*\n\n✅ *MODE VALID:*\n"
    for m in hasil:
        icon = "🔥" if m == "BAGGER" else "🟡" if m == "SWING" else "🔵"
        msg += f"{icon} {m}\n"

    msg += f"\n⭐ *Rekomendasi:* {utama} {hasil[utama]['star']} ({hasil[utama]['grade']})\n"

    if harga_beli:
        tp = harga_beli * (hasil[utama]["tp"] / hasil[utama]["entry"])
        sl = harga_beli * (hasil[utama]["sl"] / hasil[utama]["entry"])
        status = "🟢 HOLD" if harga_beli <= hasil[utama]["entry"] * 1.05 else "⚠️ EXIT / TIGHT SL"

        msg += (
            f"\n💼 Posisi kamu: `{harga_beli:.0f}`\n"
            f"🎯 TP: `{tp:.0f}`\n"
            f"🛑 SL: `{sl:.0f}`\n"
            f"📌 Status: *{status}*"
        )
    else:
        status = "🟢 BUY" if hasil[utama]["grade"] in ["A", "B"] else "⚠️ WAIT"
        msg += f"\n📌 Status: *{status}*\n"

        for m, d in hasil.items():
            msg += f"\n{m}\nEntry `{d['entry']:.0f}` | TP `{d['tp']:.0f}` | SL `{d['sl']:.0f}`"

    msg += f"\n\n_{hasil[utama]['note']}_"
    update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)

def main():
    updater = Updater(TOKEN, use_context=True)
    updater.dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, handle))
    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()
