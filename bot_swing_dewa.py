import yfinance as yf
import pandas as pd
import os
import math
from telegram import Bot, ParseMode

# ================= KONFIGURASI =================
TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

TICKERS = [
    "BBRI.JK","BMRI.JK","BBCA.JK","TLKM.JK",
    "ANTM.JK","ADRO.JK","MDKA.JK","INCO.JK",
    "UNTR.JK","PGAS.JK","CPIN.JK","KLBF.JK"
]

# ================= FUNGSI INDIKATOR =================
def ema(series, period):
    return series.ewm(span=period, adjust=False).mean()

# ================= BOT UTAMA =================
def main():
    if not TOKEN or not CHAT_ID:
        raise ValueError("TOKEN / CHAT_ID belum diset")

    bot = Bot(token=TOKEN)
    kandidat = []

    for t in TICKERS:
        try:
            df = yf.download(t, period="6mo", interval="1d", progress=False)
            if df.empty or len(df) < 80:
                continue

            # ===== FILTER LIKUIDITAS =====
            avg_value = (df["Close"] * df["Volume"]).tail(20).mean()
            if avg_value < 30_000_000_000:
                continue

            # ===== INDIKATOR =====
            df["ema20"] = ema(df["Close"], 20)
            df["ema50"] = ema(df["Close"], 50)

            last = df.iloc[-1]
            prev5 = df.iloc[-6:-1]
            prev3 = df.iloc[-4:-1]

            # ===== AKUMULASI VOLUME 5 HARI =====
            vol = prev5["Volume"].values
            if not all(vol[i] < vol[i+1] for i in range(len(vol)-1)):
                continue

            # ===== HARGA BELUM LARI =====
            price_move = (
                prev5["Close"].iloc[-1] - prev5["Close"].iloc[0]
            ) / prev5["Close"].iloc[0]

            if price_move > 0.08:
                continue

            # ===== TREND IDEAL =====
            if not (
                last["ema20"] > last["ema50"] and
                abs(last["Close"] - last["ema20"]) / last["ema20"] < 0.03
            ):
                continue

            # ===== BREAKOUT HALUS =====
            body = abs(last["Close"] - last["Open"])
            upper_shadow = last["High"] - max(last["Close"], last["Open"])

            if not (
                last["Close"] > prev3["High"].max() and
                body > upper_shadow
            ):
                continue

            # ===== SCORING LEVEL DEWA =====
            liquidity_score = math.log10(avg_value)
            volume_score = prev5["Volume"].iloc[-1] / prev5["Volume"].mean()
            ema_score = 1 - abs(last["Close"] - last["ema20"]) / last["ema20"]
            candle_score = body / (last["High"] - last["Low"])

            total_score = round(
                0.30 * liquidity_score +
                0.35 * volume_score +
                0.20 * ema_score +
                0.15 * candle_score,
                2
            )

            entry = last["Close"]
            tp1 = entry * 1.07
            tp2 = entry * 1.12
            sl = entry * 0.97

            kandidat.append({
                "ticker": t,
                "entry": entry,
                "tp1": tp1,
                "tp2": tp2,
                "sl": sl,
                "score": total_score
            })

        except Exception:
            continue

    kandidat.sort(key=lambda x: x["score"], reverse=True)

    # ================= OUTPUT TELEGRAM =================
    if kandidat:
        pesan = "👑 *SWING LEVEL DEWA (2–5 HARI)*\n\n"
        for i, k in enumerate(kandidat[:3], 1):
            pesan += (
                f"#{i} 🔥 *{k['ticker']}*\n"
                f"Entry : `{k['entry']:.0f}`\n"
                f"TP1   : `{k['tp1']:.0f}` (+7%)\n"
                f"TP2   : `{k['tp2']:.0f}` (+12%)\n"
                f"SL    : `{k['sl']:.0f}` (-3%)\n"
                f"Score : `{k['score']}`\n\n"
            )
    else:
        pesan = "📭 *Swing Level Dewa*\nTidak ada setup kualitas dewa hari ini."

    bot.send_message(
        chat_id=CHAT_ID,
        text=pesan,
        parse_mode=ParseMode.MARKDOWN
    )

if __name__ == "__main__":
    main()
