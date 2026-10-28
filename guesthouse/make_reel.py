#!/usr/bin/env python3
"""The Guest House — Instagram Reel maker (1080x1920, ~16 s, ney melody).

usage: python3 make_reel.py spec.json out.mp4
spec.json: {"header": "SHAMS & RUMI · PART 1", "title": "Before the Fire",
            "fa": ["مرده بدم زنده شدم، گریه بدم خنده شدم", "..."],
            "en": ["I was dead, I came alive.", "..."],
            "source": "Divan-e Shams, Ghazal 1393", "seed": 1}
House style: deep navy #1B2140, thin double gold #C9A45C border, cream #EFE6D2 text,
gold small-caps header. Persian verse in Vazirmatn (rendered with raqm shaping), English in a serif.
"""
import sys, os, json, math, wave, subprocess, tempfile
import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
FA_FONT = os.path.join(HERE, "fonts", "Vazirmatn-Regular.ttf")
SERIF = "/usr/share/fonts/truetype/freefont/FreeSerif.ttf"
SERIF_I = "/usr/share/fonts/truetype/freefont/FreeSerifItalic.ttf"
SERIF_B = "/usr/share/fonts/truetype/freefont/FreeSerifBold.ttf"
for f in (SERIF, SERIF_I, SERIF_B):
    if not os.path.exists(f):
        SERIF = SERIF_I = SERIF_B = "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf"
W, H, FPS, DUR = 1080, 1920, 24, 16.0
NAVY, GOLD, CREAM = (27, 33, 64), (201, 164, 92), (239, 230, 210)

def text_layer(txt, font, size, fill, rtl=False, maxw=900):
    f = ImageFont.truetype(font, size)
    kw = dict(direction="rtl", language="fa") if rtl else {}
    while True:
        l, t, r, b = f.getbbox(txt, **kw)
        if r - l <= maxw or size <= 26: break
        size -= 2; f = ImageFont.truetype(font, size)
    im = Image.new("RGBA", (r - l + 8, b - t + 8), (0, 0, 0, 0))
    ImageDraw.Draw(im).text((4 - l, 4 - t), txt, font=f, fill=fill + (255,), **kw)
    return im

def ease(x): x = max(0.0, min(1.0, x)); return x * x * (3 - 2 * x)

