#!/usr/bin/env python3
"""
Kalila & Dimna — "The Lion and the Hare" — cut-out animation test (~34 s, 1280x720).

How it works (the whole idea of the pipeline):
  * Every character is a "paper puppet" built from separate parts (body, legs, head,
    mane, ears, tail...) defined as simple polygons.
  * Each frame, code poses the parts (rotate a leg, open the jaw, tilt the head)
    and draws them on top of a pre-painted background.
  * Music and sound effects are synthesized in code (santur-like plucks in Dastgah-e Shur).
  * ffmpeg stitches frames + audio into an MP4.
No paid AI video generation is used anywhere — the only cost is CPU time.
"""
import math, os, sys, subprocess, wave
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import multiprocessing as mp

# ------------------------------------------------------------------ settings
W, H = 1280, 720
SS = 2                      # supersampling for smooth edges
FPS = 24
DUR = 50.5
NF = int(DUR * FPS)
GROUND = 600
WORLD_W = 3400
WELLX, RIMY = 2700, 468
RIM_RX, RIM_RY = 160, 44
WAT_RX, WAT_RY = 136, 33
LION_SCALE, RABBIT_SCALE = 1.05, 1.1
OUT = (61, 36, 16)
FB = "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf"
FR = "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf"
FI = "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Italic.ttf"
HERE = os.path.dirname(os.path.abspath(__file__))

SUBS = [
    (5.4, 8.6, "Long ago, a cruel lion ruled the forest."),
    (8.6, 12.0, "Every day, one animal had to become his meal."),
    (12.0, 14.6, "“O King, another lion has stolen your lunch!”"),
    (14.6, 16.9, "“He hides in a well. Come, I’ll show you!”"),
    (17.2, 22.7, "So the clever hare led the lion to a deep well."),
    (23.0, 26.4, "Inside, the lion saw a fierce lion staring back…"),
    (26.4, 28.7, "…and leapt in to fight his own reflection."),
    (28.9, 31.7, "Wisdom is stronger than strength."),
]

# ------------------------------------------------------------------ math helpers
def T(x, y): return np.array([[1, 0, x], [0, 1, y], [0, 0, 1.0]])
def R(deg):
    a = math.radians(deg); c, s = math.cos(a), math.sin(a)
    return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1.0]])
def S(sx, sy=None):
    sy = sx if sy is None else sy
    return np.array([[sx, 0, 0], [0, sy, 0], [0, 0, 1.0]])
def ap(M, pts):
    P = np.c_[np.asarray(pts, float), np.ones(len(pts))]
    return [tuple(q) for q in (P @ M.T)[:, :2]]
def ell(cx, cy, rx, ry, n=40, a0=0, a1=360):
    full = (a1 - a0) >= 360
    return [(cx + rx * math.cos(math.radians(a)), cy + ry * math.sin(math.radians(a)))
            for a in np.linspace(a0, a1, n, endpoint=not full)]
def khatam(cx, cy, r, rot=0):   # 8-point Persian star
    return [(cx + (r if k % 2 == 0 else r * 0.7654) * math.cos(math.radians(k * 22.5 + rot)),
             cy + (r if k % 2 == 0 else r * 0.7654) * math.sin(math.radians(k * 22.5 + rot)))
            for k in range(16)]
def clamp(x, a=0.0, b=1.0): return max(a, min(b, x))
def sm(a, b, t):
    x = clamp((t - a) / (b - a)); return x * x * (3 - 2 * x)
def env(t, a, b, ain, aout):
    if t < a or t > b: return 0.0
    return min(clamp((t - a) / ain), clamp((b - t) / aout))

class Pen:
    def __init__(self, img): self.d = ImageDraw.Draw(img)
    def poly(self, M, pts, fill, outline=OUT, w=3):
        self.d.polygon(ap(M, pts), fill=fill, outline=outline,
                       width=max(1, int(w * SS)) if outline else 1)
    def line(self, M, pts, fill, w=2):
        self.d.line(ap(M, pts), fill=fill, width=max(1, int(w * SS)), joint="curve")

# ------------------------------------------------------------------ LION puppet
LC = dict(body="#d9a441", far="#b0802c", mane="#9c4a17", mane2="#c46a24",
          face="#e8b65a", muzzle="#f4dca0", dark="#3b1d0a")

def lion_leg(p, Mb, jx, jy, ang, col):
    Ml = Mb @ T(jx, jy) @ R(ang)
    p.poly(Ml, [(-13, -6), (13, -6), (12, 50), (-11, 50)], col)
    p.poly(Ml, ell(4, 54, 16, 9, 24), col)

def lion_tail(p, Mb, t):
    x, y = -86.0, -92.0
    ang = math.radians(150)
    pts = [(x, y)]
    for i in range(13):
        ang += 0.12 + 0.07 * math.sin(t * 3.0 - i * 0.45)
        x += 9 * math.cos(ang); y += 9 * math.sin(ang)
        pts.append((x, y))
    p.line(Mb, pts, OUT, 9)
    p.line(Mb, pts, LC['body'], 5)
    p.poly(Mb @ T(x, y) @ R(math.degrees(ang)), ell(6, 0, 14, 9, 24), LC['mane'])

def lion_head(p, Mh, po):
    t = po.get('t', 0); shake = po.get('shake', 0)
    cx, cy = 16, -12
    wob = shake * math.sin(t * 28) * 0.25
    def scal(r0, amp, k, ph):
        return [(cx + (r0 + amp * math.sin(k * a + ph)) * math.cos(a),
                 cy + (r0 + amp * math.sin(k * a + ph)) * math.sin(a))
                for a in np.linspace(0, 2 * math.pi, 104, endpoint=False)]
    p.poly(Mh, scal(64, 8, 13, wob), LC['mane'])
    p.poly(Mh, scal(51, 6, 13, 0.25 - wob), LC['mane2'], w=2)
    for k in range(12):                                # miniature-style curls
        a = k * 2 * math.pi / 12 + 0.2 + wob
        sx, sy = cx + 58 * math.cos(a), cy + 58 * math.sin(a)
        sp = [(sx + (6 - j * 0.55) * math.cos(a + j * 0.65),
               sy + (6 - j * 0.55) * math.sin(a + j * 0.65)) for j in range(10)]
        p.line(Mh, sp, LC['dark'], 1.5)
    for ex, ey in ((0, -48), (36, -50)):
        p.poly(Mh, ell(ex, ey, 11, 10, 20), LC['face'])
        p.poly(Mh, ell(ex, ey + 1, 5, 5, 16), "#c97b6a", outline=None)
    p.poly(Mh, ell(24, -8, 35, 33), LC['face'])
    m = po.get('mouth', 0)
    p.poly(Mh, ell(45, 4, 19, 14, 30), LC['muzzle'])
    if m > 0.05:
        p.poly(Mh, [(35, 9), (65, 7), (61, 9 + 22 * m), (41, 9 + 17 * m)], "#7a1c14", w=2)
        p.poly(Mh, [(42, 9), (47, 9), (44.5, 16)], "white", outline=None)
        p.poly(Mh, [(55, 8.5), (60, 8.5), (57.5, 15)], "white", outline=None)
    else:
        p.line(Mh, [(40, 12), (50, 15), (60, 11)], LC['dark'], 2)
    for wy in (2, 6):
        p.line(Mh, [(52, wy), (72, wy - 3)], LC['dark'], 1)
    p.poly(Mh, ell(60, -4, 7, 5, 16), LC['dark'], outline=None)
    p.poly(Mh, ell(36, -20, 7, 6, 20), "white", w=2)
    p.poly(Mh, ell(38, -20, 3.5, 4, 14), LC['dark'], outline=None)
    ang = po.get('angry', 0.5)
    p.line(Mh, [(26, -31), (47, -27 + 6 * ang)], LC['dark'], 3)

