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

global_token  = None

@app.route("/")
def index():
    return "🎧 Spotifyシステムサンプル<br>まず <a href='/login'>/login</a> へアクセスしてください"

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
    global global_token

    code = request.args.get("code")
    if not code:
        return "<p>❌ 認可コードが取得できません。<a href='/login'>/login</a>からやり直してください。</p>"

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
        return f"<p>❌ アクセストークン取得に失敗しました: {err} / {desc}</p><a href='/login'>/login</a>から再度お試しください。"

    global_token  = token_json.get("access_token")

    return """
        <h3>✅ アクセストークン取得成功</h3>
        <p>➞ <a href='/emotion_classify'>/emotion_classify</a> で音響特徴量ベースの感情分類を実行</p>
        <p>➞ <a href='/audio_features_test'>/audio_features_test</a> でAPIテスト（固定曲ID）</p>
    """

def get_tracks_from_followed_artists(token):
    headers = {"Authorization": f"Bearer {token}"}
    url = "https://api.spotify.com/v1/me/following?type=artist&limit=50"
    resp = requests.get(url, headers=headers)
    print("DEBUG /me/following STATUS:", resp.status_code)
    if resp.status_code != 200:
        print("DEBUG /me/following RESPONSE:", resp.text)
        return []
    js = resp.json()
    artists = js.get("artists", {}).get("items", [])
    print("DEBUG artists:", artists)
    if not artists:
        print("DEBUG No artists found.")
        return []
    tracks = []
    for artist in artists:
        artist_id   = artist.get("id")
        artist_name = artist.get("name", "")
        if not artist_id:
            continue
        top_url = f"https://api.spotify.com/v1/artists/{artist_id}/top-tracks?market=JP"
        top_resp = requests.get(top_url, headers=headers)
        if top_resp.status_code != 200:
            continue
        top_tracks = top_resp.json().get("tracks", [])
        for t in top_tracks:
            t_id = t.get("id")
            t_name = t.get("name", "")
            if t_id:
                tracks.append({"id": t_id, "name": t_name, "artist": artist_name})
    print("DEBUG tracks:", tracks)
    return tracks

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
    print("DEBUG TRACKS in /emotion_classify:", tracks)

    if not tracks:
        return "<p>トラック情報が取得できませんでした。Spotifyで「フォロー中アーティスト」を増やして再挑戦してください。</p>"

    selected = tracks[:10]  # 10曲だけ使う
    track_ids = [t['id'] for t in selected]
    print("DEBUG TRACK_IDS:", track_ids)
    features_url = f"https://api.spotify.com/v1/audio-features?ids={','.join(track_ids)}"
    features_resp = requests.get(features_url, headers={"Authorization": f"Bearer {global_token}"})
    print("DEBUG FEATURES_STATUS:", features_resp.status_code)
    print("DEBUG FEATURES_TEXT:", features_resp.text)

    if features_resp.status_code != 200:
        return f"<pre>audio-features エラー: {features_resp.status_code}\n{features_resp.text}</pre>"

    features_list = features_resp.json().get("audio_features", [])
    print("DEBUG FEATURES_LIST:", features_list)

    html = "<h3>曲の特徴量と感情分類</h3><table border=1><tr><th>曲名</th><th>アーティスト</th><th>BPM</th><th>energy</th><th>valence</th><th>acousticness</th><th>感情</th></tr>"
    for i, feat in enumerate(features_list):
        if feat is None:
            continue
        track = selected[i]
        emotion = classify_emotion_by_features(feat)
        html += f"<tr><td>{track['name']}</td><td>{track['artist']}</td><td>{feat['tempo']:.1f}</td><td>{feat['energy']:.2f}</td><td>{feat['valence']:.2f}</td><td>{feat['acousticness']:.2f}</td><td>{emotion}</td></tr>"
    html += "</table>"

    return html

@app.route("/audio_features_test")
def audio_features_test():
    global global_token

    if not global_token:
        return "<p>❌ トークンがありません。まず <a href='/login'>/login</a> してください。</p>"

    test_id = "11dFghVXANMlKmJXsNCbNl"  # 公式サンプル曲
    url = f"https://api.spotify.com/v1/audio-features?ids={test_id}"
    res = requests.get(url, headers={"Authorization": f"Bearer {global_token}"})
    print("AUDIO_FEATURES_TEST:", res.status_code, res.text)
    html = f"<h3>audio-featuresテスト</h3><p>HTTP {res.status_code}</p>"
    try:
        html += f"<pre>{res.json()}</pre>"
    except:
        html += "<pre>JSON decode error</pre>"
    return html

if __name__ == "__main__":
    app.run()
