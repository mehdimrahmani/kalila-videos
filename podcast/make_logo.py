#!/usr/bin/env python3
"""Vintage seal logos for The Honest Historian (aged paper, worn ink stamp, lithograph feel).
usage: python3 podcast/make_logo.py [variant]   -> docs/podcast/logo.png (default variant 'b')"""
import os, sys, math, numpy as np
from PIL import Image, ImageDraw, ImageFilter
from scipy.ndimage import gaussian_filter
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(HERE, "..", "guesthouse"))
import make_reel_cinematic as R
S = 1000
rng = np.random.default_rng(11)

def paper():
    base = np.ones((S, S, 3)) * np.array([226, 211, 178])
    fib = gaussian_filter(rng.standard_normal((S, S)), 1.2) * 6 + gaussian_filter(rng.standard_normal((S, S)), 30) * 160
    stains = gaussian_filter(rng.standard_normal((S, S)), 90) * 900
    yy, xx = np.mgrid[0:S, 0:S]
    vig = 1 - 0.28 * (((xx - S / 2) / (S * 0.62)) ** 2 + ((yy - S / 2) / (S * 0.62)) ** 2)
    img = base + fib[..., None] + stains[..., None] * np.array([1.0, 0.9, 0.6])
    return np.clip(img * vig[..., None], 0, 255)

def ink_mask(draw_fn):
    m = Image.new("L", (S, S), 0); draw_fn(ImageDraw.Draw(m), m); a = np.asarray(m, float) / 255
    # worn stamp: uneven pressure, speckle gaps, slightly bled edges
    press = np.clip(0.75 + gaussian_filter(rng.standard_normal((S, S)), 60) * 9, 0.35, 1)
    gaps = gaussian_filter(rng.standard_normal((S, S)), 1.6) > 0.55
    bleed = gaussian_filter(a, 1.3)
    out = np.clip(bleed * press * (1 - gaps * 0.85), 0, 1)
    return out

def text_layer(txt, font, size, rtl=False):
    t = R.text_img(txt, font, size, rtl=rtl); return t

def paste_text(m, t, cx, cy):
    m.paste(255, (int(cx - t.width / 2), int(cy - t.height / 2)), t)

def variant_a(d, m):      # round seal, like an old Persian mohr
    c = S / 2
    d.ellipse([90, 90, S - 90, S - 90], outline=255, width=26)
    d.ellipse([140, 140, S - 140, S - 140], outline=255, width=6)
    for k in range(48):     # beaded inner ring
        a = 2 * math.pi * k / 48; r = 385
        d.ellipse([c + r * math.cos(a) - 7, c + r * math.sin(a) - 7, c + r * math.cos(a) + 7, c + r * math.sin(a) + 7], fill=255)
    paste_text(m, text_layer("تاریخ", R.NASTA, 110, True), c, 255)
    paste_text(m, text_layer("بیهقی", R.NASTA, 240, True), c, 505)
    paste_text(m, text_layer("THE HONEST HISTORIAN", R.SERIF, 34), c, 772)

def variant_b(d, m):      # square seal block, ink filled, letters reversed out (like Gazette's mark)
    d.rectangle([150, 120, S - 150, S - 120], fill=255)
    hole = Image.new("L", (S, S), 0); hd = ImageDraw.Draw(hole)
    paste_text(hole, text_layer("بیهقی", R.NASTA, 280, True), S / 2, 540)
    paste_text(hole, text_layer("تاریخ", R.NASTA, 110, True), S / 2, 255)
    hd.rectangle([185, 155, S - 185, S - 155], outline=255, width=5)
    paste_text(hole, text_layer("THE HONEST HISTORIAN", R.SERIF, 44), S / 2, 790)
    m.paste(0, (0, 0), hole)

def variant_c(d, m):      # lithograph title page: ornamental frame, dome motif, calligraphy
    d.rectangle([110, 110, S - 110, S - 110], outline=255, width=14)
    d.rectangle([140, 140, S - 140, S - 140], outline=255, width=4)
    for x in range(160, S - 150, 34):  # tiny ornament row top & bottom
        d.polygon([(x, 165), (x + 10, 155), (x + 20, 165), (x + 10, 175)], fill=255)
        d.polygon([(x, S - 165), (x + 10, S - 175), (x + 20, S - 165), (x + 10, S - 155)], fill=255)
    c = S / 2   # small domed arch (mihrab) above the name
    d.arc([c - 100, 215, c + 100, 405], 180, 360, fill=255, width=9)
    d.line([(c - 100, 310), (c - 100, 360)], fill=255, width=9); d.line([(c + 100, 310), (c + 100, 360)], fill=255, width=9)
    d.ellipse([c - 11, 192, c + 11, 214], fill=255)
    paste_text(m, text_layer("بیهقی", R.NASTA, 225, True), c, 555)
    paste_text(m, text_layer("The Honest Historian", R.SERIF_I, 54), c, 775)

def make(v, ink=(52, 30, 22)):
    p = paper(); mask = ink_mask({"a": variant_a, "b": variant_b, "c": variant_c}[v])
    if v == "a": ink = (128, 30, 26)     # oxblood seal ink
    img = p * (1 - mask[..., None] * 0.92) + np.array(ink) * mask[..., None] * 0.92
    im = Image.fromarray(np.clip(img, 0, 255).astype(np.uint8)).rotate(-2.0 if v != "c" else 0, resample=Image.BICUBIC, fillcolor=(226, 211, 178))
    return im

if __name__ == "__main__":
    out_dir = os.path.join(HERE, "..", "docs", "podcast")
    if len(sys.argv) > 1 and sys.argv[1] == "all":
        for v in "abc": make(v).save(f"/tmp/logo_{v}.png")
    else:
        v = sys.argv[1] if len(sys.argv) > 1 else "b"
        make(v).save(os.path.join(out_dir, "logo.png")); print("logo", v)
