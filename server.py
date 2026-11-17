#!/usr/bin/env python3
"""Seedream Studio - text-to-image + image editing web app (WaveSpeed Seedream 4.5).

Flask app, password-protected, ready to run locally or deploy with Docker.

Env vars:
  WAVESPEED_API_KEY  required - your WaveSpeed API key
  APP_PASSWORD       required online - the login password people must enter
  PORT               optional - port to listen on (default 3000 local; hosts inject it)
  SEEDREAM_NO_AUTH   set to "1" for a localhost-only test with no login
"""

import hashlib
import json
import os
import secrets
import ssl
import subprocess
import time
import urllib.request
import urllib.error

from flask import Flask, Response, redirect, request, send_file, send_from_directory

HERE = os.path.dirname(os.path.abspath(__file__))
PUBLIC_DIR = os.path.join(HERE, "public")

SUBMIT_URL = "https://api.wavespeed.ai/api/v3/bytedance/seedream-v4.5"
EDIT_URL = "https://api.wavespeed.ai/api/v3/bytedance/seedream-v4.5/edit"
RESULT_URL = "https://api.wavespeed.ai/api/v3/predictions/{id}/result"
FAILURE_STATES = {"failed", "cancelled", "timeout", "deleted"}

API_KEY = os.environ.get("WAVESPEED_API_KEY", "").strip()
APP_PASSWORD = os.environ.get("APP_PASSWORD", "").strip()
NO_AUTH = os.environ.get("SEEDREAM_NO_AUTH") == "1"

COOKIE = "seedream_auth"
TOKEN = hashlib.sha256(("seedream::" + APP_PASSWORD).encode()).hexdigest()


# --------------------------------------------------------------------------- #
# Local .env loading (so `python3 server.py` works without exporting vars).
# --------------------------------------------------------------------------- #
def _load_env_file():
    global API_KEY, APP_PASSWORD, TOKEN
    env_path = os.path.join(HERE, ".env")
    if not os.path.exists(env_path):
        return
    with open(env_path, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            name, _, value = line.partition("=")
            name = name.strip()
            value = value.strip().strip('"').strip("'")
            if name == "WAVESPEED_API_KEY" and not API_KEY:
                API_KEY = value
            elif name == "APP_PASSWORD" and not APP_PASSWORD:
                APP_PASSWORD = value
    TOKEN = hashlib.sha256(("seedream::" + APP_PASSWORD).encode()).hexdigest()


_load_env_file()


def make_ssl_context():
    """SSL context with trusted CAs.

    Linux (Docker) ships a CA bundle, so the default context just works.
    Python.org macOS builds ship none, so we fall back to the macOS system
    roots via the `security` tool. The try/except makes this a no-op on Linux.
    """
    ctx = ssl.create_default_context()
    try:
        pem = subprocess.run(
            [
                "security", "find-certificate", "-a", "-p",
                "/System/Library/Keychains/SystemRootCertificates.keychain",
            ],
            capture_output=True, text=True, timeout=15,
        ).stdout
        if pem and "BEGIN CERTIFICATE" in pem:
            ctx.load_verify_locations(cadata=pem)
    except Exception:
        pass
    return ctx


SSL_CTX = make_ssl_context()


# --------------------------------------------------------------------------- #
# WaveSpeed calls
# --------------------------------------------------------------------------- #
def extract_url(item):
    if isinstance(item, str):
        return item
    if isinstance(item, dict):
        return item.get("url") or item.get("image") or item.get("output")
    return None


def api_request(url, method="GET", payload=None):
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    headers = {"Authorization": "Bearer " + API_KEY}
    if data is not None:
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=60, context=SSL_CTX) as resp:
            body = resp.read().decode("utf-8")
            status = resp.status
    except urllib.error.HTTPError as err:
        body = err.read().decode("utf-8", "replace")
        status = err.code
    try:
        return status, json.loads(body)
    except json.JSONDecodeError:
        return status, body


def generate(prompt, size, images=None):
    """Submit a task and poll until it finishes. Returns (http_status, result_dict).

    With `images` (data URIs / URLs) it uses the edit endpoint; otherwise
    plain text-to-image.
    """
    images = [i for i in (images or []) if i]
    body = {
        "prompt": prompt.strip(),
        "enable_base64_output": False,
        "enable_sync_mode": False,
    }
    if images:
        endpoint = EDIT_URL
        body["images"] = images
        if size and size != "auto":
            body["size"] = size
    else:
        endpoint = SUBMIT_URL
        body["size"] = size if size and size != "auto" else "2048*2048"

    # 1. Submit once -- never auto-retry a submit (avoids double billing).
    status, result = api_request(endpoint, method="POST", payload=body)
    if status < 200 or status >= 300:
        msg = (result.get("message") or result.get("error")) if isinstance(result, dict) else str(result)[:300]
        return 502, {"error": "Submit failed: " + str(msg)}

    data = result.get("data", result) if isinstance(result, dict) else {}
    task_id = data.get("id")
    if not task_id:
        return 502, {"error": "No task id returned by WaveSpeed."}

    # 2. Poll for the result.
    deadline = time.time() + 180
    while time.time() < deadline:
        time.sleep(2)
        pstatus, presult = api_request(RESULT_URL.format(id=task_id))
        if pstatus == 429 or pstatus >= 500:
            continue
        if not isinstance(presult, dict):
            continue
        rd = presult.get("data", presult)
        state = rd.get("status")
        if state == "completed":
            outputs = [u for u in (extract_url(o) for o in (rd.get("outputs") or [])) if u]
            if not outputs:
                return 502, {"error": "Task completed but returned no image."}
            return 200, {"images": outputs, "id": task_id}
        if state in FAILURE_STATES:
            return 502, {"error": "Generation %s: %s" % (state, rd.get("error") or "no details provided.")}

    return 504, {"error": "Timed out waiting for the image. Try again."}


