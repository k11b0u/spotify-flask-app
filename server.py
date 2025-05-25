# 修正ポイントを含めたSpotify Flaskアプリのコード
from flask import Flask, redirect, request
import requests, urllib.parse, base64

app = Flask(__name__)

CLIENT_ID = "7838a0cf003644ae8b5f3f75b9eb534e"
CLIENT_SECRET = "d2d93b5ce2b7403f91125a0ea8685697"
REDIRECT_URI = "https://spotify-flask-app-pduk.onrender.com/callback"
# 音響特徴量APIのためにuser-library-readを追加
SCOPE = "user-read-playback-state user-modify-playback-state user-follow-read user-library-read"
AUTH_URL = "https://accounts.spotify.com/authorize"
TOKEN_URL = "https://accounts.spotify.com/api/token"

# グローバル変数
global_token = None
global_device_id = None

@app.route("/")
def index():
    return "🎧 Spotify 再生デモ: /login にアクセスしてください"

@app.route("/login")
def login():
    params = {
        "client_id": CLIENT_ID,
        "response_type": "code",
        "redirect_uri": REDIRECT_URI,
        "scope": SCOPE,
    }
    return redirect(f"{AUTH_URL}?{urllib.parse.urlencode(params)}")

@app.route("/callback")
def callback():
    global global_token, global_device_id

    code = request.args.get("code")
    auth_str = f"{CLIENT_ID}:{CLIENT_SECRET}"
    b64_auth = base64.b64encode(auth_str.encode()).decode()

    res = requests.post(
        TOKEN_URL,
        data={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": REDIRECT_URI,
        },
        headers={
            "Authorization": f"Basic {b64_auth}",
            "Content-Type": "application/x-www-form-urlencoded",
        },
    )

    if res.status_code != 200:
        return f"❌ トークン取得失敗: {res.text}", 400

    token = res.json().get("access_token")
    global_token = token

    devices_resp = requests.get(
        "https://api.spotify.com/v1/me/player/devices",
        headers={"Authorization": f"Bearer {token}"}
    ).json()

    devices = devices_resp.get("devices", [])
    global_device_id = devices[0]["id"] if devices else None

    return "✅ ログイン完了！ /cluster_tracks_debug にアクセスして検証できます"

@app.route("/debug_raw_features")
def debug_raw_features():
    global global_token

    # テスト用に10件の曲IDを仮で用意（後で動的に変更可）
    test_ids = "4iV5W9uYEdYUVa79Axb7Rh,0c6xIDDpzE81m2q797ordA"  # Ed Sheeran など

    res = requests.get(
        "https://api.spotify.com/v1/audio-features",
        headers={"Authorization": f"Bearer {global_token}"},
        params={"ids": test_ids}
    )

    return f"<h3>🔊 audio-features の raw JSON</h3><pre>{res.text}</pre>"

if __name__ == "__main__":
    app.run(debug=True)

