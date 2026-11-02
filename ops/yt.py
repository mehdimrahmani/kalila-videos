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

def channel(cid):
    k = "forHandle" if cid.startswith("@") else "id"
    return call(API + "channels", {"part": "snippet,statistics", k: cid})

if __name__ == "__main__":
    a = sys.argv[1:] or ["me"]
    out = {"me": lambda: me(), "videos": lambda: videos(), "analytics": lambda: analytics(int(a[1]) if len(a) > 1 else 28),
           "caption": lambda: caption(*a[1:5]), "channel": lambda: channel(a[1])}[a[0]]()
    print(json.dumps(out, ensure_ascii=False, indent=1))
