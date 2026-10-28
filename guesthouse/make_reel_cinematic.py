#!/usr/bin/env python3
"""The Guest House — cinematic Reel (1080x1920): cosmic scenes, whirling dervish, Persian verse in
Nastaliq revealed word by word, English line under it, deep male narration over soft music.

usage: python3 make_reel_cinematic.py spec.json out.mp4
spec: {"header": "Shams & Rumi · Part 1", "title": "Before the Fire",
       "segments": [{"fa": "مرده بدم زنده شدم", "en": "I was dead, I came alive."}, ...],
       "source": "Divan-e Shams · Ghazal 1393", "seed": 1}
If "segments" is missing it is built from "fa"/"en" lists (Persian lines split at "،").
Everything is generated locally (numpy/Pillow/Kokoro) — no network needed except for the TTS model files.
"""
import sys, os, json, math, wave, subprocess, tempfile
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from scipy.ndimage import gaussian_filter, zoom as nd_zoom

HERE = os.path.dirname(os.path.abspath(__file__))
NASTA = os.path.join(HERE, "fonts", "NotoNastaliqUrdu-Regular.woff2")
FA_FONT = os.path.join(HERE, "fonts", "Vazirmatn-Regular.ttf")
SERIF_I = "/usr/share/fonts/truetype/freefont/FreeSerifItalic.ttf"
SERIF = "/usr/share/fonts/truetype/freefont/FreeSerif.ttf"
if not os.path.exists(SERIF_I):
    SERIF_I = SERIF = "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf"
W, H, FPS, SR = 1080, 1920, 24, 44100
GOLD = (214, 178, 106)

PALETTES = [  # (deep, mid, bright) nebula colours
    ((18, 8, 46), (88, 40, 150), (150, 120, 255)),     # violet
    ((4, 10, 30), (20, 70, 160), (120, 200, 255)),     # cosmic blue
    ((20, 8, 2), (150, 70, 20), (255, 200, 120)),      # golden fire
    ((6, 14, 24), (30, 90, 110), (160, 230, 220)),     # teal
]

