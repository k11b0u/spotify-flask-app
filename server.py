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
    return "\ud83c\udfb5 Spotify \u518d\u751f\u30c7\u30e2 \u2014 /login \u306b\u30a2\u30af\u30bb\u30b9\u3057\u3066\u304f\u3060\u3055\u3044"

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

    return "\u2705 Spotify \u306b\u30ed\u30b0\u30a4\u30f3\u3057\u307e\u3057\u305f\uff01"

@app.route("/personal_play_debug")
def personal_play_debug():
    global global_token, global_device_id

    if not global_token or not global_device_id:
        return "\u274c \u30ed\u30b0\u30a4\u30f3\u307e\u305f\u306f\u30c7\u30d0\u30a4\u30b9\u672a\u53d6\u5f97\u3067\u3059 /login \u306b\u30a2\u30af\u30bb\u30b9\u3057\u3066\u304f\u3060\u3055\u3044"

    artists_resp = requests.get(
        "https://api.spotify.com/v1/me/following?type=artist&limit=10",
        headers={"Authorization": f"Bearer {global_token}"}
    ).json()

    artists = artists_resp.get("artists", {}).get("items", [])
    artist_ids = [a["id"] for a in artists]
    debug_output = f"\ud83c\udfa4 \u30d5\u30a9\u30ed\u30fc\u4e2d\u30a2\u30fc\u30c6\u30a3\u30b9\u30c8\u6570: {len(artist_ids)}<br>"

    all_tracks = []
    for artist_id in artist_ids:
        top_resp = requests.get(
            f"https://api.spotify.com/v1/artists/{artist_id}/top-tracks?market=JP",
            headers={"Authorization": f"Bearer {global_token}"}
        ).json()
        all_tracks.extend(top_resp.get("tracks", []))

    debug_output += f"\ud83c\udfb5 \u30c8\u30e9\u30c3\u30af\u53d6\u5f97\u6570: {len(all_tracks)}<br>"

    if not all_tracks:
        return debug_output + "\u26a0\ufe0f \u30c8\u30e9\u30c3\u30af\u304c\u53d6\u5f97\u3067\u304d\u307e\u305b\u3093\u3067\u3057\u305f"

    track_ids = [t["id"] for t in all_tracks]
    features_resp = requests.get(
        "https://api.spotify.com/v1/audio-features",
        headers={"Authorization": f"Bearer {global_token}"},
        params={"ids": ",".join(track_ids[:100])}
    ).json()

    features = features_resp.get("audio_features", [])
    bright_tracks = [t for t, f in zip(all_tracks, features)
                     if f and f.get("valence") and f["valence"] > 0.4 and f["energy"] > 0.3]

    debug_output += f"\u2728 \u660e\u308b\u3044\u66f2\u5019\u88dc\u6570: {len(bright_tracks)}<br>"

    if not bright_tracks:
        return debug_output + "\ud83d\ude13 \u660e\u308b\u3044\u66f2\u304c\u898b\u3064\u304b\u308a\u307e\u305b\u3093\u3067\u3057\u305f"

    selected = random.choice(bright_tracks)
    uri = selected["uri"]

    play_url = f"https://api.spotify.com/v1/me/player/play?device_id={global_device_id}"
    requests.put(
        play_url,
        headers={"Authorization": f"Bearer {global_token}"},
        json={"uris": [uri]}
    )

    return debug_output + f"\u2705 \u300e{selected['name']}\u300f\u3092\u518d\u751f\u3057\u307e\u3057\u305f\uff01"

if __name__ == "__main__":
    app.run()