# --------------------------------------------------------------------------- #
# Auth
# --------------------------------------------------------------------------- #
app = Flask(__name__)


def authed():
    if NO_AUTH:
        return True
    return APP_PASSWORD != "" and secrets.compare_digest(
        request.cookies.get(COOKIE, ""), TOKEN
    )


LOGIN = """<!DOCTYPE html><html lang="en"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Seedream Studio</title>
<style>
  body{margin:0;min-height:100vh;display:flex;align-items:center;justify-content:center;
    background:radial-gradient(1200px 600px at 50% -10%,#1a2033 0%,#0b0d12 60%);
    font:15px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;color:#e8ebf2}
  form{background:#151922;border:1px solid #272d3b;border-radius:14px;padding:28px;width:300px;
    box-shadow:0 10px 40px rgba(0,0,0,.35);text-align:center}
  h1{margin:0 0 4px;font-size:22px;background:linear-gradient(90deg,#6f8cff,#a46bff);
    -webkit-background-clip:text;background-clip:text;color:transparent}
  p{margin:0 0 18px;color:#8b93a7;font-size:13px}
  input{width:100%;box-sizing:border-box;background:#1c2130;border:1px solid #272d3b;color:#e8ebf2;
    border-radius:10px;padding:11px 12px;font:inherit;margin-bottom:12px}
  input:focus{outline:none;border-color:#6f8cff}
  button{width:100%;border:0;border-radius:10px;padding:11px;font-weight:600;color:#fff;cursor:pointer;
    background:linear-gradient(90deg,#6f8cff,#a46bff)}
  .e{color:#ff6b6b;font-size:13px;margin-bottom:10px}
</style></head><body><form method="post" action="/login">
<h1>Seedream Studio</h1><p>Enter the password to continue</p>
__E__
<input type="password" name="pw" placeholder="Password" autocomplete="current-password" autofocus>
<button type="submit">Enter</button>
</form></body></html>"""


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        pw = (request.form.get("pw") or "").strip()
        if APP_PASSWORD and secrets.compare_digest(pw, APP_PASSWORD):
            r = redirect("/")
            r.set_cookie(COOKIE, TOKEN, max_age=60 * 60 * 24 * 365, httponly=True, samesite="Lax")
            return r
        return Response(LOGIN.replace("__E__", '<div class="e">Wrong password</div>'),
                        mimetype="text/html")
    return Response(LOGIN.replace("__E__", ""), mimetype="text/html")


@app.route("/logout")
def logout():
    r = redirect("/login")
    r.delete_cookie(COOKIE)
    return r


# --------------------------------------------------------------------------- #
# Pages / assets
# --------------------------------------------------------------------------- #
@app.route("/")
def index():
    if not authed():
        return redirect("/login")
    return send_file(os.path.join(PUBLIC_DIR, "index.html"), mimetype="text/html")


@app.route("/<path:filename>")
def asset(filename):
    # Serve static assets (css/js) from public/. Not sensitive.
    safe = os.path.normpath(filename)
    if safe.startswith("..") or os.path.isabs(safe):
        return Response("not found", 404)
    full = os.path.join(PUBLIC_DIR, safe)
    if not os.path.isfile(full):
        return Response("not found", 404)
    return send_from_directory(PUBLIC_DIR, safe)


@app.route("/api/generate", methods=["POST"])
def api_generate():
    if not authed():
        return Response('{"error": "unauthorized"}', status=401, mimetype="application/json")
    if not API_KEY:
        return Response('{"error": "Server is missing WAVESPEED_API_KEY."}', status=500,
                        mimetype="application/json")

    data = request.get_json(silent=True) or {}
    prompt = (data.get("prompt") or "").strip()
    if not prompt:
        return Response('{"error": "A prompt is required."}', status=400, mimetype="application/json")

    images = data.get("images")
    if images is not None and not isinstance(images, list):
        return Response('{"error": "images must be a list."}', status=400, mimetype="application/json")

    try:
        status, result = generate(prompt, data.get("size"), images)
    except Exception as exc:  # noqa: BLE001
        return Response(json.dumps({"error": "Request failed: " + str(exc)}), status=500,
                        mimetype="application/json")
    return Response(json.dumps(result), status=status, mimetype="application/json")


@app.route("/healthz")
def healthz():
    return "ok"


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "3000"))
    print("\n  Seedream Studio running at http://localhost:%d" % port)
    if not API_KEY:
        print("  !  WAVESPEED_API_KEY is not set.")
    if not APP_PASSWORD and not NO_AUTH:
        print("  !  APP_PASSWORD is not set (set SEEDREAM_NO_AUTH=1 to skip login locally).")
    print("")
    app.run(host="0.0.0.0", port=port)
