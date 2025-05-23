from flask import Flask, redirect, request
import requests, urllib.parse, base64, random

app = Flask(__name__)

CLIENT_ID     = "7838a0cf003644ae8b5f3f75b9eb534e"
CLIENT_SECRET = "d2d93b5ce2b7403f91125a0ea8685697"
REDIRECT_URI  = "https://spotify-flask-app-pduk.onrender.com/callback"
SCOPE         = "user-read-playback-state user-modify-playback-state user-follow-read"
AUTH_URL      = "https://accounts.spotify.com/authorize"
TOKEN_URL     = "https://accounts.spotify.com/api/token"

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
    global_token = token

    devices_resp = requests.get(
        "https://api.spotify.com/v1/me/player/devices",
        headers={"Authorization": f"Bearer {token}"}
    ).json()
    devices = devices_resp.get("devices", [])
    global_device_id = devices[0]["id"] if devices else None

    return "✅ Spotify にログインしました！"

@app.route("/personal_play_debug")
def personal_play_debug():
    global global_token, global_device_id

    if not global_token or not global_device_id:
        return "❌ ログインまたはデバイス未取得です /login にアクセスしてください"

    # 1. フォロー中アーティスト取得（複数ページ処理）
    artists = []
    url = "https://api.spotify.com/v1/me/following?type=artist&limit=50"
    while url:
        resp = requests.get(url, headers={"Authorization": f"Bearer {global_token}"}).json()
        items = resp.get("artists", {}).get("items", [])
        artists.extend(items)
        url = resp.get("artists", {}).get("next")

    artist_ids = [a["id"] for a in artists]

    # 2. トップトラック取得
    all_tracks = []
    for artist_id in artist_ids:
        top_resp = requests.get(
            f"https://api.spotify.com/v1/artists/{artist_id}/top-tracks?market=JP",
            headers={"Authorization": f"Bearer {global_token}"}
        ).json()
        all_tracks.extend(top_resp.get("tracks", []))

    # 3. 特徴量取得（100曲ずつ）
    features = []
    for i in range(0, len(all_tracks), 100):
        batch = all_tracks[i:i+100]
        ids = [t["id"] for t in batch]
        f_resp = requests.get(
            "https://api.spotify.com/v1/audio-features",
            headers={"Authorization": f"Bearer {global_token}"},
            params={"ids": ",".join(ids)}
        ).json()
        features.extend(f_resp.get("audio_features", []))

    # 4. 明るい曲フィルタ（valence > 0.5, energy > 0.4）
    bright_tracks = []
    debug_lines = []
    for t, f in zip(all_tracks, features):
        if f:
            valence = f.get("valence", 0)
            energy = f.get("energy", 0)
            debug_lines.append(f"{t['name']} → valence: {valence:.2f}, energy: {energy:.2f}")
            if valence > 0.5 and energy > 0.4:
                bright_tracks.append(t)

    selected = random.choice(bright_tracks) if bright_tracks else None

    # HTML出力
    html = (
        f"🧑‍🎤 アーティスト数: {len(artist_ids)}<br>"
        f"📘 トラック数: {len(all_tracks)}<br>"
        f"🎈 明るい曲数: {len(bright_tracks)}<br>"
        f"🎵 選曲: {selected['name'] if selected else 'なし'}<br><br>"
        + "<br>".join(debug_lines[:50])  # 多すぎるので50曲まで表示
    )

    return html

if __name__ == "__main__":
    app.run()

