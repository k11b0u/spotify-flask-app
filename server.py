from flask import Flask, redirect, request
import requests, urllib.parse, base64

app = Flask(__name__)

CLIENT_ID     = "7838a0cf003644ae8b5f3f75b9eb534e"
CLIENT_SECRET = "d2d93b5ce2b7403f91125a0ea8685697"
REDIRECT_URI  = "https://spotify-flask-app-pduk.onrender.com/callback"
SCOPE         = "user-read-playback-state user-modify-playback-state streaming"
AUTH_URL      = "https://accounts.spotify.com/authorize"
TOKEN_URL     = "https://accounts.spotify.com/api/token"


# ルートに何も返さないと 404 → ヘルスチェックNG になることがあるので
@app.route("/")
def index():
    return "🎧 Spotify 再生デモ — /login にアクセスしてください"


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
    # --- トークン取得 ---
    code = request.args.get("code")
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
    token = res.json().get("access_token")

    # --- ユーザー情報取得 ---
    user_info = requests.get(
        "https://api.spotify.com/v1/me",
        headers={"Authorization": f"Bearer {token}"}
    ).json()
    user_line = (
        f"👤 ログイン中ユーザー: "
        f"{user_info.get('display_name')} ({user_info.get('id')})<br>"
        f"📧 メール: {user_info.get('email')}<br><br>"
    )

    # --- デバイス一覧取得 ---
    devices_resp = requests.get(
        "https://api.spotify.com/v1/me/player/devices",
        headers={"Authorization": f"Bearer {token}"}
    ).json()
    devices = devices_resp.get("devices", [])
    info_lines = [f"{d['name']} → {d['id']}" for d in devices]
    devices_html = (
        "🔌 接続中のデバイス:<br>"
        + ("<br>".join(info_lines) if info_lines else "なし")
        + "<br><br>"
    )

    # --- 再生リクエスト（先頭のデバイスを指定）---
    device_id = devices[0]["id"] if devices else None
    play_url = "https://api.spotify.com/v1/me/player/play"
    if device_id:
        play_url += f"?device_id={device_id}"
    requests.put(
        play_url,
        headers={"Authorization": f"Bearer {token}"},
        json={"context_uri": "spotify:playlist:37i9dQZF1DXcBWIGoYBM5M"}
    )

    return (
        user_line
        + devices_html
        + ("✅ " + (f"{device_id} で再生リクエストを送りました！"
                   if device_id else "再生可能なデバイスが見つかりませんでした"))
    )


if __name__ == "__main__":
    app.run()

