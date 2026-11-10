#!/usr/bin/env python3
"""Channel page of The Guest House (YouTube): banner, description, keywords, home-page rows, trailer.

A viewer who taps through from a Short should see at once what the channel is and why to subscribe
(Mehdi, 10 Nov 2026: subscribers were flat although Shorts convert at ~0.4%).

  python3 ops/channel_brand.py banner OUT.png          # draw the banner only (2560x1440, safe area 1546x423)
  python3 ops/channel_brand.py apply [TRAILER_VIDEO_ID]  # banner + description + keywords + rows (+ trailer)
Needs The Guest House token in YT_REFRESH_TOKEN (stops on any other channel). Idempotent.
"""
import os, sys, json
import numpy as np
from PIL import Image
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, "..", "guesthouse"))
import yt

DESCRIPTION = """This being human is a guest house: every morning a new arrival. (Rumi)

Rumi, Shams and the great storytellers of old Persia, from the original Persian. Real verses, honest English translations, and what they mean. Not the invented quotes you have seen a thousand times.

• Rumi & Shams: new Shorts every week, and a long reading every Friday
• The Honest Historian: true stories from Beyhaqi's thousand-year-old History, every Sunday (also a podcast on Spotify and Apple Podcasts)

Translated from the Persian by The Guest House. Narration is AI-generated; The Honest Historian is narrated with an AI rendering of the host's own voice.

Instagram: @theguesthouse.poetry"""
KEYWORDS = ('Rumi "Rumi poems" "Rumi in Persian" "Persian poetry" "Sufi poetry" Sufism "Shams Tabrizi" Masnavi '
            '"Divan-e Shams" Mowlana "Persian history" Beyhaqi "The Honest Historian" مولانا')
ROWS = [("rumi", "Rumi & Shams: verses from the original Persian"),
        ("longform", "Long readings: Rumi, with translation and meaning"),
        ("beyhaqi", "The Honest Historian: true stories from Beyhaqi")]

def banner(path):
    import make_reel_manuscript as MM
    W, H = 2560, 1440; rng = np.random.default_rng(11)
    base = np.array([236, 219, 184], np.float32)
    blot = MM.noise(H, W, rng, 120, 26); blot /= np.abs(blot).max() + 1e-9
    fib = MM.gaussian_filter(rng.standard_normal((H, W)), (0.7, 3.0)); fib /= np.abs(fib).max() + 1e-9
    a = base[None, None] * (1 + 0.06 * blot[..., None] + 0.03 * fib[..., None])
    y = np.linspace(-1, 1, H)[:, None]; x = np.linspace(-1, 1, W)[None, :]
    a *= 1 - (0.35 * np.clip(np.maximum(np.abs(x) ** 8, np.abs(y) ** 6), 0, 1))[..., None] * np.array([0.8, 1.0, 1.25])
    cy = H // 2
    # lapis band with gold rules across the whole width (looks right on TV, desktop and phone crops)
    band = slice(cy - 235, cy + 235)
    a[band] = a[band] * 0.0 + np.array(MM.LAPIS, np.float32) * (1 + 0.05 * blot[band][..., None])
    for yy in (cy - 235, cy + 229):
        a[yy:yy + 6] = MM.GOLD
    for yy in (cy - 215, cy + 213):
        a[yy:yy + 2] = MM.GOLD
    # shamsa at the left of the safe area
    S = 300; g, l, d2 = MM.shamsa(S, 0.2); sx, sy = 530, cy - S // 2
    MM.paste(a, MM.GOLD, g, sx, sy); MM.paste(a, np.array(MM.LAPIS, np.float32) * 0.7, l, sx, sy); MM.paste(a, MM.GOLD_HI, d2, sx, sy)
    # text block
    cream = np.array([246, 234, 204], np.float32)
    t1 = MM.text_mask("The Guest House", MM.SERIF, 124, maxw=760)
    MM.paste(a, cream, t1, 870, cy - 185)
    t2 = MM.text_mask("Rumi · Shams · true stories of old Persia", MM.SERIF_I, 52, maxw=760)
    MM.paste(a, MM.GOLD_HI, t2, 875, cy - 30)
    t3 = MM.text_mask("from the original Persian, honestly translated", MM.SERIF_I, 42, maxw=760)
    MM.paste(a, cream, t3, 875, cy + 50)
    t4 = MM.text_mask("مهمان‌خانه", MM.NASTA, 92, rtl=True, maxw=340)
    MM.paste(a, MM.GOLD_HI, t4, 2045 - t4.shape[1], cy - t4.shape[0] // 2 - 10)
    Image.fromarray(np.clip(a, 0, 255).astype(np.uint8)).save(path)
    return path

def apply(trailer=None):
    ch = yt.me()
    if ch["snippet"]["title"] != "The Guest House": sys.exit("wrong channel: " + ch["snippet"]["title"])
    cid = ch["id"]
    cur = yt.call(yt.API + "channels", {"part": "brandingSettings", "id": cid})["items"][0]["brandingSettings"]
    # banner
    png = banner(os.path.join(os.environ.get("TMPDIR", "/tmp"), "gh_banner.png"))
    jpg = png.replace(".png", ".jpg"); Image.open(png).convert("RGB").save(jpg, quality=92)
    up = yt.call("https://www.googleapis.com/upload/youtube/v3/channelBanners/insert", {"channelId": cid},
                 open(jpg, "rb").read(), {"Content-Type": "image/jpeg"}, "POST")
    chan = dict(cur.get("channel", {})); chan.update(description=DESCRIPTION, keywords=KEYWORDS, defaultLanguage="en")
    if trailer: chan["unsubscribedTrailer"] = trailer
    body = {"id": cid, "brandingSettings": {"channel": chan, "image": {"bannerExternalUrl": up["url"]}}}
    yt.call(yt.API + "channels", {"part": "brandingSettings"}, json.dumps(body).encode(),
            {"Content-Type": "application/json"}, "PUT")
    # home-page rows: one per playlist (skip those already there)
    pls = json.load(open(os.path.join(HERE, "..", "guesthouse", "youtube.json")))["playlists"]
    have = yt.call(yt.API + "channelSections", {"part": "snippet,contentDetails", "mine": "true"}).get("items", [])
    have_pl = {p for s in have for p in s.get("contentDetails", {}).get("playlists", [])}
    for pos, (key, title) in enumerate(ROWS):
        if pls.get(key) and pls[key] not in have_pl:
            sec = {"snippet": {"type": "singlePlaylist", "position": pos}, "contentDetails": {"playlists": [pls[key]]}}
            yt.call(yt.API + "channelSections", {"part": "snippet,contentDetails"}, json.dumps(sec).encode(),
                    {"Content-Type": "application/json"}, "POST")
            # the row shows the playlist's own title: make it descriptive
            pl = yt.call(yt.API + "playlists", {"part": "snippet", "id": pls[key]})["items"][0]
            sn = pl["snippet"]
            if sn["title"] != title:
                yt.call(yt.API + "playlists", {"part": "snippet"},
                        json.dumps({"id": pls[key], "snippet": {"title": title, "description": sn.get("description", "")}}).encode(),
                        {"Content-Type": "application/json"}, "PUT")
    print("ok", up["url"][:60], "trailer:", trailer)

if __name__ == "__main__":
    a = sys.argv[1:]
    if a and a[0] == "banner": print(banner(a[1]))
    elif a and a[0] == "apply": apply(a[1] if len(a) > 1 else None)
    else: print(__doc__)