# ---------------------------------------------------------------- visuals
def fbm(h, w, rng, octaves=6):
    out = np.zeros((h, w))
    for o in range(octaves):
        s = 2 ** o
        n = rng.standard_normal((max(2, h // (64 // min(s, 32))), max(2, w // (64 // min(s, 32)))))
        n = nd_zoom(n, (h / n.shape[0], w / n.shape[1]), order=3)[:h, :w]
        out += gaussian_filter(n, 2) / s
    out -= out.min(); return out / (out.max() + 1e-9)

def nebula(rng, pal, h=1280, w=720):
    a, b, c = fbm(h, w, rng), fbm(h, w, rng), fbm(h, w, rng)
    dens = np.clip((a * 0.6 + b * 0.4 - 0.35) * 2.2, 0, 1) ** 1.6
    core = np.clip((c - 0.55) * 3, 0, 1) ** 2 * dens
    deep, mid, br = (np.array(p, float) for p in pal)
    img = deep[None, None] * (1 - dens[..., None]) + mid[None, None] * dens[..., None]
    img += (br - mid)[None, None] * core[..., None]
    img *= (0.35 + 0.65 * fbm(h, w, rng, 4))[..., None]
    return np.clip(img, 0, 255)

def stars(rng, h, w, n=900):
    s = np.zeros((h, w))
    ys, xs = rng.integers(0, h, n), rng.integers(0, w, n)
    s[ys, xs] = rng.random(n) ** 3 * 255
    glow = gaussian_filter(s, 1.2) * 4 + gaussian_filter(s, 4) * 6
    return np.clip(s + glow, 0, 255)

def _limb(pts, widths):
    """Tapered limb polygon along a polyline."""
    pts = np.array(pts, float); left, right = [], []
    for i, (p, w) in enumerate(zip(pts, widths)):
        a = pts[min(i + 1, len(pts) - 1)] - pts[max(i - 1, 0)]
        nrm = np.array([-a[1], a[0]]) / (np.hypot(*a) + 1e-9)
        left.append(tuple(p + nrm * w / 2)); right.append(tuple(p - nrm * w / 2))
    return left + right[::-1]

def _bez(p0, p1, p2, n=12):
    return [((1 - u) ** 2 * p0[0] + 2 * (1 - u) * u * p1[0] + u * u * p2[0],
             (1 - u) ** 2 * p0[1] + 2 * (1 - u) * u * p1[1] + u * u * p2[1]) for u in np.linspace(0, 1, n)]

def dervish_mask(t, h=1280, w=720, cx=360, top=150, scale=1.0, ss=3):
    """Soft silhouette (mask, folds) of a whirling dervish: head tilted, right palm up, left palm down,
    tilted flaring skirt whose hem ripples as it spins."""
    S = ss; k = scale * S
    P = lambda x, y: (cx * S + x * k, top * S + y * k)
    m = Image.new("L", (w * S, h * S), 0); d = ImageDraw.Draw(m)
    folds = Image.new("L", (w * S, h * S), 0); fd = ImageDraw.Draw(folds)
    sw = 4 * math.sin(t * 1.1)
    # hat (sikke): tall tapered felt, tilted with the head
    hat = Image.new("L", (w * S, h * S), 0)
    ImageDraw.Draw(hat).polygon([P(2, 0), P(20, 3), P(28, 66), P(2, 68)], fill=255)
    d.polygon([P(2, 0), P(20, 3), P(28, 66), P(2, 68)], fill=255)
    d.ellipse([*P(-12, 54), *P(42, 116)], fill=255)                        # head, tilted right
    d.polygon([P(4, 108), P(26, 108), P(26, 130), P(4, 130)], fill=255)     # neck
    # torso: shoulders -> narrow waist (tennure top + jacket)
    d.polygon(_bez(P(-42, 140), P(-34, 200), P(-24, 262)) + _bez(P(24, 262), P(34, 200), P(46, 138)) +
              [P(16, 124), P(-12, 124)], fill=255)
    # right arm raised, palm up; left arm out and down, palm down
    d.polygon(_limb([P(36, 146), P(92, 92 + sw), P(140, 30 + sw), P(168, 2 + sw)], [30 * k, 26 * k, 20 * k, 14 * k]), fill=255)
    d.polygon(_limb([P(-36, 150), P(-104, 200 - sw), P(-170, 246 - sw), P(-206, 262 - sw)], [30 * k, 26 * k, 20 * k, 13 * k]), fill=255)
    d.ellipse([*P(158, -14 + sw), *P(186, 10 + sw)], fill=255)
    d.ellipse([*P(-222, 252 - sw), *P(-196, 274 - sw)], fill=255)
    # skirt: bell from the waist, tilted hem (spinning lifts one side), rippling
    N = 80; hem = []
    for i in range(N + 1):
        u = -1 + 2 * i / N
        taper = (1 - u * u) ** 0.5
        r = 270 * u + 12 * math.sin(u * 11 + t * 6.5) * taper
        y = 560 - 60 * u + (24 * math.sin(u * 8.5 - t * 5.0) + 9 * math.sin(u * 21 + t * 9)) * taper + 30 * taper
        hem.append(P(r, y))
    leftside = _bez(P(-26, 258), P(-150, 420), hem[0])
    rightside = _bez(hem[-1], P(170, 380), P(26, 258))
    d.polygon(leftside + hem + rightside, fill=255)
    # fold lines radiating from the waist
    for j in range(1, 14):
        i = int(j * N / 14); hx, hy = hem[i]
        fd.line([P(0, 262), ((hx + P(0, 262)[0]) / 2, (hy + P(0, 262)[1]) / 2 + 20 * k), (hx, hy)], fill=255, width=int(2.2 * k))
    m = m.resize((w, h), Image.LANCZOS).filter(ImageFilter.GaussianBlur(0.8))
    folds = folds.resize((w, h), Image.LANCZOS).filter(ImageFilter.GaussianBlur(1.5))
    hat = hat.resize((w, h), Image.LANCZOS).filter(ImageFilter.GaussianBlur(0.8))
    return np.asarray(m, float) / 255, np.asarray(folds, float) / 255, np.asarray(hat, float) / 255

class Scene:
    """One background: nebula + stars + optional dervish/warp, rendered at 720x1280 then upscaled."""
    def __init__(self, rng, kind, pal):
        self.kind = kind
        self.neb = nebula(rng, pal)
        self.neb2 = nebula(rng, PALETTES[(PALETTES.index(pal) + 1) % len(PALETTES)])
        self.st = stars(rng, 1600, 900)
        self.pal = np.array(pal[2], float)
        self.rng = rng
        if kind == "warp":
            n = 500; self.wa = rng.random(n) * 2 * np.pi; self.wr = rng.random(n) ** 0.5; self.wv = 0.3 + rng.random(n)

    def frame(self, t, dur):
        h, w = 1280, 720
        z = 1.0 + 0.08 * (t / dur)
        img = crop_zoom(self.neb, z + 0.06, 0, t * 0.05)
        sx = int(90 + 60 * t / dur); sy = int(160 + 100 * t / dur)
        st = self.st[sy:sy + h, sx:sx + w] * (0.85 + 0.15 * math.sin(t * 2))
        img = img + st[..., None] * 0.9
        if self.kind == "dervish":
            m, fo, hat = dervish_mask(t, top=120, scale=1.05)
            if not hasattr(self, "diss"):
                self.diss = fbm(h, w, self.rng, 5)
            yy = np.linspace(0, 1, h)[:, None]
            low = np.clip((yy - 0.42) / 0.22, 0, 1)                     # hem dissolves into stardust
            m = m * np.clip(1 - low * (1.4 - self.diss * 1.6), 0, 1) * 0.9
            inner = crop_zoom(self.neb2, 1.25, 0, t * 0.6) * 1.5 + np.array([70, 80, 100])
            inner *= (1.15 - 0.5 * yy)[..., None]                       # lit from above
            inner = inner * (1 - fo[..., None] * 0.4) * (1 - hat[..., None] * 0.55)   # folds, felt hat
            img = img * (1 - m[..., None]) + inner * m[..., None]
            rim = np.clip(gaussian_filter(m, 10) - m, 0, 1)
            img += rim[..., None] * np.array([150, 190, 255]) * 0.9
            xx = np.linspace(-1, 1, w)[None]
            beam = np.exp(-(xx / 0.3) ** 2) * np.clip(1 - yy * 1.4, 0, 1)
            img += beam[..., None] * np.array([255, 215, 140]) * 0.3
        elif self.kind == "warp":
            layer = Image.new("L", (w, h), 0); d = ImageDraw.Draw(layer)
            cx, cy = w * 0.5, h * 0.42
            for a, r0, v in zip(self.wa, self.wr, self.wv):
                r = (r0 + t * v * 0.25) % 1.2
                L = 0.02 + 0.12 * r
                x0, y0 = cx + math.cos(a) * r * 900, cy + math.sin(a) * r * 900
                x1, y1 = cx + math.cos(a) * (r + L) * 900, cy + math.sin(a) * (r + L) * 900
                d.line([(x0, y0), (x1, y1)], fill=int(255 * min(1, r * 2)), width=2)
            ln = np.asarray(layer, float)
            img += (ln + gaussian_filter(ln, 3) * 2)[..., None] * np.array([1.0, 0.85, 0.6])
            yy, xx = np.mgrid[0:h, 0:w]
            core = np.exp(-(((xx - cx) / 160) ** 2 + ((yy - cy) / 160) ** 2)) * (0.7 + 0.3 * math.sin(t * 1.7))
            img += core[..., None] * self.pal * 1.2
        elif self.kind == "sun":
            yy, xx = np.mgrid[0:h, 0:w]
            ang = (t / dur) * 0.6
            d = (xx - w * 0.8) * math.cos(1.1 + ang) + (yy - h * 0.15) * math.sin(1.1 + ang)
            img += np.exp(-np.abs(d) / 45)[..., None] * np.array([255, 200, 130]) * 0.55
            img += np.exp(-(((xx - w * 0.8) / 200) ** 2 + ((yy - h * 0.12) / 200) ** 2))[..., None] * np.array([255, 225, 180]) * 0.9
        return np.clip(img, 0, 255)

def crop_zoom(arr, z, rot=0, pan=0.0):
    h, w = arr.shape[:2]
    ch, cw = int(h / z), int(w / z)
    y0 = (h - ch) // 2; x0 = int((w - cw) / 2 + math.sin(pan) * (w - cw) / 2.2)
    sub = Image.fromarray(arr[y0:y0 + ch, x0:x0 + cw].astype(np.uint8))
    return np.asarray(sub.resize((w, h), Image.BILINEAR), float)

class Dust:
    def __init__(self, rng, n=140):
        self.p = rng.random((n, 2)); self.v = (rng.random((n, 2)) - 0.5) * 0.02 + [0, -0.012]; self.s = rng.random(n)
    def draw(self, t):
        layer = np.zeros((1280, 720))
        p = (self.p + self.v * t) % 1
        ys, xs = (p[:, 1] * 1279).astype(int), (p[:, 0] * 719).astype(int)
        layer[ys, xs] = 120 + 135 * self.s * (0.5 + 0.5 * np.sin(t * 3 + self.s * 9))
        return gaussian_filter(layer, 1.5) * 5

# ---------------------------------------------------------------- text
def text_img(txt, font, size, rtl=False):
    f = ImageFont.truetype(font, size)
    kw = dict(direction="rtl", language="fa") if rtl else {}
    l, t, r, b = f.getbbox(txt, **kw)
    pad = 40
    im = Image.new("L", (r - l + 2 * pad, b - t + 2 * pad), 0)
    ImageDraw.Draw(im).text((pad - l, pad - t), txt, font=f, fill=255, **kw)
    return im

def glow_rgba(mask, color=(255, 255, 255), glow=(255, 225, 170), gs=9, ga=0.7):
    m = np.asarray(mask, float) / 255
    g = gaussian_filter(m, gs) * ga * 2.2
    a = np.clip(m + g, 0, 1)
    col = (np.array(color, float)[None, None] * m[..., None] + np.array(glow, float)[None, None] * g[..., None]) / (m + g + 1e-6)[..., None]
    return np.dstack([col, a])

def fit_size(txt, font, size, maxw, rtl):
    while size > 30 and text_img(txt, font, size, rtl).width > maxw: size -= 4
    return size

def persian_progressive(line, size=96, maxw=980):
    """List of RGBA arrays: the line revealed word by word (right-anchored, same baseline)."""
    words = line.split()
    size = fit_size(line, NASTA, size, maxw, True)
    full = text_img(line, NASTA, size, True)
    outs = []
    for k in range(1, len(words) + 1):
        part = text_img(" ".join(words[:k]), NASTA, size, True)
        canvas = Image.new("L", full.size, 0)
        canvas.paste(part, (full.width - part.width, full.height - part.height - (full.height - part.height) // 2))
        outs.append(glow_rgba(canvas))
    return outs

def composite(base, rgba, cx, cy, alpha=1.0):
    h, w = rgba.shape[:2]; x0, y0 = int(cx - w / 2), int(cy - h / 2)
    xs0, ys0 = max(0, -x0), max(0, -y0); x0c, y0c = max(0, x0), max(0, y0)
    x1c, y1c = min(base.shape[1], x0 + w), min(base.shape[0], y0 + h)
    if x1c <= x0c or y1c <= y0c: return
    src = rgba[ys0:ys0 + (y1c - y0c), xs0:xs0 + (x1c - x0c)]
    a = src[..., 3:4] * alpha
    base[y0c:y1c, x0c:x1c] = base[y0c:y1c, x0c:x1c] * (1 - a) + src[..., :3] * a

# ---------------------------------------------------------------- audio
TTS_DIRS = [os.path.join(HERE, "..", "pipeline", "tts"), os.path.join(HERE, "tts"), "/home/claude/kalila_test/tts"]
_KOK = None
def narrate(text):
    """Deep, husky male English narration (Kokoro am_onyx) at 44.1 kHz, or None if TTS unavailable."""
    global _KOK
    try:
        from kokoro_onnx import Kokoro
    except ImportError:
        return None
    if _KOK is None:
        for d in TTS_DIRS:
            m, v = os.path.join(d, "kokoro-v1.0.onnx"), os.path.join(d, "voices-v1.0.bin")
            if os.path.exists(m) and os.path.exists(v): _KOK = Kokoro(m, v); break
        else:
            return None
    a, r = _KOK.create(text, voice="am_onyx", speed=0.8, lang="en-us")
    f = 0.9 * r / SR
    n = int(len(a) / f); a = np.interp(np.arange(n) * f, np.arange(len(a)), a)
    envl = np.convolve(np.abs(a), np.ones(400) / 400, "same")
    grit = np.convolve(np.random.default_rng(1).standard_normal(len(a)), np.ones(3) / 3, "same") * envl * 0.3
    y = np.tanh((a + grit) * 2.0) / np.tanh(2.0)
    y = np.convolve(y, [0.6, 0.3, 0.1], "same")
    # touch of room so it sits inside the music
    room = np.zeros(len(y) + int(0.4 * SR)); room[:len(y)] += y
    for dl, g in ((0.031, 0.18), (0.057, 0.12), (0.089, 0.08)):
        k = int(dl * SR); room[k:k + len(y)] += y * g
    return room / (np.abs(room).max() + 1e-9) * 0.9

def reverb(x, secs=3.2, wet=0.45, seed=3):
    rng = np.random.default_rng(seed)
    n = int(secs * SR); t = np.arange(n) / SR
    ir = rng.standard_normal(n) * np.exp(-t * 6.5 / secs)
    ir = gaussian_filter(ir, 1.5); ir /= np.sqrt((ir ** 2).sum())
    from scipy.signal import fftconvolve
    y = fftconvolve(x, ir)[:len(x)]
    return x * (1 - wet) + y * wet * 0.9

def music(dur, seed, voice_track):
    """Cinematic Shur-mode bed: warm string pad, sub drone, slow sama pulse (frame-drum heartbeat), sparse ney."""
    rng = np.random.default_rng(seed)
    N = int(dur * SR); t = np.arange(N) / SR
    D = 146.83                                     # D3
    semis = lambda s: D * 2 ** (s / 12)
    chords = [[0, 7, 12, 15], [-2, 5, 10, 14], [-4, 3, 8, 12], [0, 7, 12, 15.5]]   # Dm, C(sus), Bb, D(koron colour)
    pad = np.zeros(N); seg = dur / len(chords)
    for i, ch in enumerate(chords):
        a0, a1 = int(max(0, i * seg - 1.5) * SR), int(min(dur, (i + 1) * seg + 1.5) * SR)
        tt = np.arange(a1 - a0) / SR; L = (a1 - a0) / SR
        env = np.clip(tt / 1.6, 0, 1) * np.clip((L - tt) / 1.6, 0, 1)
        for s in ch:
            f = semis(s)
            for det in (-0.07, 0.0, 0.08):
                ph = 2 * np.pi * f * 2 ** (det / 12) * tt + rng.random() * 6
                pad[a0:a1] += (np.sin(ph) + 0.35 * np.sin(2 * ph) + 0.15 * np.sin(3 * ph)) * env * 0.05
    pad = gaussian_filter(pad, 3)
    pad *= 0.8 + 0.2 * np.sin(2 * np.pi * 0.15 * t)
    sub = 0.16 * np.sin(2 * np.pi * D / 2 * t) * np.clip(t / 3, 0, 1)
    # sama pulse ~73 bpm: DUM . . dum-DUM .  (soft, low, no jingles)
    beat = 60 / 73; pulse = np.zeros(N)
    pattern = [(0, 1.0), (1.5, 0.45), (2.0, 0.8)]
    k = 0; start = 2.0
    while start + k * 3 * beat / 2 < dur - 1:
        b0 = start + k * 3 * beat / 2
        for off, g in pattern:
            n0 = int((b0 + off * beat / 2) * SR)
            if n0 >= N: continue
            L = min(N - n0, int(0.9 * SR)); tt = np.arange(L) / SR
            f = 55 + 35 * np.exp(-tt * 25)
            hit = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-tt * 5)
            hit += gaussian_filter(rng.standard_normal(L), 6) * np.exp(-tt * 30) * 0.25
            ramp = min(1, (b0 - start) / 6 + 0.35)
            pulse[n0:n0 + L] += hit * g * 0.5 * ramp
        k += 1
    pulse *= np.clip((dur - t) / 2, 0, 1)
    # sparse ney phrases in Shur
    ney = np.zeros(N); deg = [0, 1.5, 3, 5, 7, 8, 10, 12]
    pos = 1.0
    while pos < dur - 3:
        for n in rng.choice([[7, 5, 3, 1.5, 0], [0, 1.5, 3, 1.5, 0], [12, 10, 8, 7], [3, 5, 7, 5, 3]]):
            dn = rng.choice([0.5, 0.7, 0.9]); f = D * 2 * 2 ** (n / 12)
            n0, n1 = int(pos * SR), min(N, int((pos + dn + 0.2) * SR)); tt = np.arange(n1 - n0) / SR
            vib = 1 + 0.006 * np.sin(2 * np.pi * 5 * tt) * np.minimum(1, tt / 0.3)
            ph = 2 * np.pi * f * np.cumsum(vib) / SR
            env = np.minimum(1, tt / 0.15) * np.clip((dn + 0.2 - tt) / 0.3, 0, 1)
            br = gaussian_filter(rng.standard_normal(len(tt)), 2) * 0.3
            ney[n0:n1] += (np.sin(ph) + 0.2 * np.sin(2 * ph) + br) * env * 0.12
            pos += dn
        pos += rng.choice([2.5, 3.5, 4.5])
    mix = reverb(pad + ney, 3.5, 0.55) + sub + reverb(pulse, 1.6, 0.3, 5)
    mix *= np.clip(t / 1.5, 0, 1) * np.clip((dur - t) / 2.5, 0, 1)
    mix = mix / (np.abs(mix).max() + 1e-9) * 0.8
    if voice_track is not None:
        act = gaussian_filter(np.abs(voice_track), 0.25 * SR)
        act = np.clip(act / (act.max() * 0.15 + 1e-9), 0, 1)
        act = gaussian_filter(act, 0.15 * SR)
        mix = mix * (1 - 0.68 * act) * 0.85 + voice_track * 1.0
    pk = np.abs(mix).max()
    return mix * (0.95 / pk) if pk > 0.95 else mix

# ---------------------------------------------------------------- build
def segments_of(spec):
    if spec.get("segments"): return spec["segments"]
    fa = []
    for line in spec.get("fa", []):
        fa += [p.strip() for p in line.replace("،", "|").split("|") if p.strip()]
    en = spec.get("en", [])
    n = max(len(fa), 1); segs = []
    for i in range(n):
        lo, hi = round(i * len(en) / n), round((i + 1) * len(en) / n)
        segs.append({"fa": fa[i] if i < len(fa) else "", "en": " ".join(en[lo:hi])})
    return segs

def build(spec, out):
    rng = np.random.default_rng(spec.get("seed", 1))
    segs = segments_of(spec)
    # --- timeline
    INTRO, GAP, OUTRO = 2.6, 0.5, 3.2
    t = INTRO; tl = []
    voices = []
    for s in segs:
        v = narrate(s["en"]) if s.get("en") and spec.get("voice", True) else None
        vlen = len(v) / SR if v is not None else 0
        reveal = 0.45 * max(1, len(s["fa"].split()))
        d = max(3.6, reveal + 1.2, vlen + 1.0)
        tl.append(dict(seg=s, t0=t, d=d, v=v, tv=t + 0.5))
        t += d + GAP
    DUR = round(t + OUTRO, 2)
    # --- audio
    vt = np.zeros(int(DUR * SR))
    for e in tl:
        if e["v"] is not None:
            i0 = int(e["tv"] * SR); j = min(len(vt), i0 + len(e["v"])); vt[i0:j] += e["v"][:j - i0]
    mixed = music(DUR, spec.get("seed", 1), vt if np.any(vt) else None)
    tmpd = tempfile.mkdtemp(); wav = os.path.join(tmpd, "mix.wav")
    st = np.stack([mixed, np.r_[np.zeros(300), mixed[:-300]]], 1)
    with wave.open(wav, "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((np.clip(st, -1, 1) * 32767).astype(np.int16).tobytes())
    # --- scenes: intro + one per segment, cycling kinds/palettes
    kinds = ["dervish", "warp", "sun", "dervish", "warp", "dervish"]
    scenes = [Scene(rng, "plain", PALETTES[0])]
    for i in range(len(tl)):
        scenes.append(Scene(rng, kinds[i % len(kinds)], PALETTES[(i + 1 + spec.get("seed", 1)) % len(PALETTES)]))
    starts = [0.0] + [e["t0"] - 0.4 for e in tl]
    ends = starts[1:] + [DUR]
    dust = Dust(rng)
    # --- text assets
    for e in tl:
        e["fa_imgs"] = persian_progressive(e["seg"]["fa"]) if e["seg"].get("fa") else []
        e["en_img"] = glow_rgba(text_img(e["seg"]["en"], SERIF_I, fit_size(e["seg"]["en"], SERIF_I, 50, 900, False)),
                                (240, 232, 215), (255, 220, 160), 6, 0.35) if e["seg"].get("en") else None
    title = glow_rgba(text_img(spec.get("title", ""), SERIF_I, 76), (255, 245, 225), (255, 210, 140), 12, 0.8) if spec.get("title") else None
    header = glow_rgba(text_img(spec.get("header", "").upper(), SERIF, 36), GOLD, GOLD, 5, 0.3)
    src = glow_rgba(text_img(spec.get("source", ""), SERIF, 34), GOLD, GOLD, 5, 0.3)
    handle = glow_rgba(text_img("@theguesthouse.poetry", SERIF, 34), (235, 228, 210), (235, 228, 210), 4, 0.2)
    sig = glow_rgba(text_img("Mowlana Jalal ad-Din Rumi", SERIF_I, 38), (235, 228, 210), (255, 220, 160), 6, 0.3)

    ff = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                           "-r", str(FPS), "-i", "-", "-i", wav, "-c:v", "libx264", "-crf", "19", "-preset", "medium",
                           "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", out],
                          stdin=subprocess.PIPE)
    XF = 1.0
    for fi in range(int(DUR * FPS)):
        tt = fi / FPS
        si = max(i for i in range(len(starts)) if starts[i] <= tt)
        img = scenes[si].frame(tt - starts[si], ends[si] - starts[si] + XF)
        if si > 0 and tt - starts[si] < XF:                       # cross-dissolve with a soft light flash
            a = (tt - starts[si]) / XF
            prev = scenes[si - 1].frame(tt - starts[si - 1], ends[si - 1] - starts[si - 1] + XF)
            img = prev * (1 - a) + img * a + 60 * math.sin(math.pi * a)
        img = img + dust.draw(tt)[..., None] * np.array([1.0, 0.9, 0.75])
        frame = np.asarray(Image.fromarray(np.clip(img, 0, 255).astype(np.uint8)).resize((W, H), Image.BICUBIC), float)
        # vignette + lower darkening for legibility
        if fi == 0:
            yy, xx = np.mgrid[0:H, 0:W]
            vig = 1 - 0.55 * (((xx - W / 2) / (W * 0.75)) ** 2 + ((yy - H / 2) / (H * 0.75)) ** 2)
            vig *= 1 - 0.5 * np.exp(-((yy - H * 0.81) / 230) ** 2)
            vig = np.clip(vig, 0.15, 1)[..., None]
        frame *= vig
        # text
        ease = lambda x: max(0.0, min(1.0, x)) ** 2 * (3 - 2 * max(0.0, min(1.0, x)))
        if title is not None:
            a = ease((tt - 0.4) / 0.8) * ease((INTRO + 0.2 - tt) / 0.6)
            if a > 0:
                composite(frame, header, W / 2, H * 0.40, a); composite(frame, title, W / 2, H * 0.46, a)
        for e in tl:
            t0, d = e["t0"], e["d"]
            if tt < t0 or tt > t0 + d + 0.6: continue
            out_a = ease((t0 + d + 0.6 - tt) / 0.6)
            imgs = e["fa_imgs"]
            if imgs:
                step = min(0.45, (d - 1.2) / len(imgs))
                k = (tt - t0) / step
                ki = int(min(len(imgs) - 1, max(0, math.floor(k))))
                frac = ease(k - ki) if ki < len(imgs) - 1 or k < len(imgs) else 1
                if ki > 0: composite(frame, imgs[ki - 1], W / 2, H * 0.775, out_a * (1 - frac))
                composite(frame, imgs[ki], W / 2, H * 0.775, out_a * (frac if k < len(imgs) else 1))
            if e["en_img"] is not None:
                composite(frame, e["en_img"], W / 2, H * 0.845 + 12 * (1 - ease((tt - e["tv"]) / 0.8)),
                          out_a * ease((tt - e["tv"]) / 0.8))
        a_end = ease((tt - (DUR - OUTRO)) / 0.8)
        if a_end > 0:
            composite(frame, sig, W / 2, H * 0.62, a_end); composite(frame, src, W / 2, H * 0.66, a_end)
        composite(frame, handle, W / 2, H * 0.935, ease(tt / 1.0) * 0.85)
        fade = min(1.0, tt / 0.7, (DUR - tt) / 0.9)
        frame *= max(0.0, fade)
        ff.stdin.write(np.clip(frame, 0, 255).astype(np.uint8).tobytes())
    ff.stdin.close(); ff.wait()
    return DUR

if __name__ == "__main__":
    d = build(json.load(open(sys.argv[1], encoding="utf-8")), sys.argv[2])
    print(sys.argv[2], d)
