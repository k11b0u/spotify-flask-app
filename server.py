from flask import Flask, redirect, request
import requests, urllib.parse, base64

app = Flask(__name__)

CLIENT_ID     = "7838a0cf003644ae8b5f3f75b9eb534e"
CLIENT_SECRET = "d2d93b5ce2b7403f91125a0ea8685697"
REDIRECT_URI  = "https://spotify-flask-app-pduk.onrender.com/callback"
SCOPE         = (
    "user-read-playback-state "
    "user-modify-playback-state "
    "user-follow-read "
    "user-library-read "
    "user-top-read"
)
AUTH_URL      = "https://accounts.spotify.com/authorize"
TOKEN_URL     = "https://accounts.spotify.com/api/token"

global_token = None
global_device_id = None

@app.route("/")
def index():
    return "\U0001F3A7 Spotify 再生デモ — /login にアクセスしてください"

@app.route("/login")
def login():
    params = {
        "client_id":     CLIENT_ID,
        "response_type": "code",
        "redirect_uri":  REDIRECT_URI,
        "scope":         SCOPE,
    }
    return redirect(f"{AUTH_URL}?{urllib.parse.urlencode(params)}")

@app.route("/callback")
def callback():
    global global_token, global_device_id

    code = request.args.get("code")
    if not code:
        return "❌ 認証コードが取得できませんでした"

    auth_str = f"{CLIENT_ID}:{CLIENT_SECRET}"
    b64_auth = base64.b64encode(auth_str.encode()).decode()

    res = requests.post(
        TOKEN_URL,
        data={
            "grant_type":   "authorization_code",
            "code":         code,
            "redirect_uri": REDIRECT_URI,
        },
        headers={
            "Authorization": f"Basic {b64_auth}",
            "Content-Type":  "application/x-www-form-urlencoded",
        },
    )

    if res.status_code != 200:
        return f"❌ トークン取得失敗: {res.status_code}<br><pre>{res.text}</pre>"

    token_data = res.json()
    global_token = token_data.get("access_token")
    if not global_token:
        return "❌ トークンが取得できませんでした"

    html = f"<p>✅ アクセストークン取得成功（先頭20文字）：<code>{global_token[:20]}...</code></p>"

    devices_resp = requests.get(
        "https://api.spotify.com/v1/me/player/devices",
        headers={"Authorization": f"Bearer {global_token}"}
    ).json()
    devices = devices_resp.get("devices", [])
    global_device_id = devices[0]["id"] if devices else None

    html += f"<p>🔌 デバイスID: <code>{global_device_id}</code></p>"
    html += "<p>☛ 次は <a href='/debug_raw_features'>/debug_raw_features</a> を開いてください</p>"
    return html

if __name__ == "__main__":
    app.run()
