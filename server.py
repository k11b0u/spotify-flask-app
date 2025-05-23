from flask import Flask, redirect, request
import requests, urllib.parse, base64
from collections import defaultdict
import random

app = Flask(__name__)

CLIENT_ID = "7838a0cf003644ae8b5f3f75b9eb534e"
CLIENT_SECRET = "d2d93b5ce2b7403f91125a0ea8685697"
REDIRECT_URI = "https://spotify-flask-app-pduk.onrender.com/callback"
SCOPE = "user-read-playback-state user-modify-playback-state user-follow-read"
AUTH_URL = "https://accounts.spotify.com/authorize"
TOKEN_URL = "https://accounts.spotify.com/api/token"

global_token = None
global_device_id = None

@app.route("/")
def index():
    return "🎧 Spotify 再生デモ — /login にアクセスしてください"

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

    # アーティスト取得
    artists = []
    after = None
    while True:
        url = "https://api.spotify.com/v1/me/following"
        params = {"type": "artist", "limit": 50}
        if after:
            params["after"] = after
        resp = requests.get(url, headers={"Authorization": f"Bearer {global_token}"}, params=params).json()
        items = resp.get("artists", {}).get("items", [])
        if not items:
            break
        artists.extend(items)
        if len(items) < 50:
            break
        after = items[-1]["id"]

    artist_ids = [a["id"] for a in artists]
    artist_names = {a["id"]: a["name"] for a in artists}

    all_tracks = []
    artist_to_tracks = defaultdict(list)
    for artist_id in artist_ids:
        top_resp = requests.get(
            f"https://api.spotify.com/v1/artists/{artist_id}/top-tracks?market=JP",
            headers={"Authorization": f"Bearer {global_token}"}
        ).json()
        tracks = top_resp.get("tracks", [])
        all_tracks.extend(tracks)
        artist_to_tracks[artist_id].extend(tracks)

    track_ids = [t["id"] for t in all_tracks if t.get("id")]
    features_resp = requests.get(
        "https://api.spotify.com/v1/audio-features",
        headers={"Authorization": f"Bearer {global_token}"},
        params={"ids": ",".join(track_ids[:100])}  # max 100
    ).json()
    features = features_resp.get("audio_features", [])

    bright_tracks = [t for t, f in zip(all_tracks, features) if f and f["valence"] > 0.6 and f["energy"] > 0.5]
    dim_tracks = [t for t, f in zip(all_tracks, features) if f and not (f["valence"] > 0.6 and f["energy"] > 0.5)]

    selected = random.choice(bright_tracks) if bright_tracks else None

    lines = [
        f"🧑‍🎤 アーティスト数: {len(artist_ids)}<br>",
        f"📘 トラック数: {len(all_tracks)}<br>",
        f"📍 明るい曲数: {len(bright_tracks)}<br>",
        f"🎵 選曲: {selected['name'] if selected else 'なし'}<br><br>",
        f"<b>🎶 明るい曲:</b><br>"
    ]

    for t, f in zip(all_tracks, features):
        if not f: continue
        brightness = f["valence"] > 0.6 and f["energy"] > 0.5
        emoji = "✨" if brightness else "➖"
        artist_name = next((artist_names[a] for a, ts in artist_to_tracks.items() if t in ts), "Unknown")
        line = f"{emoji} {artist_name} — {t['name']} — valence: {f['valence']:.2f}, energy: {f['energy']:.2f}<br>"
        if brightness:
            lines.append(line)

    lines.append("<br><b>🎶 明るくない曲:</b><br>")
    for t, f in zip(all_tracks, features):
        if not f: continue
        if not (f["valence"] > 0.6 and f["energy"] > 0.5):
            artist_name = next((artist_names[a] for a, ts in artist_to_tracks.items() if t in ts), "Unknown")
            line = f"➖ {artist_name} — {t['name']} — valence: {f['valence']:.2f}, energy: {f['energy']:.2f}<br>"
            lines.append(line)

    return "".join(lines)

if __name__ == "__main__":
    app.run()
