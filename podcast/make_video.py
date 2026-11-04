#!/usr/bin/env python3
"""YouTube versions of a Honest Historian episode (made from the finished podcast mp3):

  python3 podcast/make_video.py N            -> podcast/video/epNN.mp4        (1920x1080, full episode)
                                               podcast/video/epNN_short.mp4  (1080x1920, cold-open Short)
                                               podcast/video/epNN.youtube.json (title, description with chapters, tags)

Look: aged paper + the red seal (same identity as the cover), the folio title, the current chapter, a red-ink
waveform that moves with the voice, and English captions (many people watch muted).
Caption timing comes from podcast/episodes/epNN.timing.json (written by make_podcast.py). For episodes rendered
before that file existed, the timing is rebuilt by re-running only the Kokoro step (same durations as FreeVC).
Chapter names come from the episode JSON field "chapters" (one per section between '---'), optional.
"""
import os, sys, json, subprocess, tempfile, textwrap
import numpy as np
from PIL import Image
HERE = os.path.dirname(os.path.abspath(__file__)); REPO = os.path.dirname(HERE)
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(REPO, "guesthouse"))
import make_reel_cinematic as R
import make_logo as L

INK = (48, 30, 22); RED = (128, 30, 26)
OUT = os.path.join(HERE, "video")

