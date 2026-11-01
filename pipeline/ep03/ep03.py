#!/usr/bin/env python3
"""Kalila & Dimna — Episode 3: The Ring-Dove and the Hunter's Net (~3.4 min).
Adapted from ep01/ep1.py (via ep02/ep02.py: same timeline helper, hosts, cards, word card, render + audio)."""
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
tl.scene("meadow", ["n1", 0.3, "n2", 0.4, "h1", 0.3, "r1"], lead=1.4, tail=0.8)
tl.scene("flock", ["n3", 0.2, "y1", 0.2, "g1"], lead=0.6, tail=0.6)
tl.scene("caught", ["n4", 0.2, "y2", 0.3, "h2", 0.3, "n5"], lead=0.4, tail=0.5)
tl.scene("together", ["g2", 0.5, "g3"], lead=0.3, tail=0.4)
tl.scene("fly", ["n6", 0.2, "h3"], lead=0.2, tail=1.2)
tl.scene("chase", ["n7", 0.3, "h4"], lead=0.8, tail=1.6)
tl.scene("rock", ["g4", 0.3, "n8", 0.3, "g5", 0.4, "z1"], lead=0.6, tail=0.6)
tl.scene("chew", ["g6", 0.2, "z2", 0.2, "g7", 0.3, "z3", 0.3, "n9"], lead=0.3, tail=1.0)
tl.scene("friends", ["r2", 0.3, "z4", 0.4, "n10"], lead=1.4, tail=1.8)
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
MW = 2700           # meadow world width (chase pans across it)
GY = 618            # ground line where the doves stand
CROW_PERCH = (232, 236)
BUSH_X = 1075
NET_CX = 640
SNAP = None         # set after timeline (word "snap")
# the flock: (offset from the cluster centre, kind, face, scale)
FLOCK = [(-268, "dove_grey", 1, 1.3), (-182, "dove_white", 1, 1.25), (-92, "dove_brown", 1, 1.3),
         (6, "ringdove", 1, 1.5), (108, "dove_blue", -1, 1.3), (196, "dove_white", -1, 1.25)]
NET_L, NET_R, NETH = -330, 280, 300
RING = 3; YOUNG = 1
SNAP = word_time('n4', 'snap')

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

def build_meadow_world():
    img = sky(H * SS, MW * SS); p = Pen(img); M = S(SS); rng = np.random.default_rng(31)
    sun(p, M, 1010, 108)
    for x in range(120, MW, 380):
        cloud(p, M, x + rng.uniform(-60, 60), rng.uniform(80, 200), rng.uniform(0.7, 1.05))
    hills(p, M, MW, 420, 70, 0.4, 230, "#d9b6a3", "#9c7a68")
    hills(p, M, MW, 500, 55, 1.7, 160, "#b9ba86", "#7f8156")
    # wheat fields far right (the chase)
    for k, x0 in enumerate(range(1500, MW, 320)):
        p.poly(M, [(x0, 548), (x0 + 300, 548), (x0 + 290, 572), (x0 - 10, 572)], ["#e2c46a", "#cdb05a"][k % 2],
               outline="#9c8440", w=1.5)
    for x in (930, 1180, 1650, 1700, 2250, 2520):
        cypress(p, M, x, 560, rng.uniform(170, 220), 22)
    for x in (560, 1420, 1980, 2400):
        blossom_tree(p, M, x, 566, rng)
    gp = [(x, 572 + 6 * math.sin(x / 90)) for x in range(0, MW + 10, 10)] + [(MW + 10, H), (0, H)]
    p.poly(M, gp, "#93ad62", outline="#5f7a3a", w=2)
    big_tree(p, M, 170, 600)
    for _ in range(900):
        fx, fy = rng.uniform(0, MW), rng.uniform(585, 700)
        if 270 < fx < 940 and 575 < fy < 650: continue            # keep the net's spot tidy
        if rng.random() < 0.6: p.line(M, [(fx - 3, fy), (fx, fy - 7), (fx + 3, fy)], "#5f7a3a", 1.2)
        else: flower(p, M, fx, fy, ["#c8423a", "#fff7ea", "#3d6db5", "#d96f9a"][rng.integers(4)])
    return img

def crop_world(cam):
    cx = int(round(cam * SS))
    return A['meadow'].crop((cx, 0, cx + W * SS, H * SS)).convert('RGBA')

