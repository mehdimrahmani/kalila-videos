#!/usr/bin/env python3
"""3000x3000 podcast cover: night-sky nebula, gold frame, Nastaliq 'تاریخ بیهقی', English title."""
import os, sys, numpy as np
from PIL import Image, ImageDraw, ImageFont
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(HERE, "..", "guesthouse"))
import make_reel_cinematic as R
S = 3000
rng = np.random.default_rng(7)
neb = R.nebula(rng, ((10, 12, 30), (60, 40, 25), (230, 180, 110)), 1000, 1000)
st = R.stars(rng, 1000, 1000, 700)
img = np.clip(neb * 0.8 + st[..., None] * 0.9, 0, 255)
im = Image.fromarray(img.astype(np.uint8)).resize((S, S), Image.BICUBIC)
arr = np.asarray(im, float)
yy, xx = np.mgrid[0:S, 0:S]
arr *= np.clip(1 - 0.6 * (((xx - S / 2) / (S * 0.75)) ** 2 + ((yy - S / 2) / (S * 0.75)) ** 2), 0.2, 1)[..., None]
arr *= np.clip(1 - 0.55 * np.exp(-((yy - S * 0.62) / 700) ** 2), 0, 1)[..., None]
base = arr.copy()
def put(rgba, cy):
    R.composite(base, rgba, S / 2, cy)
fa = R.glow_rgba(R.text_img("تاریخ بیهقی", R.NASTA, 440, rtl=True), (250, 236, 205), (255, 205, 120), 30, 0.9)
put(fa, S * 0.43)
put(R.glow_rgba(R.text_img("THE HONEST HISTORIAN", R.SERIF, 190), R.GOLD, R.GOLD, 10, 0.4), S * 0.66)
put(R.glow_rgba(R.text_img("Stories from Beyhaqi", R.SERIF_I, 150), (240, 230, 210), (255, 220, 160), 10, 0.4), S * 0.74)
put(R.glow_rgba(R.text_img("with Mehdi Rahmani", R.SERIF, 100), (220, 210, 190), (220, 210, 190), 6, 0.2), S * 0.86)
out = Image.fromarray(np.clip(base, 0, 255).astype(np.uint8))
d = ImageDraw.Draw(out)
for inset, w in ((90, 14), (130, 5)):
    d.rectangle([inset, inset, S - inset, S - inset], outline=R.GOLD, width=w)
os.makedirs(os.path.join(HERE, "..", "docs", "podcast"), exist_ok=True)
p = os.path.join(HERE, "..", "docs", "podcast", "cover.jpg")
out.save(p, quality=88); print(p, os.path.getsize(p))
