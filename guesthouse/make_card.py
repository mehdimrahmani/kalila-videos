#!/usr/bin/env python3
"""The Guest House — weekly feed card (1080x1350, 4:5), same cinematic look as the Reels, no Canva.

usage: python3 make_card.py spec.json out.png
Uses the same spec as make_reel_cinematic.py ("header", "title", "segments" or "fa"/"en", "source", "seed").
"""
import sys, json
import numpy as np
from PIL import Image
import make_reel_cinematic as R

W, H = 1080, 1350

def build(spec, out):
    seed = spec.get("seed", 1)
    rng = np.random.default_rng(seed)
    theme = spec.get("theme", "cosmic")
    kinds, style = R.THEMES.get(theme, R.THEMES["cosmic"])
    kind = ["dervish", "sun", "dervish", "warp"][seed % 4] if theme == "cosmic" else kinds[0]
    pal = R.PALETTES[(seed + 1) % len(R.PALETTES)]
    sc = R.Scene(rng, kind, pal)
    sc.dtop, sc.dscale = 115, 0.46                             # small figure in the upper half
    bg = sc.frame(2.0, 8.0)                                   # 720x1280 portrait
    off = {"candle": 330, "dome": 200, "reeds": 200}.get(kind, 60)
    bg = bg[off:off + 900]                                     # 4:5 window, figure in the upper part
    G = R.GOLD if style == "light" else (128, 30, 26)
    gl = (5, 0.3) if style == "light" else (1, 0.05)
    img = np.asarray(Image.fromarray(np.clip(bg, 0, 255).astype(np.uint8)).resize((W, H), Image.BICUBIC), float)
    yy, xx = np.mgrid[0:H, 0:W]
    vig = 1 - 0.5 * (((xx - W / 2) / (W * 0.8)) ** 2 + ((yy - H / 2) / (H * 0.8)) ** 2)
    vig *= 1 - (0.6 if style == "light" else 0.0) * np.clip((yy - H * 0.42) / (H * 0.2), 0, 1)        # dark lower half for the text
    img *= np.clip(vig, 0.12, 1)[..., None]

    segs = R.segments_of(spec)
    R.composite(img, R.glow_rgba(R.text_img(spec.get("header", "").upper(), R.SERIF, 34), G, G, *gl), W / 2, 70)

    def layout(k):
        items = []
        if spec.get("title"):
            items.append(((R.glow_rgba(R.text_img(spec["title"], R.SERIF_I, int(56 * k)), (255, 245, 225), (255, 210, 140), 10, 0.7) if style == "light" else R.glow_rgba(R.text_img(spec["title"], R.SERIF_I, int(56 * k)), R.INK, R.INK, 1, 0.05)), -56 + int(30 * k)))
        for s in segs:
            if s.get("fa"):
                items.append((R.persian_progressive(s["fa"], size=int(70 * k), maxw=960, style=style)[-1], -64 + int(6 * k)))
        items.append((None, int(30 * k)))
        for s in segs:
            if s.get("en"):
                items.append(((R.glow_rgba(R.en_block(s["en"], size=int(40 * k), maxw=940), (240, 232, 215), (255, 220, 160), 5, 0.3) if style == "light" else R.glow_rgba(R.en_block(s["en"], size=int(40 * k), maxw=940), (70, 45, 30), (70, 45, 30), 1, 0.05)), -66 + int(8 * k)))
        items.append((None, int(10 * k)))
        items.append((R.glow_rgba(R.text_img(spec.get("source", ""), R.SERIF, 30), G, G, *gl), -30))
        items.append((R.glow_rgba(R.text_img("translated from the Persian", R.SERIF_I, 27), G, G, *gl), 0))
        return items, sum((it.shape[0] if it is not None else 0) + g for it, g in items)

    top, bottom = ({"dervish": H * 0.47, "candle": H * 0.47, "dome": H * 0.47, "reeds": H * 0.49}.get(kind, H * 0.30)), H - 105
    k = 1.0
    items, hgt = layout(k)
    while hgt > bottom - top and k > 0.55:
        k -= 0.06; items, hgt = layout(k)
    y = bottom - hgt
    for it, gap in items:
        if it is None: y += gap; continue
        R.composite(img, it, W / 2, y + it.shape[0] / 2); y += it.shape[0] + gap
    hc = (235, 228, 210) if style == "light" else R.INK
    handle = R.glow_rgba(R.text_img("@theguesthouse.poetry", R.SERIF, 32), hc, hc, 4 if style == "light" else 1, 0.2 if style == "light" else 0.05)
    R.composite(img, handle, W / 2, H - 60, 0.85)
    Image.fromarray(np.clip(img, 0, 255).astype(np.uint8)).save(out, quality=95)

if __name__ == "__main__":
    build(json.load(open(sys.argv[1], encoding="utf-8")), sys.argv[2])
    print(sys.argv[2])
