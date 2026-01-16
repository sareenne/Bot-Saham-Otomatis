import yfinance as yf
import os
from telegram.ext import Updater, MessageHandler, Filters
from telegram import ParseMode

TOKEN = os.getenv("TELEGRAM_TOKEN")

# ================= HELPER =================
def ema(series, p):
    return series.ewm(span=p, adjust=False).mean()

def confidence(p):
    if p >= 5:
        return "A"
    if p >= 3:
        return "B"
    return "C"

def tps(entry, levels):
    return [entry * lvl for lvl in levels]

# ================= ANALISA =================
def analyze(kode):
    df = yf.download(kode + ".JK", period="6mo", interval="1d", progress=False)
    if df.empty or len(df) < 120:
        return None, "Data tidak cukup / kode salah"

    df["ema20"] = ema(df["Close"], 20)
    df["ema50"] = ema(df["Close"], 50)
    df["ema100"] = ema(df["Close"], 100)
    df["vol_ma20"] = df["Volume"].rolling(20).mean()

    last = df.iloc[-1]

    close = float(last["Close"])
    ema20 = float(last["ema20"])
    ema50 = float(last["ema50"])
    ema100 = float(last["ema100"])
    volume = float(last["Volume"])
    vol_ma20 = float(last["vol_ma20"])

    avg_value = float((df["Close"] * df["Volume"]).tail(20).mean())
    hasil = {}

    # ===== BAGGER =====
    p = 0
    if avg_value >= 25_000_000_000: p += 1
    if ema20 > ema50 and ema50 > ema100: p += 1
    if abs(close - ema50) / ema50 <= 0.05: p += 1

    vol5 = df["Volume"].tail(5).values
    if vol5[4] > vol5[3] > vol5[2] > vol5[1] > vol5[0]: p += 1

    close10 = df["Close"].tail(10).values
    if (close10[-1] - close10[0]) / close10[0] <= 0.15: p += 1

    if p >= 3:
        hasil["BAGGER"] = {
            "entry": close,
            "tp": tps(close, [1.10, 1.20, 1.30]),
            "sl": close * 0.93,
            "grade": confidence(p),
            "note": "Akumulasi rapi, potensi menengah"
        }

    # ===== SWING =====
    p = 0
    if avg_value >= 20_000_000_000: p += 1
    if ema20 > ema50: p += 1
    if abs(close - ema20) / ema20 <= 0.03: p += 1
    if volume > vol_ma20 * 1.5: p += 1

    close3 = df["Close"].tail(3).values
    if (close3[-1] - close3[0]) / close3[0] <= 0.07: p += 1

    if p >= 3:
        hasil["SWING"] = {
            "entry": close,
            "tp": tps(close, [1.04, 1.06, 1.08]),
            "sl": close * 0.97,
            "grade": confidence(p),
            "note": "Momentum pendek, cocok 2–5 hari"
        }

    # ===== SCALPING =====
    p = 0
    if avg_value >= 50_000_000_000: p += 1
    if volume > vol_ma20: p += 1
    if close > ema20: p += 1

    if p >= 2:
        hasil["SCALPING"] = {
            "entry": close,
            "tp": tps(close, [1.008, 1.012, 1.016]),
            "sl": close * 0.995,
            "grade": confidence(p),
            "note": "Intraday cepat, perlu disiplin"
        }

    if not hasil:
        return None, "Tidak ada setup aman saat ini"

    return hasil, None

# ================= TELEGRAM =================
def handle(update, context):
    parts = update.message.text.strip().upper().split()
    kode = parts[0]

    harga_beli = float(parts[1]) if len(parts) == 2 else None

    hasil, error = analyze(kode)
    if error:
        update.message.reply_text(f"❌ *{kode}*\n{error}", parse_mode=ParseMode.MARKDOWN)
        return

    # MODE UTAMA (prioritas aman)
    prioritas = ["BAGGER", "SWING", "SCALPING"]
    utama = next(m for m in prioritas if m in hasil)
    d_utama = hasil[utama]

    # LOGIKA REKOM
    if harga_beli is None:
        rekom = "🟢 BUY" if d_utama["grade"] in ["A", "B"] else "⚠️ WAIT"
        posisi = "Belum punya saham"
    else:
        posisi = f"Punya di {harga_beli:.0f}"
        if harga_beli < d_utama["sl"]:
            rekom = "🔴 EXIT (CUT LOSS)"
        elif harga_beli <= d_utama["entry"] * 1.03:
            rekom = "🟢 HOLD"
        else:
            rekom = "🟡 HOLD / PARTIAL TP"

    # OUTPUT
    msg = (
        f"📊 *{kode}*\n"
        f"📌 {posisi}\n"
        f"📢 *REKOM*: {rekom}\n\n"
        f"MODE TERDETEKSI:\n"
    )

    for m in hasil:
        msg += f"- {m} ({hasil[m]['grade']})\n"

    msg += f"\nMODE UTAMA: *{utama}*\n\n"

    for m, d in hasil.items():
        msg += (
            f"▶️ *{m}*\n"
            f"Entry : {d['entry']:.0f}\n"
            f"TP 1  : {d['tp'][0]:.0f}\n"
            f"TP 2  : {d['tp'][1]:.0f}\n"
            f"TP 3  : {d['tp'][2]:.0f}\n"
            f"SL    : {d['sl']:.0f}\n\n"
        )

    msg += f"📝 _{d_utama['note']}_"
    update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)

def main():
    updater = Updater(TOKEN, use_context=True)
    updater.dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, handle))
    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()
