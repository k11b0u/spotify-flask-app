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

# ── グローバル変数 ────────────────────────────────────────────────────
global_token  = None
global_scopes = None  # トークン取得時に返ってくるスコープを保存
global_device_id = None

# ── ルート定義 ────────────────────────────────────────────────────────
@app.route("/")
def index():
    return "🎧 Spotify デバッグ用サンプル — まず <a href='/login'>/login</a> へアクセスしてください"

@app.route("/login")
def login():
    """
    Spotify 認可ページへリダイレクトし、認可コードを取得する
    """
    params = {
        "client_id":     CLIENT_ID,
        "response_type": "code",
        "redirect_uri":  REDIRECT_URI,
        "scope":         SCOPE,
    }
    return redirect(f"{AUTH_URL}?{urllib.parse.urlencode(params)}")

@app.route("/callback")
def callback():
    """
    Spotify から認可コードを受け取り、アクセストークンを取得して画面表示する。
    ‘scope’ フィールドも取り出し、global_scopes に保持する。
    """
    global global_token, global_scopes, global_device_id

    code = request.args.get("code")
    if not code:
        return "<p>❌ 認可コードが取得できませんでした。</p><p><a href='/login'>/login</a> からやり直してください。</p>"

    # Authorization: Basic {Base64(client_id:client_secret)}
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
    # トークンが取れなかった場合
    if "access_token" not in token_json:
        err = token_json.get("error", "unknown_error")
        desc = token_json.get("error_description", "")
        return f"<p>❌ アクセストークン取得に失敗しました: {err} / {desc}</p><p><a href='/login'>/login</a> から再度お試しください。</p>"

    # 正常に取れていれば保存
    global_token  = token_json.get("access_token")
    global_scopes = token_json.get("scope", "")

    # （任意）デバイス一覧を取得し、先頭のIDを保存しておく
    devices_resp = requests.get(
        "https://api.spotify.com/v1/me/player/devices",
        headers={"Authorization": f"Bearer {global_token}"}
    ).json()
    devices = devices_resp.get("devices", [])
    global_device_id = devices[0]["id"] if devices else None

    # 画面表示
    return f"""
        <h3>✅ アクセストークン取得成功</h3>
        <p>🪪 トークン（先頭20文字）: <code>{global_token[:20]}...</code></p>
        <p>🔑 付与された scope: <code>{global_scopes}</code></p>
        <p>🔌 デバイスID: <code>{global_device_id}</code></p>
        <hr>
        <p>➞ まずは <a href='/debug_token'>/debug_token</a> で <b>トークンの有効性</b> をチェック</p>
        <p>➞ 次に <a href='/debug_raw_features'>/debug_raw_features</a> で <b>フォロー中アーティスト→audio-features</b> を試します</p>
    """

@app.route("/debug_token")
def debug_token():
    """
    /me エンドポイントを叩いて、アクセストークンが有効かどうか確認する
    """
    global global_token

    if not global_token:
        return "<p>❌ トークンがありません。<a href='/login'>/login</a> して取得してください。</p>"

    # /me を呼ぶ
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
    """
    フォロー中アーティストのトップトラックをまとめて取得する。
    戻り値:
      - 成功時：[
          {"id": track_id, "name": track_name, "artist": artist_name}, …
        ]
      - フォロー情報取得で 403 が返った時：{"error": "followed_forbidden"}
      - 取得に失敗して曲がない、などの時：空リスト []
    """
    headers = {"Authorization": f"Bearer {token}"}
    followed_url = "https://api.spotify.com/v1/me/following?type=artist&limit=50"
    resp = requests.get(followed_url, headers=headers)

    if resp.status_code == 403:
        # フォロー中アーティストを取得する権限がない（テストユーザー登録の問題？）
        return {"error": "followed_forbidden"}

    if resp.status_code != 200:
        # その他のエラー
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

        # 各アーティストの日本でのトップトラックを取得
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

@app.route("/debug_raw_features")
def debug_raw_features():
    """
    フォロー中アーティストからトップトラックを取得し、その ID を使って /audio-features を呼ぶ。
    途中で 403 が返ってきた場合には、「テストユーザー登録」や「再認証」を促すメッセージを表示。
    """
    global global_token

    html = "<h3>🎵 audio-features の raw JSON（フォロー中アーティストのトラック）</h3>"

    if not global_token:
        return html + "<pre>❌ トークンがありません。<a href='/login'>/login</a> から再度認証してください。</pre>"

    #
    # 1) フォロー中アーティストのトップトラックを取得
    #
    track_info = get_tracks_from_followed_artists(global_token)
    if isinstance(track_info, dict) and track_info.get("error") == "followed_forbidden":
        # フォロー情報取得時に 403 が返ってきた
        return (
            html +
            "<pre>⛔ フォロー中アーティスト情報の取得で 403 Forbidden が返されました。\n"
            "　・Spotify Developer Dashboard でアプリが Development Mode の場合、ご自身のアカウントが“テストユーザー”として正しく登録されているか？\n"
            "　・アクセストークンが期限切れではないか？\n"
            "　をご確認ください。<br>"
            "<a href='/login'>/login</a> から再度認証してみてください。</pre>"
        )

    if not track_info:
        # アーティストがいない or トップトラックが存在しない場合
        return html + "<pre>⛔ フォロー中アーティスト または トップトラックが見つかりません。</pre>"

    #
    # 2) 先頭10曲だけ選んで表示
    #
    selected = track_info[:10]
    ids_only = [t["id"] for t in selected]

    html += "<h4>📝 選択されたトラック（最初の10件）:</h4>"
    html += "<ul>"
    for t in selected:
        html += f"<li>{t['artist']} - {t['name']} (<code>{t['id']}</code>)</li>"
    html += "</ul>"

    #
    # 3) /audio-features を叩く
    #
    ids_param     = ",".join(ids_only)
    features_url  = f"https://api.spotify.com/v1/audio-features?ids={ids_param}"
    features_resp = requests.get(features_url, headers={"Authorization": f"Bearer {global_token}"})

    if features_resp.status_code == 403:
        return (
            html +
            "<hr>"
            "<pre>⛔ audio-features の取得で 403 Forbidden が返されました。\n"
            "　・アクセストークンが有効期限切れではないか？\n"
            "　・アプリが開発モードの場合、ご自身のアカウントがテストユーザーとして登録されているか？\n"
            "　をご確認ください。\n"
            "<a href='/login'>/login</a> から再度認証してみてください。</pre>"
        )

    if features_resp.status_code != 200:
        return html + f"<pre>⛔ audio-features エラー: HTTP {features_resp.status_code}\n{features_resp.text}</pre>"

    try:
        features_json = features_resp.json()
    except:
        features_json = {"error": "JSON decode error"}

    html += "<hr>"
    html += f"<p><strong>🪪 トークン（先頭20文字）:</strong><br><code>{global_token[:20]}...</code></p>"
    html += f"<p><strong>🎵 Track IDs:</strong><br><code>{ids_only}</code></p>"
    html += f"<pre>{features_json}</pre>"

    return html

if __name__ == "__main__":
    app.run()
