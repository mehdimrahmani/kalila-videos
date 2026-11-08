#!/usr/bin/env python3
"""Kalila & Dimna — Episode 4: The Crow and the Snake (~3.3 min).
Adapted from ep03/ep03.py (same timeline helper, hosts, cards, word card, LOOK pass, render + audio)."""
import os, sys, math, wave, subprocess
import numpy as np
from PIL import Image, ImageDraw, ImageFont, features
import multiprocessing as mp
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from kd_lib import *
import make_episode as ME
EP = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, EP)
from lines import LINES, NAMES_EN, NAMES_FA
FA = {k: fa for k, _, _, fa in LINES}

# ------------------------------------------------------------------ timeline
tl = Timeline(os.path.join(EP, "vo"))
tl.scene("tree_open", ["o1", "o2", "o3"], lead=1.2, tail=0.7)
tl.scene("title", [], lead=3.4, tail=0)
tl.scene("home", ["n1", 0.3, "m1"], lead=1.4, tail=0.6)
tl.scene("snake", ["n2", 0.3, "s1", 0.3, "n3", 0.4, "f1", 0.3, "s2"], lead=0.3, tail=1.4)
tl.scene("worry", ["m2", 0.3, "f2"], lead=0.3, tail=1.6)
tl.scene("jackal", ["n4", 0.3, "j1", 0.3, "j2", 0.3, "f3"], lead=1.6, tail=1.6)
tl.scene("garden", ["n5", 0.6, "n6", 0.4, "g1"], lead=0.8, tail=0.8)
tl.scene("chase", ["n7", 0.3, "f4"], lead=0.6, tail=1.0)
tl.scene("drop", ["n8", 0.4, "g2", 0.4, "s3", 0.3, "g3", 0.3, "s4", 0.4, "n9"], lead=0.8, tail=1.0)
tl.scene("hatch", ["n10", 0.3, "b1", 0.4, "m3"], lead=0.8, tail=1.6)
tl.scene("tree_close", ["c1", "c2", 0.4, "c3", "c4", 1.4, "c5"], lead=0.8, tail=1.0)
tl.scene("end", [], lead=4.6, tail=0)
DUR = tl.t
NF = int(DUR * FPS)
ENV = tl.envelopes(NF)
def spk(who, t): return ENV.get(who, np.zeros(NF + 1))[min(NF, max(0, int(t * FPS)))]
def SB(name): return [(a, b) for n, a, b in tl.scenes if n == name][0]
def cue(k): return tl.cue(k)
def cend(k): c = tl.cue(k); return c[1] + c[2]
def word_time(key, word, frac=0.0):
    k, st, d, _, txt = tl.cue(key)
    i = txt.lower().find(word.lower())
    return st + d * (max(i, 0) / len(txt)) * 0.97 + frac
def blink(t, off=0.0): return 1.0 if ((t + off) % 3.9) < 0.12 else 0.0
def lerp(a, b, u): return a + (b - a) * u

A = {}
GY = 640                     # ground line
TX = 640                     # the crows' tree trunk (centre)
NEST = (716, 292)            # nest centre on the branch
NS = 1.4                     # nest scale
HOLE = (566, 646)            # the snake's hole at the foot of the tree
MOM = (NEST[0] + 66, NEST[1] - 12); DAD = (NEST[0] - 70, NEST[1] - 12)     # crow feet on the nest rim

# ------------------------------------------------------------------ backgrounds
def sky(hh, ww, top=(236, 200, 120), bot=(250, 238, 206)):
    g = np.linspace(0, 1, hh)[:, None]
    col = (np.array(top, float) * (1 - g) + np.array(bot, float) * g).astype(np.uint8)
    return Image.fromarray(np.ascontiguousarray(np.broadcast_to(col[:, None, :], (hh, ww, 3))), 'RGB')

def hills(p, M, x1, base, amp, sd, wl, col, oc):
    xs = np.arange(0, x1 + 20, 8)
    y = base - amp * (0.55 + 0.45 * np.sin(xs / wl + sd) * np.sin(xs / (wl * 0.41) + sd * 2))
    p.poly(M, list(zip(xs, y)) + [(x1 + 20, H), (0, H)], col, outline=oc, w=2)

def sun(p, M, x, y):
    for k in range(16):
        a = math.radians(k * 22.5)
        p.poly(M, [(x + 40 * math.cos(a - 0.12), y + 40 * math.sin(a - 0.12)), (x + 62 * math.cos(a), y + 62 * math.sin(a)),
                   (x + 40 * math.cos(a + 0.12), y + 40 * math.sin(a + 0.12))], "#e9a93a", outline=None)
    p.poly(M, ell(x, y, 40, 40), "#f2c14e", outline="#b9802a", w=2)

def grass(p, M, rng, x0, x1, n, skip=None):
    for _ in range(n):
        fx, fy = rng.uniform(x0, x1), rng.uniform(GY - 50, 700)
        if skip and skip(fx, fy): continue
        if rng.random() < 0.6: p.line(M, [(fx - 3, fy), (fx, fy - 7), (fx + 3, fy)], "#5f7a3a", 1.2)
        else: flower(p, M, fx, fy, ["#c8423a", "#fff7ea", "#3d6db5", "#d96f9a"][rng.integers(4)])

def nest_back(p, M):
    p.poly(M, ell(0, 0, 62, 22, 30), "#8a5a2e", w=2.5)
    p.poly(M, ell(0, -4, 48, 12, 26), "#5a3a1c", outline=None)

def nest_front(p, M):
    p.poly(M, ell(0, 4, 64, 20, 30, 0, 180) + [(-64, 4)], "#9c6a3a", w=2.5)
    rng = np.random.default_rng(8)
    for k in range(14):
        x = -58 + k * 9 + rng.uniform(-3, 3)
        p.line(M, [(x - 8, 6 + rng.uniform(-3, 3)), (x + 10, 14 + rng.uniform(-4, 4))], "#6b4226", 1.6)

def build_tree_world():
    img = sky(H * SS, W * SS); p = Pen(img); V = S(SS); rng = np.random.default_rng(41)
    sun(p, V, 1110, 110)
    cloud(p, V, 180, 120, 0.9); cloud(p, V, 980, 210, 0.7)
    hills(p, V, W, 430, 70, 0.9, 220, "#d9b6a3", "#9c7a68")
    hills(p, V, W, 505, 55, 2.4, 150, "#b9ba86", "#7f8156")
    for x in (120, 1150, 1210):
        cypress(p, V, x, 580, rng.uniform(180, 220), 22)
    blossom_tree(p, V, 300, 586, rng); blossom_tree(p, V, 1000, 590, rng)
    gp = [(x, 592 + 6 * math.sin(x / 90)) for x in range(0, W + 10, 10)] + [(W + 10, H), (0, H)]
    p.poly(V, gp, "#93ad62", outline="#5f7a3a", w=2)
    # the tall plane tree (chenar)
    trunk = [(TX - 52, GY + 14), (TX + 56, GY + 14), (TX + 34, GY - 90), (TX + 28, 330), (TX + 140, 304), (TX + 142, 318),
             (TX + 36, 356), (TX + 30, 190), (TX + 70, 120), (TX + 56, 114), (TX + 12, 180), (TX - 20, 150), (TX - 120, 200),
             (TX - 124, 188), (TX - 28, 132), (TX - 30, 300), (TX - 36, GY - 90)]
    p.poly(V, trunk, "#7a4c2a", w=3)
    for k in range(9):
        yy = GY - 30 - k * 44
        p.line(V, [(TX - 18, yy), (TX - 2, yy - 10), (TX + 16, yy - 4)], "#4e2f18", 1.6)
    # roots
    for dx, s in ((-60, -1), (64, 1)):
        p.poly(V, [(TX + dx * 0.6, GY - 10), (TX + dx * 1.3, GY + 16), (TX + dx * 0.5, GY + 14)], "#7a4c2a", w=2)
    # the snake's hole between the roots
    p.poly(V, ell(HOLE[0], HOLE[1], 26, 13, 24), "#2a1c12", outline=OUT, w=2.5)
    # canopy: leaves above and around the branches (the nest stays visible)
    blobs = [(-250, 150, 70), (-170, 96, 80), (-60, 70, 86), (60, 66, 84), (170, 96, 78), (250, 150, 66),
             (-210, 210, 56), (220, 210, 52), (-110, 160, 60)]
    for cx, cy, r in blobs:
        p.poly(V, ell(TX + cx, cy, r + 4, r * 0.8 + 4, 40), "#3e6533", outline=None)
    for cx, cy, r in blobs:
        p.poly(V, ell(TX + cx, cy, r, r * 0.8, 40), "#6c9a52", outline=None)
    for _ in range(60):
        a = rng.uniform(0, 2 * math.pi); r = rng.uniform(0, 1) ** 0.6 * 250
        bx, by = TX + r * math.cos(a), 130 + r * 0.32 * math.sin(a)
        p.poly(V, ell(bx, by, 6, 3.5, 10), ["#9cc06a", "#4f7a3a", "#b6cf7a"][rng.integers(3)], outline=None)
    grass(p, V, rng, 0, W, 420, lambda x, y: 470 < x < 820 and y < 680)
    return img

