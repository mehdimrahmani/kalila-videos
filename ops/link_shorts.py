#!/usr/bin/env python3
"""Put a link to the matching long video at the top of every Short on The Guest House channel.

- Honest Historian Shorts ("Folio N ... #Shorts")  -> the full podcast episode "Folio N: ..."
- Rumi Shorts                                        -> the newest long-form Rumi reading
The first description line becomes "▶ <label>: https://youtu.be/<id>". Idempotent: a Short already pointing
at the right video is left alone; an old "▶ " line is replaced. Costs ~50 quota units per changed Short.

usage (with The Guest House token in YT_REFRESH_TOKEN):  python3 ops/link_shorts.py [--dry]
"""
import os, re, sys, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import yt

def secs(d):
    m = re.match(r"P(?:(\d+)D)?T?(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", d)
    dd, h, mi, s = (int(x or 0) for x in m.groups())
    return dd * 86400 + h * 3600 + mi * 60 + s

def main(dry=False):
    ch = yt.me()
    if ch["snippet"]["title"] != "The Guest House":
        sys.exit("wrong channel: " + ch["snippet"]["title"])
    up = ch["contentDetails"]["relatedPlaylists"]["uploads"]
    ids, tok = [], None
    while True:
        p = {"part": "contentDetails", "playlistId": up, "maxResults": 50}
        if tok: p["pageToken"] = tok
        r = yt.call(yt.API + "playlistItems", p)
        ids += [i["contentDetails"]["videoId"] for i in r["items"]]
        tok = r.get("nextPageToken")
        if not tok: break
    vids = []
    for k in range(0, len(ids), 50):
        vids += yt.call(yt.API + "videos", {"part": "snippet,contentDetails,status", "id": ",".join(ids[k:k + 50])})["items"]
    for v in vids:   # when it goes (went) public: scheduled uploads carry status.publishAt
        v["_when"] = v["status"].get("publishAt") or v["snippet"]["publishedAt"]
    longs = [v for v in vids if secs(v["contentDetails"]["duration"]) > 180]
    shorts = [v for v in vids if secs(v["contentDetails"]["duration"]) <= 180]
    folio = {}
    for v in longs:
        m = re.match(r"Folio (\d+):", v["snippet"]["title"])
        if m: folio[m.group(1)] = v["id"]
    rumi_longs = sorted([v for v in longs if "Rumi" in v["snippet"]["title"]], key=lambda v: v["_when"])
    changed = 0
    for v in shorts:
        sn = v["snippet"]; t = sn["title"]
        m = re.search(r"Folio (\d+)", t)
        if m and "Historian" in t:
            target, label = folio.get(m.group(1)), "Full episode (Folio %s)" % m.group(1)
        elif "Rumi" in t:
            # the newest long Rumi reading that is public by the time this Short goes public (else the oldest)
            ok = [x for x in rumi_longs if x["_when"] <= v["_when"]] or rumi_longs[:1]
            target, label = (ok[-1]["id"] if ok else None), "Full Rumi reading"
        else:
            continue
        if not target: continue
        line = "▶ %s: https://youtu.be/%s" % (label, target)
        desc = sn.get("description", "")
        if desc.startswith(line): continue
        rest = "\n".join(l for l in desc.split("\n") if not l.startswith("▶ ")).lstrip("\n")
        new = line + "\n\n" + rest
        print(("DRY " if dry else "") + v["id"], t[:60], "->", target)
        if dry: continue
        body = {"id": v["id"], "snippet": {"title": t, "description": new[:5000], "categoryId": sn.get("categoryId", "27"),
                                           "tags": sn.get("tags", [])}}
        for k in ("defaultLanguage", "defaultAudioLanguage"):
            if sn.get(k): body["snippet"][k] = sn[k]
        yt.call(yt.API + "videos", {"part": "snippet"}, json.dumps(body).encode(), {"Content-Type": "application/json"}, "PUT")
        changed += 1
    print("changed", changed)

if __name__ == "__main__":
    main("--dry" in sys.argv)