def draw_lion(p, M, po):
    t = po.get('t', 0); ph = po.get('walk', 0); amp = po.get('amp', 0); st = po.get('stretch', 0)
    br = 1 + 0.018 * math.sin(t * 2.2)
    Mb = M @ T(0, -80) @ S(1, br) @ T(0, 80)
    for jx, sgn in ((-45, 1), (68, -1)):                 # far legs
        lion_leg(p, Mb, jx, -62, amp * math.sin(ph) * sgn + (st if jx < 0 else -st), LC['far'])
    lion_tail(p, Mb, t)
    p.poly(Mb, ell(0, -80, 92, 42, 56), LC['body'])
    p.line(Mb, ell(-8, -70, 62, 18, 30, 20, 160), "#b98a35", 2)   # belly line
    for jx, sgn in ((-62, -1), (52, 1)):                 # near legs
        lion_leg(p, Mb, jx, -62, amp * math.sin(ph) * sgn + (st if jx < 0 else -st), LC['body'])
    lion_head(p, Mb @ T(76, -108) @ R(po.get('head', 0)), po)

# ------------------------------------------------------------------ HARE puppet
RC = dict(body="#efe6d2", shade="#d3c6aa", pink="#e7a6a0", dark="#2b1a0e")

def hare_ear(p, Mh, bx, by, ang, col):
    Me = Mh @ T(bx, by) @ R(ang)
    p.poly(Me, ell(0, -26, 7.5, 27, 30), col)
    p.poly(Me, ell(0, -24, 3.5, 18, 20), RC['pink'], outline=None)

def draw_hare(p, M, po):
    t = po['t']
    Mr = M @ T(0, -po.get('hop', 0)) @ T(0, -30) @ R(po.get('tilt', 0)) @ T(0, 30)
    Mh = Mr @ T(22, -50) @ R(po.get('head', 0))
    e = po.get('ear', 0)
    hare_ear(p, Mh, 2, -18, -22 + e, RC['shade'])
    p.poly(Mr @ T(-14, -10) @ R(po.get('foot', 0)), ell(6, 3, 22, 8, 24), RC['shade'])
    p.poly(Mr, ell(-34, -40, 10, 10, 20), "white")
    p.poly(Mr, ell(0, -34, 33, 25, 40), RC['body'])
    Mf = Mr @ T(18, -22) @ R(po.get('fleg', 0))
    p.poly(Mf, [(-6, -4), (6, -4), (7, 18), (-6, 18)], RC['body'])
    p.poly(Mf, ell(2, 20, 8, 4.5, 16), RC['body'])
    p.poly(Mh, ell(10, -8, 19, 16, 32), RC['body'])
    hare_ear(p, Mh, 10, -20, -8 + e * 1.2, RC['body'])
    p.poly(Mh, ell(18, -12, 4.5, 5, 16), RC['dark'], outline=None)
    p.poly(Mh, ell(19.5, -14, 1.5, 1.5, 10), "white", outline=None)
    p.poly(Mh, ell(28, -6, 3, 2.5, 12), RC['pink'], outline=None)
    p.line(Mh, [(26, -2), (23, 1), (20, -1)], RC['dark'], 1)
    for wy in (-5, -1):
        p.line(Mh, [(27, wy), (40, wy - 3 + (wy + 3))], RC['dark'], 0.8)

# ------------------------------------------------------------------ WORLD painting
def cloud(p, M, x, y, s):
    circ = [(0, 0, 26), (30, -8, 30), (62, 0, 24), (18, 12, 20), (46, 12, 20)]
    for cx, cy, r in circ:
        p.poly(M, ell(x + cx * s, y + cy * s, (r + 3) * s, (r + 3) * s * 0.8, 28), "#6d8fb3", outline=None)
    for cx, cy, r in circ:
        p.poly(M, ell(x + cx * s, y + cy * s, r * s, r * s * 0.8, 28), "#fbf4e2", outline=None)
    curl = [(x + 30 * s + 10 * s * math.cos(a) * (1 - a / 9), y - 4 * s + 8 * s * math.sin(a) * (1 - a / 9))
            for a in np.linspace(0, 7, 20)]
    p.line(M, curl, "#6d8fb3", 1.5)

def hill(base, amp, seed, wl):
    xs = np.arange(0, WORLD_W + 20, 8)
    y = base - amp * (0.55 + 0.45 * np.sin(xs / wl + seed) * np.sin(xs / (wl * 0.41) + seed * 2))
    return list(zip(xs, y)) + [(WORLD_W + 20, H), (0, H)]

def cypress(p, M, x, base, h, w):
    pts_l, pts_r = [], []
    for k in range(25):
        u = k / 24
        wid = w * (math.sin(math.pi * min(1, u * 1.15)) ** 0.7) * (1 - u * 0.3)
        pts_l.append((x - wid, base - u * h)); pts_r.append((x + wid, base - u * h))
    p.poly(M, [(x - 4, base + 6), (x + 4, base + 6), (x + 4, base - 10), (x - 4, base - 10)], "#6b4226", w=1.5)
    p.poly(M, pts_l + pts_r[::-1], "#2f5e3e", outline="#1d3a26", w=2)
    for k in range(1, 7):
        yy = base - h * k / 7.5
        p.line(M, [(x - w * 0.35, yy + 8), (x, yy), (x + w * 0.35, yy + 8)], "#4f7f52", 1.5)