ROCK_X, HOLE = 930, (842, 606)
def build_rock_set():
    img = sky(H * SS, W * SS, (233, 178, 112), (250, 232, 196)); p = Pen(img); V = S(SS)
    rng = np.random.default_rng(12)
    sun(p, V, 180, 120)
    cloud(p, V, 520, 110, 0.9); cloud(p, V, 900, 170, 0.7)
    hills(p, V, W, 430, 60, 2.3, 200, "#d9b6a3", "#9c7a68")
    hills(p, V, W, 505, 50, 0.9, 140, "#b9ba86", "#7f8156")
    cypress(p, V, 120, 560, 190, 22); cypress(p, V, 1180, 566, 160, 20)
    blossom_tree(p, V, 300, 566, rng)
    gp = [(x, 572 + 6 * math.sin(x / 80)) for x in range(0, W + 10, 10)] + [(W + 10, H), (0, H)]
    p.poly(V, gp, "#93ad62", outline="#5f7a3a", w=2)
    # the big rock with Zirak's hole
    rock = [(770, 640), (790, 560), (830, 500), (900, 462), (990, 456), (1060, 490), (1100, 560), (1110, 640)]
    p.poly(V, rock, "#a99a86", outline=OUT, w=3)
    p.poly(V, [(830, 520), (900, 476), (980, 470), (950, 500), (880, 520)], "#c4b7a3", outline=None)
    for a, b in (((960, 520), (1010, 560)), ((1040, 600), (1070, 560)), ((880, 560), (905, 590))):
        p.line(V, [a, b], "#7e705e", 2)
    p.poly(V, ell(HOLE[0], HOLE[1] + 6, 30, 26, 30, 180, 360) + [(HOLE[0] + 30, HOLE[1] + 34), (HOLE[0] - 30, HOLE[1] + 34)],
           "#3a2a1e", outline=OUT, w=2.5)
    for _ in range(420):
        fx, fy = rng.uniform(0, W), rng.uniform(588, 700)
        if 90 < fx < 900 and 588 < fy < 660: continue
        if rng.random() < 0.6: p.line(V, [(fx - 3, fy), (fx, fy - 7), (fx + 3, fy)], "#5f7a3a", 1.2)
        else: flower(p, V, fx, fy, ["#c8423a", "#fff7ea", "#3d6db5", "#d96f9a"][rng.integers(4)])
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
    fa_text(d, (w / 2 * SS, 98 * SS), "کبوتر", 70 * SS, (28, 52, 99, 255))
    f2 = ImageFont.truetype(FB, 32 * SS)
    d.text((w / 2 * SS, 166 * SS), "kabootar  =  dove", font=f2, fill=(90, 50, 12, 255), anchor="mm")
    return im

def init():
    ME.init_assets()
    A['border'] = ME.ASSETS['border']; A['card'] = ME.ASSETS['card']
    A['tree'] = build_tree_set().convert('RGBA')
    A['meadow'] = build_meadow_world()
    A['rock'] = build_rock_set().convert('RGBA')
    A['wcard'] = build_word_card()
    gold, cream = (226, 182, 74, 255), (250, 240, 214, 255)
    A['t1'] = text_img("KALILA & DIMNA", FB, 60, gold, 2, (90, 60, 12, 255))
    A['t2'] = text_img("The Ring-Dove and the Hunter's Net", FI, 42, cream)
    A['t3'] = text_img("—  Episode 3  —", FR, 24, gold)
    A['e1'] = text_img("Next time", FI, 30, cream)
    A['e2'] = text_img("The Crow and the Snake", FB, 46, gold, 2, (90, 60, 12, 255))
    A['e3'] = text_img("A new story every Saturday", FR, 26, cream)
    A['q'] = text_img("?", FB, 50, (250, 240, 214, 255), 3, (40, 24, 10, 255))
    A['bang'] = text_img("!", FB, 54, (200, 40, 30, 255), 3, (255, 255, 255, 255))
    A['snap'] = text_img("SNAP!", FB, 46, (200, 40, 30, 255), 3, (255, 255, 255, 255))
    A['fly'] = text_img("FLY!", FB, 54, (226, 182, 74, 255), 3, (40, 24, 10, 255))
    A['huff'] = text_img("huff... puff...", FI, 26, (90, 50, 12, 255))
    A['nib'] = text_img("nibble nibble!", FI, 24, (90, 50, 12, 255))
    A['zzz'] = text_img("1  2  3", FB, 34, (250, 240, 214, 255), 3, (40, 24, 10, 255))

# ------------------------------------------------------------------ actors
def dove(p, V, i, x, y, t, fly=0, face=None, **kw):
    off, kind, f0, sc = FLOCK[i]
    who = 'G' if i == RING else ('Y' if i == YOUNG else None)
    s = spk(who, t) if who else 0.0
    face = f0 if face is None else face
    po = dict(t=t, mouth=s, blink=blink(t, i * 0.7), look=0.3, fly=fly, flap=t * 14 + i * 1.3,
              head=6 * s * math.sin(t * 9))
    hd = kw.pop('head', 0); po.update(kw); po['head'] += hd
    draw_bird(p, V @ T(x, y) @ S(sc * face, sc), kind, po)

def crow(p, V, x, y, t, face=1, fly=0, **kw):
    s = spk('C', t)
    po = dict(t=t, mouth=s, blink=blink(t, 2.2), look=0.4, fly=fly, flap=t * 11, head=6 * s * math.sin(t * 9), sly=0.5)
    hd = kw.pop('head', 0); po.update(kw); po['head'] += hd
    draw_bird(p, V @ T(x, y) @ S(1.35 * face, 1.35), "crow", po)

def hunter(p, V, x, y, t, face=1, sc=1.0, **kw):
    s = spk('H', t)
    po = dict(t=t, mouth=s, blink=blink(t, 1.1), look=0.4, head=4 * s * math.sin(t * 7))
    hd = kw.pop('head', 0); po.update(kw); po['head'] += hd
    draw_hunter(p, V @ T(x, y) @ S(sc * face, sc), po)