def ts(t):
    h = int(t // 3600); m = int(t % 3600 // 60); s = t % 60
    return f"{h}:{m:02d}:{s:05.2f}"

def mmss(t):
    t = int(t); return f"{t // 60}:{t % 60:02d}" if t < 3600 else f"{t // 3600}:{t % 3600 // 60:02d}:{t % 60:02d}"

# ------------------------------------------------------------------ timing
def timing(ep):
    p = os.path.join(HERE, "episodes", f"ep{ep['n']:02d}.timing.json")
    if os.path.exists(p):
        return json.load(open(p))
    import make_podcast as P
    k = P.kokoro(); tl = []; t = 0.8; sec = 0
    dur = lambda c: (lambda a: len(a[0]) / a[1])(k.create(c, voice="am_onyx", speed=0.9, lang="en-us"))
    if ep.get("cold_open"):
        for c in P.chunks(ep["cold_open"]):
            d = dur(c); tl.append((t, t + d, c, -1)); t += d + 0.35
        t += 1.0
    t += 9.0
    for par in ep["paragraphs"]:
        if par.strip() == "---":
            t += 14.5; sec += 1; continue
        for c in P.chunks(par):
            d = dur(c); tl.append((t, t + d, c, sec)); t += d + 0.28
        t += 0.5
    res = {"timeline": tl, "total": t + 12.5, "estimated": True}
    json.dump(res, open(p, "w"), indent=0)
    return res

def cues(timeline, maxc=74, lines=2):
    """Split each spoken chunk into caption cards (<= 2 lines of ~37 chars), timed by length."""
    out = []
    for a, b, text, sec in timeline:
        words = text.split(); cards, cur = [], ""
        for w in words:
            if len(cur) + len(w) + 1 > maxc and cur:
                cards.append(cur); cur = w
            else:
                cur = (cur + " " + w).strip()
        if cur: cards.append(cur)
        tot = sum(len(c) for c in cards); t = a
        for c in cards:
            d = (b - a) * len(c) / tot
            out.append((t, t + d, "\\N".join(textwrap.wrap(c, maxc // lines + 4)), sec)); t += d
    return out

def sections(ep, timeline, total):
    """(start, name) per section; cold open and welcome get their own chapter."""
    names = ep.get("chapters") or []
    first = {}
    for a, b, text, sec in timeline:
        first.setdefault(sec, a)
    ch = []
    if -1 in first: ch.append((0.0, "Cold open"))
    nsec = max(first) + 1
    for s in range(nsec):
        if s not in first: continue
        start = 0.0 if (s == 0 and -1 not in first) else max(0.0, first[s] - (9.0 if s == 0 else 14.0))
        nm = names[s] if s < len(names) else ("Welcome" if s == 0 else f"Part {s}")
        ch.append((start, nm))
    return ch

# ------------------------------------------------------------------ art
def paper(W, H, seed=3):
    from scipy.ndimage import gaussian_filter
    rng = np.random.default_rng(seed)
    base = np.ones((H, W, 3)) * np.array([226, 211, 178])
    base += gaussian_filter(rng.standard_normal((H, W)), 1.5)[..., None] * 7
    base += gaussian_filter(rng.standard_normal((H, W)), max(W, H) / 13)[..., None] * 1600 * np.array([1.0, 0.9, 0.6])
    yy, xx = np.mgrid[0:H, 0:W]
    base *= np.clip(1 - 0.32 * (((xx - W / 2) / (W * 0.62)) ** 2 + ((yy - H / 2) / (H * 0.62)) ** 2), 0, 1)[..., None]
    return base

def seal(arr, cx, cy, size):
    m = L.ink_mask(L.variant_a)
    m = np.asarray(Image.fromarray((m * 255).astype(np.uint8)).rotate(-2.0, resample=Image.BICUBIC)
                   .resize((size, size), Image.LANCZOS), float) / 255
    y0, x0 = int(cy - size / 2), int(cx - size / 2)
    reg = arr[y0:y0 + size, x0:x0 + size]
    arr[y0:y0 + size, x0:x0 + size] = reg * (1 - m[..., None] * 0.92) + np.array(RED) * m[..., None] * 0.92

def text(arr, s, font, size, cx, cy, color=INK):
    R.composite(arr, R.glow_rgba(R.text_img(s, font, size), color, color, 1, 0.05), cx, cy)

def frame(arr, W, H, pad):
    from PIL import ImageDraw
    im = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8)); d = ImageDraw.Draw(im)
    d.rectangle([pad, pad, W - pad, H - pad], outline=INK, width=4)
    d.rectangle([pad + 14, pad + 14, W - pad - 14, H - pad - 14], outline=INK, width=1)
    return im

def wide_bg(ep, path):
    W, H = 1920, 1080
    a = paper(W, H); seal(a, 420, 470, 560)
    text(a, "THE HONEST HISTORIAN", R.SERIF, 52, 1290, 200)
    text(a, "Stories from Beyhaqi", R.SERIF_I, 40, 1290, 262)
    t = ep["title"]; head, _, rest = t.partition(":")
    text(a, head.upper(), R.SERIF, 34, 1290, 360, RED)
    for i, ln in enumerate(textwrap.wrap(rest.strip() or t, 26)):
        text(a, ln, R.SERIF, 64, 1290, 440 + i * 78)
    text(a, "with Mehdi Rahmani", R.SERIF_I, 32, 420, 790)
    frame(a, W, H, 34).save(path)

def tall_bg(ep, path):
    W, H = 1080, 1920
    a = paper(W, H, 5); seal(a, 540, 430, 520)
    text(a, "THE HONEST HISTORIAN", R.SERIF, 56, 540, 760)
    text(a, "Stories from Beyhaqi", R.SERIF_I, 42, 540, 830)
    frame(a, W, H, 30).save(path)

def end_card(ep, path, W=1080, H=1920):
    from PIL import ImageDraw
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0)); a = np.zeros((H, W, 4))
    im = Image.fromarray(np.clip(paper(W, H, 9), 0, 255).astype(np.uint8)).convert("RGBA")
    arr = np.asarray(im.convert("RGB"), float).copy(); seal(arr, 540, 560, 600)
    text(arr, "Hear the full story", R.SERIF, 64, 540, 1060)
    text(arr, ep["title"].split(":")[0], R.SERIF, 52, 540, 1150, RED)
    text(arr, "on our channel and podcast", R.SERIF_I, 46, 540, 1230)
    frame(arr, W, H, 30).save(path)

# ------------------------------------------------------------------ subtitles
ASS_HEAD = """[Script Info]
ScriptType: v4.00+
PlayResX: {W}
PlayResY: {H}
WrapStyle: 2

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Cap,FreeSerif,{cap},&H00161E30,&H00161E30,&H00B8D3E2,&H00000000,0,0,0,0,100,100,0,0,1,{ol},0,2,{ml},{mr},{mv},1
Style: Chap,FreeSerif,{chs},&H001A1E80,&H001A1E80,&H00B8D3E2,&H00000000,0,1,0,0,100,100,1,0,1,0,0,8,{cml},{cmr},{cmv},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

def write_ass(path, cs, chaps, total, W, H, **st):
    ev = [f"Dialogue: 0,{ts(a)},{ts(b)},Cap,,0,0,0,,{{\\fad(120,120)}}{t}" for a, b, t, _ in cs]
    for i, (a, name) in enumerate(chaps):
        b = chaps[i + 1][0] if i + 1 < len(chaps) else total
        ev.append(f"Dialogue: 0,{ts(a)},{ts(b)},Chap,,0,0,0,,{{\\fad(600,600)}}— {name} —")
    open(path, "w", encoding="utf-8").write(ASS_HEAD.format(W=W, H=H, **st) + "\n".join(ev) + "\n")

# ------------------------------------------------------------------ build
def build(n):
    ep = json.load(open(os.path.join(HERE, "episodes", f"ep{n:02d}.json")))
    mp3 = os.path.join(REPO, "docs", "podcast", "episodes", f"ep{n:02d}.mp3")
    real = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", mp3],
                                capture_output=True, text=True).stdout)
    tm = timing(ep); tl = [tuple(x) for x in tm["timeline"]]
    k = real / tm["total"] if tm.get("estimated") else 1.0          # tiny drift correction for rebuilt timing
    tl = [(a * k, b * k, c, s) for a, b, c, s in tl]
    os.makedirs(OUT, exist_ok=True); tmp = tempfile.mkdtemp()
    chaps = sections(ep, tl, real)

    # ---- full episode, 1920x1080
    bg = os.path.join(tmp, "bg.png"); wide_bg(ep, bg)
    ass = os.path.join(tmp, "cap.ass")
    write_ass(ass, cues(tl, 84), chaps, real, 1920, 1080, cap=46, ol=0, ml=200, mr=200, mv=92,
              chs=38, cml=860, cmr=110, cmv=640)
    out = os.path.join(OUT, f"ep{n:02d}.mp4")
    fc = (f"[1:a]showwaves=s=1000x120:mode=cline:rate=24:colors=0x801E1A:scale=sqrt,format=rgba,"
          f"colorkey=0x000000:0.1:0.0[w];[0:v][w]overlay=790:760[v1];[v1]subtitles='{ass}'[v]")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-loop", "1", "-framerate", "24", "-i", bg, "-i", mp3,
                    "-filter_complex", fc, "-map", "[v]", "-map", "1:a", "-c:v", "libx264", "-preset", "veryfast",
                    "-tune", "stillimage", "-crf", "24", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k",
                    "-shortest", "-movflags", "+faststart", out], check=True)

    # ---- cold-open Short, 1080x1920
    cold = [x for x in tl if x[3] == -1]
    if cold:
        end = min(58.0, cold[-1][1] + 7.0); e0 = end - 3.2
        bg2 = os.path.join(tmp, "bg2.png"); tall_bg(ep, bg2)
        endp = os.path.join(tmp, "end.png"); end_card(ep, endp)
        ass2 = os.path.join(tmp, "cap2.ass")
        write_ass(ass2, [c for c in cues(cold, 44) if c[0] < e0], [], end, 1080, 1920, cap=66, ol=0, ml=90, mr=90,
                  mv=330, chs=10, cml=0, cmr=0, cmv=0)
        sh = os.path.join(OUT, f"ep{n:02d}_short.mp4")
        fc2 = (f"[1:a]showwaves=s=860x140:mode=cline:rate=24:colors=0x801E1A:scale=sqrt,format=rgba,"
               f"colorkey=0x000000:0.1:0.0[w];[0:v][w]overlay=110:1000[v1];[v1]subtitles='{ass2}'[v2];"
               f"[2:v]format=rgba,fade=t=in:st={e0}:d=0.6:alpha=1[e];[v2][e]overlay=0:0:enable='gte(t,{e0})'[v3];"
               f"[v3]fade=t=in:st=0:d=0.3[v];[1:a]afade=t=out:st={end - 1.2}:d=1.2[a]")
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-loop", "1", "-framerate", "24", "-t", str(end), "-i", bg2,
                        "-t", str(end), "-i", mp3, "-loop", "1", "-framerate", "24", "-t", str(end), "-i", endp,
                        "-filter_complex", fc2, "-map", "[v]", "-map", "[a]", "-c:v", "libx264", "-preset", "veryfast",
                        "-crf", "22", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k", "-t", str(end),
                        "-movflags", "+faststart", sh], check=True)

    # ---- YouTube metadata
    folio = ep["title"].split(":")[0]
    desc = (f"{ep['description']}\n\n"
            + "\n".join(f"{mmss(a)} {name}" for a, name in chaps)
            + f"\n\nSource: {ep['source']}.\nRetold in English from the Persian original by Mehdi Rahmani and narrated "
              "with an AI rendering of his own voice.\n\nListen on Spotify, Apple Podcasts and every podcast app: "
              "https://mehdimrahmani.github.io/kalila-videos/podcast/\n\n#History #PersianHistory #Podcast "
              "#Beyhaqi #MedievalHistory #Storytelling")
    meta = {"title": f"{ep['title']} | The Honest Historian – Stories from Beyhaqi"[:100], "description": desc,
            "tags": ["Beyhaqi", "History of Beyhaqi", "Tarikh-e Beyhaqi", "Persian history", "Ghaznavid", "Sultan Masud",
                     "Iran history", "history podcast", "medieval history", "storytelling", "تاریخ بیهقی"],
            "categoryId": "27", "privacy": "public", "madeForKids": False, "synthetic": True, "language": "en"}
    json.dump(meta, open(os.path.join(OUT, f"ep{n:02d}.youtube.json"), "w"), ensure_ascii=False, indent=1)
    if cold:
        suffix = f"… | {folio} — The Honest Historian #Shorts"
        hook = ep.get("cold_open", "").split(".")[0].rstrip(",;: ")
        room = min(70, 100 - len(suffix))
        if len(hook) > room:  # cut on a word boundary so the suffix (and #Shorts) always fits
            hook = hook[:room].rsplit(" ", 1)[0].rstrip(",;: ")
        ms = dict(meta, title=f"{hook}{suffix}",
                  description=f"{ep['cold_open']}\n\nThe full story: {ep['title']} — on our channel and on every podcast app.\n"
                              "https://mehdimrahmani.github.io/kalila-videos/podcast/\n\nNarrated with an AI rendering of "
                              "Mehdi Rahmani's voice.\n\n#History #PersianHistory #Beyhaqi #Shorts")
        json.dump(ms, open(os.path.join(OUT, f"ep{n:02d}_short.youtube.json"), "w"), ensure_ascii=False, indent=1)
    print(out, round(real, 1), "s;", len(chaps), "chapters")

if __name__ == "__main__":
    build(int(sys.argv[1]))
