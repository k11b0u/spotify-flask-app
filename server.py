from flask import Flask, redirect, request
import requests, urllib.parse, base64, random
from sklearn.cluster import KMeans

app = Flask(__name__)

CLIENT_ID     = "7838a0cf003644ae8b5f3f75b9eb534e"
CLIENT_SECRET = "d2d93b5ce2b7403f91125a0ea8685697"
REDIRECT_URI  = "https://spotify-flask-app-pduk.onrender.com/callback"
SCOPE         = "user-read-playback-state user-modify-playback-state user-follow-read"
AUTH_URL      = "https://accounts.spotify.com/authorize"
TOKEN_URL     = "https://accounts.spotify.com/api/token"

# グローバル状態
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

@app.route("/cluster_tracks_debug")
def cluster_tracks_debug():
    global global_token, global_device_id

    if not global_token:
        return "❌ トークン未取得です /login にアクセスしてください"

    # アーティスト取得
    artists_resp = requests.get(
        "https://api.spotify.com/v1/me/following?type=artist&limit=20",
        headers={"Authorization": f"Bearer {global_token}"}
    ).json()
    artists = artists_resp.get("artists", {}).get("items", [])
    artist_ids = [a["id"] for a in artists]

    all_tracks = []
    for artist_id in artist_ids:
        top_resp = requests.get(
            f"https://api.spotify.com/v1/artists/{artist_id}/top-tracks?market=JP",
            headers={"Authorization": f"Bearer {global_token}"}
        ).json()
        all_tracks.extend(top_resp.get("tracks", []))

    track_ids = [t["id"] for t in all_tracks if t.get("id")]
    track_names = [t["name"] for t in all_tracks if t.get("id")]

    features_resp = requests.get(
        "https://api.spotify.com/v1/audio-features",
        headers={"Authorization": f"Bearer {global_token}"},
        params={"ids": ",".join(track_ids[:100])}  # 最大100件
    ).json()

    features = features_resp.get("audio_features", [])
    valid = [(t, f) for t, f in zip(all_tracks, features) if f]
    invalid = [t["name"] for t, f in zip(all_tracks, features) if not f]

    html = f"""
    🧑‍🎤 アーティスト数: {len(artist_ids)}<br>
    📘 トラック数: {len(track_ids)}<br>
    🎯 有効な特徴量: {len(valid)}<br>
    ❌ 無効なトラック: {len(invalid)}<br>
    <hr>
    <h3>🎶 全トラック情報:</h3>
    <ul>
    """
    for t, f in valid:
        html += f"<li>{t['name']} — Valence: {f['valence']}, Energy: {f['energy']}, Tempo: {f['tempo']}</li>"
    html += "</ul>"

    html += "<h3>🚫 特徴量取得できなかった曲:</h3><ul>"
    for name in invalid:
        html += f"<li>{name}</li>"
    html += "</ul>"

    return html

if __name__ == "__main__":
    app.run()
