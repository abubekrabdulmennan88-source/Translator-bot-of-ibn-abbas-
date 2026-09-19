import os
import json
import time
import threading
import re
import requests
from bs4 import BeautifulSoup
from flask import Flask

# ---------- Config (set these as environment variables on Render) ----------
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
CHANNEL_ID = os.environ.get("CHANNEL_ID", "@ibnuabbas_hara")
SOURCE_CHANNEL = os.environ.get("SOURCE_CHANNEL", "Awraq_Alyasmin")
CHECK_INTERVAL_SECONDS = int(os.environ.get("CHECK_INTERVAL_SECONDS", "600"))  # 10 minutes
STATE_FILE = "state.json"

TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}"
SOURCE_URL = f"https://t.me/s/{SOURCE_CHANNEL}"
SOURCE_LABEL = f"📚 ምንጭ: {SOURCE_CHANNEL}"

app = Flask(__name__)


@app.route("/")
def health():
    return "Translator Abubeker Abdu is running.", 200


# ---------------------------- State handling ----------------------------
def load_state():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return {"last_id": 0}


def save_state(state):
    try:
        with open(STATE_FILE, "w") as f:
            json.dump(state, f)
    except Exception as e:
        print(f"[state] failed to save: {e}")


# ---------------------------- Fetch source posts ----------------------------
def fetch_messages():
    """Returns a list of (message_id, text) tuples, oldest first, text-only posts."""
    try:
        resp = requests.get(SOURCE_URL, timeout=20, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
        })
        resp.raise_for_status()
    except Exception as e:
        print(f"[fetch] request failed: {e}")
        return []

    soup = BeautifulSoup(resp.text, "html.parser")
    messages = []
    for wrap in soup.select("div.tgme_widget_message[data-post]"):
        data_post = wrap.get("data-post", "")
        # data-post looks like "Awraq_Alyasmin/12345"
        m = re.search(r"/(\d+)$", data_post)
        if not m:
            continue
        msg_id = int(m.group(1))

        text_div = wrap.select_one("div.tgme_widget_message_text")
        if not text_div:
            continue  # skip non-text posts (photo/video only, etc.)

        # Preserve line breaks
        for br in text_div.find_all("br"):
            br.replace_with("\n")
        text = text_div.get_text().strip()
        if not text:
            continue

        messages.append((msg_id, text))

    messages.sort(key=lambda x: x[0])
    return messages


# ---------------------------- Translation ----------------------------
def translate_to_amharic(text):
    """Free Google Translate scraping endpoint. Translates as-is, no summarizing."""
    try:
        resp = requests.get(
            "https://translate.googleapis.com/translate_a/single",
            params={
                "client": "gtx",
                "sl": "auto",
                "tl": "am",
                "dt": "t",
                "q": text,
            },
            timeout=20,
            headers={"User-Agent": "Mozilla/5.0"},
        )
        resp.raise_for_status()
        data = resp.json()
        translated = "".join(seg[0] for seg in data[0] if seg[0])
        if not translated.strip():
            return None
        return translated
    except Exception as e:
        print(f"[translate] failed: {e}")
        return None


# ---------------------------- Posting ----------------------------
def post_to_channel(text):
    payload = {
        "chat_id": CHANNEL_ID,
        "text": text,
        "disable_web_page_preview": True,
    }
    try:
        resp = requests.post(f"{TELEGRAM_API}/sendMessage", data=payload, timeout=20)
        if resp.status_code != 200:
            print(f"[post] telegram error {resp.status_code}: {resp.text}")
            return False
        return True
    except Exception as e:
        print(f"[post] failed: {e}")
        return False


# ---------------------------- Main loop ----------------------------
def worker_loop():
    if not BOT_TOKEN:
        print("[worker] BOT_TOKEN is not set. Exiting worker.")
        return

    state = load_state()

    # First run: don't dump the whole channel history, just mark current latest as seen.
    if state.get("last_id", 0) == 0:
        messages = fetch_messages()
        if messages:
            state["last_id"] = messages[-1][0]
            save_state(state)
            print(f"[worker] first run, baseline set to message id {state['last_id']}")

    while True:
        try:
            messages = fetch_messages()
            new_messages = [m for m in messages if m[0] > state.get("last_id", 0)]

            for msg_id, original_text in new_messages:
                translated = translate_to_amharic(original_text)
                if not translated:
                    print(f"[worker] skipping message {msg_id}, translation failed")
                    continue

                final_text = f"{translated}\n\n{SOURCE_LABEL}"
                if post_to_channel(final_text):
                    print(f"[worker] posted message {msg_id}")
                    state["last_id"] = msg_id
                    save_state(state)
                else:
                    print(f"[worker] failed to post message {msg_id}, will retry next cycle")
                    break  # stop this cycle, retry from same point next time

                time.sleep(3)  # small gap between posts

        except Exception as e:
            print(f"[worker] unexpected error: {e}")

        time.sleep(CHECK_INTERVAL_SECONDS)


if __name__ == "__main__":
    t = threading.Thread(target=worker_loop, daemon=True)
    t.start()

    port = int(os.environ.get("PORT", "10000"))
    app.run(host="0.0.0.0", port=port)
