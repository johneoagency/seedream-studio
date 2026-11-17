# Put Seedream Studio online (DigitalOcean)

Goal: a public web address like `https://seedream-studio-xxxx.ondigitalocean.app`
that works 24/7 — even when your Mac is off — protected by a password so only
people you share it with can use it (and spend your WaveSpeed credits).

You need two accounts: **GitHub** (holds the code) and **DigitalOcean** (runs it).
No Terminal needed — just drag-and-drop + clicks. This is the same flow you used
for spoofer, just on DigitalOcean's **App Platform**.

Keep handy:
- Your **WaveSpeed API key**
- The **login password** (in your `.env`, line `APP_PASSWORD=`)

---

## Step 1 — Put the code on GitHub (~3 min)

1. Go to https://github.com and log in (or sign up, free).
2. Click **+** (top-right) → **New repository**.
3. Name it `seedream-studio`. Set it to **Private**. Click **Create repository**.
4. On the next page, click **“uploading an existing file”**.
5. In Finder, open this app's folder and select these files/folders:
   - `server.py`
   - `requirements.txt`
   - `Dockerfile`
   - `.dockerignore`
   - `render.yaml`
   - `DEPLOY-GUIDE.md`
   - `README.md`
   - the **`public`** folder (with `index.html`, `style.css`, `app.js`)

   Drag them all into the browser upload box.
   **Do NOT upload the `.env` file** — it has your secret key. (It's left out on purpose.)
6. Click **Commit changes**.

Your code is now on GitHub.

---

## Step 2 — Deploy on DigitalOcean App Platform (~5 min)

1. Go to https://cloud.digitalocean.com/apps and log in.
2. Click **Create App** → choose **GitHub** as the source
   (authorize DigitalOcean to see your repos if it asks).
3. Pick your **seedream-studio** repo → **Next**.
4. DigitalOcean detects the **Dockerfile** automatically. Leave the build settings
   as-is. It's a **Web Service** on the default HTTP port — that's correct.
5. Find **Environment Variables** (under the component's settings / “Edit”) and add
   **two** of them, both marked **Encrypted** (secret):

   | Key | Value |
   |-----|-------|
   | `WAVESPEED_API_KEY` | *(paste your WaveSpeed key)* |
   | `APP_PASSWORD` | *(the password from your `.env`)* |

6. Pick the **Basic** plan, smallest size (around **$5/month**). Click through
   **Next** until you can click **Create Resources**.
7. Wait ~3–5 min for the first build. When it's done, the app page shows your
   public URL at the top: **`https://seedream-studio-xxxx.ondigitalocean.app`**.

Open the link, enter your password, and you're in.

---

## Sharing it

Send people two things:
1. the link: `https://seedream-studio-xxxx.ondigitalocean.app`
2. the password (`APP_PASSWORD`)

Anyone with both can make and edit images — which bills your WaveSpeed account
(~$0.04 per image). Change the password anytime: App → **Settings** →
**Environment Variables** → edit `APP_PASSWORD` → **Save** (it redeploys).

---

## Updating it later

If the app changes, re-upload the changed file(s) to your GitHub repo
(**Add file → Upload files** → drag → **Commit**). DigitalOcean notices and
redeploys automatically within a minute or two.

---

## Cost summary

- **DigitalOcean App Platform Basic:** ~$5/month, always on (no sleep).
- **WaveSpeed:** pay-as-you-go, ~$0.04 per image generated.

(New DigitalOcean accounts often come with free trial credit that covers the
first couple of months.)

---

## Prefer Render instead? (also works, has a free tier)

The repo also includes `render.yaml`, so you can deploy on Render exactly like
spoofer: https://render.com → **New + → Blueprint** → pick the repo → fill in
`WAVESPEED_API_KEY` and `APP_PASSWORD` → **Apply**. Render's **free** plan sleeps
after ~15 min idle (first visit then takes ~50s to wake); upgrade to Starter
(~$7/mo) to stay awake.
