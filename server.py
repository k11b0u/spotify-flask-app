from flask import Flask, redirect, request
import requests, urllib.parse, base64, random
from sklearn.cluster import KMeans
import numpy as np

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
    return "🎧 Spotify クラスタリングデモ — /login にアクセスしてください"

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
    global global_token

    if not global_token:
        return "❌ トークン未取得 /login にアクセスしてください"

    # フォロー中アーティスト取得
    artists_resp = requests.get(
        "https://api.spotify.com/v1/me/following?type=artist&limit=15",
        headers={"Authorization": f"Bearer {global_token}"}
    ).json()
    artists = artists_resp.get("artists", {}).get("items", [])
    artist_ids = [a["id"] for a in artists]
    artist_names = [a["name"] for a in artists]

    # トップトラック取得
    all_tracks = []
    for artist_id in artist_ids:
        top_resp = requests.get(
            f"https://api.spotify.com/v1/artists/{artist_id}/top-tracks?market=JP",
            headers={"Authorization": f"Bearer {global_token}"}
        ).json()
        all_tracks.extend(top_resp.get("tracks", []))

    track_ids = [t["id"] for t in all_tracks]
    track_names = [t["name"] for t in all_tracks]

    # 特徴量取得
    features_resp = requests.get(
        "https://api.spotify.com/v1/audio-features",
        headers={"Authorization": f"Bearer {global_token}"},
        params={"ids": ",".join(track_ids[:100])}
    ).json()

    features = features_resp.get("audio_features", [])
    valid_tracks = []
    invalid_tracks = []
    track_info_lines = []

    for t, f in zip(all_tracks, features):
        if f:
            valence = f["valence"]
            energy = f["energy"]
            tempo = f["tempo"]
            valid_tracks.append((t["name"], valence, energy, tempo))
            track_info_lines.append(f"🎵 {t['name']} - valence: {valence}, energy: {energy}, tempo: {tempo}")
        else:
            invalid_tracks.append(t["name"])

    html = f"""
    🧑‍🎤 アーティスト数: {len(artist_names)}<br>
    📘 トラック数: {len(all_tracks)}<br>
    ✅ 有効な特徴量: {len(valid_tracks)}<br>
    ❌ 無効なトラック: {len(invalid_tracks)}<br>
    <hr>
    <h4>🎶 全トラック情報:</h4>
    {"<br>".join(track_info_lines)}<br><br>
    <h4>❌ 特徴量取得できなかった曲:</h4>
    {"<br>".join(invalid_tracks)}<br>
    """

    return html

if __name__ == "__main__":
    app.run()
