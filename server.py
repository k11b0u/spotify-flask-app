from flask import Flask, redirect, request
import requests, urllib.parse, base64

app = Flask(__name__)

CLIENT_ID = "7838a0cf003644ae8b5f3f75b9eb534e"
CLIENT_SECRET = "d2d93b5ce2b7403f91125a0ea8685697"
REDIRECT_URI = "https://spotify-flask-app-pduk.onrender.com/callback"
SCOPE = "user-read-playback-state user-modify-playback-state streaming"
AUTH_URL = "https://accounts.spotify.com/authorize"
TOKEN_URL = "https://accounts.spotify.com/api/token"


@app.route("/login")
def login():
    params = {
        "client_id": CLIENT_ID,
        "response_type": "code",
        "redirect_uri": REDIRECT_URI,
        "scope": SCOPE
    }
    url = f"{AUTH_URL}?{urllib.parse.urlencode(params)}"
    return redirect(url)


@app.route("/callback")
def callback():
    code = request.args.get("code")
    auth_str = f"{CLIENT_ID}:{CLIENT_SECRET}"
    b64_auth = base64.b64encode(auth_str.encode()).decode()

    # ← ここから再挿入してください
    res = requests.post(
        TOKEN_URL,
        data={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": REDIRECT_URI
        },
        headers={
            "Authorization": f"Basic {b64_auth}",
            "Content-Type": "application/x-www-form-urlencoded"
        }
    )
    # ← ここまで

    token = res.json().get("access_token")

    # 1) ログイン中のユーザー情報を取得
    user_info = requests.get(
        "https://api.spotify.com/v1/me",
        headers={"Authorization": f"Bearer {token}"}
    ).json()

    # 2) 接続中デバイス一覧を取得
    devices_resp = requests.get(
        "https://api.spotify.com/v1/me/player/devices",
        headers={"Authorization": f"Bearer {token}"}
    ).json()

    # デバイス名のリストを組み立て
    device_names = [d["name"] for d in devices_resp.get("devices", [])]
    devices_line = (
        "🔌 接続中のデバイス: "
        + (", ".join(device_names) if device_names else "なし")
        + "<br><br>"
    )

    # ユーザー名／ID も一緒に表示
    user_line = (
        f"👤 ログイン中ユーザー: "
        f"{user_info.get('display_name')} ({user_info.get('id')})<br>"
    )
    user_line += f"📧 メール: {user_info.get('email')}<br><br>"

    # プレイリスト再生リクエスト
    playlist_uri = "spotify:playlist:37i9dQZF1DXcBWIGoYBM5M"
    requests.put(
        "https://api.spotify.com/v1/me/player/play",
        headers={"Authorization": f"Bearer {token}"},
        json={"context_uri": playlist_uri}
    )

    # ユーザー／デバイス情報と再生結果を返す
    return (
        user_line
        + devices_line
        + "✅ Spotify に再生リクエストを送りました！"
    )
