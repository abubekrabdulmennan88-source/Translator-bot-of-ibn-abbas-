# Translator Abubeker Abdu

Fetches new text posts from https://t.me/Awraq_Alyasmin, translates them to Amharic
(free Google Translate, no API key), and posts them to @ibnuabbas_hara with a source line.

## Setup on GitHub (mobile)
1. Create a new repo, e.g. `translator-abubeker-abdu`.
2. Upload these 3 files: `main.py`, `requirements.txt`, `README.md`.

## Deploy on Render.com (free)
1. Go to render.com → New → Web Service → connect the GitHub repo.
2. Runtime: Python 3.
3. Build command: `pip install -r requirements.txt`
4. Start command: `python main.py`
5. Instance type: Free.
6. Add Environment Variables:
   - `BOT_TOKEN` = your new "Translator Abubeker Abdu" bot token from BotFather
   - `CHANNEL_ID` = `@ibnuabbas_hara`
   - `SOURCE_CHANNEL` = `Awraq_Alyasmin`
   - `CHECK_INTERVAL_SECONDS` = `600` (10 minutes — optional, this is the default)
7. Deploy.

## Important: keep it awake
Render's free plan spins the service down after 15 minutes with no web traffic.
Set up a free monitor at uptimerobot.com to ping your Render URL (the one Render
gives you, like `https://your-app.onrender.com`) every 10 minutes. This keeps the
worker loop running continuously.

## Notes
- The bot must be an admin of @ibnuabbas_hara to post.
- Text-only posts are translated as-is (no editing/summarizing) and stored progress
  is kept in `state.json` on the running instance, so it won't repost old messages.