def mouse(p, V, x, y, t, face=1, sc=1.45, **kw):
    s = spk('Z', t)
    po = dict(t=t, mouth=s, blink=blink(t, 0.5), look=0.5, head=6 * s * math.sin(t * 9), arm=-30 - 30 * s * math.sin(t * 5))
    hd = kw.pop('head', 0); po.update(kw); po['head'] += hd
    draw_mouse(p, V @ T(x, y) @ S(sc * face, sc), po)

# ------------------------------------------------------------------ the net
ROPE, ROPE2 = "#6b4a2a", "#a07a4a"
def mesh(p, V, top, bot, n=9, w=2.2):
    """diamond rope net between two curves top(u), bot(u), u in 0..1 (lists of points, same length)"""
    top = np.asarray(top, float); bot = np.asarray(bot, float); k = len(top)
    def P(u, v):
        u = min(1.0, max(0.0, u)); f = u * (k - 1); i = min(k - 2, int(f)); r = f - i
        a = top[i] * (1 - r) + top[i + 1] * r; b = bot[i] * (1 - r) + bot[i + 1] * r
        return tuple(a * (1 - v) + b * v)
    vs = np.linspace(0, 1, 8)
    for j in range(-n, 2 * n):
        u0 = j / n
        for sgn in (1, -1):
            pts = [P(u0 + sgn * v * 0.9, v) for v in vs if 0 <= u0 + sgn * v * 0.9 <= 1]
            if len(pts) > 1:
                p.line(V, pts, ROPE, w)
    p.line(V, [tuple(q) for q in top], ROPE, w + 1.6); p.line(V, [tuple(q) for q in bot], ROPE, w + 1.6)
    p.line(V, [tuple(top[0]), tuple(bot[0])], ROPE, w + 1.2); p.line(V, [tuple(top[-1]), tuple(bot[-1])], ROPE, w + 1.2)
    for q in list(top[::2]) + list(bot[::2]):
        p.poly(V, ell(q[0], q[1], 2.6, 2.6, 8), ROPE2, outline=ROPE, w=1)

def flat_net(p, V, cx, y=GY, half=NETH, grain=True, t=0, gone=0.0):
    top = [(cx - half + 20 + 2 * (half - 20) * u, y - 22) for u in np.linspace(0, 1, 12)]
    bot = [(cx - half + 2 * half * u, y + 12) for u in np.linspace(0, 1, 12)]
    mesh(p, V, top, bot, n=12, w=1.6)
    if grain:
        rng = np.random.default_rng(4)
        for _ in range(60):
            gx, gy = rng.uniform(cx - half + 20, cx + half - 20), rng.uniform(y - 18, y + 8)
            if rng.random() < gone: continue
            p.poly(V, ell(gx, gy, 2.6, 1.8, 8), "#f2c14e", outline="#a87a1e", w=0.8)

def dome_net(p, V, x0, x1, y=GY + 6, h=110, wob=0.0, t=0):
    us = np.linspace(0, 1, 16)
    top = [(lerp(x0, x1, u), y - h * math.sin(math.pi * u) ** 0.8 - wob * 6 * math.sin(t * 17 + u * 9)) for u in us]
    bot = [(lerp(x0, x1, u), y + 4 * math.sin(u * 20)) for u in us]
    mesh(p, V, top, bot, n=11, w=1.8)

def bag_net(p, V, feet, sag=95, t=0):
    """net hanging from the flying doves' feet"""
    feet = sorted(feet)
    xs = np.array([f[0] for f in feet]); ys = np.array([f[1] for f in feet])
    us = np.linspace(0, 1, 14)
    top = [(np.interp(u, np.linspace(0, 1, len(xs)), xs), np.interp(u, np.linspace(0, 1, len(ys)), ys)) for u in us]
    cx = xs.mean()
    bot = [(cx + (q[0] - cx) * 0.55, q[1] + sag * (0.6 + 0.4 * math.sin(math.pi * u)) + 5 * math.sin(t * 4 + u * 5))
           for q, u in zip(top, us)]
    mesh(p, V, top, bot, n=10)

def grain_toss(p, V, t, t0, x0, y0):
    rng = np.random.default_rng(int(t0 * 10))
    for k in range(26):
        u = (t - t0 - k * 0.02) / 0.9
        if 0 < u < 1:
            tx = x0 - rng.uniform(80, 560); ty = GY + rng.uniform(-18, 8)
            x = lerp(x0, tx, u); y = lerp(y0, ty, u) - 90 * math.sin(math.pi * u)
            p.poly(V, ell(x, y, 2.6, 1.8, 8), "#f2c14e", outline="#a87a1e", w=0.8)

# ------------------------------------------------------------------ flock motion
def ground_pos(i, cx=NET_CX):
    return cx + FLOCK[i][0], GY + (-12 if i % 2 == 0 else 8)

def flock_air(i, t):
    """positions while circling above the meadow in the flock scene"""
    a, b = SB("flock")
    u = sm(a - 0.3, a + 4.5, t)
    ang = 0.55 * (t - a)
    cx = lerp(1500, 640 + 230 * math.cos(ang), u); cy = lerp(160, 270 + 45 * math.sin(ang), u)
    k = i - RING
    vx = -1 if u < 0.95 else -math.sin(ang)
    dx = abs(k) * 78 * (1 if vx < 0 else -1); dy = k * 46 + 6 * math.sin(t * 2 + i)
    return cx + dx, cy + dy, (-1 if vx < 0 else 1)