def blossom_tree(p, M, x, base, rng):
    p.poly(M, [(x - 7, base), (x + 7, base), (x + 4, base - 70), (x + 18, base - 110),
               (x + 10, base - 112), (x - 2, base - 80), (x - 16, base - 112), (x - 22, base - 108), (x - 5, base - 70)],
           "#6b4226", w=2)
    blobs = [(-30, -120, 32), (5, -140, 38), (36, -118, 30), (-8, -105, 28), (18, -100, 26)]
    for cx, cy, r in blobs:
        p.poly(M, ell(x + cx, base + cy + 0, r + 3, r + 3, 28), "#3e6533", outline=None)
    for cx, cy, r in blobs:
        p.poly(M, ell(x + cx, base + cy, r, r, 28), "#6c9a52", outline=None)
    for _ in range(26):
        a = rng.uniform(0, 2 * math.pi); r = rng.uniform(0, 40)
        bx, by = x + 3 + r * 1.3 * math.cos(a), base - 120 + r * 0.8 * math.sin(a)
        p.poly(M, ell(bx, by, 3.2, 3.2, 10), rng.choice(["#f2b8c6", "#fff5f0", "#e98aa5"]), outline=None)

def flower(p, M, x, y, col):
    for k in range(5):
        a = k * 2 * math.pi / 5
        p.poly(M, ell(x + 3.4 * math.cos(a), y + 3.4 * math.sin(a), 2.6, 2.6, 10), col, outline=None)
    p.poly(M, ell(x, y, 1.8, 1.8, 8), "#f3c94a", outline=None)

def build_world():
    ww, hh = WORLD_W * SS, H * SS
    g = np.linspace(0, 1, hh)[:, None]
    top, bot = np.array([229, 192, 112.]), np.array([249, 238, 208.])
    col = (top * (1 - g) + bot * g).astype(np.uint8)
    img = Image.fromarray(np.ascontiguousarray(np.broadcast_to(col[:, None, :], (hh, ww, 3))), 'RGB')
    p = Pen(img); M = S(SS); rng = np.random.default_rng(11)
    # gold sun with rays
    for k in range(16):
        a = math.radians(k * 22.5)
        p.poly(M, [(1050 + 40 * math.cos(a - 0.12), 120 + 40 * math.sin(a - 0.12)),
                   (1050 + 62 * math.cos(a), 120 + 62 * math.sin(a)),
                   (1050 + 40 * math.cos(a + 0.12), 120 + 40 * math.sin(a + 0.12))], "#e9a93a", outline=None)
    p.poly(M, ell(1050, 120, 40, 40), "#f2c14e", outline="#b9802a", w=2)
    for x in range(140, WORLD_W, 430):
        cloud(p, M, x + rng.uniform(-80, 80), rng.uniform(90, 200), rng.uniform(0.8, 1.2))
    for _ in range(14):
        bx, by = rng.uniform(0, WORLD_W), rng.uniform(170, 300)
        p.line(M, [(bx - 9, by - 4), (bx, by), (bx + 9, by - 5)], "#5a4a3a", 1.6)
    p.poly(M, hill(400, 75, 0.7, 210), "#d9b6a3", outline="#9c7a68", w=2)
    p.poly(M, hill(478, 58, 2.1, 150), "#b9ba86", outline="#7f8156", w=2)
    for _ in range(40):
        sx = rng.uniform(0, WORLD_W); sy = rng.uniform(470, 545)
        p.poly(M, ell(sx, sy, 12, 9, 18), "#6f8a4a", outline="#4a6131", w=1.2)
    for x in (140, 760, 1290, 1720, 2240, 3200):
        cypress(p, M, x + rng.uniform(-30, 30), 566, rng.uniform(200, 240), 26)
    for x in (470, 1500, 1980, 3000):
        blossom_tree(p, M, x + rng.uniform(-30, 30), 566, rng)
    gp = [(x, 560 + 6 * math.sin(x / 90)) for x in range(0, WORLD_W + 10, 10)] + [(WORLD_W + 10, H), (0, H)]
    p.poly(M, gp, "#93ad62", outline="#5f7a3a", w=2)
    path = ([(x, 588 + 3 * math.sin(x / 70)) for x in range(0, WORLD_W + 10, 10)] +
            [(x, 632 + 3 * math.sin(x / 55 + 1)) for x in range(WORLD_W, -10, -10)])
    p.poly(M, path, "#cdb684", outline=None)
    for _ in range(900):
        fx, fy = rng.uniform(0, WORLD_W), rng.uniform(570, 700)
        if 584 < fy < 636: continue
        if rng.random() < 0.55:
            p.line(M, [(fx - 3, fy), (fx, fy - 7), (fx + 3, fy)], "#5f7a3a", 1.2)
        else:
            flower(p, M, fx, fy, rng.choice(["#c8423a", "#fff7ea", "#3d6db5", "#d96f9a"]))
    # well (back parts)
    for px in (WELLX - 182, WELLX + 166):
        p.poly(M, [(px, 300), (px + 16, 300), (px + 16, GROUND - 6), (px, GROUND - 6)], "#7a4a26", w=2)
    p.poly(M, [(WELLX - 196, 292), (WELLX + 196, 292), (WELLX + 196, 308), (WELLX - 196, 308)], "#8a5a30", w=2)
    p.poly(M, [(WELLX - 34, 296), (WELLX + 34, 296), (WELLX + 34, 330), (WELLX - 34, 330)], "#a07040", w=2)
    for k in range(6):
        p.line(M, [(WELLX - 30 + k * 12, 298), (WELLX - 26 + k * 12, 328)], "#5e3a1c", 1.2)
    p.poly(M, ell(WELLX, RIMY, RIM_RX, RIM_RY, 64), "#bca78a", w=3)
    for k in range(18):
        a = math.radians(k * 20 + 5)
        p.line(M, [(WELLX + WAT_RX * math.cos(a), RIMY + WAT_RY * math.sin(a)),
                   (WELLX + RIM_RX * math.cos(a), RIMY + RIM_RY * math.sin(a))], "#8c7556", 1.3)
    p.poly(M, ell(WELLX, RIMY, WAT_RX, WAT_RY, 64), "#2a5b85", outline="#1b3a55", w=2)
    for dx, dy, r in ((-60, -8, 26), (40, 6, 34), (-10, 12, 18)):
        p.line(M, ell(WELLX + dx, RIMY + dy, r, r * 0.25, 16, 200, 340), "#5c8fb8", 1.5)
    return img

