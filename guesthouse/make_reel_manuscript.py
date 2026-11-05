#!/usr/bin/env python3
"""The Guest House — "illuminated manuscript" Reel with narration + tafsir (1080x1920, CPU only).
Approved by Mehdi on 4 Nov 2026 as the page's signature style.

Look: aged paper, lapis + gold illuminated border, a gold shamsa (sun medallion) that slowly turns and gleams
(and glows during the tafsir), the Persian verse written in Nastaliq ink right-to-left with the English under it,
candle-light breathing, dust in the light, slow camera push-in.
Sound: the warm deep narrator + Shur-mode music from make_reel_cinematic.py (unchanged).
Beats: hook -> verse lines -> tafsir (the narrator explains the meaning) -> outro (next part / follow).

usage: python3 guesthouse/make_reel_manuscript.py spec.json out.mp4
spec: {"header": "Shams & Rumi · Part 1", "source": "Divan-e Shams · Ghazal 1393", "seed": 1,
       "hook": "one sentence that makes a stranger stay",
       "segments": [{"fa": "one hemistich exactly as in the source", "en": "its translation", "say": optional narration}],
       "tafsir": ["short sentences the narrator says, one per screen"],
       "outro": {"say": "Part two. Who was Shams of Tabriz? Follow The Guest House.", "title": "Part 2 · Who was Shams of Tabriz?"}}
Needs the Kokoro model in pipeline/tts/ or guesthouse/tts/ (see make_reel_cinematic.py); renders ~6 min per minute.
"""
import sys, os, json, math, subprocess, tempfile, wave
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from scipy.ndimage import gaussian_filter, zoom as nd_zoom

GH = os.path.dirname(os.path.abspath(__file__))
NASTA = os.path.join(GH, "fonts", "NotoNastaliqUrdu-Regular.woff2")
SERIF_I = "/usr/share/fonts/truetype/freefont/FreeSerifItalic.ttf"
SERIF = "/usr/share/fonts/truetype/freefont/FreeSerif.ttf"
W, H, FPS = 1080, 1920, 24
M = 1.08                      # oversize canvas for the camera push-in
CW, CH = int(W * M), int(H * M)
INK = (38, 22, 14); SEPIA = (92, 60, 34)
GOLD = np.array([212, 170, 92]); GOLD_HI = np.array([255, 232, 170])
LAPIS = (26, 48, 104)

