#!/usr/bin/env python3
"""Static art for the long-form Remotion scene: aged paper (wide, oversized for camera moves) and the
lapis + gold illuminated border as a transparent PNG. Reuses the manuscript Reel's look."""
import os, sys, numpy as np
from PIL import Image
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(HERE, "..", "guesthouse"))
import make_reel_manuscript as M
OUT = os.path.join(HERE, "remotion", "public", "common")
W, H = 1920, 1080; MG = 1.1
M.W, M.H = W, H; M.CW, M.CH = int(W * MG), int(H * MG)
rng = np.random.default_rng(5)
paper = M.paper(rng)
Image.fromarray(np.clip(paper, 0, 255).astype(np.uint8)).save(os.path.join(OUT, "paper.jpg"), quality=92)
# border at exact frame size
M.CW, M.CH = W, H
g, l = M.border_layers(rng)
gcol, _ = M.gold_paint(g)
rgba = np.zeros((H, W, 4), np.float32)
rgba[..., :3] = np.array(M.LAPIS, np.float32) * l[..., None] * (1 - g[..., None]) + gcol * g[..., None]
rgba[..., 3] = np.clip(l * 0.92 + g, 0, 1) * 255
Image.fromarray(np.clip(rgba, 0, 255).astype(np.uint8), "RGBA").save(os.path.join(OUT, "border.png"))
print("ok")
