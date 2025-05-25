from flask import Flask, redirect, request
import requests, urllib.parse, base64, json

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
    global_token = res.json().get("access_token")

    devices_resp = requests.get(
        "https://api.spotify.com/v1/me/player/devices",
        headers={"Authorization": f"Bearer {global_token}"}
    ).json()
    devices = devices_resp.get("devices", [])
    global_device_id = devices[0]["id"] if devices else None

    return "✅ Spotify にログインしました！"

@app.route("/debug_raw_features")
def debug_raw_features():
    global global_token

    # フォロー中アーティスト取得
    artists_resp = requests.get(
        "https://api.spotify.com/v1/me/following?type=artist&limit=15",
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
    if not track_ids:
        return "❌ トラックIDが取得できませんでした"

    features_resp = requests.get(
        "https://api.spotify.com/v1/audio-features",
        headers={"Authorization": f"Bearer {global_token}"},
        params={"ids": ",".join(track_ids[:100])}
    ).json()

    return "<h3>🎛 audio-features の raw JSON</h3><pre>" + json.dumps(features_resp, indent=2, ensure_ascii=False) + "</pre>"

if __name__ == "__main__":
    app.run()
