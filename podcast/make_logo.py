#!/usr/bin/env python3
"""Seal-style logo: 'بیهقی' in Nastaliq, cream on a deep ink square, like a scribe's seal."""
import os, sys, numpy as np
from PIL import Image, ImageDraw
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(HERE, "..", "guesthouse"))
import make_reel_cinematic as R
S = 800
base = np.zeros((S, S, 3)); base[:] = (24, 28, 26)
t = R.text_img("بیهقی", R.NASTA, 300, rtl=True)
rgba = R.glow_rgba(t, (241, 233, 214), (241, 233, 214), 1, 0.05)
R.composite(base, rgba, S / 2, S * 0.47)
small = R.glow_rgba(R.text_img("THE HONEST HISTORIAN", R.SERIF, 46), (214, 178, 106), (214, 178, 106), 1, 0.05)
R.composite(base, small, S / 2, S * 0.86)
im = Image.fromarray(np.clip(base, 0, 255).astype(np.uint8)); d = ImageDraw.Draw(im)
d.rectangle([28, 28, S - 28, S - 28], outline=(214, 178, 106), width=6)
p = os.path.join(HERE, "..", "docs", "podcast", "logo.png"); im.save(p); print(p)
