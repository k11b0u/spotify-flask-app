from flask import Flask, redirect, request
import requests, urllib.parse, base64

app = Flask(__name__)

# Spotify認証情報
CLIENT_ID     = "7838a0cf003644ae8b5f3f75b9eb534e"
CLIENT_SECRET = "d2d93b5ce2b7403f91125a0ea8685697"
REDIRECT_URI  = "https://spotify-flask-app-pduk.onrender.com/callback"
SCOPE         = "user-read-playback-state user-modify-playback-state streaming"
AUTH_URL      = "https://accounts.spotify.com/authorize"
TOKEN_URL     = "https://accounts.spotify.com/api/token"

# トークン・デバイスID保存（簡易版）
global_token = None
global_device_id = None

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
    global global_token, global_device_id

    # --- トークン取得 ---
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
    token = res.json().get("access_token")
    global_token = token  # グローバルに保存

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

    # --- デフォルト再生 ---
    device_id = devices[0]["id"] if devices else None
    global_device_id = device_id  # グローバルに保存

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

@app.route("/emotion_play")
def emotion_play():
    global global_token, global_device_id

    emotion = request.args.get("emotion")
    if not global_token or not global_device_id:
        return "❌ トークンまたはデバイスIDが未取得です。先に /login にアクセスしてください", 400

    emotion_to_playlist = {
        "happy": "spotify:playlist:37i9dQZF1DXdPec7aLTmlC",  # Happy Hits!
        "sad": "spotify:playlist:37i9dQZF1DWVrtsSlLKzro",    # Sad Songs
        "calm": "spotify:playlist:37i9dQZF1DX3rxVfibe1L0",    # Chill
        "angry": "spotify:playlist:37i9dQZF1EIeIgNZCaOGbMi",   # Rock Hard
    }

    playlist_uri = emotion_to_playlist.get(emotion)
    if not playlist_uri:
        return f"⚠️ 感情 '{emotion}' に対応するプレイリストが見つかりません", 400

    requests.put(
        f"https://api.spotify.com/v1/me/player/play?device_id={global_device_id}",
        headers={"Authorization": f"Bearer {global_token}"},
        json={"context_uri": playlist_uri}
    )

    return f"🎵 感情「{emotion}」に対応したプレイリストを再生しました！"

if __name__ == "__main__":
    app.run()