def lift_pos(i, cy, t, cx=NET_CX, spread=0.8):
    off = FLOCK[i][0] * spread
    return cx + off, cy - 18 * (1 - abs(FLOCK[i][0]) / 180) + 6 * math.sin(t * 5 + i * 1.7)

def draw_lifting(fr, V, cx, cy, t, land=0.0, face=1, extra=None):
    """the whole flock flying with the net under them. land 0 = flying, 1 = standing in the net on the ground"""
    p = Pen(fr)
    pos = []
    for i in range(len(FLOCK)):
        x, y = lift_pos(i, cy, t, cx, 0.8 + 0.2 * land)
        gx, gy = ground_pos(i, cx)
        x, y = lerp(x, gx, land), lerp(y, gy, land)
        pos.append((x, y))
    if land < 0.5:
        bag_net(p, V, [(x - 6 * face, y - 10) for x, y in pos], sag=lerp(95, 20, land * 2), t=t)
    for i, (x, y) in enumerate(pos):
        dove(p, V, i, x, y, t, fly=1 if land < 0.6 else 0, face=face, **(extra(i) if extra else {}))
    if land >= 0.5:
        dome_net(p, V, cx + NET_L, cx + NET_R, h=lerp(40, 115, (land - 0.5) * 2), t=t)
    return pos

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
        if o2[1] < t < cend('o2'): kpo['head'] += 8 * math.sin(t * 6)          # Kalila pulls and pulls
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
        # two little doves flutter by during the moral
        c2 = cue('c2')
        u = (t - c2[1]) / 4.0
        if 0 < u < 1:
            for j in range(2):
                draw_bird(p, V @ T(lerp(-80, 1380, u) - 70 * j, 300 - 60 * math.sin(math.pi * u) + 30 * j) @ S(0.9),
                          ["ringdove", "dove_grey"][j], dict(t=t, fly=1, flap=t * 14 + j))
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

def crow_on_tree(p, V, t, look=0.6, **kw):
    crow(p, V, *CROW_PERCH, t, face=1, look=look, **kw)

def meadow_frame(t):
    a, b = SB("meadow"); lt = t - a
    fr = crop_world(0); p = Pen(fr); V = S(SS)
    spread_t = word_time('n2', 'spread'); throw_t = word_time('n2', 'threw')
    hide_t = cue('h1')[1] + 1.0
    # net appears (unrolled) and grain
    unroll = sm(spread_t, spread_t + 1.2, t)
    if unroll > 0:
        half = NETH * unroll
        flat_net(p, V, NET_CX - 25 + NETH - half, GY, half, grain=t > throw_t + 0.8)
    # hunter: walks in, spreads, throws, hides
    arrive = spread_t - 0.2
    if t < arrive:
        x = lerp(1420, 880, sm(cue('n2')[1] - 1.2, arrive, t)); walking = True; face = -1
    elif t < hide_t:
        x = 880; walking = False; face = -1
    else:
        x = lerp(880, BUSH_X, sm(hide_t, hide_t + 1.4, t)); walking = t < hide_t + 1.4; face = 1 if t < hide_t + 1.4 else -1
    throw = env(t, throw_t - 0.3, throw_t + 0.6, 0.2, 0.3)
    crouch = sm(hide_t + 1.3, hide_t + 1.9, t)
    if x < 1400:
        hunter(p, V, x, GY + 20, t, face=face, walk=t * 5 if walking else 0, amp=1 if walking else 0,
               arm=6 - 110 * throw - 40 * spk('H', t) * (0.5 + 0.5 * math.sin(t * 4)), crouch=crouch,
               look=0.8, brow=0.6)
        grain_toss(p, V, t, throw_t, x - 50, GY - 160)
    bush(p, V, BUSH_X, GY + 40, 1.5, 0.0)
    worried = sm(cue('r1')[1] - 0.3, cue('r1')[1], t)
    crow_on_tree(p, V, t, look=1.0, head=14 * worried)
    if t > cue('r1')[1]:
        put_text(fr, A['bang'], CROW_PERCH[0] + 40, CROW_PERCH[1] - 110, env(t, cue('r1')[1], b, 0.2, 0.4))
    return fr

def flock_frame(t):
    a, b = SB("flock")
    fr = crop_world(0); p = Pen(fr); V = S(SS)
    flat_net(p, V, NET_CX - 25, grain=True)
    hunter(p, V, BUSH_X, GY + 20, t, face=-1, crouch=1, look=-0.8 + 0.3 * math.sin(t))
    bush(p, V, BUSH_X, GY + 40, 1.5, 0.15 * math.sin(t * 3))
    crow_on_tree(p, V, t, look=1.0, head=-10)
    for i in range(len(FLOCK)):
        x, y, f = flock_air(i, t)
        dove(p, V, i, x, y, t, fly=1, face=f)
    return fr

