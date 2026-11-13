#!/usr/bin/env python3
"""YouTube Short cut from ONE poem of a long-form Rumi video (The Guest House), pointing viewers to the full video.

usage: python3 guesthouse/lf_short.py LF_SPEC.json POEM_INDEX OUTDIR [FULL_VIDEO_ID]
  -> OUTDIR/<lfNN>_p<i>.mp4  (1080x1920, navy reel style of make_reel.py, ney + English narration,
                               last 3 s: a "Watch the full reading" pill in the top header band)
  -> OUTDIR/<lfNN>_p<i>.youtube.json  (draft meta: title, description with exact verses + link, tags)
Verses come only from the long-form spec (already checked against ganjoor.net) — nothing is invented here.
Poems already used as Shorts are listed in guesthouse/youtube.json "lf_shorts"; poems whose first Persian line
already appears in guesthouse/specs/*.json (Instagram reels) should be skipped by the caller.
"""
import sys, os, json, subprocess, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import make_reel, yt_endcard

def main(spec_path, idx, outdir, video_id=None):
    lf = json.load(open(spec_path, encoding="utf-8")); i = int(idx); p = lf["poems"][i]
    os.makedirs(outdir, exist_ok=True)
    base = os.path.join(outdir, f"{lf['id']}_p{i + 1}")
    reel = {"header": lf["title"].split(":")[0], "title": p["name"],
            "fa": [l["fa"] for l in p["lines"]], "en": [l["en"] for l in p["lines"]],
            "source": p["source"].replace(" · ", ", "), "seed": lf.get("seed", 1) * 10 + i,
            # voices alternate Short by Short (Mehdi, 13 Nov 2026: "4 is better, 2 is good too, alternate them")
            "voice_style": "lewis" if (int("".join(c for c in lf["id"] if c.isdigit()) or 0) + i) % 2 == 0 else "george_lewis"}
    raw = base + "_raw.mp4"
    make_reel.build(reel, raw)
    # end card: point to the full long-form video
    dur = float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                                         "-of", "csv=p=0", raw]).decode())
    png = os.path.join(tempfile.mkdtemp(), "cta.png")
    yt_endcard.card("", "Watch the full reading", png)   # pill only, placed in the top header band
    t0 = max(0.0, dur - 3.0)
    mid = os.path.join(tempfile.mkdtemp(), "mid.png"); yt_endcard.mid_pill("Subscribe for more Rumi", mid)
    a, b = yt_endcard.mid_window(dur)       # a subscribe pill for ~4 s mid-way, in the top header band
    # Both pills go to the TOP header band (y 200-430): YouTube's own title/channel/subscribe overlay covers the
    # bottom ~25% of a Short, so anything drawn there is hidden (Mehdi, 13 Nov 2026). The header duplicates the
    # title anyway, so a navy box hides it while a pill is shown.
    box = "x=95:y=200:w=890:h=230:color=0x1B2140:t=fill"
    flt = (f"[1:v]format=rgba,fade=t=in:st={t0:.2f}:d=0.6:alpha=1[c];"
           f"[2:v]format=rgba,fade=t=in:st={a:.2f}:d=0.5:alpha=1,fade=t=out:st={b - 0.5:.2f}:d=0.5:alpha=1[m];"
           f"[0:v]drawbox={box}:enable='between(t,{a:.2f},{b:.2f})+gte(t,{t0:.2f})'[v00];"
           f"[v00][m]overlay=0:255:enable='between(t,{a:.2f},{b:.2f})'[v0];"
           f"[v0][c]overlay=0:115:enable='gte(t,{t0:.2f})'[v]")
    subprocess.check_call(["ffmpeg", "-v", "error", "-y", "-i", raw, "-loop", "1", "-t", f"{dur:.2f}", "-i", png,
                           "-loop", "1", "-t", f"{dur:.2f}", "-i", mid,
                           "-filter_complex", flt, "-map", "[v]", "-map", "0:a", "-c:v", "libx264", "-crf", "19",
                           "-pix_fmt", "yuv420p", "-c:a", "copy", "-movflags", "+faststart", base + ".mp4"])
    os.remove(raw)
    en1 = p["lines"][0]["en"].rstrip(",;:")
    title = f"{en1} — Rumi in the original Persian #Shorts"
    if len(title) > 100: title = f"{p['name']} — Rumi in the original Persian #Shorts"
    link = f"▶ Full reading ({lf['title']}): https://youtu.be/{video_id}\n\n" if video_id else ""
    verses = "\n".join(l["fa"] for l in p["lines"]) + "\n\n" + "\n".join(l["en"] for l in p["lines"])
    desc = (link + verses + f"\n\nRumi · {p['source']}\nFrom our long-form reading: {lf['title']}\n"
            "Translated from the Persian by The Guest House. Narration voice is AI-generated.\n\n"
            "#Rumi #SufiPoetry #PersianPoetry #Mowlana #Sufism #RumiQuotes")
    meta = {"title": title, "description": desc,
            "tags": ["Rumi", "Rumi poetry", "Sufi poetry", "Persian poetry", "Mowlana", "مولانا", "Divan-e Shams",
                     "Masnavi", "Rumi in Persian", "Rumi translation"],
            "categoryId": "27", "privacy": "public", "madeForKids": False, "synthetic": True, "language": "en"}
    json.dump(meta, open(base + ".youtube.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(base + ".mp4", round(dur, 1), "s |", title)

if __name__ == "__main__":
    main(*sys.argv[1:5])