def build_meadow_rocks():
    """the wise jackal's meadow: flat rocks, a pomegranate tree"""
    img = sky(H * SS, W * SS, (233, 190, 120), (250, 236, 204)); p = Pen(img); V = S(SS); rng = np.random.default_rng(7)
    sun(p, V, 160, 120); cloud(p, V, 620, 110, 0.8); cloud(p, V, 1020, 180, 0.9)
    hills(p, V, W, 420, 60, 1.6, 200, "#d9b6a3", "#9c7a68")
    hills(p, V, W, 500, 50, 0.3, 140, "#b9ba86", "#7f8156")
    cypress(p, V, 90, 580, 200, 22); cypress(p, V, 1200, 582, 180, 20)
    gp = [(x, 590 + 5 * math.sin(x / 80)) for x in range(0, W + 10, 10)] + [(W + 10, H), (0, H)]
    p.poly(V, gp, "#93ad62", outline="#5f7a3a", w=2)
    # a pomegranate tree on the left where the crow lands
    p.poly(V, [(330, GY + 10), (356, GY + 10), (350, 430), (390, 380), (384, 372), (344, 410), (336, 360), (326, 362), (334, 430),
               (300, 400), (294, 408), (330, GY - 140)], "#6b4226", w=2.5)
    for cx, cy, r in ((290, 360, 62), (360, 330, 70), (420, 366, 56), (330, 400, 48)):
        p.poly(V, ell(cx, cy, r + 3, r * 0.8 + 3, 36), "#3e6533", outline=None)
        p.poly(V, ell(cx, cy, r, r * 0.8, 36), "#5f8c47", outline=None)
    for x, y in ((280, 340), (330, 300), (402, 352), (350, 392), (440, 372), (300, 396)):
        p.poly(V, ell(x, y, 9, 9, 16), "#c8423a", outline="#7a1c14", w=1.5)
        p.poly(V, [(x - 3, y - 9), (x, y - 13), (x + 3, y - 9)], "#7a1c14", outline=None)
    # the jackal's flat rock
    p.poly(V, [(660, GY + 20), (680, GY - 30), (760, GY - 52), (930, GY - 46), (990, GY - 10), (1000, GY + 20)], "#b3a48e",
           outline=OUT, w=3)
    p.poly(V, [(700, GY - 30), (770, GY - 46), (900, GY - 40), (840, GY - 30)], "#cbbfa9", outline=None)
    grass(p, V, rng, 0, W, 400, lambda x, y: 640 < x < 1010 and y < 660)
    return img

POOL = (540, 600)            # necklace stone beside the pool
def build_garden():
    img = sky(H * SS, W * SS, (226, 196, 140), (248, 236, 210)); p = Pen(img); V = S(SS); rng = np.random.default_rng(3)
    cloud(p, V, 300, 100, 0.8); cloud(p, V, 900, 140, 0.7)
    # palace wall with tiled arches
    p.poly(V, [(0, 250), (W, 250), (W, 560), (0, 560)], "#e8d6b4", outline=OUT, w=2.5)
    p.poly(V, [(0, 236), (W, 236), (W, 256), (0, 256)], "#1d3f73", outline=OUT, w=2)
    for k in range(0, W, 46):
        p.poly(V, khatam(k + 23, 246, 7), "#e2b64a", outline=None)
    for x in (140, 400, 880, 1140):
        p.poly(V, ell(x, 400, 70, 110, 30, 180, 360) + [(x + 70, 560), (x - 70, 560)], "#2f6db0", outline=OUT, w=2.5)
        p.poly(V, ell(x, 404, 56, 96, 30, 180, 360) + [(x + 56, 560), (x - 56, 560)], "#173a66", outline=None)
        p.poly(V, khatam(x, 330, 14), "#e2b64a", outline="#8a6418", w=1)
    # big central dome-arch (iwan)
    p.poly(V, ell(640, 360, 120, 150, 36, 180, 360) + [(760, 560), (520, 560)], "#e2b64a", outline=OUT, w=3)
    p.poly(V, ell(640, 368, 100, 132, 36, 180, 360) + [(740, 560), (540, 560)], "#2f6db0", outline=None)
    for r in (60, 40):
        p.poly(V, khatam(640, 380, r * 0.6, r), ["#e2b64a", "#fff7ea"][r == 40], outline="#8a6418", w=1)
    for x in (40, 270, 1010, 1240):
        cypress(p, V, x, 584, rng.uniform(220, 260), 26)
    gp = [(0, 560), (W, 560), (W, H), (0, H)]
    p.poly(V, gp, "#93ad62", outline="#5f7a3a", w=2)
    # pool with a fountain
    p.poly(V, [(560, 586), (1040, 586), (1100, 650), (500, 650)], "#d8cdb6", outline=OUT, w=2.5)
    p.poly(V, [(574, 592), (1028, 592), (1080, 644), (520, 644)], "#5fa6c9", outline=None)
    for k in range(6):
        y = 600 + k * 8
        p.line(V, [(620 + 15 * k, y), (680 + 15 * k, y)], "#a9d6e8", 1.5)
    # the stone where the necklace lies
    p.poly(V, ell(POOL[0] - 30, POOL[1] + 30, 52, 20, 24), "#b3a48e", outline=OUT, w=2.5)
    for _ in range(140):
        fx, fy = rng.uniform(0, W), rng.uniform(660, 705)
        flower(p, V, fx, fy, ["#c8423a", "#fff7ea", "#3d6db5", "#d96f9a"][rng.integers(4)])
    return img