def caught_frame(t):
    a, b = SB("caught")
    fr = crop_world(0); p = Pen(fr); V = S(SS)
    land_end = SNAP - 0.5
    u = sm(a, land_end, t)
    if t < SNAP:
        flat_net(p, V, NET_CX - 25, grain=True, gone=sm(land_end, SNAP, t) * 0.5)
    pull = t > cue('n5')[1]
    for i in range(len(FLOCK)):
        x0, y0, f0 = flock_air(i, a)
        gx, gy = ground_pos(i)
        x, y = lerp(x0, gx, u), lerp(y0, gy, u)
        if u < 1:
            dove(p, V, i, x, y, t, fly=1, face=f0 if u < 0.5 else FLOCK[i][2])
        elif t < SNAP:
            dove(p, V, i, gx, gy, t, peck=0.9 * max(0, math.sin(t * 9 + i * 1.3)))
        else:
            panic = 1 if (t < SNAP + 2.5 or pull) else 0
            dove(p, V, i, gx + 3 * panic * math.sin(t * 13 + i), gy, t, fly=panic and (i % 2 == 0 or pull),
                 hop=panic * 8 * abs(math.sin(t * 7 + i)), look=-0.5 if t > cue('h2')[1] else 0.3,
                 tilt=-10 * pull * math.sin(t * 6 + i))
    if t >= SNAP:
        dome_net(p, V, NET_CX + NET_L, NET_CX + NET_R, h=115 * sm(SNAP, SNAP + 0.25, t) + 1, wob=1.0 if pull else 0.4, t=t)
        put_text(fr, A['snap'], NET_CX, 380, env(t, SNAP, SNAP + 1.4, 0.05, 0.4))
    # hunter jumps up and comes over, rubbing his hands
    h2 = cue('h2')[1]
    up = sm(h2 - 0.4, h2, t)
    hx = lerp(BUSH_X, 930, sm(h2 + 0.2, cend('h2') + 1.5, t))
    walking = h2 + 0.2 < t < cend('h2') + 1.5
    hunter(p, V, hx, GY + 20, t, face=-1, crouch=1 - up, walk=t * 4 if walking else 0, amp=1 if walking else 0,
           arm=-50 - 20 * math.sin(t * 8) * up, arm2=-40 + 20 * math.sin(t * 8) * up, look=0.6, brow=0.2,
           hop=10 * abs(math.sin(t * 6)) * env(t, h2, cend('h2'), 0.2, 0.2))
    if t < h2 + 0.5:
        bush(p, V, BUSH_X, GY + 40, 1.5, 0.0)
    else:
        bush(p, V, BUSH_X + 60, GY + 40, 1.5, 0.0)
    crow_on_tree(p, V, t, look=1.0, head=10)
    return fr

def together_frame(t):
    a, b = SB("together")
    fr = crop_world(0); p = Pen(fr); V = S(SS)
    g3 = cue('g3')
    count = (t - g3[1]) / max(0.1, g3[2])
    for i in range(len(FLOCK)):
        gx, gy = ground_pos(i)
        ready = 0 if count < 0.2 else 1
        look = 1.0 * (1 if gx < NET_CX + 8 else -1) if i != RING else 0.0
        dove(p, V, i, gx, gy, t, look=look if i != RING else 0.3, head=-8 * ready if i != RING else -6,
             wing=-30 * ready * abs(math.sin(t * 5 + i)), hop=4 * ready * abs(math.sin(t * 9 + i)))
    dome_net(p, V, NET_CX + NET_L, NET_CX + NET_R, h=115, wob=0.15, t=t)
    hx = lerp(930, 880, sm(a, b, t))
    hunter(p, V, hx, GY + 20, t, face=-1, walk=t * 2.5 if t < b - 0.6 else 0, amp=0.5 if t < b - 0.6 else 0,
           arm=-60 - 30 * sm(b - 1.5, b, t), arm2=-40, look=0.6, brow=0.2, lean=6 * sm(b - 1.5, b, t))
    bush(p, V, BUSH_X + 60, GY + 40, 1.5, 0.0)
    crow_on_tree(p, V, t, look=1.0, head=10)
    if count > 0:
        k = min(3, int(count * 4.2))
        if k < 3:
            put_text(fr, text_img(str(k + 1), FB, 64, (250, 240, 214, 255), 3, (40, 24, 10, 255)), NET_CX, 330,
                     1.0)
        else:
            put_text(fr, A['fly'], NET_CX, 330, 1.0)
    return fr

def fly_frame(t):
    a, b = SB("fly"); lt = t - a
    fr = crop_world(0); p = Pen(fr); V = S(SS)
    up = sm(a, a + 2.6, t)
    cy = lerp(GY, 250, up) + (cue('h3')[1] < t) * 0
    land = 1 - sm(a, a + 0.5, t)
    cx = NET_CX + 160 * sm(cue('h3')[1], b, t)
    draw_lifting(fr, V, cx, cy, t, land=land, face=1)
    if lt < 1.2:
        put_text(fr, A['fly'], NET_CX, 330 - 30 * lt, 1 - sm(0.6, 1.2, lt))
    # hunter grabs at the empty air, then shakes his fist (no harm done!)
    jump = env(t, a + 0.3, a + 1.4, 0.3, 0.4)
    h3 = cue('h3')
    shake = env(t, h3[1] - 0.2, b, 0.2, 0.4)
    hunter(p, V, 880 - 120 * sm(a + 0.2, a + 1.0, t), GY + 20, t, face=-1, hop=40 * jump, arm=-160 * jump - 150 * shake + 25 * shake * math.sin(t * 14),
           arm2=-120 * jump, look=0.0, head=-20 * (jump + shake) * 0.6, brow=1.0)
    bush(p, V, BUSH_X + 60, GY + 40, 1.5, 0.0)
    # the crow takes off and follows
    cu = sm(h3[1] + 0.4, b + 0.4, t)
    if cu < 0.02:
        crow_on_tree(p, V, t, look=1.0, head=-10 * up)
    else:
        crow(p, V, lerp(CROW_PERCH[0], 560, cu), lerp(CROW_PERCH[1], 150, cu) - 40 * math.sin(math.pi * cu), t, fly=1)
    return fr

