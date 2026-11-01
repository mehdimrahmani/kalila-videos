#!/usr/bin/env python3
"""3000x3000 cover in the nostalgic style chosen by Mehdi (1 Nov 2026): aged paper + the red seal (logo variant A)
+ English title in dark ink."""
import os, sys, numpy as np
from PIL import Image, ImageDraw
from scipy.ndimage import gaussian_filter
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, "..", "guesthouse"))
import make_logo as L
import make_reel_cinematic as R
S = 3000
rng = np.random.default_rng(3)
base = np.ones((S, S, 3)) * np.array([226, 211, 178])
base += gaussian_filter(rng.standard_normal((S, S)), 1.5)[..., None] * 7
base += gaussian_filter(rng.standard_normal((S, S)), 220)[..., None] * 2600 * np.array([1.0, 0.9, 0.6])
yy, xx = np.mgrid[0:S, 0:S]
base *= np.clip(1 - 0.3 * (((xx - S / 2) / (S * 0.62)) ** 2 + ((yy - S / 2) / (S * 0.62)) ** 2), 0, 1)[..., None]
img = Image.fromarray(np.clip(base, 0, 255).astype(np.uint8))
mask = L.ink_mask(L.variant_a)                                   # 1000x1000 worn-ink seal mask
mask = np.asarray(Image.fromarray((mask * 255).astype(np.uint8)).rotate(-2.0, resample=Image.BICUBIC)
                  .resize((2000, 2000), Image.LANCZOS), float) / 255
arr0 = np.asarray(img, float).copy()
reg = arr0[180:2180, 500:2500]
arr0[180:2180, 500:2500] = reg * (1 - mask[..., None] * 0.92) + np.array([128, 30, 26]) * mask[..., None] * 0.92
img = Image.fromarray(np.clip(arr0, 0, 255).astype(np.uint8))
arr = np.asarray(img, float).copy()
ink = (48, 30, 22)
for txt, font, size, y in (("THE HONEST HISTORIAN", R.SERIF, 170, 2300), ("Stories from Beyhaqi", R.SERIF_I, 140, 2510),
                           ("with Mehdi Rahmani", R.SERIF, 95, 2700)):
    R.composite(arr, R.glow_rgba(R.text_img(txt, font, size), ink, ink, 1, 0.05), S / 2, y)
out = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))
d = ImageDraw.Draw(out)
d.rectangle([70, 70, S - 70, S - 70], outline=ink, width=10); d.rectangle([105, 105, S - 105, S - 105], outline=ink, width=3)
p = os.path.join(HERE, "..", "docs", "podcast", "cover.jpg"); out.save(p, quality=88); print(p)