CW = 3000                    # chase world: garden wall at the left, open hills, the tree at the right
def build_chase_world():
    img = sky(H * SS, CW * SS); p = Pen(img); V = S(SS); rng = np.random.default_rng(19)
    for x in range(150, CW, 420):
        cloud(p, V, x + rng.uniform(-60, 60), rng.uniform(80, 200), rng.uniform(0.7, 1.0))
    hills(p, V, CW, 430, 70, 0.4, 230, "#d9b6a3", "#9c7a68")
    hills(p, V, CW, 505, 55, 1.9, 160, "#b9ba86", "#7f8156")
    p.poly(V, [(0, 340), (420, 340), (420, 590), (0, 590)], "#e8d6b4", outline=OUT, w=2.5)
    p.poly(V, [(0, 326), (432, 326), (432, 346), (0, 346)], "#1d3f73", outline=OUT, w=2)
    for x in (110, 300):
        p.poly(V, ell(x, 460, 50, 80, 24, 180, 360) + [(x + 50, 590), (x - 50, 590)], "#2f6db0", outline=OUT, w=2)
    for x in (600, 1100, 1700, 2200):
        blossom_tree(p, V, x, 590, rng)
    for x in (820, 1400, 1460, 2000, 2500):
        cypress(p, V, x, 584, rng.uniform(170, 220), 22)
    gp = [(x, 592 + 6 * math.sin(x / 90)) for x in range(0, CW + 10, 10)] + [(CW + 10, H), (0, H)]
    p.poly(V, gp, "#93ad62", outline="#5f7a3a", w=2)
    # the crows' tree far right (silhouette shape)
    big_tree(p, V, 2820, 600)
    grass(p, V, rng, 0, CW, 900)
    return img

def tint(img, rgb, amt):
    ov = Image.new('RGBA', img.size, rgb + (255,))
    return Image.blend(img, ov, amt)

# ------------------------------------------------------------------ Persian text
def find_pfont():
    for f in ["/usr/share/fonts/truetype/vazirmatn/Vazirmatn-Bold.ttf",
              os.path.join(os.path.dirname(EP), "fonts", "Vazirmatn-Bold.ttf"),
              "/usr/share/fonts/truetype/noto/NotoNaskhArabic-Bold.ttf",
              "/usr/share/fonts/opentype/noto/NotoNaskhArabic-Bold.ttf",
              "/usr/share/fonts/truetype/noto/NotoSansArabic-Bold.ttf",
              "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"]:
        if os.path.exists(f): return f
PFONT = find_pfont()

def fa_text(d, xy, s, size, fill):
    if features.check('raqm'):
        f = ImageFont.truetype(PFONT, size, layout_engine=ImageFont.Layout.RAQM)
        d.text(xy, s, font=f, fill=fill, anchor="mm", direction="rtl", language="fa")
    else:
        import arabic_reshaper
        from bidi.algorithm import get_display
        f = ImageFont.truetype(PFONT, size)
        d.text(xy, get_display(arabic_reshaper.reshape(s)), font=f, fill=fill, anchor="mm")