def chase_frame(t):
    a, b = SB("chase"); lt = t - a
    h4 = cue('h4')
    cam = 1300 * sm(a, h4[1] - 0.2, t)
    fr = crop_world(cam); p = Pen(fr); V = S(SS)
    Vw = V @ T(-cam, 0)
    # flock with the net in screen space; they fly off to the right during h4
    off = 900 * sm(h4[1] + 0.4, h4[1] + 4.0, t)
    cx, cy = 760 + off + 20 * math.sin(lt * 1.3), 220 + 14 * math.sin(lt * 2) - 80 * sm(h4[1], h4[1] + 4, t)
    draw_lifting(fr, V, cx, cy, t, land=0.0, face=1)
    crow(p, V, cx - 330 + 0.9 * off + 30 * math.sin(lt * 1.7), 140 + 12 * math.sin(lt * 2.4), t, fly=1, look=1.0)
    # the hunter runs, slows down, puffs, and gives up
    run = 1 - sm(h4[1] - 0.6, h4[1] + 0.4, t)
    hx_screen = lerp(380, 600, sm(a, h4[1], t))
    leave = sm(cend('h4') + 0.1, b, t)
    hx_screen -= 520 * leave
    lean = 18 * (1 - run) * env(t, h4[1] - 0.6, cend('h4') - 1.5, 0.4, 0.6)
    hunter(p, V, hx_screen, GY + 20, t, face=-1 if leave > 0.01 else 1, walk=t * (9 * run + 3 * (leave > 0.01)),
           amp=1 if (run > 0.1 or leave > 0.01) else 0,
           arm=-60 * run - 10 * spk('H', t), arm2=40 * run, lean=lean + 10 * run, look=0.8, brow=0.6 * run,
           head=10 * (1 - run) * math.sin(t * 2))
    if 1 - run > 0.5 and t < cend('h4') - 1.5:
        put_text(fr, A['huff'], hx_screen + 10, 300 + 6 * math.sin(t * 3), env(t, h4[1], cend('h4') - 1.5, 0.3, 0.3))
    return fr

RX = 430           # where the net lands in the rock scene
MOUSE_X = 770
def rock_frame(t):
    a, b = SB("rock")
    fr = A['rock'].copy(); p = Pen(fr); V = S(SS)
    n8 = cue('n8')
    u = sm(a, n8[1] + 0.4, t)
    cx = lerp(-260, RX, u); cy = lerp(240, 300, u)
    land = sm(n8[1] + 0.2, cend('n8'), t)
    cy = lerp(cy, GY, land)

    def ex(i):
        if i == RING and t > cue('g5')[1] - 0.3: return dict(look=1.0, head=-6)
        return dict(look=0.8 if land > 0.5 else 0.3)
    draw_lifting(fr, V, cx, cy, t, land=land, face=1, extra=ex)
    # Zirak peeks out, then hops out of his hole
    z1 = cue('z1')
    peek = sm(cue('g5')[1] + 1.0, cue('g5')[1] + 1.6, t)
    out_t = word_time('z1', "oh,") - 0.2
    hop_u = clamp((t - out_t) / 0.8)
    if peek > 0 and hop_u <= 0:
        mouse(p, V, HOLE[0] - 2 + 4 * peek, HOLE[1] + 26 - 8 * peek, t, face=-1, sc=1.45 * (0.6 + 0.4 * peek), head_only=1,
              look=1.0)
    elif hop_u > 0:
        mx = lerp(HOLE[0] - 10, MOUSE_X, hop_u)
        my = GY + 14 - 70 * math.sin(math.pi * hop_u)
        mouse(p, V, mx, my, t, face=-1, look=1.0, arm=-110 * spk('Z', t) - 20)
    if cue('g5')[1] < t < cue('g5')[1] + 1.6:
        put_text(fr, A['q'], HOLE[0], HOLE[1] - 70, env(t, cue('g5')[1], cue('g5')[1] + 1.6, 0.2, 0.3))
    return fr

