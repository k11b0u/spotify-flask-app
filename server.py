from flask import Flask, redirect, request
import requests, urllib.parse, base64

app = Flask(__name__)

CLIENT_ID     = "your_client_id"
CLIENT_SECRET = "your_client_secret"
REDIRECT_URI  = "your_redirect_uri"
SCOPE         = "user-read-playback-state user-modify-playback-state user-follow-read"
AUTH_URL      = "https://accounts.spotify.com/authorize"
TOKEN_URL     = "https://accounts.spotify.com/api/token"

# グローバル状態
global_token = None
global_device_id = None

@app.route("/cluster_tracks_debug")
def cluster_tracks_debug():
    import random

    global global_token, global_device_id

    if not global_token or not global_device_id:
        return "❌ ログインまたはデバイス未取得です /login にアクセスしてください"

    # 1. フォロー中アーティスト取得
    artists_resp = requests.get(
        "https://api.spotify.com/v1/me/following?type=artist&limit=15",
        headers={"Authorization": f"Bearer {global_token}"}
    ).json()

    artists = artists_resp.get("artists", {}).get("items", [])
    artist_ids = [a["id"] for a in artists]
    artist_names = [a["name"] for a in artists]

    all_tracks = []
    for artist_id in artist_ids:
        top_resp = requests.get(
            f"https://api.spotify.com/v1/artists/{artist_id}/top-tracks?market=JP",
            headers={"Authorization": f"Bearer {global_token}"}
        ).json()
        all_tracks.extend(top_resp.get("tracks", []))

    track_ids = [t["id"] for t in all_tracks]
    track_names = [t["name"] for t in all_tracks]
    if not track_ids:
        return "❌ トラックが取得できませんでした"

    features_resp = requests.get(
        "https://api.spotify.com/v1/audio-features",
        headers={"Authorization": f"Bearer {global_token}"},
        params={"ids": ",".join(track_ids[:100])}
    ).json()

    features = features_resp.get("audio_features", [])
    valid_tracks = [(t, f) for t, f in zip(all_tracks, features) if f]
    invalid_tracks = [(t["name"], t["id"]) for t, f in zip(all_tracks, features) if not f]

    html = ""
    html += f"🧑‍🎤 アーティスト数: {len(artist_ids)}<br>"
    html += f"📘 トラック数: {len(track_ids)}<br>"
    html += f"✅ 特徴量取得成功: {len(valid_tracks)}<br>"
    html += f"❌ 取得失敗（None）: {len(invalid_tracks)}<br><br>"

    html += "<h3>🎵 有効なトラック:</h3>"
    for t, f in valid_tracks:
        html += f"{t['name']} - valence: {f['valence']}, energy: {f['energy']}, tempo: {f['tempo']}<br>"

    html += "<h3>🛑 無効なトラック:</h3>"
    for name, id_ in invalid_tracks:
        html += f"{name} (ID: {id_})<br>"

    return html

# 他のエンドポイントやloginなどは省略
