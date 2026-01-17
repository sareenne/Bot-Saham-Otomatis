import os
import requests

print("=== START SCRIPT ===")

tg_token = os.getenv("TG_TOKEN")
chat_id = os.getenv("TG_CHAT_ID")

print("TG_TOKEN:", tg_token[:10] if tg_token else None)
print("TG_CHAT_ID:", chat_id)

if not tg_token or not chat_id:
    print("❌ TOKEN / CHAT_ID TIDAK TERBACA")
    exit(0)

url = f"https://api.telegram.org/bot{tg_token}/sendMessage"
payload = {
    "chat_id": chat_id,
    "text": "🚨 TES PALING MINIMAL: HARUS MASUK 🚨"
}

r = requests.post(url, data=payload)

print("STATUS CODE:", r.status_code)
print("RESPONSE:", r.text)

print("=== END SCRIPT ===")
