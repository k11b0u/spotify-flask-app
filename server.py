from flask import Flask, redirect, request
import requests, urllib.parse, base64

app = Flask(__name__)

CLIENT_ID = "7838a0cf003644ae8b5f3f75b9eb534e"
CLIENT_SECRET = "d2d93b5ce2b7403f91125a0ea8685697"
REDIRECT_URI = "https://spotify-flask-app-pduk.onrender.com/callback"
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

     # アクセストークン取得
     res = requests.post(
         TOKEN_URL,
         data={
             "grant_type": "authorization_code",
             "code": code,
             "redirect_uri": REDIRECT_URI
         },
         headers={
             "Authorization": f"Basic {b64_auth}",
             "Content-Type": "application/x-www-form-urlencoded"
         }
     )
     token = res.json().get("access_token")

    # ログイン中のユーザー情報を取得
    user_info = requests.get(
        "https://api.spotify.com/v1/me",
        headers={"Authorization": f"Bearer {token}"}
    ).json()

    # 例：ユーザー名とIDをビューに埋め込む
    user_line = f"🔍 ログイン中ユーザー: {user_info.get('display_name')} ({user_info.get('id')})<br><br>"

     # プレイリスト再生リクエスト
     requests.put(
         "https://api.spotify.com/v1/me/player/play",
         headers={"Authorization": f"Bearer {token}"},
         json={"context_uri": playlist_uri}
     )

    # ユーザー情報を先頭に付けて返す
    return user_line + "✅ Spotifyに再生リクエストを送りました！"


if __name__ == "__main__":
    app.run()
