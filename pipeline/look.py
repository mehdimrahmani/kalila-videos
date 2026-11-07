"""Picture-book "look" pass for Kalila & Dimna frames (applied to the final W x H frame, inside the border).

    from look import Look
    LK = Look(W, H, border=24)
    img = LK(img, lt, sd)          # lt = time inside the scene, sd = scene duration

- slow camera breathing: a gentle push-in (and drift) over each scene, so still shots feel filmed
- gouache paper grain + soft painted edges (multiplied texture, fixed per episode so it does not flicker)
- warm grade with lifted shadows, a soft bloom on bright areas (sun, moon, lamps), and a gentle vignette
Everything is numpy/Pillow, deterministic, ~25 ms per 1080p frame.
"""
import numpy as np
from PIL import Image, ImageFilter

def _smooth(a, b, t):
    x = min(1.0, max(0.0, (t - a) / (b - a))) if b > a else 1.0
    return x * x * (3 - 2 * x)

class Look:
    def __init__(self, W, H, border=24, seed=7, push=0.045, grain=0.07, bloom=0.22, vignette=0.28):
        self.W, self.H, self.b = W, H, border
        self.push, self.bloom_k = push, bloom
        w, h = W - 2 * border, H - 2 * border
        self.w, self.h = w, h
        rng = np.random.default_rng(seed)
        # paper: fine grain + larger fibrous blotches, as a multiply layer around 1.0
        fine = rng.normal(0, 1, (h, w)).astype(np.float32)
        coarse = np.asarray(Image.fromarray(rng.normal(0, 1, (h // 16 + 1, w // 16 + 1)).astype(np.float32), mode="F")
                            .resize((w, h), Image.BICUBIC), np.float32)
        from scipy.ndimage import gaussian_filter
        fibre = gaussian_filter(np.asarray(Image.fromarray(rng.normal(0, 1, (h // 3 + 1, w // 3 + 1)).astype(np.float32), mode="F")
                                           .resize((w, h), Image.BILINEAR), np.float32), (1.2, 4.0))
        paper = 1 + grain * (0.25 * fine + 0.45 * coarse / (np.abs(coarse).max() + 1e-6) + 0.5 * fibre / (np.abs(fibre).max() + 1e-6))
        yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
        r = np.sqrt(((xx - w / 2) / (w / 2)) ** 2 + ((yy - h / 2) / (h / 2)) ** 2)
        vig = 1 - vignette * np.clip(r - 0.55, 0, None) ** 1.6
        self.mul = (paper * vig)[..., None].astype(np.float32)
        warm = np.array([1.025, 1.0, 0.955], np.float32)
        self.warm = warm

    def camera(self, im, lt, sd):
        """Push in from 1.0 to 1+push across the scene, drifting slightly right/up."""
        k = 1 + self.push * _smooth(0, max(sd, 0.1), lt)
        w, h = self.w, self.h
        cw, ch = w / k, h / k
        dx = (w - cw) * 0.55; dy = (h - ch) * 0.45
        return im.transform((w, h), Image.EXTENT, (dx, dy, dx + cw, dy + ch), Image.BICUBIC)

    def __call__(self, img, lt=0.0, sd=1.0, move=True):
        b = self.b
        inner = img.crop((b, b, self.W - b, self.H - b))
        if move: inner = self.camera(inner, lt, sd)
        a = np.asarray(inner, np.float32) / 255.0
        lum = a @ np.array([0.299, 0.587, 0.114], np.float32)
        # bloom: blur of the brightest parts, screened back in
        hi = np.clip((lum - 0.78) / 0.22, 0, 1)[..., None] * a
        bl = np.asarray(Image.fromarray((hi * 255).astype(np.uint8)).resize((self.w // 4, self.h // 4), Image.BILINEAR)
                        .filter(ImageFilter.GaussianBlur(9)).resize((self.w, self.h), Image.BILINEAR), np.float32) / 255.0
        a = 1 - (1 - a) * (1 - self.bloom_k * bl)
        # grade: lift shadows a touch, soft S-curve, warm highlights
        a = 0.03 + 0.97 * a
        a = a + 0.06 * (a - a * a) * (2 * a - 1) * -1      # gentle contrast roll-off on the ends
        a = a * (1 + (self.warm - 1) * lum[..., None])
        a = a * self.mul
        out = Image.fromarray((np.clip(a, 0, 1) * 255 + 0.5).astype(np.uint8))
        img = img.copy(); img.paste(out, (b, b))
        return img
