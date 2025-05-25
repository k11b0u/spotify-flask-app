from flask import Flask, redirect, request, jsonify
import requests, urllib.parse, base64

app = Flask(__name__)

# Spotify認証情報
CLIENT_ID     = "7838a0cf003644ae8b5f3f75b9eb534e"
CLIENT_SECRET = "d2d93b5ce2b7403f91125a0ea8685697"
REDIRECT_URI  = "https://spotify-flask-app-pduk.onrender.com/callback"
SCOPE         = "user-read-playback-state user-modify-playback-state user-follow-read"
AUTH_URL      = "https://accounts.spotify.com/authorize"
TOKEN_URL     = "https://accounts.spotify.com/api/token"

# グローバル状態
global_token = None
global_track_ids = []

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
    global global_token, global_track_ids

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
    global_token = res.json().get("access_token")

    # テスト用track ID取得（例: ビリーアイリッシュの代表曲）
    global_track_ids = [
        "4RVwu0g32PAqgUiJoXsdF8",  # example track
        "3n3Ppam7vgaVa1iaRUc9Lp",
        "0VjIjW4GlUZAMYd2vXMi3b"
    ]

    return "✅ Spotify 認証完了。/debug_raw_features にアクセスしてください"

@app.route("/debug_raw_features")
def debug_raw_features():
    global global_token, global_track_ids

    if not global_token or not global_track_ids:
        return "❌ トークンまたはトラックIDがありません。先に /login にアクセスしてください"

    # トークン確認
    debug_headers = {
        "Authorization": f"Bearer {global_token}"
    }

    # 特徴量取得
    features_resp = requests.get(
        "https://api.spotify.com/v1/audio-features",
        headers=debug_headers,
        params={"ids": ",".join(global_track_ids[:100])}  # 最大100件
    )

    return f"""
    <h3>🔊 audio-features の raw JSON</h3>
    <pre>{features_resp.text}</pre>
    <hr>
    <h4>🪪 トークン（先頭20文字）:</h4>
    <pre>{global_token[:20]}...</pre>
    <h4>🎵 Track IDs:</h4>
    <pre>{global_track_ids}</pre>
    """

if __name__ == "__main__":
    app.run(debug=True)
