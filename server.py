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

# ── グローバル変数 ──────────────────────────────
global_token  = None
global_scopes = None
global_device_id = None

@app.route("/")
def index():
    return "🎧 Spotify デバッグ用サンプル — まず <a href='/login'>/login</a> へアクセスしてください"

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
    global global_token, global_scopes, global_device_id

    code = request.args.get("code")
    if not code:
        return "<p>❌ 認可コードが取得できませんでした。</p><p><a href='/login'>/login</a> からやり直してください。</p>"

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
    token_json = res.json()
    if "access_token" not in token_json:
        err = token_json.get("error", "unknown_error")
        desc = token_json.get("error_description", "")
        return f"<p>❌ アクセストークン取得に失敗しました: {err} / {desc}</p><p><a href='/login'>/login</a> から再度お試しください。</p>"

    global_token  = token_json.get("access_token")
    global_scopes = token_json.get("scope", "")

    devices_resp = requests.get(
        "https://api.spotify.com/v1/me/player/devices",
        headers={"Authorization": f"Bearer {global_token}"}
    ).json()
    devices = devices_resp.get("devices", [])
    global_device_id = devices[0]["id"] if devices else None

    return f"""
        <h3>✅ アクセストークン取得成功</h3>
        <p>🪪 トークン（先頭20文字）: <code>{global_token[:20]}...</code></p>
        <p>🔑 付与された scope: <code>{global_scopes}</code></p>
        <p>🔌 デバイスID: <code>{global_device_id}</code></p>
        <hr>
        <p>➞ まずは <a href='/debug_token'>/debug_token</a> で <b>トークンの有効性</b> をチェック</p>
        <p>➞ 次に <a href='/debug_raw_features'>/debug_raw_features</a> で <b>フォロー中アーティスト→audio-features</b> を試します</p>
        <p>➞ 新機能 <a href='/emotion_classify'>/emotion_classify</a> で <b>音響特徴量ベースの感情分類</b> を試す</p>
    """

@app.route("/debug_token")
def debug_token():
    global global_token

    if not global_token:
        return "<p>❌ トークンがありません。<a href='/login'>/login</a> して取得してください。</p>"

    resp = requests.get("https://api.spotify.com/v1/me", headers={"Authorization": f"Bearer {global_token}"})
    if resp.status_code == 200:
        me_json = resp.json()
        username = me_json.get("display_name") or me_json.get("id")
        return f"<p>✅ /me 呼び出し成功。ログイン中ユーザー: <strong>{username}</strong></p><pre>{me_json}</pre>"
    elif resp.status_code == 401:
        return "<p>⛔ /me 呼び出しで 401 Unauthorized。アクセストークンが期限切れの可能性があります。<br><a href='/login'>/login</a> から再試行してください。</p>"
    elif resp.status_code == 403:
        return "<p>⛔ /me 呼び出しで 403 Forbidden。トークンに必要なスコープが付与されていないか、テストユーザー登録がおかしいかもしれません。<br>– Developer Dashboard でテストユーザー登録を再確認。<br><a href='/login'>/login</a> から再試行してください。</p>"
    else:
        return f"<p>⛔ /me 呼び出しで予期せぬエラー: HTTP {resp.status_code}</p><pre>{resp.text}</pre>"

def get_tracks_from_followed_artists(token):
    headers = {"Authorization": f"Bearer {token}"}
    followed_url = "https://api.spotify.com/v1/me/following?type=artist&limit=50"
    resp = requests.get(followed_url, headers=headers)
    if resp.status_code == 403:
        return {"error": "followed_forbidden"}
    if resp.status_code != 200:
        return []
    js = resp.json()
    artists = js.get("artists", {}).get("items", [])
    if not artists:
        return []
    result = []
    for artist in artists:
        artist_id   = artist.get("id")
        artist_name = artist.get("name", "")
        if not artist_id:
            continue
        top_url  = f"https://api.spotify.com/v1/artists/{artist_id}/top-tracks?market=JP"
        top_resp = requests.get(top_url, headers=headers)
        if top_resp.status_code != 200:
            continue
        top_json = top_resp.json()
        tracks   = top_json.get("tracks", [])
        for t in tracks:
            t_id   = t.get("id")
            t_name = t.get("name", "")
            if t_id:
                result.append({"id": t_id, "name": t_name, "artist": artist_name})
    return result

# ここから新規追加▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼
def classify_emotion_by_features(feat):
    bpm = feat['tempo']
    energy = feat['energy']
    valence = feat['valence']
    acousticness = feat['acousticness']

    if bpm < 65 and energy < 0.5:
        return '怒り'
    elif 70 <= bpm < 100 and valence < 0.3:
        return '悲しみ'
    elif 100 <= bpm < 120 and energy < 0.6:
        return '無気力'
    elif bpm >= 120 and valence > 0.6:
        return '幸福'
    elif acousticness > 0.7 and 65 <= bpm < 90:
        return 'リラックス'
    else:
        return '不安'

@app.route("/emotion_classify")
def emotion_classify():
    global global_token

    if not global_token:
        return "<p>❌ トークンがありません。まず <a href='/login'>/login</a> してください。</p>"

    tracks = get_tracks_from_followed_artists(global_token)
    if not tracks or isinstance(tracks, dict):
        return "<p>トラック情報の取得に失敗しました。</p>"

    selected = tracks[:10]
    track_ids = [t['id'] for t in selected]
    features_url = f"https://api.spotify.com/v1/audio-features?ids={','.join(track_ids)}"
    features_resp = requests.get(features_url, headers={"Authorization": f"Bearer {global_token}"})
    if features_resp.status_code != 200:
        return f"<pre>audio-features エラー: {features_resp.status_code}</pre>"

    features_list = features_resp.json().get("audio_features", [])

    html = "<h3>曲の特徴量と感情分類（BPM/energy/valenceベース）</h3><table border=1><tr><th>曲名</th><th>アーティスト</th><th>BPM</th><th>energy</th><th>valence</th><th>acousticness</th><th>感情</th></tr>"
    for i, feat in enumerate(features_list):
        if feat is None:
            continue
        track = selected[i]
        emotion = classify_emotion_by_features(feat)
        html += f"<tr><td>{track['name']}</td><td>{track['artist']}</td><td>{feat['tempo']:.1f}</td><td>{feat['energy']:.2f}</td><td>{feat['valence']:.2f}</td><td>{feat['acousticness']:.2f}</td><td>{emotion}</td></tr>"
    html += "</table>"

    return html
# ここまで新規追加▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲

# 既存の /debug_raw_features などは省略（↑のまま）

if __name__ == "__main__":
    app.run()
