from flask import Flask, redirect, request
import requests, urllib.parse, base64

app = Flask(__name__)

CLIENT_ID     = "7838a0cf003644ae8b5f3f75b9eb534e"
CLIENT_SECRET = "d2d93b5ce2b7403f91125a0ea8685697"
REDIRECT_URI  = "https://spotify-flask-app-pduk.onrender.com/callback"
SCOPE         = (
    "user-read-playback-state "
    "user-modify-playback-state "
    "user-follow-read "
    "user-library-read "
    "user-top-read"
)
AUTH_URL      = "https://accounts.spotify.com/authorize"
TOKEN_URL     = "https://accounts.spotify.com/api/token"

# グローバル変数
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

    return f"""
        <p>✅ アクセストークン取得成功（先頭20文字）: <code>{token[:20]}...</code></p>
        <p>🔌 デバイスID: <code>{global_device_id}</code></p>
        <p>➞ 次は <a href='/debug_raw_features'>/debug_raw_features</a> を開いてください</p>
    """

def get_tracks_from_followed_artists(token):
    headers = {"Authorization": f"Bearer {token}"}
    followed_url = "https://api.spotify.com/v1/me/following?type=artist&limit=10"
    followed = requests.get(followed_url, headers=headers).json()
    artists = followed.get("artists", {}).get("items", [])

    track_ids = []
    for artist in artists:
        artist_id = artist["id"]
        top_url = f"https://api.spotify.com/v1/artists/{artist_id}/top-tracks?market=JP"
        top_tracks = requests.get(top_url, headers=headers).json()
        items = top_tracks.get("tracks", [])
        track_ids.extend([t["id"] for t in items])

    return track_ids

@app.route("/debug_raw_features")
def debug_raw_features():
    global global_token

    html = "<h3>🎵 audio-features の raw JSON</h3>"
    if not global_token:
        return html + "<pre>❌ トークンがありません</pre>"

    track_ids = get_tracks_from_followed_artists(global_token)[:10]  # 多すぎるとURLが長くなるため制限
    if not track_ids:
        return html + "<pre>⛔ 曲が取得できませんでした（フォロー中のアーティストに曲がない？）</pre>"

    ids_param = ",".join(track_ids)
    url = f"https://api.spotify.com/v1/audio-features?ids={ids_param}"

    res = requests.get(url, headers={"Authorization": f"Bearer {global_token}"})
    try:
        res_json = res.json()
    except:
        res_json = {"error": "JSON decode error"}

    html += "<hr>"
    html += f"<p><strong>🪪 トークン（先頭20文字）:</strong><br><code>{global_token[:20]}...</code></p>"
    html += f"<p><strong>🎵 Track IDs:</strong><br><code>{track_ids}</code></p>"
    html += f"<pre>{res_json}</pre>"
    return html

if __name__ == "__main__":
    app.run()