def build_word_card():
    w, h = 520, 210
    im = Image.new('RGBA', (w * SS, h * SS), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.rounded_rectangle([0, 0, w * SS - 1, h * SS - 1], radius=26 * SS, fill=(226, 182, 74, 255),
                        outline=(90, 60, 12, 255), width=4 * SS)
    d.rounded_rectangle([12 * SS, 12 * SS, (w - 12) * SS, (h - 12) * SS], radius=18 * SS, fill=(250, 240, 214, 255),
                        outline=(160, 112, 30, 255), width=2 * SS)
    p = Pen(im)
    for x in (52, w - 52):
        p.poly(S(SS), khatam(x, 105, 22), "#d4a63c", outline="#8a6418", w=1.5)
        p.poly(S(SS), khatam(x, 105, 13, 22.5), "#1d3f73", outline=None)
    f1 = ImageFont.truetype(FI, 21 * SS)
    d.text((w / 2 * SS, 36 * SS), "Persian word of the day", font=f1, fill=(120, 80, 20, 255), anchor="mm")
    fa_text(d, (w / 2 * SS, 98 * SS), "مار", 74 * SS, (28, 52, 99, 255))
    f2 = ImageFont.truetype(FB, 32 * SS)
    d.text((w / 2 * SS, 166 * SS), "maar  =  snake", font=f2, fill=(90, 50, 12, 255), anchor="mm")
    return im

def init():
    ME.init_assets()
    A['border'] = ME.ASSETS['border']; A['card'] = ME.ASSETS['card']
    A['tree'] = build_tree_set().convert('RGBA')
    A['home'] = build_tree_world().convert('RGBA')
    A['rocks'] = build_meadow_rocks().convert('RGBA')
    A['garden'] = build_garden().convert('RGBA')
    A['chase'] = build_chase_world()
    A['wcard'] = build_word_card()
    gold, cream = (226, 182, 74, 255), (250, 240, 214, 255)
    A['t1'] = text_img("KALILA & DIMNA", FB, 60, gold, 2, (90, 60, 12, 255))
    A['t2'] = text_img("The Crow and the Snake", FI, 46, cream)
    A['t3'] = text_img("—  Episode 4  —", FR, 24, gold)
    A['e1'] = text_img("Next time", FI, 30, cream)
    A['e2'] = text_img("The Heron and the Crab", FB, 46, gold, 2, (90, 60, 12, 255))
    A['e3'] = text_img("A new story every Saturday", FR, 26, cream)
    A['q'] = text_img("?", FB, 50, (250, 240, 214, 255), 3, (40, 24, 10, 255))
    A['bang'] = text_img("!", FB, 54, (200, 40, 30, 255), 3, (255, 255, 255, 255))
    A['idea'] = text_img("!", FB, 60, (226, 182, 74, 255), 3, (40, 24, 10, 255))
    A['plop'] = text_img("PLOP!", FB, 46, (200, 40, 30, 255), 3, (255, 255, 255, 255))
    A['swoosh'] = text_img("swoosh!", FI, 30, (90, 50, 12, 255))
    A['hiss'] = text_img("hsss...", FI, 28, (60, 90, 30, 255))
    A['crack'] = text_img("crack!", FB, 34, (200, 40, 30, 255), 3, (255, 255, 255, 255))
    A['shoo'] = text_img("Shoo!", FB, 40, (200, 40, 30, 255), 3, (255, 255, 255, 255))
    A['caw'] = text_img("Caw! Caw! Caw!", FB, 34, (250, 240, 214, 255), 3, (40, 24, 10, 255))

# ------------------------------------------------------------------ actors
def bird(p, V, kind, who, x, y, t, face=1, sc=1.2, fly=0, off=0.0, **kw):
    s = spk(who, t) if who else 0.0
    po = dict(t=t, mouth=s, blink=blink(t, off), look=0.4, fly=fly, flap=t * 12 + off, head=6 * s * math.sin(t * 9))
    hd = kw.pop('head', 0); po.update(kw); po['head'] += hd
    draw_bird(p, V @ T(x, y) @ S(sc * face, sc), kind, po)

def dad(p, V, x, y, t, face=1, **kw): bird(p, V, "crow", 'F', x, y, t, face, 1.5, off=0.0, **kw)
def mom(p, V, x, y, t, face=-1, **kw): bird(p, V, "crow_mom", 'M', x, y, t, face, 1.4, off=1.7, **kw)

def snake(p, V, pts, t, **kw):
    s = spk('S', t)
    po = dict(t=t, mouth=s, blink=blink(t, 0.9), look=0.4, width=17, brow=0.7, head=8 * s * math.sin(t * 7))
    hd = kw.pop('head', 0); po.update(kw); po['head'] += hd
    draw_snake(p, V, pts, po)

def guard(p, V, x, y, t, face=1, sc=1.0, who='G', **kw):
    s = spk(who, t) if who else 0.0
    po = dict(t=t, mouth=s, blink=blink(t, 1.1 + x * 0.001), look=0.4, head=4 * s * math.sin(t * 7), pal=GUARD, brow=0.4)
    hd = kw.pop('head', 0); po.update(kw); po['head'] += hd
    draw_hunter(p, V @ T(x, y) @ S(sc * face, sc), po)

def eggs(p, V, t, n=3, crack=0.0, wob=0.0):
    for k in range(n):
        x = NEST[0] + (-24 + 24 * k) * NS; y = NEST[1] - 8 * NS
        a = wob * 8 * math.sin(t * 10 + k * 2)
        M = V @ T(x, y) @ R(a) @ S(NS)
        p.poly(M, ell(0, -10, 11, 14, 20), "#bcd6c4", outline=OUT, w=1.8)
        for q in ((-4, -14), (3, -6), (5, -18)):
            p.poly(M, ell(q[0], q[1], 1.8, 1.4, 8), "#6f8f7a", outline=None)
        if crack > 0:
            p.line(M, [(-10, -12), (-5, -8), (-1, -14), (4, -8), (10, -12)], OUT, 1.6)

# ------------------------------------------------------------------ scenes
KX, DX, HS = 420, 850, 1.32
def tree_frame(name, t):
    fr = A['tree'].copy(); p = Pen(fr); V = S(SS)
    kpo = jackal_pose('kalila', t, spk('K', t), look=0.6)
    dpo = jackal_pose('dimna', t, spk('D', t), look=0.6)
    if name == "tree_close":
        c3 = cue('c3')
        if c3[1] < t < c3[1] + 1.0: dpo['hop'] = 30 * abs(math.sin(math.pi * (t - c3[1]) / 0.5))
    if name == "tree_open":
        o2 = cue('o2')
        if o2[1] < t < cend('o2'): kpo['head'] += 10 * abs(math.sin(t * 9))          # peck, peck, peck
    draw_jackal(p, V @ T(DX, 640) @ S(-HS, HS), 'dimna', dpo)
    bush(p, V, 1125, 650, 1.35, 0)
    draw_jackal(p, V @ T(KX, 640) @ S(HS), 'kalila', kpo)
    if name == "tree_close":
        a0, a1 = cue('c3')[1] - 0.3, cend('c4') + 1.2
        al = min(sm(a0, a0 + 0.5, t), 1 - sm(a1 - 0.4, a1, t))
        if al > 0:
            sc = 0.85 + 0.15 * sm(a0, a0 + 0.5, t)
            card = A['wcard'] if sc > 0.999 else A['wcard'].resize((int(A['wcard'].width * sc), int(A['wcard'].height * sc)), Image.LANCZOS)
            put_text(fr, card, W / 2 + 20, 165, al)
        # a crow flies by during the moral
        c2 = cue('c2'); u = (t - c2[1]) / 4.0
        if 0 < u < 1:
            draw_bird(p, V @ T(lerp(-80, 1380, u), 300 - 60 * math.sin(math.pi * u)) @ S(0.9), "crow",
                      dict(t=t, fly=1, flap=t * 12))
    return fr

def card_frame(t, which):
    a, b = SB(which); lt = t - a
    fr = A['card'].copy()
    ME.card_rosette(fr, t, 190 if which == "title" else 200)
    if which == "title":
        put_text(fr, A['t1'], W / 2, 330, sm(0.2, 0.9, lt))
        put_text(fr, A['t2'], W / 2, 410, sm(0.6, 1.3, lt))
        put_text(fr, A['t3'], W / 2, 470, sm(1.0, 1.7, lt))
    else:
        put_text(fr, A['e1'], W / 2, 330, sm(0.2, 0.8, lt))
        put_text(fr, A['e2'], W / 2, 395, sm(0.5, 1.1, lt))
        put_text(fr, A['e3'], W / 2, 480, sm(0.9, 1.5, lt))
    return fr

def nest_scene(fr, t, eggs_n=3, crack=0.0, wob=0.0):
    p = Pen(fr); V = S(SS)
    nest_back(p, V @ T(*NEST) @ S(NS))
    eggs(p, V, t, eggs_n, crack, wob)
    return p, V

def home_frame(t):
    a, b = SB("home")
    fr = A['home'].copy(); p = Pen(fr); V = S(SS)
    nest_back(p, V @ T(*NEST) @ S(NS))
    # the parents fly in and land on the rim; the eggs appear while the narrator says "three little eggs"
    u = sm(a, a + 2.4, t)
    dad(p, V, lerp(-60, DAD[0], u), lerp(140, DAD[1], u) - 60 * math.sin(math.pi * u), t, face=1, fly=u < 0.97)
    egg_t = word_time('n1', 'three')
    if t > egg_t:
        eggs(p, V, t, 3, wob=env(t, egg_t, egg_t + 1.2, 0.1, 0.5))
    nest_front(p, V @ T(*NEST) @ S(NS))
    v = sm(a + 0.5, a + 3.0, t)
    mom(p, V, lerp(1340, MOM[0], v), lerp(120, MOM[1], v) - 50 * math.sin(math.pi * v), t, face=-1, fly=v < 0.97,
        look=-0.6, head=-14 * env(t, cue('m1')[1], cend('m1'), 0.3, 0.4),
        hop=6 * abs(math.sin(t * 7)) * env(t, cue('m1')[1], cend('m1'), 0.3, 0.3))
    if t > cue('m1')[1]:
        for j in range(5):                                      # little hearts of joy -> gold stars
            ph = ((t - cue('m1')[1]) * 0.4 + j / 5) % 1
            M = V @ T(NEST[0] - 60 + j * 30, NEST[1] - 50 - 120 * ph) @ R(t * 60) @ S(0.4 + 0.4 * math.sin(math.pi * ph))
            p.poly(M, khatam(0, 0, 10), "#f2c14e", outline="#b9802a", w=1)
    return fr

def climb_pts(u, t, peek=1.0):
    """snake path: out of the hole (u=0) and up the trunk towards the nest (u=1)"""
    # head travels along a fixed spine; the body follows the same spine behind it
    spine = [(HOLE[0], HOLE[1] + 4), (HOLE[0] + 10, GY - 20), (TX - 30, GY - 120), (TX - 34, 520), (TX - 26, 440),
             (TX - 32, 380), (TX - 20, 350), (NEST[0] - 96, 318)]
    sp = np.array(spine, float)
    seg = np.r_[0, np.cumsum(np.linalg.norm(np.diff(sp, axis=0), axis=1))]
    total = seg[-1]
    head_s = 70 + (total - 70) * u
    L = 300; n = 40
    pts = []
    for i in range(n + 1):
        s_ = head_s - L * i / n
        s_ -= 60 * (1 - peek)
        if s_ < 0:
            pts.append((HOLE[0], HOLE[1] + 6 - min(0, s_) * 0.0)); continue
        x = np.interp(s_, seg, sp[:, 0]); y = np.interp(s_, seg, sp[:, 1])
        k = min(len(seg) - 2, np.searchsorted(seg, s_) - 1)
        d = sp[k + 1] - sp[k]; d /= np.linalg.norm(d) + 1e-9
        w = 8 * math.sin(s_ / 40 - t * 6)
        pts.append((x - d[1] * w, y + d[0] * w))
    # keep only the part out of the hole
    vis = [q for q in pts if not (abs(q[0] - HOLE[0]) < 1 and q[1] >= HOLE[1] + 5)]
    return vis

def snake_frame(t):
    a, b = SB("snake")
    fr = A['home'].copy(); p = Pen(fr); V = S(SS)
    nest_back(p, V @ T(*NEST) @ S(NS)); eggs(p, V, t, 3)
    s1 = cue('s1'); n3 = cue('n3'); f1 = cue('f1'); s2 = cue('s2')
    # out of the hole during s1, up the trunk during n3, stopped by dad during f1, back down after s2
    peek = sm(s1[1] - 0.8, s1[1] + 0.6, t)
    up = sm(n3[1] + 0.5, cend('n3') + 0.6, t) * 0.92
    down = sm(cend('s2') - 0.4, b - 0.1, t)
    u = up - 0.92 * down * (up > 0.5)
    if peek > 0:
        pts = climb_pts(max(u, 0.0), t if down < 0.01 else -t, peek)
        if len(pts) > 3:
            snake(p, V, pts, t, scared=0.6 * env(t, f1[1], f1[1] + 1.5, 0.1, 0.5), brow=0.9,
                  look=-0.3 if t > f1[1] else 0.6)
        if s1[1] < t < cend('s1') + 0.5:
            put_text(fr, A['hiss'], HOLE[0] - 90, HOLE[1] - 90, env(t, s1[1], cend('s1') + 0.5, 0.2, 0.3))
    nest_front(p, V @ T(*NEST) @ S(NS))
    # father crow flaps and squawks at the snake
    att = env(t, f1[1] - 0.3, cend('f1') + 0.4, 0.3, 0.5)
    dad(p, V, DAD[0] - 40 * att, DAD[1] + 40 * att, t, face=-1 if att > 0.1 else 1, fly=att > 0.1, look=0.8,
        head=12 * att, brow=1)
    mom(p, V, MOM[0], MOM[1], t, face=-1, look=0.8, head=10 * sm(n3[1], n3[1] + 1, t),
        wing=-30 * abs(math.sin(t * 6)) * env(t, n3[1] + 2, cend('s2'), 0.3, 0.3))
    if f1[1] < t < cend('f1') + 0.4:
        put_text(fr, A['bang'], DAD[0] - 70, DAD[1] - 110, env(t, f1[1], cend('f1') + 0.4, 0.15, 0.3))
    return fr

def worry_frame(t):
    a, b = SB("worry")
    fr = A['home'].copy(); p = Pen(fr); V = S(SS)
    nest_back(p, V @ T(*NEST) @ S(NS)); eggs(p, V, t, 3); nest_front(p, V @ T(*NEST) @ S(NS))
    m2 = cue('m2'); f2 = cue('f2')
    sad = sm(a, m2[1], t)
    mom(p, V, MOM[0], MOM[1], t, face=-1, look=-0.8, head=-22 * sad + 4 * math.sin(t * 3) * spk('M', t), peck=0.25 * sad)
    leave = sm(cend('f2') + 0.1, b, t)
    dad(p, V, lerp(DAD[0], 1360, leave), lerp(DAD[1], 120, leave) - 40 * math.sin(math.pi * leave), t, face=1,
        fly=leave > 0.01, look=0.6, head=-8 * env(t, f2[1], cend('f2'), 0.3, 0.3))
    if f2[1] + 1.5 < t < cend('f2'):
        put_text(fr, A['idea'], DAD[0] + 10, DAD[1] - 120, env(t, f2[1] + 1.5, cend('f2'), 0.2, 0.3))
    return fr

def jackal_frame(t):
    a, b = SB("jackal")
    fr = A['rocks'].copy(); p = Pen(fr); V = S(SS)
    # the wise jackal on his rock, facing left towards the crow on the low branch
    jpo = jackal_pose('kalila', t, spk('J', t), look=0.5)
    jpo['wag'] = 0.3 + 0.4 * spk('J', t)
    j2 = cue('j2')
    jpo['head'] += -10 * env(t, j2[1], cend('j2'), 0.4, 0.4)
    draw_jackal(p, V @ T(830, GY - 44) @ S(-1.25, 1.25), 'wise', jpo)
    u = sm(a, a + 2.6, t)
    cx, cy = lerp(-80, 610, u), lerp(160, GY - 4, u) - 70 * math.sin(math.pi * u)
    f3 = cue('f3')
    dad(p, V, cx, cy, t, face=1, fly=u < 0.97, look=0.6,
        hop=10 * abs(math.sin(t * 8)) * env(t, f3[1], cend('f3'), 0.2, 0.3),
        head=-8 * env(t, cue('j1')[1], cend('j2'), 0.4, 0.4))
    if f3[1] + 1.0 < t < cend('f3') + 0.8:
        put_text(fr, A['idea'], 600, GY - 150, env(t, f3[1] + 1.0, cend('f3') + 0.8, 0.2, 0.3))
    # while the plan is told: a little thought bubble with the necklace
    al = env(t, j2[1] + 1.0, cend('j2') + 0.2, 0.4, 0.4)
    if al > 0.02:
        bub = Image.new('RGBA', fr.size, (0, 0, 0, 0)); q = Pen(bub)
        q.poly(V, ell(560, 250, 110, 70, 40), "#fffaf0", outline=OUT, w=2.5)
        for k, (x, y, r) in enumerate(((660, 330, 14), (700, 372, 9))):
            q.poly(V, ell(x, y, r, r, 16), "#fffaf0", outline=OUT, w=2)
        draw_necklace(q, V @ T(560, 250) @ S(1.6), t)
        put_text(fr, bub, W / 2, H / 2, al)
    return fr

def garden_frame(t):
    a, b = SB("garden")
    fr = A['garden'].copy(); p = Pen(fr); V = S(SS)
    n6 = cue('n6'); g1 = cue('g1')
    grab = word_time('n6', 'picked')
    swoop = sm(n6[1] - 0.6, grab, t)
    lift = sm(grab + 0.3, b, t)
    # necklace on the stone until the crow grabs it
    if t < grab:
        draw_necklace(p, V @ T(POOL[0] - 30, POOL[1] + 10), t)
    # the guard by the pool: idle, then points and shouts
    alarm = sm(g1[1] - 0.3, g1[1] + 0.2, t)
    guard(p, V, 900, GY + 36, t, face=-1, arm=10 - 120 * alarm, arm2=20, stick=-10 + 20 * alarm,
          look=-0.6 + 1.2 * alarm, brow=0.2 + 0.8 * alarm, hop=12 * abs(math.sin(t * 7)) * env(t, g1[1], cend('g1'), 0.2, 0.3))
    # the crow: circles above, swoops down, picks it up, flies up and away to the left slowly
    if t < n6[1] - 0.6:
        ang = (t - a) * 1.1
        cx, cy, f = 640 + 280 * math.cos(ang), 160 + 40 * math.sin(ang), (-1 if math.sin(ang) > 0 else 1)
    else:
        sx, sy = 640 + 280 * math.cos((n6[1] - 0.6 - a) * 1.1), 160 + 40 * math.sin((n6[1] - 0.6 - a) * 1.1)
        cx, cy = lerp(sx, POOL[0] - 34, swoop), lerp(sy, POOL[1] + 4, swoop)
        cx, cy = lerp(cx, 380, lift), lerp(cy, 230, lift)
        f = 1 if lift < 0.01 else -1
        if swoop > 0.95 and lift < 0.01: f = 1
    landed = swoop > 0.97 and lift < 0.02
    dad(p, V, cx, cy, t, face=f, fly=not landed, peck=0.8 * env(t, grab - 0.4, grab + 0.3, 0.2, 0.2), look=0.8)
    if t >= grab:
        bx = cx + f * 1.2 * 34; by = cy - 1.2 * 52 + (40 * 0.8 * env(t, grab - 0.4, grab + 0.3, 0.2, 0.2))
        draw_necklace(p, V @ T(bx, by), t, hang=1)
    if n6[1] < t < n6[1] + 1.6:
        put_text(fr, A['swoosh'], 470, 380, env(t, n6[1], n6[1] + 1.6, 0.2, 0.4))
    if g1[1] < t < cend('g1'):
        put_text(fr, A['bang'], 905, 320, env(t, g1[1], cend('g1'), 0.15, 0.3))
    return fr

def chase_frame(t):
    a, b = SB("chase"); lt = t - a
    cam = (CW - W) * sm(a, b - 0.2, t)
    cx = int(round(cam * SS))
    fr = A['chase'].crop((cx, 0, cx + W * SS, H * SS)).convert('RGBA'); p = Pen(fr); V = S(SS)
    # crow in screen space, flying right slowly and looking back
    f4 = cue('f4')
    bx, by = 660 + 40 * math.sin(lt * 0.8), 230 + 18 * math.sin(lt * 2.2)
    lookback = env(t, f4[1] - 0.2, cend('f4') + 0.2, 0.3, 0.3)
    dad(p, V, bx, by, t, face=1, fly=1, look=0.8 - 1.6 * lookback, head=-18 * lookback, flap=lt * 9)
    draw_necklace(p, V @ T(bx + 41, by - 62), t, hang=1)
    # two guards running behind (screen space), the second with a staff
    for k, (gx, sc) in enumerate(((330, 0.95), (180, 0.9))):
        ph = t * 9 + k * 1.7
        guard(p, V, gx + 30 * math.sin(lt * 0.9 + k), GY + 36, t, face=1, sc=sc, who=None, walk=ph, amp=1,
              arm=-70 - 30 * math.sin(ph) if k == 0 else -40, arm2=40 * math.sin(ph), lean=10, look=0.9,
              stick=-30 if k == 1 else None, hop=8 * abs(math.sin(ph)))
    return fr

PLOP = None
def drop_frame(t):
    a, b = SB("drop")
    fr = A['home'].copy(); p = Pen(fr); V = S(SS)
    nest_back(p, V @ T(*NEST) @ S(NS)); eggs(p, V, t, 3); nest_front(p, V @ T(*NEST) @ S(NS))
    mom(p, V, MOM[0], MOM[1], t, face=-1, look=-0.8, head=-14)
    n8 = cue('n8'); g2 = cue('g2'); s3 = cue('s3'); g3 = cue('g3'); s4 = cue('s4'); n9 = cue('n9')
    plop = word_time('n8', 'plop')
    # crow arrives from the left, hovers above the hole, drops the necklace, then flies to the nest
    u = sm(a, plop - 0.4, t)
    hx, hy = HOLE[0] + 20, 430
    cx, cy = lerp(-80, hx, u), lerp(220, hy, u)
    v = sm(plop + 0.6, plop + 2.6, t)
    cx, cy = lerp(cx, DAD[0], v), lerp(cy, DAD[1], v)
    dad(p, V, cx, cy, t, face=1 if v < 0.9 else 1, fly=v < 0.97, look=1.0 if v < 0.5 else 0.4,
        head=20 * env(t, plop - 0.5, plop + 0.8, 0.2, 0.3))
    if t < plop:
        draw_necklace(p, V @ T(cx + 41, cy - 62), t, hang=1)
    else:
        fu = clamp((t - plop) / 0.45)
        if fu < 1:
            draw_necklace(p, V @ T(lerp(hx + 41, HOLE[0], fu), lerp(hy - 62, HOLE[1] - 10, fu * fu)), t, hang=1)
        put_text(fr, A['plop'], HOLE[0], HOLE[1] - 110, env(t, plop + 0.3, plop + 1.6, 0.05, 0.4))
    # guards run in from the right and stop by the hole
    gu = sm(plop - 1.0, g2[1] + 0.2, t)
    g_leave = sm(cue('n9')[1] + 2.0, b, t)
    g1x = lerp(1400, 700, gu) + 700 * g_leave; g2x = lerp(1560, 880, gu) + 700 * g_leave
    walking = (0.01 < gu < 0.99) or g_leave > 0.01
    poke = env(t, g2[1] + 1.0, s3[1] + 0.6, 0.3, 0.3)
    jump = env(t, s3[1], s3[1] + 1.0, 0.1, 0.4)
    shoo = env(t, g3[1], cend('g3') + 0.3, 0.2, 0.4)
    gf = -1 if g_leave < 0.01 else 1
    guard(p, V, g2x, GY + 36, t, face=gf, sc=0.92, who=None, walk=t * 8 if walking else 0, amp=1 if walking else 0,
          look=-0.6, arm=-30 * shoo, hop=30 * jump)
    # the necklace back in the first guard's hand after the snake has left
    got = t > cend('s4') + 0.3
    guard(p, V, g1x, GY + 36, t, face=gf, sc=0.98, walk=t * 8 if walking else 0, amp=1 if walking else 0,
          arm=(-110 if got else -40 - 12 * poke * math.sin(t * 10) - 80 * shoo),
          stick=None if got else (-10 + 32 * poke + 10 * shoo), lean=10 * poke, look=-0.8, brow=0.3 + 0.7 * shoo,
          hop=20 * jump)
    if got and g_leave < 0.6:
        aa = math.radians(-110)
        draw_necklace(p, V @ T(g1x + gf * 0.98 * (6 - 78 * math.sin(aa)), GY + 36 + 0.98 * (-186 + 78 * math.cos(aa))), t, hang=1)
    # snake: pops out when poked, then slides away to the left, out of the picture
    out = sm(s3[1] - 0.3, s3[1] + 0.5, t)
    away = sm(s4[1] + 0.2, cend('n9') - 1.0, t)
    if out > 0:
        if away < 0.01:
            hx_, hy_ = HOLE[0] - 10 - 60 * out, HOLE[1] - 50 * out
            pts = snake_points(hx_, hy_, 200, 70 + 120 * out, t, amp=6, curl=-6)
            pts = [q for q in pts if q[1] < HOLE[1] + 2] or pts[:3]
        else:
            hx_ = lerp(HOLE[0] - 70, -400, away)
            pts = snake_points(hx_, GY + 20, 180, 300, t * 2, amp=14, speed=10)
            # tail still coming out of the hole at the start
            pts = [q if q[0] < HOLE[0] else (HOLE[0], HOLE[1] + 4) for q in pts]
        snake(p, V, pts, t, scared=sm(g3[1] - 0.2, g3[1] + 0.3, t), brow=0.8, look=0.8)
        if s4[1] < t < cend('s4'):
            put_text(fr, A['shoo'], 620, 470, env(t, g3[1], cend('g3') + 0.3, 0.1, 0.3))
    if g3[1] < t < cend('g3') + 0.3:
        put_text(fr, A['shoo'], 700, 440, env(t, g3[1], cend('g3') + 0.3, 0.1, 0.3))
    return fr

def hatch_frame(t):
    """close-up of the nest: three eggs crack, three babies say caw"""
    a, b = SB("hatch")
    fr = A['home'].copy()
    # zoom on the nest
    z = 1.9
    cx, cy = NEST[0], NEST[1] + 10
    box = (int((cx - W / z / 2) * SS), int((cy - H / z / 2 - 20) * SS), int((cx + W / z / 2) * SS), int((cy + H / z / 2 - 20) * SS))
    bx0 = max(0, box[0]); by0 = max(0, box[1])
    fr = fr.crop((bx0, by0, bx0 + box[2] - box[0], by0 + box[3] - box[1])).resize((W * SS, H * SS), Image.BICUBIC)
    p = Pen(fr)
    ox, oy = bx0 / SS, by0 / SS
    V = S(SS) @ S(z) @ T(-ox, -oy)
    n10 = cue('n10'); b1 = cue('b1'); m3 = cue('m3')
    cracks = [word_time('n10', 'crack', 0.0), word_time('n10', 'crack, crack', 0.35), word_time('n10', 'crack!', 0.0) + 0.35]
    cracks = sorted(cracks)
    nest_back(p, V @ T(*NEST) @ S(NS))
    for k in range(3):
        x = NEST[0] + (-24 + 24 * k) * NS; y = NEST[1] - 8 * NS
        hatched = t > cracks[k] + 0.25
        if not hatched:
            M = V @ T(x, y) @ R(6 * math.sin(t * 12 + k) * (t > a + 0.6)) @ S(NS)
            p.poly(M, ell(0, -10, 11, 14, 20), "#bcd6c4", outline=OUT, w=1.8)
            if t > cracks[k] - 0.4:
                p.line(M, [(-10, -12), (-5, -8), (-1, -14), (4, -8), (10, -12)], OUT, 1.6)
        else:
            pop = clamp((t - cracks[k] - 0.25) / 0.4)
            caw = env(t, b1[1] + k * 0.35, b1[1] + k * 0.35 + 0.5, 0.05, 0.2) if b1[1] < t < cend('b1') + 0.3 else 0
            draw_bird(p, V @ T(x, y + 4 - 6 * pop) @ S(0.75 * (-1 if k == 0 else 1), 0.75), "crow_baby",
                      dict(t=t, mouth=max(caw, 0.4 * spk('B', t)), blink=blink(t, k), look=0.3, head=-25 - 15 * caw,
                           hop=4 * caw))
            # half shells
            Ms = V @ T(x, y + 2) @ S(NS)
            p.poly(Ms, ell(0, -2, 11, 7, 16, 0, 180) + [(-11, -2)], "#bcd6c4", outline=OUT, w=1.4)
    nest_front(p, V @ T(*NEST) @ S(NS))
    # parents on both sides
    mom(p, V, MOM[0] + 40, MOM[1], t, face=-1, look=-0.8, head=-10 + 14 * env(t, m3[1], cend('m3'), 0.3, 0.3))
    dad(p, V, DAD[0] - 40, DAD[1], t, face=1, look=0.8, head=-10)
    for k, c in enumerate(cracks):
        if c - 0.1 < t < c + 0.9:
            put_text(fr, A['crack'], 420 + 220 * k, 170, env(t, c - 0.1, c + 0.9, 0.05, 0.3))
    if b1[1] < t < cend('b1') + 0.6:
        put_text(fr, A['caw'], W / 2, 150, env(t, b1[1], cend('b1') + 0.6, 0.1, 0.3))
    if t > m3[1]:
        for j in range(8):
            ph = ((t - m3[1]) * 0.25 + j / 8) % 1
            M = S(SS) @ T(200 + j * 120 + 20 * math.sin(t + j), 620 - 380 * ph) @ R(t * 50) @ S(0.6 + 0.6 * math.sin(math.pi * ph))
            p.poly(M, khatam(0, 0, 10), "#f2c14e", outline="#b9802a", w=1)
    return fr

# Look pass (pipeline/look.py). NO_PUSH: titles, end card, and scenes that must flow continuously into the next.
from look import Look
LOOK = Look(W, H)
NO_PUSH = {"title", "end", "home", "snake"}

def render(i):
    t = i / FPS
    name, lt, sd = tl.scene_at(t)
    if name is None: name, lt, sd = "end", 4.0, 4.6
    if name.startswith("tree"): fr = tree_frame(name, t)
    elif name in ("title", "end"): fr = card_frame(t, name)
    else: fr = globals()[name + "_frame"](t)
    fr.alpha_composite(A['border'])
    img = fr.convert('RGB').resize((W, H), Image.LANCZOS)
    img = LOOK(img, lt, sd, move=name not in NO_PUSH)   # picture-book look: paper, grade, bloom, slow push-in
    f = min(clamp(lt / 0.35), clamp((sd - lt) / 0.35))
    if name == "tree_open": f = min(clamp(lt / 0.7), clamp((sd - lt) / 0.35))
    if name == "end": f = min(clamp(lt / 0.35), clamp((sd - lt) / 0.8))
    if name == "home": f = clamp(lt / 0.35)
    if name == "snake": f = clamp((sd - lt) / 0.35)
    if f < 0.999: img = Image.blend(Image.new('RGB', (W, H)), img, f)
    return img.tobytes()

# ------------------------------------------------------------------ audio
def noise(n, seed=3, k=400):
    wn = np.random.default_rng(seed).standard_normal(n)
    lp = np.convolve(wn, np.ones(k) / k, 'same')
    return lp / (np.abs(lp).max() + 1e-9)

def flutter(dur, rate=12, seed=9):
    n = int(dur * SR); tt = np.arange(n) / SR
    wn = np.random.default_rng(seed).standard_normal(n)
    hp = wn - np.convolve(wn, np.ones(30) / 30, 'same')
    return hp * (0.5 + 0.5 * np.sin(2 * np.pi * rate * tt)) ** 3 * np.minimum(1, tt / 0.1) * np.minimum(1, (dur - tt) / 0.3)

def hiss(dur, seed=4):
    n = int(dur * SR); tt = np.arange(n) / SR
    wn = np.random.default_rng(seed).standard_normal(n)
    hp = wn - np.convolve(wn, np.ones(6) / 6, 'same')
    return hp * np.minimum(1, tt / 0.15) * np.minimum(1, (dur - tt) / 0.3)

def build_audio(path):
    N = int(SR * DUR); t = np.arange(N) / SR
    mus = np.zeros(N); sfx = np.zeros(N)
    def add(buf, st, sig, g=1.0):
        i = int(st * SR); j = min(N, i + len(sig))
        if 0 <= i < N: buf[i:j] += sig[:j - i] * g
    def seq(st, step, notes, vel=1.0, dur=1.6, end=None):
        k = 0; tt = st
        while True:
            if end is None and k >= len(notes): break
            if end is not None and tt >= end: break
            n = notes[k % len(notes)]
            if n != '-': add(mus, tt, santur(NOTES[n], dur), vel)
            tt += step; k += 1
    def riz(st, end, note, vel=0.4, rate=0.075, swell=False):
        tt = st; k = 0
        while tt < end:
            v = vel * ((0.4 + 0.6 * (tt - st) / max(1e-3, end - st)) if swell else 1) * (0.8 + 0.2 * (k % 2))
            add(mus, tt, santur(NOTES[note], 0.5), v); tt += rate; k += 1
    def tombak(st, end, beat=0.6, g=0.5):
        k = 0; tt = st
        while tt < end:
            add(mus, tt, dum(), g); add(mus, tt + beat / 2, tak(seed=k), g * 1.6); add(mus, tt + beat * 0.75, tak(seed=k + 40), g)
            tt += beat; k += 1
    sc = {n: (a, b) for n, a, b in tl.scenes}
    playful = ["D4", "F4", "A4", "G4", "F4", "Ek4", "D4", "-", "A3", "D4", "F4", "G4", "A4", "-", "G4", "F4"]
    happy = ["D5", "C5", "Bb4", "A4", "Bb4", "A4", "G4", "A4", "F4", "G4", "A4", "-"]
    flow = ["D4", "-", "F4", "A4", "G4", "-", "F4", "Ek4", "D4", "-", "A3", "-", "C4", "D4", "-", "-"]
    sneaky = ["D4", "-", "Ek4", "-", "D4", "C4", "-", "A3", "-", "-", "Bb3", "-", "A3", "-", "-", "-"]
    sad = ["A4", "-", "G4", "F4", "-", "Ek4", "D4", "-", "-", "C4", "D4", "-", "-", "-"]
    a, b = sc['tree_open']; seq(a + 0.2, 0.32, playful, 0.7, end=b - 0.2); tombak(a + 0.2, b - 0.3, 0.64, 0.3)
    a, b = sc['title']; seq(a + 0.2, 0.3, ["A3", "D4", "Ek4", "F4", "Ek4", "D4", "C4", "D4", "-", "A4"], 0.9)
    a, b = sc['home']; seq(a + 0.2, 0.36, flow, 0.55, 1.8, end=b)
    a, b = sc['snake']; seq(a + 0.1, 0.42, sneaky, 0.6, 1.6, end=cue('f1')[1])
    riz(cue('f1')[1], cend('f1'), 'A3', 0.3, swell=True); seq(cue('s2')[1], 0.45, sneaky, 0.5, 1.6, end=b)
    a, b = sc['worry']; seq(a + 0.2, 0.55, sad, 0.5, 2.0, end=cue('f2')[1] + 1.5)
    seq(cue('f2')[1] + 1.5, 0.3, ["D4", "F4", "A4", "D5"], 0.6, 1.4)
    a, b = sc['jackal']; seq(a + 0.2, 0.4, flow, 0.5, 1.8, end=cue('f3')[1])
    seq(cue('f3')[1] + 0.8, 0.12, ["D4", "F4", "A4", "D5", "-", "A4", "D5"], 0.7, 1.2)
    a, b = sc['garden']; seq(a + 0.2, 0.3, happy, 0.5, 1.2, end=cue('n6')[1])
    seq(cue('n6')[1], 0.07, ["D5", "C5", "Bb4", "A4", "G4", "F4"], 0.7, 0.9)
    riz(cue('g1')[1], b, 'D4', 0.25)
    a, b = sc['chase']; seq(a + 0.1, 0.24, ["D4", "F4", "A4", "F4", "G4", "A4", "Bb4", "A4", "G4", "F4", "Ek4", "F4"], 0.6, 1.0, end=b)
    tombak(a + 0.1, b, 0.4, 0.5)
    a, b = sc['drop']; plop = word_time('n8', 'plop')
    seq(a + 0.2, 0.3, sneaky, 0.5, 1.4, end=plop)
    add(mus, plop + 0.4, dum(0.5), 0.8)
    riz(cue('s3')[1], cend('s4'), 'A3', 0.25)
    seq(cue('n9')[1], 0.26, happy, 0.6, 1.2, end=b - 0.2); tombak(cue('n9')[1], b - 0.3, 0.5, 0.4)
    a, b = sc['hatch']; seq(a + 0.2, 0.3, playful, 0.55, 1.2, end=b - 0.2)
    a, b = sc['tree_close']; seq(a + 0.2, 0.36, ["D4", "-", "F4", "G4", "A4", "-", "Bb4", "A4", "G4", "-", "F4", "Ek4", "D4", "-", "-", "-"], 0.6, end=b - 0.2)
    c3 = cue('c3'); seq(c3[1] - 0.3, 0.1, ["D5", "A4", "D5", "F4"], 0.5, 1.6)
    a, b = sc['end']
    seq(a + 0.2, 0.3, ["D4", "F4", "A4", "D5", "-", "C5", "A4", "Bb4", "A4", "-", "-", "D4"], 0.85)
    for nn in ("D3", "A3", "D4"): add(mus, a + 3.3, santur(NOTES[nn], 2.0), 0.8)
    mus += (np.sin(2 * np.pi * NOTES['D2'] * t) + 0.5 * np.sin(2 * np.pi * NOTES['A2'] * t)) * 0.05
    # sfx
    a, b = sc['home']; add(sfx, a, flutter(3.0), 0.6)
    add(sfx, cue('s1')[1] - 0.6, hiss(1.0), 0.35); add(sfx, cend('s2'), hiss(1.2, 5), 0.3)
    add(sfx, cue('f1')[1] - 0.2, flutter(1.6, 15, 4), 0.7)
    add(sfx, cend('f2'), flutter(1.6, 12, 7), 0.6)
    a, b = sc['jackal']; add(sfx, a, flutter(2.6, 12, 8), 0.6)
    add(sfx, cue('n6')[1] - 0.6, flutter(2.4, 14, 3), 0.8)
    a, b = sc['chase']; add(sfx, a, flutter(b - a, 9, 6), 0.5)
    plop = word_time('n8', 'plop'); add(sfx, plop + 0.4, tak(0.1, seed=2), 2.2)
    for k in range(4): add(sfx, cue('g2')[1] + 1.2 + k * 0.25, tak(0.06, seed=k + 5), 0.8)
    add(sfx, cue('s3')[1] - 0.3, hiss(0.8, 6), 0.4); add(sfx, cue('s4')[1] + 0.2, hiss(2.5, 7), 0.3)
    for c in (word_time('n10', 'crack', 0.0), word_time('n10', 'crack, crack', 0.35), word_time('n10', 'crack!', 0.0) + 0.35):
        add(sfx, c, tak(0.08, seed=int(c)), 1.6)
    br = noise(N, 3) * (0.55 + 0.45 * np.sin(2 * np.pi * t / 6.5) ** 2)
    gate = np.zeros(N)
    for nm in ("home", "snake", "worry", "jackal", "garden", "chase", "drop", "hatch"):
        a, b = sc[nm]; gate[int(a * SR):int(b * SR)] = 1
    gate = np.convolve(gate, np.ones(int(0.5 * SR)) / int(0.5 * SR), 'same')
    sfx += br * gate * 0.12
    vo = tl.mix_voice(N)
    rev = mus.copy()
    for dly, g in ((0.071, 0.3), (0.113, 0.22), (0.197, 0.15), (0.311, 0.1)):
        k = int(dly * SR); rev[k:] += mus[:-k] * g
    ve = np.convolve(np.abs(vo), np.ones(int(0.25 * SR)) / int(0.25 * SR), 'same')
    duck = 1 - 0.62 * np.clip(ve / (ve.max() * 0.15 + 1e-9), 0, 1)
    duck = np.convolve(duck, np.ones(int(0.2 * SR)) / int(0.2 * SR), 'same')
    rev = rev / (np.abs(rev).max() + 1e-9) * 0.5 * duck
    sfx = sfx / (np.abs(sfx).max() + 1e-9) * 0.22 * (0.5 + 0.5 * duck)
    vo = vo / (np.abs(vo).max() + 1e-9) * 0.9
    k = int(0.013 * SR)
    L = rev + sfx + vo; Rr = np.r_[np.zeros(k), rev[:-k]] + sfx + vo
    st = np.stack([L, Rr], 1) * (np.minimum(1, t / 0.3) * np.clip((DUR - t) / 0.8, 0, 1))[:, None]
    pk = np.abs(st).max()
    if pk > 0.95: st *= 0.95 / pk
    with wave.open(path, 'wb') as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((st * 32767).astype(np.int16).tobytes())

def write_fa_srt(path):
    def ts(x):
        ms = int(round(x * 1000)); return f"{ms//3600000:02d}:{ms//60000%60:02d}:{ms//1000%60:02d},{ms%1000:03d}"
    with open(path, "w", encoding="utf-8") as f:
        for i, (k, st, d, sp, _) in enumerate(tl.cues, 1):
            lab = NAMES_FA.get(sp)
            f.write(f"{i}\n{ts(st)} --> {ts(st + d + 0.2)}\n{(lab + ': ') if lab else ''}{FA[k]}\n\n")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "info":
        print("DUR", round(DUR, 2)); [print(n, round(a, 1), round(b, 1)) for n, a, b in tl.scenes]
        for c in tl.cues: print(c[0], round(c[1], 1), round(c[2], 1))
        sys.exit()
    init()
    if len(sys.argv) > 1 and sys.argv[1] == "stills":
        for ts in [float(x) for x in sys.argv[2:]]:
            Image.frombytes('RGB', (W, H), render(int(ts * FPS))).save(os.path.join(EP, f"still_{ts:05.1f}.png"))
        sys.exit()
    wav = os.path.join(EP, "audio.wav"); build_audio(wav)
    tl.srt(os.path.join(EP, "ep04.en.srt"), NAMES_EN)
    write_fa_srt(os.path.join(EP, "ep04.fa.srt"))
    out = os.path.join(EP, "render_ep04.mp4")
    ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
                           "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-i", wav,
                           "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p",
                           "-c:a", "aac", "-b:a", "160k", "-shortest", "-movflags", "+faststart", out],
                          stdin=subprocess.PIPE)
    with mp.get_context("fork").Pool(os.cpu_count()) as pool:
        for k, buf in enumerate(pool.imap(render, range(NF), chunksize=4)):
            ff.stdin.write(buf)
            if k % 480 == 0: print(f"frame {k}/{NF}", flush=True)
    ff.stdin.close(); ff.wait()
    print("done:", out)
