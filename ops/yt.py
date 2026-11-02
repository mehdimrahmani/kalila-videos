#!/usr/bin/env python3
"""Tiny YouTube Data/Analytics API client for our own channels.
Credentials come from env vars (never commit them):
  YT_CLIENT_ID, YT_CLIENT_SECRET, YT_REFRESH_TOKEN   (or ~/.secrets/youtube_oauth.json)
usage:
  python3 ops/yt.py me                      # channel id, title, stats
  python3 ops/yt.py videos                  # latest uploads with stats
  python3 ops/yt.py analytics 28            # last N days: views, watch time, subs, retention, countries, traffic
  python3 ops/yt.py caption VIDEO_ID LANG FILE.srt [NAME]   # upload a caption track
  python3 ops/yt.py channel UC...           # public stats of any channel (competitors)
  python3 ops/yt.py playlist-create "Title" "Description"   # -> playlist id (public)
  python3 ops/yt.py playlist-add PLAYLIST_ID VIDEO_ID
  python3 ops/yt.py upload FILE.mp4 META.json   # META: {"title","description","tags":[],"privacy":"public","categoryId":"27","madeForKids":false}
"""
import os, sys, json, datetime, urllib.request, urllib.parse, uuid

def creds():
    p = os.path.expanduser("~/.secrets/youtube_oauth.json")
    d = json.load(open(p)) if os.path.exists(p) else {}
    return (os.environ.get("YT_CLIENT_ID") or d.get("client_id"),
            os.environ.get("YT_CLIENT_SECRET") or d.get("client_secret"),
            os.environ.get("YT_REFRESH_TOKEN") or d.get("refresh_token_kalila"))

def token():
    cid, sec, rt = creds()
    body = urllib.parse.urlencode({"client_id": cid, "client_secret": sec, "refresh_token": rt,
                                   "grant_type": "refresh_token"}).encode()
    return json.load(urllib.request.urlopen("https://oauth2.googleapis.com/token", body))["access_token"]

TOK = None
def call(url, params=None, data=None, headers=None, method=None):
    global TOK
    TOK = TOK or token()
    if params: url += "?" + urllib.parse.urlencode(params)
    h = {"Authorization": "Bearer " + TOK}; h.update(headers or {})
    req = urllib.request.Request(url, data=data, headers=h, method=method)
    try:
        return json.load(urllib.request.urlopen(req))
    except urllib.error.HTTPError as e:
        sys.exit(f"HTTP {e.code}: {e.read().decode()[:800]}")

API = "https://www.googleapis.com/youtube/v3/"
def me():
    return call(API + "channels", {"part": "snippet,statistics,contentDetails", "mine": "true"})["items"][0]

def videos(n=20):
    up = me()["contentDetails"]["relatedPlaylists"]["uploads"]
    ids = [i["contentDetails"]["videoId"] for i in
           call(API + "playlistItems", {"part": "contentDetails", "playlistId": up, "maxResults": n})["items"]]
    v = call(API + "videos", {"part": "snippet,statistics,contentDetails,status", "id": ",".join(ids)})["items"]
    return [{"id": x["id"], "title": x["snippet"]["title"], "published": x["snippet"]["publishedAt"],
             "privacy": x["status"]["privacyStatus"], "duration": x["contentDetails"]["duration"],
             **{k: int(x["statistics"].get(k, 0)) for k in ("viewCount", "likeCount", "commentCount")}} for x in v]

def report(days, dims=None, metrics="views,estimatedMinutesWatched,averageViewDuration,averageViewPercentage,subscribersGained,subscribersLost", sort=None, maxr=None):
    end = datetime.date.today(); start = end - datetime.timedelta(days=days)
    p = {"ids": "channel==MINE", "startDate": start.isoformat(), "endDate": end.isoformat(), "metrics": metrics}
    if dims: p["dimensions"] = dims
    if sort: p["sort"] = sort
    if maxr: p["maxResults"] = maxr
    r = call("https://youtubeanalytics.googleapis.com/v2/reports", p)
    cols = [c["name"] for c in r.get("columnHeaders", [])]
    return [dict(zip(cols, row)) for row in r.get("rows", [])]

