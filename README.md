# Seedream Studio

A password-protected text-to-image + image-editing web app powered by
**Seedream 4.5** via the [WaveSpeed](https://wavespeed.ai) API. Your API key
stays on the server — it is never exposed to the browser.

Runs locally with Python, or online with Docker (see **DEPLOY-GUIDE.md**).

## Run it locally

1. Install dependencies (one time):
   ```bash
   pip install -r requirements.txt
   ```

2. Add your settings:
   ```bash
   cp .env.example .env
   ```
   Open `.env` and set `WAVESPEED_API_KEY` and `APP_PASSWORD`.

3. Start it:
   ```bash
   python3 server.py
   ```

4. Open **http://localhost:3000**, enter your password, and go.

   (To skip the login while testing locally: `SEEDREAM_NO_AUTH=1 python3 server.py`)

## Usage

- **Text-to-image:** type a prompt, pick an aspect ratio, click **Generate**.
- **With a reference image:** click the upload box (or drag an image in), then
  describe how to change it. Use **Auto** size to match the reference's shape.
  Remove the image with the ✕ to go back to text-only.
- Images appear newest-first; click **Open ↗** to view full size or save.

## Put it online

See **[DEPLOY-GUIDE.md](DEPLOY-GUIDE.md)** — a step-by-step guide to hosting it on
DigitalOcean (with a Render option too). It uses the included `Dockerfile`, and a
login password keeps strangers from spending your WaveSpeed credits.

## How it works

- `server.py` — Flask app. Serves the UI behind a password (`APP_PASSWORD`) and
  exposes `POST /api/generate`. With no reference image it calls
  `bytedance/seedream-v4.5` (text-to-image); with an uploaded image it calls
  `bytedance/seedream-v4.5/edit`. It polls `predictions/{id}/result` until done
  and returns the image URL(s). Uploaded images are sent as data URIs, downscaled
  in the browser first.
- `public/` — the browser UI (`index.html`, `style.css`, `app.js`).
- `Dockerfile`, `requirements.txt`, `render.yaml` — for deploying online.

## Notes

- Each generation is a billed WaveSpeed API call (~$0.04 per image). The submit is
  sent exactly once (no auto-retry) to avoid double billing; only polling retries.
- Never commit your `.env` — it holds your secret key. (`.gitignore` excludes it.)