def build(spec, out):
    layers = []   # (img, y_center, t_in)
    y = 360
    layers.append((text_layer(spec["header"].upper(), SERIF_B, 40, GOLD), y, 0.3)); y += 80
    if spec.get("title"):
        layers.append((text_layer(spec["title"], SERIF_I, 64, CREAM), y, 0.8)); y += 150
    t = 1.8
    for line in spec.get("fa", []):
        layers.append((text_layer(line, FA_FONT, 52, CREAM, rtl=True), y, t)); y += 100; t += 1.1
    sep_y = y - 20
    y += 70
    t_en = t + 0.4
    for line in spec.get("en", []):
        layers.append((text_layer(line, SERIF_I, 54, CREAM), y, t + 0.4)); y += 82; t += 1.2
    y += 60
    layers.append((text_layer(spec.get("source", ""), SERIF, 34, GOLD), y, t + 0.6)); y += 60
    layers.append((text_layer("translated from the Persian", SERIF_I, 30, GOLD), y, t + 0.8))
    layers.append((text_layer("@theguesthouse.poetry", SERIF, 38, CREAM), H - 300, 0.6))
    # vertically centre the block between top and the handle
    block_top, block_bot = 360, y + 40
    shift = int((H - 300 - 120 - block_bot + 300 - block_top) / 2)
    base = Image.new("RGB", (W, H), NAVY)
    d = ImageDraw.Draw(base)
    for inset, w in ((54, 3), (70, 1)):
        d.rectangle([inset, inset, W - inset, H - inset], outline=GOLD, width=w)
    d.line([(W / 2 - 90, sep_y + shift), (W / 2 + 90, sep_y + shift)], fill=GOLD, width=2)
    # small 8-point star ornaments
    for cx, cy in ((W / 2, 250), (W / 2, H - 200)):
        pts = []
        for k in range(16):
            r = 16 if k % 2 == 0 else 7
            a = math.radians(k * 22.5 - 90)
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
        d.polygon(pts, fill=GOLD)
    tmpd = tempfile.mkdtemp()
    global DUR
    voice = None
    if spec.get("voice", True) and spec.get("en"):
        voice = narrate(spec.get("voice_text") or " ... ".join(spec["en"]))
        if voice is not None:
            DUR = max(16.0, round(t_en + len(voice) / 44100 + 1.6, 1))
    wav = os.path.join(tmpd, "ney.wav"); ney(wav, spec.get("seed", 1), voice=voice, t_voice=t_en)
    ff = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                           "-r", str(FPS), "-i", "-", "-i", wav, "-c:v", "libx264", "-crf", "20", "-pix_fmt", "yuv420p",
                           "-c:a", "aac", "-b:a", "160k", "-shortest", "-movflags", "+faststart", out], stdin=subprocess.PIPE)
    for i in range(int(DUR * FPS)):
        tt = i / FPS
        fr = base.copy().convert("RGBA")
        for img, yc, tin in layers:
            a = ease((tt - tin) / 0.9)
            if a <= 0: continue
            dy = int(14 * (1 - a))
            im = img if a >= 1 else Image.fromarray((np.array(img) * np.array([1, 1, 1, a])).astype(np.uint8), "RGBA")
            yy = yc + (shift if yc != H - 300 else 0)
            fr.alpha_composite(im, (int((W - img.width) / 2), int(yy - img.height / 2 + dy)))
        z = 1 + 0.035 * tt / DUR                      # slow push-in
        cw, ch = int(W / z), int(H / z)
        fr = fr.crop(((W - cw) // 2, (H - ch) // 2, (W + cw) // 2, (H + ch) // 2)).resize((W, H), Image.LANCZOS)
        fade = min(1.0, tt / 0.6, (DUR - tt) / 0.8)
        if fade < 1: fr = Image.blend(Image.new("RGBA", (W, H), NAVY + (255,)), fr, max(0, fade))
        ff.stdin.write(fr.convert("RGB").tobytes())
    ff.stdin.close(); ff.wait()

def ney(path, seed=1, sr=44100, voice=None, t_voice=4.0):
    """Breathy ney-like melody in Dastgah-e Shur (D, E-koron, F, G, A), with drone."""
    rng = np.random.default_rng(seed)
    D = 293.66
    deg = {"D": 0, "Ek": 1.5, "F": 3, "G": 5, "A": 7, "Bb": 8, "C": 10, "D5": 12, "C4": -2, "A3": -5}
    phrases = [["A3", "D", "Ek", "F", "Ek", "D"], ["F", "G", "A", "G", "F", "Ek", "D"],
               ["D", "F", "Ek", "D", "C4", "D"], ["A", "Bb", "A", "G", "F", "Ek", "D"]]
    order = [phrases[k % 4] for k in rng.permutation(4)][:3]
    N = int(sr * DUR); t = np.arange(N) / sr; out = np.zeros(N)
    pos = 0.6
    for ph in order:
        for k, n in enumerate(ph):
            dur = 1.1 if k == len(ph) - 1 else rng.choice([0.45, 0.6, 0.6, 0.8])
            f = D * 2 ** (deg[n] / 12)
            n0, n1 = int(pos * sr), min(N, int((pos + dur + 0.15) * sr))
            tt = np.arange(n1 - n0) / sr
            vib = 1 + 0.006 * np.sin(2 * np.pi * 5.2 * tt) * np.minimum(1, tt / 0.3)
            ph_ = 2 * np.pi * f * np.cumsum(vib) / sr
            tone = np.sin(ph_) + 0.25 * np.sin(2 * ph_) + 0.08 * np.sin(3 * ph_)
            breath = np.convolve(rng.standard_normal(len(tt)), np.ones(12) / 12, "same") * 0.35
            envl = np.minimum(1, tt / 0.12) * np.clip((dur + 0.15 - tt) / 0.25, 0, 1)
            out[n0:n1] += (tone * 0.8 + breath * (0.5 + 0.5 * np.sin(ph_))) * envl * 0.5
            pos += dur
        pos += 0.5
        if pos > DUR - 1.5: break
    out *= 0.75
    out += 0.07 * (np.sin(2 * np.pi * D / 2 * t) + 0.5 * np.sin(2 * np.pi * D * 0.75 * t))   # drone (D + A)
    out += daf(N, sr, rng)                                                               # sama rhythm
    rev = out.copy()
    for dl, g in ((0.09, 0.35), (0.17, 0.25), (0.29, 0.16), (0.43, 0.1)):
        k = int(dl * sr); rev[k:] += out[:-k] * g
    rev *= np.minimum(1, t / 0.8) * np.clip((DUR - t) / 1.2, 0, 1)
    rev = rev / (np.abs(rev).max() + 1e-9) * 0.8
    if voice is not None:                      # narration on top, music ducked well under it
        v = np.zeros(N); i0 = int(t_voice * sr); j0 = min(N, i0 + len(voice))
        v[i0:j0] = voice[:j0 - i0]
        act = np.convolve(np.abs(v), np.ones(int(0.35 * sr)) / int(0.35 * sr), "same")
        act = np.clip(act / (act.max() * 0.08 + 1e-9), 0, 1)
        act = np.convolve(act, np.ones(int(0.3 * sr)) / int(0.3 * sr), "same")
        rev = rev * (1 - 0.75 * act) * 0.8 + v * 0.95
        pk = np.abs(rev).max()
        if pk > 0.95: rev *= 0.95 / pk
    st = np.stack([rev, np.r_[np.zeros(500), rev[:-500]]], 1)
    with wave.open(path, "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(sr)
        w.writeframes((st * 32767).astype(np.int16).tobytes())

def daf(N, sr, rng):
    """Sama-style daf in 6/8: DUM . tak DUM tak tak, slowly building, with jingle rings and a deep boom."""
    out = np.zeros(N); T = N / sr
    def hit(t0, kind, g):
        n0 = int(t0 * sr)
        if n0 >= N: return
        L = min(N - n0, int(0.6 * sr)); tt = np.arange(L) / sr
        if kind == "dum":
            f = 62 + 40 * np.exp(-tt * 30)
            x = np.sin(2 * np.pi * np.cumsum(f) / sr) * np.exp(-tt * 7)
            x += np.convolve(rng.standard_normal(L), np.ones(30) / 30, "same") * np.exp(-tt * 40) * 0.6
        else:
            x = (rng.standard_normal(L) - np.convolve(rng.standard_normal(L), np.ones(6) / 6, "same")) * np.exp(-tt * 45) * 0.5
            x += np.sin(2 * np.pi * 190 * tt) * np.exp(-tt * 25) * 0.4
        jing = rng.standard_normal(L) * sum(np.sin(2 * np.pi * fr * tt) for fr in (5200, 6900, 8300)) / 3
        x += jing * np.exp(-tt * 14) * 0.18                    # daf rings
        out[n0:n0 + L] += x * g
    pat = [("dum", 1.0), None, ("tak", 0.55), ("dum", 0.85), ("tak", 0.5), ("tak", 0.4)]
    t0, i = 0.9, 0
    while t0 < T - 0.8:
        prog = min(1, t0 / (T * 0.7))
        step = 60 / (96 + 22 * prog) / 2                       # eighth note; tempo rises like a whirl
        p = pat[i % 6]
        if p: hit(t0 + rng.normal(0, 0.004), p[0], p[1] * (0.55 + 0.45 * prog))
        if i % 12 == 0 and t0 > 3: hit(t0, "dum", 0.9)          # big downbeat boom
        t0 += step; i += 1
    return out * 0.55

TTS_DIRS = [os.path.join(HERE, "..", "pipeline", "tts"), "/home/claude/kalila_test/tts"]
def narrate(text, sr=44100):
    """Deep, slightly husky male English narration (Kokoro am_onyx), resampled to 44.1 kHz."""
    try:
        from kokoro_onnx import Kokoro
    except ImportError:
        return None
    for d in TTS_DIRS:
        m, v = os.path.join(d, "kokoro-v1.0.onnx"), os.path.join(d, "voices-v1.0.bin")
        if os.path.exists(m) and os.path.exists(v): break
    else:
        return None
    a, r = Kokoro(m, v).create(text, voice="am_onyx", speed=0.82, lang="en-us")
    f = 0.9 * r / sr                                  # pitch down ~10% while resampling
    n = int(len(a) / f); a = np.interp(np.arange(n) * f, np.arange(len(a)), a)
    envl = np.convolve(np.abs(a), np.ones(400) / 400, "same")
    grit = np.convolve(np.random.default_rng(1).standard_normal(len(a)), np.ones(3) / 3, "same") * envl * 0.35
    y = np.tanh((a + grit) * 2.2) / np.tanh(2.2)
    y = np.convolve(y, [0.6, 0.3, 0.1], "same")
    return y / (np.abs(y).max() + 1e-9) * 0.9

if __name__ == "__main__":
    build(json.load(open(sys.argv[1], encoding="utf-8")), sys.argv[2])
    print(sys.argv[2])