def analytics(days):
    return {"totals": report(days),
            "by_video": report(days, "video", "views,estimatedMinutesWatched,averageViewDuration,averageViewPercentage,subscribersGained", "-views", 25),
            "countries": report(days, "country", "views,estimatedMinutesWatched", "-views", 15),
            "traffic": report(days, "insightTrafficSourceType", "views,estimatedMinutesWatched", "-views"),
            "content_type": report(days, "creatorContentType", "views,estimatedMinutesWatched,averageViewDuration"),
            "age_gender": report(days, "ageGroup,gender", "viewerPercentage")}

def caption(vid, lang, path, name=""):
    meta = json.dumps({"snippet": {"videoId": vid, "language": lang, "name": name, "isDraft": False}}).encode()
    b = uuid.uuid4().hex
    body = (f"--{b}\r\nContent-Type: application/json; charset=UTF-8\r\n\r\n").encode() + meta + \
           (f"\r\n--{b}\r\nContent-Type: application/octet-stream\r\n\r\n").encode() + open(path, "rb").read() + f"\r\n--{b}--".encode()
    return call("https://www.googleapis.com/upload/youtube/v3/captions", {"part": "snippet", "uploadType": "multipart"},
                body, {"Content-Type": f"multipart/related; boundary={b}"}, "POST")

def upload(path, meta_path):
    m = json.load(open(meta_path))
    body = json.dumps({"snippet": {"title": m["title"][:100], "description": m.get("description", ""),
                                   "tags": m.get("tags", []), "categoryId": m.get("categoryId", "27"),
                                   "defaultLanguage": m.get("language", "en"), "defaultAudioLanguage": m.get("language", "en")},
                       "status": {"privacyStatus": m.get("privacy", "public"), "selfDeclaredMadeForKids": m.get("madeForKids", False),
                                  "containsSyntheticMedia": m.get("synthetic", True)}}).encode()
    global TOK
    TOK = TOK or token()
    size = os.path.getsize(path)
    req = urllib.request.Request("https://www.googleapis.com/upload/youtube/v3/videos?uploadType=resumable&part=snippet,status",
                                 data=body, method="POST", headers={"Authorization": "Bearer " + TOK,
                                 "Content-Type": "application/json; charset=UTF-8", "X-Upload-Content-Type": "video/mp4",
                                 "X-Upload-Content-Length": str(size)})
    loc = urllib.request.urlopen(req).headers["Location"]
    req = urllib.request.Request(loc, data=open(path, "rb").read(), method="PUT",
                                 headers={"Authorization": "Bearer " + TOK, "Content-Type": "video/mp4"})
    try:
        return json.load(urllib.request.urlopen(req, timeout=600))
    except urllib.error.HTTPError as e:
        sys.exit(f"HTTP {e.code}: {e.read().decode()[:800]}")

def playlist_create(title, desc=""):
    b = json.dumps({"snippet": {"title": title, "description": desc, "defaultLanguage": "en"},
                    "status": {"privacyStatus": "public"}}).encode()
    return call(API + "playlists", {"part": "snippet,status"}, b, {"Content-Type": "application/json"}, "POST")

def playlist_add(pid, vid):
    b = json.dumps({"snippet": {"playlistId": pid, "resourceId": {"kind": "youtube#video", "videoId": vid}}}).encode()
    return call(API + "playlistItems", {"part": "snippet"}, b, {"Content-Type": "application/json"}, "POST")

def channel(cid):
    k = "forHandle" if cid.startswith("@") else "id"
    return call(API + "channels", {"part": "snippet,statistics", k: cid})

if __name__ == "__main__":
    a = sys.argv[1:] or ["me"]
    out = {"me": lambda: me(), "videos": lambda: videos(), "analytics": lambda: analytics(int(a[1]) if len(a) > 1 else 28),
           "caption": lambda: caption(*a[1:5]), "channel": lambda: channel(a[1]), "upload": lambda: upload(a[1], a[2]),
           "playlist-create": lambda: playlist_create(a[1], a[2] if len(a) > 2 else ""),
           "playlist-add": lambda: playlist_add(a[1], a[2])}[a[0]]()
    print(json.dumps(out, ensure_ascii=False, indent=1))