def build_well_front():
    x0, y0 = WELLX - RIM_RX - 10, RIMY - 5
    img = Image.new('RGBA', ((2 * RIM_RX + 20) * SS, (GROUND + 40 - y0) * SS), (0, 0, 0, 0))
    p = Pen(img); M = S(SS) @ T(-x0, -y0)
    top = ell(WELLX, RIMY + 12, RIM_RX, RIM_RY, 40, 0, 180)
    bottom = ell(WELLX, GROUND - 10, RIM_RX, RIM_RY * 0.7, 40, 180, 0)
    p.poly(M, top + bottom, "#c9b493", w=3)
    ty0, ty1 = 52, 72        # turquoise tile band
    p.poly(M, ell(WELLX, RIMY + ty0, RIM_RX - 1, RIM_RY * 0.9, 40, 0, 180) +
           ell(WELLX, RIMY + ty1, RIM_RX - 1, RIM_RY * 0.86, 40, 180, 0), "#2f8f9d", outline="#1d5f6a", w=1.5)
    for a in np.linspace(12, 168, 14):
        r = math.radians(a)
        cx = WELLX + (RIM_RX - 1) * math.cos(r); cy = RIMY + (ty0 + ty1) / 2 + RIM_RY * 0.88 * math.sin(r)
        p.poly(M, [(cx, cy - 5), (cx + 4, cy), (cx, cy + 5), (cx - 4, cy)], "#f4ead0", outline=None)
    rows = [12, 32, 52, 72, 96, 120]
    for i, d in enumerate(rows):
        if d not in (52, 72):
            p.line(M, ell(WELLX, RIMY + d, RIM_RX, RIM_RY * (1 - 0.3 * d / 130), 40, 0, 180), "#8c7556", 1.5)
        if i + 1 < len(rows) and d != 52:
            nxt = rows[i + 1]
            for a in np.linspace(18, 162, 7) + (10 if i % 2 else 0):
                r = math.radians(a)
                x = WELLX + RIM_RX * math.cos(r)
                y1 = RIMY + d + RIM_RY * (1 - 0.3 * d / 130) * math.sin(r)
                p.line(M, [(x, y1), (x, y1 + (nxt - d) * 0.92)], "#8c7556", 1.2)
    p.poly(M, ell(WELLX, RIMY, RIM_RX, RIM_RY, 40, 0, 180) + ell(WELLX, RIMY + 12, RIM_RX, RIM_RY, 40, 180, 0),
           "#dccaa8", w=2.5)
    return img, (x0, y0)

def build_border():
    im = Image.new('RGBA', (W * SS, H * SS), (28, 52, 99, 255))
    d = ImageDraw.Draw(im); b = 24
    d.rectangle([b * SS, b * SS, (W - b) * SS - 1, (H - b) * SS - 1], fill=(0, 0, 0, 0))
    gold = (212, 166, 60, 255)
    d.rectangle([3 * SS, 3 * SS, (W - 3) * SS - 1, (H - 3) * SS - 1], outline=gold, width=2 * SS)
    d.rectangle([(b - 3) * SS, (b - 3) * SS, (W - b + 3) * SS - 1, (H - b + 3) * SS - 1], outline=gold, width=2 * SS)
    p = Pen(im); M = S(SS)
    dia = lambda x, y: [(x, y - 5), (x + 5, y), (x, y + 5), (x - 5, y)]
    for x in range(44, W - 30, 36):
        for y in (12, H - 12): p.poly(M, dia(x, y), gold, outline=None)
    for y in range(44, H - 30, 36):
        for x in (12, W - 12): p.poly(M, dia(x, y), gold, outline=None)
    for x, y in ((12, 12), (W - 12, 12), (12, H - 12), (W - 12, H - 12)):
        p.poly(M, khatam(x, y, 11), gold, outline=None)
    return im