def chew_frame(t):
    a, b = SB("chew")
    fr = A['rock'].copy(); p = Pen(fr); V = S(SS)
    n9 = cue('n9')
    # order of freeing: everyone except the Ring-Dove, then the Ring-Dove last
    order = [5, 4, 2, 1, 0, RING]
    t0 = n9[1] + 0.3; step = (n9[2] - 0.4) / len(order)
    free_at = {i: t0 + k * step for k, i in enumerate(order)}
    trapped = [i for i in range(len(FLOCK)) if t < free_at[i] + 0.3]
    # mouse position: chews along the net
    if t < t0:
        mx = MOUSE_X; chew = 0
    else:
        nxt = [i for i in order if t < free_at[i] + 0.3]
        target = (RX + FLOCK[nxt[0]][0] + 46) if nxt else MOUSE_X
        mx = lerp(MOUSE_X, min(MOUSE_X, target), sm(t0 - 0.3, t0 + 0.3, t)) if nxt else lerp(RX + 70, MOUSE_X, sm(free_at[RING] + 0.3, free_at[RING] + 1.2, t))
        chew = 1 if nxt else 0
    for i in range(len(FLOCK)):
        gx, gy = ground_pos(i, RX)
        if i in trapped:
            look = 1.0 if i == RING else (0.8 if gx < mx else -0.6)
            dove(p, V, i, gx, gy, t, look=look, head=-4 if i == RING else 0)
        else:
            u = clamp((t - free_at[i] - 0.3) / 1.2)
            tx, ty = 300 + 120 * order.index(i), 210 + 30 * (order.index(i) % 2)
            dove(p, V, i, lerp(gx, tx, sm(0, 1, u)), lerp(gy, ty, sm(0, 1, u)) + 6 * math.sin(t * 4 + i), t, fly=1,
                 face=1 if order.index(i) % 2 else -1)
    if trapped:
        xs = [RX + FLOCK[i][0] for i in trapped]
        dome_net(p, V, min(xs) - 64, max(xs) + 64, h=115 if len(trapped) > 1 else 100, t=t)
    else:
        # bits of chewed rope on the grass
        for k in range(7):
            q = RX - 160 + k * 52
            p.line(V, [(q, GY + 12), (q + 18, GY + 6 + 3 * (k % 3))], ROPE, 2.4)
    z = spk('Z', t)
    mouse(p, V, mx, GY + 14, t, face=-1, chew=chew, arm=(-70 if chew else -30 - 80 * z), arm2=-70 if chew else -20,
          head=(14 if chew else 0), look=1.0 if not chew else 0.3)
    if chew:
        put_text(fr, A['nib'], mx - 10, GY - 140 + 6 * math.sin(t * 6), env(t, t0, free_at[RING] + 0.3, 0.3, 0.3))
    return fr

def friends_frame(t):
    a, b = SB("friends"); lt = t - a
    fr = A['rock'].copy(); p = Pen(fr); V = S(SS)
    # the doves fly down and stand around Zirak
    u = sm(a, a + 1.6, t)
    spots = [(255, 1), (335, 1), (415, 1), (495, 1), (690, -1), (590, -1)]
    order = [5, 4, 2, 1, 0, RING]
    for k, i in enumerate(order):
        tx, ty = 300 + 120 * k, 210 + 30 * (k % 2)
        sx, f = spots[k]
        x, y = lerp(tx, sx, u), lerp(ty, GY + 4, u)
        dove(p, V, i, x, y, t, fly=1 if u < 0.95 else 0, face=f if u > 0.5 else 1,
             hop=6 * abs(math.sin(t * 5 + i)) * sm(cue('n10')[1], cue('n10')[1] + 0.5, t), look=0.6)
    # the crow lands on the rock
    r2 = cue('r2')
    cu = sm(a - 0.2, r2[1] - 0.1, t)
    crow(p, V, lerp(-80, 912, cu), lerp(140, 462, cu) - 60 * math.sin(math.pi * cu), t, face=-1, fly=1 if cu < 0.97 else 0,
         look=1.0, head=8)
    mouse(p, V, MOUSE_X, GY + 14, t, face=1 if t < cue('n10')[1] else -1, look=1.0,
          head=-22 if r2[1] - 0.5 < t < cend('z4') else 0,
          arm=-150 * env(t, cue('z4')[1] + 1.0, cend('z4') + 0.6, 0.2, 0.3) - 30)
    if t > cue('n10')[1]:
        for j in range(8):
            ph = (lt * 0.25 + j / 8) % 1
            M = V @ T(330 + j * 80 + 20 * math.sin(lt + j), 560 - 260 * ph) @ R(t * 50) @ S(0.5 + 0.5 * math.sin(math.pi * ph))
            p.poly(M, khatam(0, 0, 10), "#f2c14e", outline="#b9802a", w=1)
    return fr

