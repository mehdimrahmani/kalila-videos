#!/usr/bin/env python3
"""YouTube metadata, English captions and a thumbnail for a rendered long-form video.

usage: python3 longform/make_meta.py longform/specs/lfNN_x.json
reads  longform/remotion/public/<id>/timeline.json and longform/remotion/out/<id>.mp4
writes longform/remotion/out/<id>.youtube.json, <id>.en.srt, <id>.thumb.jpg
Spec may carry "yt_title" (else "<title> | N Persian Sufi Poems with English Translation").
"""
import os, sys, json, subprocess
HERE = os.path.dirname(os.path.abspath(__file__))

def ts(t, srt=False):
    h, r = divmod(t, 3600); m, s = divmod(r, 60)
    if srt: return "%02d:%02d:%02d,%03d" % (h, m, int(s), int((s % 1) * 1000))
    return ("%d:%02d:%02d" % (h, m, int(s))) if h else ("%d:%02d" % (m, int(s)))

def main(spec_path):
    spec = json.load(open(spec_path, encoding="utf-8")); i = spec["id"]
    tl = json.load(open(os.path.join(HERE, "remotion", "public", i, "timeline.json"), encoding="utf-8"))
    out = os.path.join(HERE, "remotion", "out")
    ev = tl["events"]; n = len(spec["poems"])
    chap = ["0:00 Introduction"] + ["%s %s · %s" % (ts(e["t0"]), e["name"], e["source"]) for e in ev if e["kind"] == "chapter"]
    end = [e for e in ev if e["kind"] == "end"]
    if end: chap.append("%s Closing" % ts(end[0]["t0"]))
    verses = []
    for p in spec["poems"]:
        verses.append("— %s (%s)" % (p["name"], p["source"]))
        verses += ["%s\n%s" % (l["fa"], l["en"]) for l in p["lines"]]
        verses.append("")
    title = spec.get("yt_title") or "%s | %d Persian Sufi Poems with English Translation" % (spec["title"], n)
    desc = "\n".join([
        "%s — %s" % (spec["title"], spec["fa_title"]),
        "Real verses of Rumi (Mowlana Jalaluddin Balkhi), read in honest English translation from the original Persian, with a short reflection after each poem.",
        "", "Chapters:", *chap, "", "The verses:", *verses,
        "Every week: a new long reading from Rumi. Short daily verses on the channel and on Instagram @theguesthouse.poetry",
        "", "Narration voice and music are AI-generated; translations follow the Persian text closely.",
        "", "#Rumi #Sufi #PersianPoetry #Mowlana #Masnavi #Shams"])
    meta = {"title": title[:100], "description": desc[:4900],
            "tags": ["Rumi", "Rumi poems", "Rumi poetry", "Persian poetry", "Sufi poetry", "Masnavi", "Divan-e Shams",
                     "Mowlana", "Rumi quotes", "Shams Tabrizi", "Sufism", "Rumi English translation", "مولانا", "مثنوی", "دیوان شمس"],
            "privacy": "public", "categoryId": "27", "madeForKids": False, "synthetic": True, "language": "en"}
    json.dump(meta, open(os.path.join(out, i + ".youtube.json"), "w"), ensure_ascii=False, indent=1)
    cues = []
    for e in ev:
        if e["kind"] in ("intro", "tafsir", "outro"): cues.append((e["t0"], e["t1"], e["text"]))
        elif e["kind"] == "line": cues.append((e["en_t0"], e["t1"] - 0.6, e["en"]))
    with open(os.path.join(out, i + ".en.srt"), "w", encoding="utf-8") as f:
        for k, (a, b, t) in enumerate(cues, 1):
            f.write("%d\n%s --> %s\n%s\n\n" % (k, ts(a, True), ts(b, True), t))
    # thumbnail: the title card, fully drawn
    tt = next(e for e in ev if e["kind"] == "title")
    t = min(4.0, max(1.5, tt["t1"] - 1.0))
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", str(t), "-i", os.path.join(out, i + ".mp4"), "-frames:v", "1",
                    "-q:v", "3", os.path.join(out, i + ".thumb.jpg")], check=True)
    print(title); print("\n".join(chap))

if __name__ == "__main__":
    main(sys.argv[1])