def build_card_bg():
    im = Image.new('RGBA', (W * SS, H * SS), (21, 48, 90, 255))
    p = Pen(im); M = S(SS)
    for yy in range(0, H + 120, 120):
        for xx in range(0, W + 120, 120):
            ox = 60 if (yy // 120) % 2 else 0
            p.poly(M, khatam(xx + ox, yy, 34), None, outline=(36, 70, 122, 255), w=2)
    return im

def text_img(s, font_path, size, fill, stroke=0, stroke_fill=OUT):
    f = ImageFont.truetype(font_path, size * SS)
    l, t, r, b = f.getbbox(s, stroke_width=stroke * SS)
    im = Image.new('RGBA', (r - l + 4, b - t + 4), (0, 0, 0, 0))
    ImageDraw.Draw(im).text((-l + 2, -t + 2), s, font=f, fill=fill,
                            stroke_width=stroke * SS, stroke_fill=stroke_fill)
    return im

def put_text(fr, im, cx, cy, alpha):
    if alpha <= 0.01: return
    if alpha < 1:
        im = im.copy(); a = im.getchannel('A').point(lambda v: int(v * alpha)); im.putalpha(a)
    fr.alpha_composite(im, dest=(int(cx * SS - im.width / 2), int(cy * SS - im.height / 2)))

ASSETS = {}
def init_assets():
    ASSETS['world'] = build_world()
    ASSETS['well'], ASSETS['well_xy'] = build_well_front()
    ASSETS['border'] = build_border()
    ASSETS['card'] = build_card_bg()
    gold, cream = (226, 182, 74, 255), (250, 240, 214, 255)
    ASSETS['subs'] = [(a, b, text_img(s, FB, 29, cream, 3, (40, 24, 10, 255))) for a, b, s in SUBS]
    ASSETS['t1'] = text_img("KALILA & DIMNA", FB, 60, gold, 2, (90, 60, 12, 255))
    ASSETS['t2'] = text_img("The Lion and the Hare", FI, 40, cream)
    ASSETS['t3'] = text_img("—  Episode 1  —", FR, 24, gold)
    ASSETS['e1'] = text_img("Next time", FI, 30, cream)
    ASSETS['e2'] = text_img("The Monkey and the Tortoise", FB, 50, gold, 2, (90, 60, 12, 255))
    ASSETS['e3'] = text_img("KALILA & DIMNA", FR, 24, cream)
    ASSETS['hare_env'] = speech_env_frames({"h0", "h1", "h2", "h3"})
    ASSETS['lion_env'] = speech_env_frames({"l1", "l2", "l3"})
    rng = np.random.default_rng(7)
    ASSETS['drops'] = [(rng.uniform(-70, 70), rng.uniform(-170, 170), rng.uniform(-500, -230), rng.uniform(4, 8))
                       for _ in range(40)]

# ------------------------------------------------------------------ VOICE-OVER (Kokoro neural TTS)
TTS_DIR = os.path.join(HERE, "tts")
HARE_PITCH = 1.12            # hare lines are pitched up -> small, cute voice
LION_PITCH = 0.86            # lion lines are pitched down -> big, deep voice
VO = [  # (clip, start second, subtitle text)
    ("title", 1.2, "Kalila and Dimna. The Lion and the Hare."),
    ("n1", 5.9, "Long ago, in a green forest, there lived a big, cruel lion."),
    ("n2", 11.5, "Every day, one animal had to go to him… to become his dinner."),
    ("h1", 15.8, "“Oh, great King! Another lion has stolen your lunch!”"),
    ("h2", 20.0, "“He is hiding in a deep well. Come, I’ll show you!”"),
    ("n3", 24.0, "So the clever little hare led the lion through the forest, all the way to an old well."),
    ("n4", 30.6, "The lion looked down into the water… and saw a fierce lion, staring right back at him!"),
    ("n5", 36.3, "With a mighty roar, he leapt in to fight… his own reflection!"),
    ("n6", 40.6, "And so, the little hare saved the whole forest. Because wisdom is stronger than strength."),
    ("end", 47.3, "Next time: The Monkey and the Tortoise."),
]

def load_clip(name, sr_out):
    import soundfile as sf
    a, sr = sf.read(os.path.join(TTS_DIR, name + ".wav"), dtype='float32')
    if a.ndim > 1: a = a.mean(1)
    factor = (HARE_PITCH if name.startswith("h") else LION_PITCH if name.startswith("l") else 1.0) * sr / sr_out
    n = int(len(a) / factor)
    return np.interp(np.arange(n) * factor, np.arange(len(a)), a)

# Dialogue lines inserted into the story. While a line plays, the story clock "holds"
# (characters keep breathing / talking, but the plot pauses), so the timeline adapts to the voices.
INSERTS = [  # (story time, clip, pad before, pad after, text)
    (11.35, "l1", 0.2, 0.4, "LION: “I am the king of this forest! Bring me my dinner!”"),
    (15.65, "h0", 0.1, 0.3, "HARE: “Oh no… today it’s my turn.”"),
    (19.75, "l2", 0.15, 0.4, "LION: “Another lion? In MY forest?! Show me where he is!”"),
    (35.75, "l3", 0.1, 0.3, "LION: “You there! Get out of my forest!”"),
    (40.1, "h3", 0.1, 0.2, "HARE: “Hooray! The forest is free!”"),
]
INS = [(p, pb + len(load_clip(c, 1000)) / 1000 + pa, c, pb, txt) for p, c, pb, pa, txt in INSERTS]
def sh(ts):            # story time -> real time
    return ts + sum(d for p, d, *_ in INS if p < ts)
def story(tr):         # real time -> story time (frozen during inserted dialogue)
    off = 0.0
    for p, d, *_ in INS:
        if tr < p + off: break
        if tr < p + off + d: return p
        off += d
    return tr - off
VO_ALL = sorted([(n, sh(st), txt) for n, st, txt in VO] + [(c, sh(p) + pb, txt) for p, d, c, pb, txt in INS],
                key=lambda v: v[1])
DUR = sh(50.5)
NF = int(DUR * FPS)

def speech_env_frames(names):
    """per-frame loudness (0..1) of the given voice clips — drives the hare's talking animation"""
    e = np.zeros(NF + 1)
    for name, st, _ in VO_ALL:
        if name not in names: continue
        a = load_clip(name, FPS * 100)
        for i in range(len(a) // 100):
            fi = int(st * FPS) + i
            if fi <= NF: e[fi] = np.abs(a[i * 100:(i + 1) * 100]).mean()
    return np.clip(e / (e.max() + 1e-9) * 1.6, 0, 1)

def write_srt(path):
    def ts(x):
        ms = int(round(x * 1000)); return f"{ms//3600000:02d}:{ms//60000%60:02d}:{ms//1000%60:02d},{ms%1000:03d}"
    with open(path, "w", encoding="utf-8") as f:
        for i, (name, st, txt) in enumerate(VO_ALL, 1):
            dur = len(load_clip(name, 1000)) / 1000
            f.write(f"{i}\n{ts(st)} --> {ts(st + dur + 0.3)}\n{txt}\n\n")

# ------------------------------------------------------------------ TIMELINE (the "direction")
def lion_x(t): return 420 if t < 23.6 else 420 + (2440 - 420) * sm(23.6, 30.0, t)
def cam_x(t):
    c = 2060 * sm(23.6, 30.2, t)
    c += 5 * math.sin(t * 43) * env(t, 9.8, 11.3, 0.2, 0.4) + 6 * math.sin(t * 47) * env(t, 38.6, 39.4, 0.05, 0.5)
    return c

def lion_state(t, tr=None):
    tr = t if tr is None else tr
    po = dict(t=tr, walk=0, amp=0, head=0, mouth=0, angry=0.5, shake=0, stretch=0)
    x = lion_x(t); y = GROUND; lean = 0; rot = 0; vis = True; mask = False
    spd = abs(lion_x(t + 0.02) - lion_x(t - 0.02)) / 0.04
    k = clamp(spd / 120)
    po['walk'] = (x - 420) / 30.0; po['amp'] = 24 * k
    po['head'] = 3 * math.sin(po['walk'] * 2) * k
    e = env(t, 9.8, 11.3, 0.25, 0.4)                      # first roar
    po['mouth'] = e; po['head'] -= 14 * e; po['shake'] = e; po['angry'] = 0.5 + 0.5 * e
    if 14.8 < t < 30: po['head'] += 6 * sm(14.8, 15.4, t) * (1 - sm(23.4, 23.8, t))   # looks down at the hare
    e2 = env(t, 18.9, 19.7, 0.15, 0.3)                    # "another lion?!"
    po['mouth'] = max(po['mouth'], 0.6 * e2); po['shake'] = max(po['shake'], e2)
    if t > 17.0: po['angry'] = 1.0
    sp = ASSETS['lion_env'][min(NF, int(tr * FPS))]          # the lion talks: jaw follows his voice
    if sp > 0.02:
        po['mouth'] = max(po['mouth'], 0.85 * sp); po['head'] -= 6 * sp; po['angry'] = 1.0
    if t >= 30.0:                                         # peers into the well
        l = sm(30.0, 30.8, t) * (1 - sm(37.2, 37.6, t))
        lean = 18 * l; po['head'] += 16 * l
        e3 = env(t, 35.8, 36.9, 0.15, 0.3)
        po['mouth'] = max(po['mouth'], e3); po['shake'] = max(po['shake'], e3)
    if t >= 37.6:                                         # the leap
        u = clamp((t - 37.6) / 1.15)
        x = 2440 + 290 * u
        y = GROUND * (1 - u) + (RIMY + 260) * u - 4 * 200 * u * (1 - u)
        rot = -18 + 80 * u
        po['stretch'] = 32 * math.sin(math.pi * min(1, u * 1.3)); po['mouth'] = 0.5
        mask = u > 0.3; vis = u < 1
    return x, y, lean, rot, po, vis, mask

def hare_state(t, tr=None):
    tr = t if tr is None else tr
    po = dict(t=t, hop=0, tilt=0, foot=0, fleg=0, head=0, ear=0)
    vis = t >= 12.0
    if t < 14.8:
        x = 1380 - (1380 - 780) * sm(12.0, 14.8, t); face = -1; moving = t < 14.65
    elif t < 23.6:
        x = 780; face = -1 if t < 23.2 else 1; moving = False
    elif t < 30:
        x = 780 + (2950 - 780) * sm(23.6, 29.4, t); face = 1 if t < 29.6 else -1; moving = t < 29.3
    else:
        x = 2950; face = -1 if t < 43.4 else 1; moving = False
    def hop(ph, h):
        po['hop'] = h * math.sin(math.pi * ph); po['tilt'] = -10 * math.cos(math.pi * ph)
        po['foot'] = 28 * math.sin(math.pi * ph); po['fleg'] = -30 * math.sin(math.pi * ph)
        po['ear'] = 10 * math.sin(math.pi * ph)
    if moving: hop((t % 0.42) / 0.42, 30)
    if 14.8 < t < 15.6: x += 1.6 * math.sin(t * 70); po['ear'] = 14      # trembling
    sp = ASSETS['hare_env'][min(NF, int(tr * FPS))]                      # talking, driven by the voice
    if sp > 0.02:
        po['head'] = 7 * sp * math.sin(tr * 11); po['ear'] = 4 * sp + 9 * sp * math.sin(tr * 7)
    if 22.6 < t < 23.0: hop((t - 22.6) / 0.4, 22)
    if 37.4 < t < 39.6: po['ear'] = -12; po['head'] = -8 + 3 * math.sin(t * 20) * env(t, 38.6, 39.5, .05, .3)
    if 40.2 < t < 46.0: hop(((t - 40.2) % 0.5) / 0.5, 34)
    return x, face, po, vis

# ------------------------------------------------------------------ FRAME rendering
def draw_reflection(fr, t, cam, tr):
    a = sm(31.4, 32.2, t) * (1 - sm(38.2, 38.6, t))
    if a <= 0: return
    bw, bh = 2 * WAT_RX * SS, 2 * WAT_RY * SS
    tmp = Image.new('RGBA', (bw, bh), (0, 0, 0, 0)); p = Pen(tmp)
    po = dict(lion_state(t, tr)[4])
    rip = 2.5 * math.sin(tr * 3.1)
    M = S(SS) @ T(WAT_RX + rip, WAT_RY + 3) @ S(0.42 * (1 + 0.03 * math.sin(t * 4)), -0.42) @ T(-16, 12)
    lion_head(p, M, po)
    arr = np.array(tmp).astype(np.float32)
    arr[..., :3] = arr[..., :3] * 0.72 + np.array([60, 110, 150]) * 0.28
    m = Image.new('L', (bw, bh), 0); ImageDraw.Draw(m).ellipse([6, 6, bw - 6, bh - 6], fill=255)
    arr[..., 3] *= (np.array(m) / 255.0) * 0.85 * a
    fr.alpha_composite(Image.fromarray(arr.astype(np.uint8), 'RGBA'),
                       dest=(int((WELLX - WAT_RX - cam) * SS), int((RIMY - WAT_RY) * SS)))

def draw_splash(p, t, cam):
    ts = 38.6
    if t < ts or t > 40.5: return
    dt = t - ts; V = S(SS) @ T(-cam, 0)
    water, white = np.array([42, 91, 133]), np.array([225, 242, 250])
    for k in range(3):
        d = dt - k * 0.25
        if 0 < d < 1.3:
            r = 20 + 112 * d / 1.3; al = 1 - d / 1.3
            c = tuple(int(v) for v in water * (1 - al) + white * al)
            pts = ap(V, ell(WELLX, RIMY, r, r * WAT_RY / WAT_RX, 40))
            p.d.line(pts + [pts[0]], fill=c, width=2 * SS)
    for ox, vx, vy, sz in ASSETS['drops']:
        x = WELLX + ox + vx * dt; y = RIMY + vy * dt + 0.5 * 1100 * dt * dt
        if y > RIMY + 10 and dt > 0.1: continue
        p.poly(V, ell(x, y, sz, sz * 1.3, 14), (190, 228, 244), outline=(44, 109, 148), w=1.5)

def scene_frame(t, tr):
    cam = round(cam_x(t) * SS) / SS
    cx = int(cam * SS)
    fr = ASSETS['world'].crop((cx, 0, cx + W * SS, H * SS)).convert('RGBA')
    VIEW = S(SS) @ T(-cam, 0)
    if 31.4 < t < 38.6: draw_reflection(fr, t, cam, tr)
    x, y, lean, rot, po, vis, mask = lion_state(t, tr)
    M = VIEW @ T(x, y) @ T(62, 0) @ R(lean) @ T(-62, 0) @ T(0, -80) @ R(rot) @ T(0, 80) @ S(LION_SCALE)
    if vis and mask:          # inside the leap: lion goes behind the well wall and is clipped by the water
        layer = Image.new('RGBA', fr.size, (0, 0, 0, 0))
        draw_lion(Pen(layer), M, po)
        layer.paste((0, 0, 0, 0), box=(int((WELLX - WAT_RX - cam) * SS), int(RIMY * SS),
                                       int((WELLX + WAT_RX - cam) * SS), H * SS))
        fr.alpha_composite(layer)
    wx0, wy0 = ASSETS['well_xy']
    if wx0 - cam < W:
        wf = ASSETS['well']; fr.paste(wf, (int((wx0 - cam) * SS), int(wy0 * SS)), wf)
    if vis and not mask:      # standing beside the well: lion is in front of it
        draw_lion(Pen(fr), M, po)
    p = Pen(fr)
    draw_splash(p, t, cam)
    hx, face, hpo, hvis = hare_state(t, tr)
    if hvis:
        draw_hare(p, VIEW @ T(hx, GROUND + 2) @ S(RABBIT_SCALE * face, RABBIT_SCALE), hpo)
    fr.alpha_composite(ASSETS['border'])
    return fr

def card_rosette(fr, t, cy):
    p = Pen(fr); M = S(SS) @ T(W / 2, cy)
    p.poly(M @ R(t * 12), khatam(0, 0, 78), "#d4a63c", outline="#8a6418", w=2)
    p.poly(M @ R(22.5 - t * 8), khatam(0, 0, 56), "#1d3f73", outline="#d4a63c", w=2)
    p.poly(M, ell(0, 0, 20, 20), "#d4a63c", outline="#8a6418", w=2)

def title_frame(t):
    fr = ASSETS['card'].copy()
    card_rosette(fr, t, 190)
    put_text(fr, ASSETS['t1'], W / 2, 330, sm(0.5, 1.3, t))
    put_text(fr, ASSETS['t2'], W / 2, 405, sm(1.1, 1.9, t))
    put_text(fr, ASSETS['t3'], W / 2, 465, sm(1.7, 2.5, t))
    fr.alpha_composite(ASSETS['border'])
    return fr

def end_frame(t):
    fr = ASSETS['card'].copy()
    card_rosette(fr, t, 190)
    put_text(fr, ASSETS['e1'], W / 2, 320, sm(47.0, 47.6, t))
    put_text(fr, ASSETS['e2'], W / 2, 385, sm(47.3, 47.9, t))
    put_text(fr, ASSETS['e3'], W / 2, 470, sm(47.6, 48.2, t))
    fr.alpha_composite(ASSETS['border'])
    return fr

def fade(t):
    if t < 5.5: return min(sm(0, 0.6, t), 1 - sm(4.9, 5.5, t))
    if t < 46.8: return min(sm(5.5, 6.1, t), 1 - sm(46.2, 46.8, t))
    return min(sm(46.8, 47.4, t), 1 - sm(49.8, 50.5, t))

def render(i):
    tr = i / FPS; t = story(tr)
    fr = title_frame(t) if t < 5.5 else (scene_frame(t, tr) if t < 46.8 else end_frame(t))
    img = fr.convert('RGB').resize((W, H), Image.LANCZOS)
    f = fade(t)
    if f < 0.999: img = Image.blend(Image.new('RGB', (W, H)), img, f)
    return img.tobytes()

# ------------------------------------------------------------------ AUDIO (synthesized)
SR = 44100
NOTES = {'D2': 73.42, 'A2': 110.0, 'C3': 130.81, 'D3': 146.83, 'F3': 174.61, 'G3': 196.0, 'A3': 220.0,
         'Bb3': 233.08, 'C4': 261.63, 'D4': 293.66, 'F4': 349.23, 'G4': 392.0, 'A4': 440.0,
         'Bb4': 466.16, 'C5': 523.25, 'D5': 587.33}
NOTES['Ek3'] = NOTES['D3'] * 2 ** (1.5 / 12)   # E-koron (quarter-flat): the soul of Shur
NOTES['Ek4'] = NOTES['D4'] * 2 ** (1.5 / 12)

def santur(f, dur=1.7, vel=1.0):
    t = np.arange(int(dur * SR)) / SR
    s = np.zeros_like(t)
    for k, (a, dec) in enumerate([(1, 2.0), (0.55, 2.8), (0.33, 3.8), (0.2, 5.0), (0.12, 6.5), (0.07, 8)], 1):
        inh = k * (1 + 0.0007 * k * k)
        for det in (-3.0, 3.0):
            s += a * np.sin(2 * np.pi * f * inh * t * (1 + det / 1731)) * np.exp(-dec * t)
    s *= np.minimum(1, t / 0.002)
    return s * vel / 6

def dum(dur=0.45):
    t = np.arange(int(dur * SR)) / SR
    f = 55 + 95 * np.exp(-t * 14)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 8)
def tak(dur=0.09, seed=1):
    t = np.arange(int(dur * SR)) / SR
    n = np.random.default_rng(seed).standard_normal(len(t))
    return np.diff(n, prepend=0) * np.exp(-t * 55) * 0.25

def roar(dur, amp=1.0, seed=5):
    n = int(dur * SR); t = np.arange(n) / SR
    wn = np.random.default_rng(seed).standard_normal(n)
    br = np.cumsum(wn); br -= np.convolve(br, np.ones(1500) / 1500, 'same'); br /= np.abs(br).max() + 1e-9
    f0 = 92 + 22 * np.sin(2 * np.pi * 0.9 * t) - 28 * t / dur
    saw = 2 * ((np.cumsum(f0) / SR) % 1) - 1
    g = (0.55 * saw + 0.9 * br) * (0.6 + 0.4 * np.sin(2 * np.pi * 29 * t))
    g = np.convolve(g, np.ones(14) / 14, 'same')
    e = np.minimum(1, t / 0.12) * np.exp(-1.4 * t / dur) * (1 - np.clip((t - dur + 0.25) / 0.25, 0, 1))
    return g * e * amp

def splash(dur=1.3):
    n = int(dur * SR); t = np.arange(n) / SR
    wn = np.random.default_rng(9).standard_normal(n)
    s = np.convolve(wn, np.ones(5) / 5, 'same') * np.exp(-t * 5) * 0.7
    for k in range(7):
        st = 0.15 + k * 0.11; m = (t > st) & (t < st + 0.07)
        tt = t[m] - st
        s[m] += 0.25 * np.sin(2 * np.pi * (500 + 900 * tt / 0.07 + k * 60) * tt) * np.exp(-tt * 30)
    return s

def build_audio(path):
    N = int(SR * DUR)
    mus = np.zeros(N); sfx = np.zeros(N); vo = np.zeros(N)
    def add(buf, start, sig, g=1.0, real=False):
        i = int((start if real else sh(start)) * SR); j = min(N, i + len(sig))
        if i < N: buf[i:j] += sig[:j - i] * g
    def seq(start, step, notes, vel=1.0, dur=1.7):
        for k, n in enumerate(notes):
            if n != '-': add(mus, start + k * step, santur(NOTES[n], dur), vel)
    def riz(start, end, note, vel=0.5, rate=0.075, swell=False):   # santur tremolo
        k = 0; tt = start
        while tt < end:
            v = vel * (0.4 + 0.6 * (tt - start) / (end - start) if swell else 1) * (0.8 + 0.2 * (k % 2))
            add(mus, tt, santur(NOTES[note], 0.5), v); tt += rate; k += 1
    t = np.arange(N) / SR
    drone = (np.sin(2 * np.pi * NOTES['D2'] * t) + 0.5 * np.sin(2 * np.pi * NOTES['A2'] * t)
             + 0.2 * np.sin(2 * np.pi * NOTES['D3'] * t)) * (0.85 + 0.15 * np.sin(2 * np.pi * 0.2 * t))
    dg = np.interp(t, [sh(x) for x in [0, 1.5, 5.5, 6.5, 15, 23.6, 30, 37.4, 38.7, 40, 48, 50.5]],
                   [0, .05, .05, .07, .07, .045, .06, .09, .02, .05, .05, 0])
    mus += drone * dg
    seq(0.5, 0.32, ["A3", "D4", "Ek4", "F4", "Ek4", "D4", "C4", "D4", "-", "F4", "G4", "A4", "G4", "F4", "Ek4", "D4"], 0.9)
    seq(6.0, 0.55, ["D3", "Ek3", "D3", "-", "F3", "Ek3", "D3", "-", "D3", "Ek3", "F3", "G3"], 1.0, 2.2)
    add(mus, 9.8, dum(), 0.9); add(mus, 10.9, dum(), 0.6)
    seq(12.6, 0.4, ["G3", "-", "F3", "Ek3", "D3", "-", "-"], 0.7, 2.0)
    seq(15.4, 0.25, ["D5", "C5", "Bb4", "A4", "Bb4", "A4", "G4", "A4", "F4", "G4", "A4", "-",
                     "A4", "Bb4", "C5", "D5", "C5", "A4", "-", "G4"], 0.6, 1.2)
    seq(20.2, 0.3, ["A4", "G4", "F4", "G4", "A4", "-", "Bb4", "A4", "G4", "-", "A4"], 0.5, 1.2)
    seq(23.6, 0.3, ["D4", "-", "F4", "Ek4", "D4", "-", "A3", "C4", "D4", "-", "F4", "G4", "A4", "-",
                    "G4", "F4", "Ek4", "-", "D4", "C4", "D4"], 0.9)
    for k in range(11):
        b0 = 23.6 + k * 0.6
        add(mus, b0, dum(), 0.55); add(mus, b0 + 0.3, tak(seed=k), 0.9); add(mus, b0 + 0.45, tak(seed=k + 50), 0.6)
    riz(30.0, 33.5, 'A3', 0.3, swell=True); riz(33.5, 37.4, 'Bb3', 0.4, swell=True)
    seq(37.6, 0.07, ["D4", "Ek4", "F4", "G4", "A4", "Bb4", "C5", "D5"], 0.7, 0.8)
    seq(38.15, 0.06, ["D5", "C5", "Bb4", "A4", "G4", "F4", "Ek4", "D4"], 0.7, 0.8)
    add(mus, 38.65, dum(0.8), 1.0)
    seq(40.0, 0.3, ["D4", "F4", "A4", "D5", "C5", "A4", "Bb4", "A4", "G4", "F4", "Ek4", "-"], 0.9)
    seq(43.6, 0.3, ["D4", "F4", "G4", "A4", "Bb4", "A4", "G4", "F4", "Ek4", "D4", "-", "-"], 0.8)
    riz(47.4, 48.4, 'D4', 0.4)
    for n in ("D3", "A3", "D4"): add(mus, 47.4, santur(NOTES[n], 2.0), 0.8)
    add(sfx, 9.8, roar(1.5), 0.9)
    add(sfx, 18.9, roar(0.8, seed=6), 0.5)
    add(sfx, 35.8, roar(1.1, seed=7), 0.8)
    add(sfx, 35.95, roar(1.1, seed=8), 0.35)
    add(sfx, 38.6, splash(), 1.0)
    for name, st, _ in VO_ALL: add(vo, st, load_clip(name, SR), real=True)
    rev = mus.copy()
    for dly, g in ((0.071, 0.32), (0.113, 0.24), (0.197, 0.17), (0.311, 0.11), (0.43, 0.07)):
        k = int(dly * SR); rev[k:] += mus[:-k] * g
    # duck the music while someone is speaking
    ve = np.convolve(np.abs(vo), np.ones(int(0.25 * SR)) / int(0.25 * SR), 'same')
    duck = 1 - 0.6 * np.clip(ve / (ve.max() * 0.15 + 1e-9), 0, 1)
    duck = np.convolve(duck, np.ones(int(0.2 * SR)) / int(0.2 * SR), 'same')
    rev = rev / (np.abs(rev).max() + 1e-9) * 0.55 * duck
    sfx = sfx / (np.abs(sfx).max() + 1e-9) * 0.6
    vo = vo / (np.abs(vo).max() + 1e-9) * 0.9
    k = int(0.013 * SR)
    L = rev + sfx + vo; Rr = np.r_[np.zeros(k), rev[:-k]] + sfx + vo
    st = np.stack([L, Rr], 1)
    st *= (np.minimum(1, t / 0.3) * np.clip((DUR - t) / 0.7, 0, 1))[:, None]
    pk = np.abs(st).max()
    if pk > 0.95: st *= 0.95 / pk
    with wave.open(path, 'wb') as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((st * 32767).astype(np.int16).tobytes())

# ------------------------------------------------------------------ main
if __name__ == "__main__":
    init_assets()
    if len(sys.argv) > 1 and sys.argv[1] == "stills":
        for ts in [float(x) for x in sys.argv[2:]]:
            Image.frombytes('RGB', (W, H), render(int(ts * FPS))).save(os.path.join(HERE, f"still_{ts:05.1f}.png"))
        sys.exit()
    wav = os.path.join(HERE, "audio.wav"); build_audio(wav)
    write_srt(os.path.join(HERE, "Kalila_Dimna_Ep1_Lion_and_Hare.en.srt"))
    out = os.path.join(HERE, "Kalila_Dimna_Ep1_Lion_and_Hare_v3_dialogue.mp4")
    ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
                           "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-i", wav,
                           "-c:v", "libx264", "-preset", "medium", "-crf", "19", "-pix_fmt", "yuv420p",
                           "-c:a", "aac", "-b:a", "160k", "-shortest", "-movflags", "+faststart", out],
                          stdin=subprocess.PIPE)
    with mp.get_context("fork").Pool(os.cpu_count()) as pool:
        for k, buf in enumerate(pool.imap(render, range(NF), chunksize=4)):
            ff.stdin.write(buf)
            if k % 120 == 0: print(f"frame {k}/{NF}", flush=True)
    ff.stdin.close(); ff.wait()
    print("done:", out)