def noise(h, w, rng, scale, sigma):
    n = rng.standard_normal((max(2, h // scale), max(2, w // scale)))
    n = nd_zoom(n, (h / n.shape[0], w / n.shape[1]), order=3)[:h, :w]
    return gaussian_filter(n, sigma)

def paper(rng):
    h, w = CH, CW
    base = np.array([236, 219, 184], np.float32)
    blot = noise(h, w, rng, 90, 20); blot /= np.abs(blot).max() + 1e-9
    mid = noise(h, w, rng, 18, 3); mid /= np.abs(mid).max() + 1e-9
    fib = gaussian_filter(rng.standard_normal((h, w)), (0.6, 2.5)); fib /= np.abs(fib).max() + 1e-9
    a = base[None, None] * (1 + 0.06 * blot[..., None] + 0.025 * mid[..., None] + 0.03 * fib[..., None])
    # foxing stains
    for _ in range(14):
        cx, cy, r = rng.uniform(0, w), rng.uniform(0, h), rng.uniform(20, 120)
        yy, xx = np.ogrid[:h, :w]
        d = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2) / r
        a *= 1 - (0.10 * np.exp(-d ** 2))[..., None] * np.array([0.6, 0.8, 1.0])
    # darker, burnt edges
    y = np.linspace(-1, 1, h)[:, None]; x = np.linspace(-1, 1, w)[None, :]
    e = np.clip(np.maximum(np.abs(x) ** 6, np.abs(y) ** 8) + 0.25 * blot * 0.2, 0, 1)
    a *= 1 - (0.45 * e)[..., None] * np.array([0.8, 1.0, 1.25])
    return np.clip(a, 0, 255)

def gold_paint(mask, shade=None):
    """mask (h,w) 0..1 -> RGBA gold with a little relief"""
    m = mask.astype(np.float32)
    gy, gx = np.gradient(gaussian_filter(m, 1.5))
    rel = np.clip(0.5 + (-gx - gy) * 6, 0, 1)[..., None]
    col = GOLD * (0.75 + 0.5 * rel)
    return col, m

def border_layers(rng):
    """returns (gold_mask, lapis_mask, dots_mask) at canvas size"""
    g = Image.new('L', (CW, CH), 0); l = Image.new('L', (CW, CH), 0)
    dg, dl = ImageDraw.Draw(g), ImageDraw.Draw(l)
    ox, oy = int((CW - W) / 2) + 46, int((CH - H) / 2) + 46
    x0, y0, x1, y1 = ox, oy, CW - ox, CH - oy
    dg.rectangle([x0, y0, x1, y1], outline=255, width=5)
    dl.rectangle([x0 + 12, y0 + 12, x1 - 12, y1 - 12], outline=255, width=30)
    dg.rectangle([x0 + 12, y0 + 12, x1 - 12, y1 - 12], outline=255, width=3)
    dg.rectangle([x0 + 42, y0 + 42, x1 - 42, y1 - 42], outline=255, width=3)
    dg.rectangle([x0 + 52, y0 + 52, x1 - 52, y1 - 52], outline=255, width=1)
    # gold rosettes along the lapis band
    def ros(cx, cy, r):
        for k in range(8):
            a = k * math.pi / 4
            dg.ellipse([cx + r * 0.55 * math.cos(a) - r * 0.32, cy + r * 0.55 * math.sin(a) - r * 0.32,
                        cx + r * 0.55 * math.cos(a) + r * 0.32, cy + r * 0.55 * math.sin(a) + r * 0.32], fill=255)
        dl.ellipse([cx - r * 0.25, cy - r * 0.25, cx + r * 0.25, cy + r * 0.25], fill=255)
    step = 54
    for x in range(x0 + 27 + step, x1 - 27, step):
        ros(x, y0 + 27, 11); ros(x, y1 - 27, 11)
    for y in range(y0 + 27 + step, y1 - 27, step):
        ros(x0 + 27, y, 11); ros(x1 - 27, y, 11)
    for cx, cy in [(x0 + 27, y0 + 27), (x1 - 27, y0 + 27), (x0 + 27, y1 - 27), (x1 - 27, y1 - 27)]:
        dg.ellipse([cx - 26, cy - 26, cx + 26, cy + 26], fill=255); dl.ellipse([cx - 14, cy - 14, cx + 14, cy + 14], fill=255)
    return (np.asarray(g, np.float32) / 255, np.asarray(l, np.float32) / 255)

def shamsa(size, rot):
    """gold sun medallion with lapis centre; rot in radians"""
    ss = 2; S = size * ss; c = S / 2
    g = Image.new('L', (S, S), 0); l = Image.new('L', (S, S), 0)
    dg, dl = ImageDraw.Draw(g), ImageDraw.Draw(l)
    n = 32
    pts = []
    for k in range(n * 2):
        a = rot + k * math.pi / n
        r = c * (0.98 if k % 2 == 0 else 0.70)
        pts.append((c + r * math.cos(a), c + r * math.sin(a)))
    dg.polygon(pts, fill=255)
    pts2 = []
    for k in range(32):
        a = -rot * 1.5 + k * math.pi / 16
        r = c * (0.66 if k % 2 == 0 else 0.56)
        pts2.append((c + r * math.cos(a), c + r * math.sin(a)))
    dl.polygon(pts2, fill=255)
    dl.ellipse([c - c * 0.47, c - c * 0.47, c + c * 0.47, c + c * 0.47], fill=255)
    d2 = Image.new('L', (S, S), 0); dd = ImageDraw.Draw(d2)
    dd.ellipse([c - c * 0.47, c - c * 0.47, c + c * 0.47, c + c * 0.47], outline=255, width=int(c * 0.03))
    dg = dd
    for k in range(12):
        a = rot * 2 + k * math.pi / 6
        dg.ellipse([c + c * 0.27 * math.cos(a) - c * 0.07, c + c * 0.27 * math.sin(a) - c * 0.07,
                    c + c * 0.27 * math.cos(a) + c * 0.07, c + c * 0.27 * math.sin(a) + c * 0.07], fill=255)
    dg.ellipse([c - c * 0.1, c - c * 0.1, c + c * 0.1, c + c * 0.1], fill=255)
    r = lambda im: np.asarray(im.resize((size, size), Image.LANCZOS), np.float32) / 255
    return r(g), r(l), r(d2)

def text_mask(txt, font_path, size, rtl=False, maxw=900):
    f = ImageFont.truetype(font_path, size)
    kw = dict(direction='rtl', language='fa') if rtl else {}
    while True:
        bb = f.getbbox(txt, **kw)
        if bb[2] - bb[0] <= maxw or size < 30: break
        size -= 4; f = ImageFont.truetype(font_path, size)
    w, h = bb[2] - bb[0] + 40, bb[3] - bb[1] + 60
    im = Image.new('L', (w, h), 0)
    ImageDraw.Draw(im).text((20 - bb[0], 30 - bb[1]), txt, font=f, fill=255, **kw)
    return np.asarray(im, np.float32) / 255

def wrap(txt, font_path, size, maxw):
    f = ImageFont.truetype(font_path, size); words = txt.split(); lines = []; cur = ""
    for wd in words:
        t = (cur + " " + wd).strip()
        if f.getlength(t) > maxw and cur: lines.append(cur); cur = wd
        else: cur = t
    lines.append(cur); return lines

def paste(canvas, col, mask, x, y, alpha=1.0):
    h, w = mask.shape
    x, y = int(x), int(y)
    sub = canvas[y:y + h, x:x + w]
    m = (mask[:sub.shape[0], :sub.shape[1]] * alpha)[..., None]
    c = col if np.ndim(col) == 1 else col[:sub.shape[0], :sub.shape[1]]
    canvas[y:y + h, x:x + w] = sub * (1 - m) + np.asarray(c, np.float32) * m

def ss(t, a, b):
    x = np.clip((t - a) / (b - a), 0, 1); return x * x * (3 - 2 * x)

sys.path.insert(0, GH)
import make_reel_cinematic as MC
SR = MC.SR

def say(text):
    a = MC.narrate(text)
    if a is None: raise SystemExit("TTS not available")
    return a

def build(spec, out):
    rng = np.random.default_rng(spec.get("seed", 1))
    # ---------------- narration timeline
    beats = []          # dict(kind, t0, t1, ...)
    voice = []; t = 1.0
    def add(kind, text, gap=0.5, lead=0.0, **kw):
        nonlocal t
        a = say(text); t += lead
        beats.append(dict(kind=kind, t0=t, t1=t + len(a) / SR, text=text, audio=a, **kw))
        t += len(a) / SR + gap
    add("hook", spec["hook"], gap=0.6)
    for s in spec["segments"]:
        add("verse", s.get("say", s["en"]), gap=0.9, lead=0.6, fa=s["fa"], en=s["en"])
    for i, sent in enumerate(spec["tafsir"]):
        add("tafsir", sent, gap=0.35, lead=0.5 if i == 0 else 0.0)
    add("outro", spec["outro"]["say"], gap=0.4, lead=0.5, title=spec["outro"]["title"])
    DUR = t + 1.2
    N = int(DUR * SR)
    vt = np.zeros(N)
    for b in beats:
        i = int(b["t0"] * SR); vt[i:i + len(b["audio"])] += b["audio"][:N - i]
    mix = MC.music(DUR, spec.get("seed", 1), vt)
    wav = tempfile.mktemp(suffix=".wav")
    with wave.open(wav, "wb") as wf:
        wf.setnchannels(1); wf.setsampwidth(2); wf.setframerate(SR)
        wf.writeframes((np.clip(mix, -1, 1) * 32767).astype(np.int16).tobytes())
    # group consecutive verse / tafsir beats into on-screen blocks
    verse_beats = [b for b in beats if b["kind"] == "verse"]
    for k, b in enumerate(verse_beats):
        nxt = verse_beats[k + 1]["t0"] if k + 1 < len(verse_beats) else None
        b["show_end"] = (nxt - 0.15) if nxt else b["t1"] + 0.8
    taf = [b for b in beats if b["kind"] == "tafsir"]
    taf_t0, taf_t1 = taf[0]["t0"] - 0.5, taf[-1]["t1"] + 0.3
    hook = beats[0]; outro = beats[-1]
    # ---------------- static page
    base = paper(rng)
    bg, bl = border_layers(rng)
    gcol, _ = gold_paint(bg)
    paste(base, LAPIS, bl, 0, 0, 0.92)
    base = base * (1 - bg[..., None]) + gcol * bg[..., None]
    jad = Image.new('L', (CW, CH), 0); dj = ImageDraw.Draw(jad)
    jx0, jy0, jx1, jy1 = int(CW * 0.12), int(CH * 0.47), int(CW * 0.88), int(CH * 0.80)
    dj.rectangle([jx0, jy0, jx1, jy1], outline=255, width=2); dj.rectangle([jx0 + 8, jy0 + 8, jx1 - 8, jy1 - 8], outline=255, width=1)
    jm = np.asarray(jad, np.float32) / 255
    base = base * (1 - 0.8 * jm[..., None]) + GOLD * 0.8 * jm[..., None]
    hdr = text_mask(spec.get("header", "").upper(), SERIF, 34)
    paste(base, np.array(LAPIS, np.float32), hdr, (CW - hdr.shape[1]) / 2, CH * 0.405, 0.95)
    hand = text_mask("@theguesthouse.poetry", SERIF, 30)
    paste(base, SEPIA, hand, (CW - hand.shape[1]) / 2, CH * 0.875, 0.8)
    src = text_mask(spec.get("source", ""), SERIF_I, 36)
    # ---------------- text masks
    MAXW = int(CW * 0.64)
    def block(txt, font, size, maxw=MAXW):
        return [text_mask(l, font, size) for l in wrap(txt, font, size, maxw)]
    hook_m = block(spec["hook"], SERIF_I, 56)
    for b in verse_beats:
        b["fa_m"] = text_mask(b["fa"], NASTA, 120, rtl=True, maxw=int(CW * 0.66))
        b["en_m"] = block(b["en"], SERIF_I, 50, int(CW * 0.62))
    taf_label = text_mask("TAFSIR", SERIF, 34)
    taf_label_fa = text_mask("تفسیر", NASTA, 64, rtl=True)
    for b in taf: b["m"] = block(b["text"], SERIF_I, 50)
    out_m = block(outro["title"], SERIF_I, 58)
    follow = text_mask("Follow @theguesthouse.poetry", SERIF, 40)
    # ---------------- light & dust
    nd = 90
    dpos = np.stack([rng.uniform(0, CW, nd), rng.uniform(0, CH, nd)], 1)
    dvel = np.stack([rng.uniform(-6, 6, nd), rng.uniform(-14, -3, nd)], 1)
    dsz = rng.uniform(1.2, 3.2, nd)
    yy, xx = np.mgrid[:CH, :CW]
    d_light = np.sqrt(((xx - CW * 0.5) / (CW * 0.75)) ** 2 + ((yy - CH * 0.36) / (CH * 0.55)) ** 2)
    pool = np.exp(-d_light ** 2 * 1.6).astype(np.float32)
    SH = 430; gy, gx = np.mgrid[:SH, :SH]
    def lines(fr, ms, ycenter, col, alpha, gap=-14):
        tot = sum(m.shape[0] + gap for m in ms) - gap; y = ycenter - tot / 2
        for m in ms:
            paste(fr, col, m, (CW - m.shape[1]) / 2, y, alpha); y += m.shape[0] + gap
    YC = (jy0 + jy1) / 2
    enc = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                            "-r", str(FPS), "-i", "-", "-i", wav, "-c:v", "libx264", "-crf", "19", "-pix_fmt", "yuv420p",
                            "-c:a", "aac", "-b:a", "160k", "-shortest", out], stdin=subprocess.PIPE)
    NF = int(DUR * FPS)
    for i in range(NF):
        t = i / FPS
        fr = base.copy()
        # shamsa (glows brighter while the narrator explains)
        sg, sl, sd = shamsa(SH, t * 0.06)
        cx, cy = (CW - SH) / 2, CH * 0.13
        sweep = np.exp(-((gx + gy) / SH - ((t * 0.22) % 2.4 - 0.2) * 1.4) ** 2 / 0.01)[..., None]
        glow = ss(t, taf_t0, taf_t0 + 1) * (1 - ss(t, taf_t1, taf_t1 + 1))
        col = GOLD * (0.85 + 0.3 * (1 - gy / SH))[..., None] * (1 + 0.12 * glow) + (GOLD_HI - GOLD) * sweep * 0.9
        paste(fr, col, sg, cx, cy, 1.0)
        paste(fr, LAPIS, np.clip(sl - sd, 0, 1), cx, cy, 0.95)
        paste(fr, col, sd, cx, cy, 1.0)
        # hook
        v0 = verse_beats[0]["t0"]
        a = ss(t, hook["t0"] - 0.3, hook["t0"] + 0.4) * (1 - ss(t, v0 - 0.45, v0 - 0.1))
        if a > 0: lines(fr, hook_m, YC, SEPIA, a)
        # verses
        for b in verse_beats:
            if not (b["t0"] - 0.2 < t < b["show_end"] + 0.5): continue
            vis = ss(t, b["t0"] - 0.2, b["t0"]) * (1 - ss(t, b["show_end"], b["show_end"] + 0.45))
            prog = ss(t, b["t0"] - 0.1, b["t0"] + min(2.4, b["t1"] - b["t0"] + 0.6))
            m = b["fa_m"]; h, w = m.shape
            xr = np.linspace(0, 1, w)[None, :]
            rev = np.clip((prog * 1.15 - (1 - xr)) / 0.15, 0, 1)
            mm = m * rev * vis
            tot = h + 10 + sum(e.shape[0] - 14 for e in b["en_m"])
            y0 = YC - tot / 2
            paste(fr, INK, np.clip(mm + gaussian_filter(mm, 1.2) * 0.35, 0, 1), (CW - w) / 2, y0)
            ea = ss(t, b["t0"] + 0.6, b["t0"] + 1.4) * vis
            yl = y0 + h + 10
            for e in b["en_m"]:
                paste(fr, SEPIA, e, (CW - e.shape[1]) / 2, yl, ea); yl += e.shape[0] - 14
        # tafsir
        la = ss(t, taf_t0, taf_t0 + 0.6) * (1 - ss(t, taf_t1, taf_t1 + 0.5))
        if la > 0:
            paste(fr, GOLD * 0.8, taf_label_fa, (CW - taf_label_fa.shape[1]) / 2, jy0 + 30, la)
            for k, b in enumerate(taf):
                e1 = taf[k + 1]["t0"] - 0.05 if k + 1 < len(taf) else taf_t1
                a = ss(t, b["t0"] - 0.25, b["t0"] + 0.15) * (1 - ss(t, e1 - 0.2, e1 + 0.1))
                if a > 0: lines(fr, b["m"], YC + 30, SEPIA, a)
        # outro
        a = ss(t, outro["t0"] - 0.3, outro["t0"] + 0.4)
        if a > 0:
            lines(fr, out_m, YC - 30, INK, a)
            paste(fr, np.array(LAPIS, np.float32), follow, (CW - follow.shape[1]) / 2, YC + 90, a)
        # source line appears with the verses and stays
        a = ss(t, verse_beats[0]["t0"], verse_beats[0]["t0"] + 1)
        paste(fr, SEPIA, src, (CW - src.shape[1]) / 2, CH * 0.815, 0.9 * a)
        # light + dust
        flick = 0.9 + 0.06 * math.sin(t * 2.1) + 0.03 * math.sin(t * 5.3 + 1)
        fr = fr * (0.70 + 0.34 * pool[..., None] * flick) * np.array([1.03, 0.98, 0.88])
        p = (dpos + dvel * t) % [CW, CH]
        for (px, py), s in zip(p, dsz):
            r = int(s * 3); x0, y0 = int(px) - r, int(py) - r
            if x0 < 0 or y0 < 0 or x0 + 2 * r >= CW or y0 + 2 * r >= CH: continue
            g = np.exp(-((np.arange(2 * r)[:, None] - r) ** 2 + (np.arange(2 * r)[None, :] - r) ** 2) / (s * s))
            fr[y0:y0 + 2 * r, x0:x0 + 2 * r] += (g * 70 * pool[int(py), int(px)])[..., None] * np.array([1, 0.9, 0.7])
        z = 1 + (M - 1) * (1 - ss(t, 0, DUR))
        cw, chh = int(W * z), int(H * z); ox, oy = (CW - cw) // 2, (CH - chh) // 2
        img = Image.fromarray(np.clip(fr[oy:oy + chh, ox:ox + cw], 0, 255).astype(np.uint8)).resize((W, H), Image.BICUBIC)
        a = ss(t, 0, 0.6) * (1 - ss(t, DUR - 0.8, DUR))
        if a < 1: img = Image.blend(Image.new('RGB', (W, H)), img, a)
        enc.stdin.write(img.tobytes())
    enc.stdin.close(); enc.wait(); os.remove(wav)
    return DUR

if __name__ == "__main__":
    print(build(json.load(open(sys.argv[1], encoding="utf-8")), sys.argv[2]))