def render(i):
    t = i / FPS
    name, lt, sd = tl.scene_at(t)
    if name is None: name, lt, sd = "end", 4.0, 4.6
    if name.startswith("tree"): fr = tree_frame(name, t)
    elif name in ("title", "end"): fr = card_frame(t, name)
    else: fr = globals()[name + "_frame"](t)
    fr.alpha_composite(A['border'])
    img = fr.convert('RGB').resize((W, H), Image.LANCZOS)
    f = min(clamp(lt / 0.35), clamp((sd - lt) / 0.35))
    if name == "tree_open": f = min(clamp(lt / 0.7), clamp((sd - lt) / 0.35))
    if name == "end": f = min(clamp(lt / 0.35), clamp((sd - lt) / 0.8))
    if name == "meadow": f = clamp(lt / 0.35)
    if name in ("flock", "caught", "together", "chew"): f = 1.0          # one continuous shot
    if name == "fly": f = clamp((sd - lt) / 0.35)
    if name == "rock": f = clamp(lt / 0.35)
    if name == "friends": f = clamp((sd - lt) / 0.35)
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
    a, b = sc['tree_open']; seq(a + 0.2, 0.32, playful, 0.7, end=b - 0.2); tombak(a + 0.2, b - 0.3, 0.64, 0.3)
    a, b = sc['title']; seq(a + 0.2, 0.3, ["A3", "D4", "Ek4", "F4", "Ek4", "D4", "C4", "D4", "-", "A4"], 0.9)
    a, b = sc['meadow']; seq(a + 0.2, 0.42, flow, 0.55, 1.8, end=cue('h1')[1] - 0.3)
    seq(cue('h1')[1] - 0.3, 0.38, sneaky, 0.55, 1.6, end=b)
    a, b = sc['flock']; seq(a + 0.1, 0.28, happy, 0.6, 1.2, end=cue('g1')[1])
    riz(cue('g1')[1], b, 'A3', 0.22, swell=True)
    a, b = sc['caught']
    seq(a, 0.3, ["D4", "F4", "A4", "-", "G4", "F4"], 0.5, 1.2, end=SNAP - 0.2)
    add(mus, SNAP, dum(0.8), 1.0); seq(SNAP, 0.1, ["Ek4", "D4", "C4", "A3"], 0.7, 1.4)
    riz(SNAP + 1.0, b, 'D3', 0.22)
    a, b = sc['together']
    seq(a + 0.2, 0.6, ["D4", "-", "F4", "-", "A4", "-", "G4", "F4", "Ek4", "D4", "-", "-"], 0.5, 1.8, end=cue('g3')[1])
    g3 = cue('g3')
    for k in range(3): add(mus, g3[1] + g3[2] * (0.12 + 0.24 * k), santur(NOTES[["A3", "D4", "F4"][k]], 1.0), 0.8)
    a, b = sc['fly']
    seq(a, 0.07, ["D4", "Ek4", "F4", "G4", "A4", "Bb4", "C5", "D5"], 0.8, 0.9)
    seq(a + 0.7, 0.25, happy + ["D5", "-", "A4", "-"], 0.7, 1.2, end=b - 0.2); tombak(a + 0.7, b - 0.2, 0.5, 0.45)
    a, b = sc['chase']; seq(a + 0.1, 0.24, ["D4", "F4", "A4", "F4", "G4", "A4", "Bb4", "A4", "G4", "F4", "Ek4", "F4"], 0.6, 1.0,
                            end=cue('h4')[1]); tombak(a + 0.1, cue('h4')[1], 0.4, 0.5)
    seq(cue('h4')[1] + 0.2, 0.5, ["A3", "-", "G3", "-", "F3", "-", "D3", "-", "-", "-"], 0.5, 1.8, end=b)
    a, b = sc['rock']; seq(a + 0.2, 0.36, flow, 0.55, 1.6, end=b - 0.2)
    a, b = sc['chew']; seq(a + 0.2, 0.5, ["D4", "-", "C4", "D4", "F4", "-", "Ek4", "D4", "-", "-"], 0.45, 2.0, end=cue('n9')[1])
    n9 = cue('n9'); seq(n9[1], 0.2, playful, 0.55, 1.0, end=cend('n9'))
    for k in range(int(n9[2] / 0.12)): add(sfx, n9[1] + 0.3 + k * 0.12, tak(0.05, seed=k + 7), 0.5)
    a, b = sc['friends']; seq(a + 0.2, 0.26, happy, 0.6, 1.2, end=b - 0.2); tombak(cue('n10')[1], b - 0.3, 0.5, 0.4)
    a, b = sc['tree_close']; seq(a + 0.2, 0.36, ["D4", "-", "F4", "G4", "A4", "-", "Bb4", "A4", "G4", "-", "F4", "Ek4", "D4", "-", "-", "-"], 0.6, end=b - 0.2)
    c3 = cue('c3'); seq(c3[1] - 0.3, 0.1, ["D5", "A4", "D5", "F4"], 0.5, 1.6)
    a, b = sc['end']
    seq(a + 0.2, 0.3, ["D4", "F4", "A4", "D5", "-", "C5", "A4", "Bb4", "A4", "-", "-", "D4"], 0.85)
    for nn in ("D3", "A3", "D4"): add(mus, a + 3.3, santur(NOTES[nn], 2.0), 0.8)
    mus += (np.sin(2 * np.pi * NOTES['D2'] * t) + 0.5 * np.sin(2 * np.pi * NOTES['A2'] * t)) * 0.05
    # sfx: wing flutters, the net snap
    a, b = sc['flock']; add(sfx, a, flutter(4.5), 0.6)
    add(sfx, SNAP, tak(0.12, seed=3), 2.5)
    add(sfx, SNAP + 0.05, flutter(2.4, 15, 4), 0.8)
    add(sfx, cue('n5')[1], flutter(cue('n5')[2], 15, 5), 0.6)
    a, b = sc['fly']; add(sfx, a, flutter(b - a, 13, 6), 0.9)
    a, b = sc['rock']; add(sfx, a, flutter(cend('n8') - a, 13, 8), 0.5)
    # meadow breeze
    br = noise(N, 3) * (0.55 + 0.45 * np.sin(2 * np.pi * t / 6.5) ** 2)
    gate = np.zeros(N)
    for nm in ("meadow", "flock", "caught", "together", "fly", "chase", "rock", "chew", "friends"):
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
    tl.srt(os.path.join(EP, "ep03.en.srt"), NAMES_EN)
    write_fa_srt(os.path.join(EP, "ep03.fa.srt"))
    out = os.path.join(EP, "render_ep03.mp4")
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
