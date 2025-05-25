from flask import Flask, redirect, request
import requests, urllib.parse, base64
from sklearn.cluster import KMeans
import numpy as np

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

@app.route("/cluster_tracks")
def cluster_tracks():
    global global_token

    if not global_token:
        return "❌ ログインしてください /login"

    # フォロー中アーティスト取得
    artists_resp = requests.get(
        "https://api.spotify.com/v1/me/following?type=artist&limit=20",
        headers={"Authorization": f"Bearer {global_token}"}
    ).json()

    artists = artists_resp.get("artists", {}).get("items", [])
    artist_ids = [a["id"] for a in artists]

    # 各アーティストのトップトラックを取得
    all_tracks = []
    for artist_id in artist_ids:
        top_resp = requests.get(
            f"https://api.spotify.com/v1/artists/{artist_id}/top-tracks?market=JP",
            headers={"Authorization": f"Bearer {global_token}"}
        ).json()
        all_tracks.extend(top_resp.get("tracks", []))

    # 音響特徴量取得
    track_ids = [t["id"] for t in all_tracks if t.get("id")][:100]
    features_resp = requests.get(
        "https://api.spotify.com/v1/audio-features",
        headers={"Authorization": f"Bearer {global_token}"},
        params={"ids": ",".join(track_ids)}
    ).json()
    features = features_resp.get("audio_features", [])

    # 特徴量をベクトル化（valence, energy, tempo）
    data = []
    names = []
    for t, f in zip(all_tracks, features):
        if f and f.get("valence") is not None:
            data.append([f["valence"], f["energy"], f["tempo"]])
            names.append(t["name"])

    if len(data) < 3:
        return "❌ 有効なトラックが少なすぎます"

    # クラスタリング（k=3）
    kmeans = KMeans(n_clusters=3, random_state=0, n_init=10)
    labels = kmeans.fit_predict(np.array(data))

    # クラスタごとにまとめ
    clusters = {0: [], 1: [], 2: []}
    for name, label in zip(names, labels):
        clusters[label].append(name)

    html = "<h2>🎵 トラックのクラスタリング結果 (valence, energy, tempo)</h2>"
    for cluster_id, tracks in clusters.items():
        html += f"<b>Cluster {cluster_id + 1}</b>:<br>"
        html += "<br>".join(tracks) + "<br><br>"

    return html

if __name__ == "__main__":
    app.run()
