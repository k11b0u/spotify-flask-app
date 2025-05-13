from flask import Flask, redirect, request
import requests, urllib.parse, base64

app = Flask(__name__)

CLIENT_ID = "7838a0cf003644ae8b5f3f75b9eb534e"
CLIENT_SECRET = "f78cf9e77948400aabdc89b7d31b28ff"
REDIRECT_URI = "https://spotify-flask-app.onrender.com/callback"
SCOPE = "user-read-playback-state user-modify-playback-state streaming"
AUTH_URL = "https://accounts.spotify.com/authorize"
TOKEN_URL = "https://accounts.spotify.com/api/token"


@app.route("/login")
def login():
    params = {
        "client_id": CLIENT_ID,
        "response_type": "code",
        "redirect_uri": REDIRECT_URI,
        "scope": SCOPE
    }
    url = f"{AUTH_URL}?{urllib.parse.urlencode(params)}"
    return redirect(url)


@app.route("/callback")
def callback():
    code = request.args.get("code")
    auth_str = f"{CLIENT_ID}:{CLIENT_SECRET}"
    b64_auth = base64.b64encode(auth_str.encode()).decode()

    res = requests.post(TOKEN_URL, data={
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": REDIRECT_URI
    }, headers={
        "Authorization": f"Basic {b64_auth}",
        "Content-Type": "application/x-www-form-urlencoded"
    })

    token = res.json().get("access_token")

    # プレイリスト再生（Spotifyアプリが開いていれば再生される）
    playlist_uri = "spotify:playlist:37i9dQZF1DXdPec7aLTmlC"
    requests.put("https://api.spotify.com/v1/me/player/play", headers={
        "Authorization": f"Bearer {token}"
    },json={"context_uri": "spotify:playlist:37i9dQZF1DXcBWIGoYBM5M"}
                )


    return "✅ Spotifyに再生リクエストを送りました！"

if __name__ == "__main__":
    app.run()
