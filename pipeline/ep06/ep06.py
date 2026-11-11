#!/usr/bin/env python3
"""Kalila & Dimna — Episode 6: The Tortoise and the Two Ducks (~3.2 min).
Adapted from ep05/ep05.py (itself from ep03) (same timeline helper, hosts, cards, word card, LOOK pass, render + audio)."""
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
tl.scene("pond", ["n1", 0.3, "n2", 0.3, "t1", 0.3, "a1"], lead=1.4, tail=0.6)
tl.scene("dry", ["n3", 0.3, "b1", 0.2, "a2", 0.3, "t2", 0.3, "b2"], lead=0.6, tail=0.6)
tl.scene("idea", ["a3", 0.3, "b3", 0.3, "t3"], lead=0.6, tail=0.6)
tl.scene("lift", ["n4", 0.3, "n5"], lead=0.4, tail=1.2)
tl.scene("village", ["n6", 0.3, "y1", 0.1, "z1", 0.3, "n7", 0.3, "a4", 0.3, "t4"], lead=0.8, tail=0.5)
tl.scene("fall", ["n8", 0.2, "n9", 0.4, "b4"], lead=0.2, tail=1.0)
tl.scene("hay", ["t5", 0.4, "a5"], lead=1.2, tail=1.0)
tl.scene("lake", ["n10", 0.4, "t6", 0.4, "n11"], lead=0.6, tail=1.8)
tl.scene("tree_close", ["x1", "x2", 0.4, "x3", "x4", 1.4, "x5"], lead=0.8, tail=1.0)
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
CW = 4700                    # one wide world: little pond (left), hills, the village with the haystack, the big blue lake (right)
POND = (700, 652)            # the little pond (it dries up)
VX = 3000                    # village centre
VCAM = VX - 640
HAY = (VX + 130, 652)        # the soft haystack
KIDX = (VX - 340, VX - 215)  # girl, boy
LK = 4330                    # the big blue lake
CAMMAX = CW - W
WATER = "#5fa6c9"; MUD = "#9a8a5c"
TS = 1.15                    # tortoise scale
DA, DB = 1.25, 1.12
BOFF, AOFF = 265, 215        # duck offsets from the group centre when flying with the stick          # duck scales (A = white duck, B = little brown duck)

# ------------------------------------------------------------------ backgrounds
def sky(hh, ww, top=(236, 200, 120), bot=(250, 238, 206)):
    g = np.linspace(0, 1, hh)[:, None]
    col = (np.array(top, float) * (1 - g) + np.array(bot, float) * g).astype(np.uint8)
    return Image.fromarray(np.ascontiguousarray(np.broadcast_to(col[:, None, :], (hh, ww, 3))), 'RGB')

def hills(p, M, x1, base, amp, sd, wl, col, oc):
    xs = np.arange(0, x1 + 20, 8)
    y = base - amp * (0.55 + 0.45 * np.sin(xs / wl + sd) * np.sin(xs / (wl * 0.41) + sd * 2))
    p.poly(M, list(zip(xs, y)) + [(x1 + 20, H), (0, H)], col, outline=oc, w=2)

def sun(p, M, x, y, r=40, rot=0.0, col="#f2c14e", ray="#e9a93a"):
    for k in range(16):
        a = math.radians(k * 22.5 + rot)
        p.poly(M, [(x + r * math.cos(a - 0.12), y + r * math.sin(a - 0.12)), (x + r * 1.55 * math.cos(a), y + r * 1.55 * math.sin(a)),
                   (x + r * math.cos(a + 0.12), y + r * math.sin(a + 0.12))], ray, outline=None)
    p.poly(M, ell(x, y, r, r, 40), col, outline="#b9802a", w=2)

def grass(p, M, rng, x0, x1, n, skip=None):
    for _ in range(n):
        fx, fy = rng.uniform(x0, x1), rng.uniform(GY - 50, 712)
        if skip and skip(fx, fy): continue
        if rng.random() < 0.6: p.line(M, [(fx - 3, fy), (fx, fy - 7), (fx + 3, fy)], "#5f7a3a", 1.2)
        else: flower(p, M, fx, fy, ["#c8423a", "#fff7ea", "#3d6db5", "#d96f9a"][rng.integers(4)])

def reeds(p, M, x, base, rng, n=5):
    for k in range(n):
        xx = x + k * 9 + rng.uniform(-3, 3); hh = rng.uniform(60, 110); lean = rng.uniform(-8, 8)
        p.line(M, [(xx, base), (xx + lean * 0.5, base - hh * 0.6), (xx + lean, base - hh)], "#4f7a3a", 3)
        if rng.random() < 0.6:
            p.poly(M, ell(xx + lean * 0.9, base - hh + 4, 4.5, 13, 14), "#7a4c2a", w=1.5)

def house(p, M, x, base, w, h, dome=False, col="#d9b98a"):
    p.poly(M, [(x - w / 2, base), (x - w / 2, base - h), (x + w / 2, base - h), (x + w / 2, base)], col, w=2.5)
    p.poly(M, [(x - w / 2 - 6, base - h), (x + w / 2 + 6, base - h), (x + w / 2 + 6, base - h + 10), (x - w / 2 - 6, base - h + 10)], "#b9966a", w=2)
    if dome:
        p.poly(M, ell(x, base - h, w * 0.32, w * 0.3, 30, 180, 360), "#e2c79a", w=2.5)
    p.poly(M, [(x - 12, base), (x - 12, base - 40), (x, base - 50), (x + 12, base - 40), (x + 12, base)], "#6b4a2a", w=2)
    for sx in (-w * 0.32, w * 0.32):
        p.poly(M, [(x + sx - 9, base - h + 26), (x + sx + 9, base - h + 26), (x + sx + 9, base - h + 46), (x + sx - 9, base - h + 46)], "#3b5f7a", w=1.5)

LAKE_POLY = [(LK - 380, 600), (LK - 330, 552), (LK - 160, 534), (LK + 120, 530), (LK + 330, 540), (LK + 400, 580), (LK + 420, 720), (LK - 400, 720)]
def build_world():
    img = sky(H * SS, CW * SS); p = Pen(img); V = S(SS); rng = np.random.default_rng(66)
    sun(p, V, 1040, 110)
    for x in range(160, CW, 440):
        cloud(p, V, x + rng.uniform(-60, 60), rng.uniform(70, 210), rng.uniform(0.7, 1.05))
    hills(p, V, CW, 430, 70, 0.4, 230, "#d9b6a3", "#9c7a68")
    hills(p, V, CW, 505, 60, 1.7, 150, "#b9ba86", "#7f8156")
    for x in (90, 1240, 1500, 1700, 2050, 2200, 3700, 3850, 4640):
        cypress(p, V, x, 580, rng.uniform(170, 230), 22)
    for x in (230, 1380, 1880, 2350, 3560):
        blossom_tree(p, V, x, 588, rng)
    gp = [(x, 572 + 6 * math.sin(x / 90)) for x in range(0, CW + 10, 10)] + [(CW + 10, H), (0, H)]
    p.poly(V, gp, "#93ad62", outline="#5f7a3a", w=2)
    # the village (houses behind the children)
    for x, w_, h_, dm in ((VX - 520, 130, 110, True), (VX - 360, 110, 90, False), (VX - 40, 120, 100, True),
                          (VX + 360, 120, 96, False), (VX + 520, 140, 120, True)):
        house(p, V, x, 590, w_, h_, dm, ["#d9b98a", "#e6c9a0", "#cfae80"][int(x) % 3])
    p.poly(V, [(VX - 600, 590), (VX + 600, 590), (VX + 600, 600), (VX - 600, 600)], "#c2a074", w=2)
    # the big blue lake
    p.poly(V, LAKE_POLY, "#d8cdb6", outline=OUT, w=2.5)
    p.poly(V, [(q[0] + (8 if q[0] < LK else -8), q[1] + 8) for q in LAKE_POLY[:-2]] + [(LK + 412, 720), (LK - 392, 720)], WATER, outline=None)
    for k in range(12):
        x = LK - 300 + (k * 97) % 640; y = 560 + (k * 37) % 140
        p.line(V, [(x, y), (x + 50, y)], "#a9d6e8", 1.6)
    for x in (LK + 380, LK + 404):
        reeds(p, V, x, 640, rng, 3)
    # reeds around the little pond
    for x in (POND[0] - 360, POND[0] - 336, POND[0] + 330, POND[0] + 356):
        reeds(p, V, x, 650, rng, 3)
    haystack(p, V, HAY[0], HAY[1], 1.0)
    grass(p, V, rng, 0, CW, 1300, lambda x, y: (POND[0] - 350 < x < POND[0] + 350 and 590 < y < 720)
          or (LK - 420 < x < LK + 430 and y < 730) or (HAY[0] - 160 < x < HAY[0] + 160 and y < 660))
    return img

def pond(p, V, t, water):
    """the little pond: a mud bed, and water that shrinks as it dries (water 1 = full)"""
    p.poly(V, ell(POND[0], POND[1], 330, 62, 48), "#8a7444" if water < 1 else "#d8cdb6", outline=OUT, w=2.5)
    p.poly(V, ell(POND[0], POND[1] + 3, 318, 54, 48), MUD if water < 1 else "#d8cdb6", outline=None)
    if water < 1:
        for k in range(9):
            x = POND[0] - 260 + 64 * k; y = POND[1] - 20 + (k * 17) % 40
            p.line(V, [(x, y), (x + 14, y + 8), (x + 10, y + 18), (x + 26, y + 22)], "#6e5a34", 1.5)
    if water > 0.02:
        p.poly(V, ell(POND[0] + 10 * (1 - water), POND[1] + 4, 316 * water, 52 * water ** 0.7, 48), WATER, outline=None)
        for k in range(int(6 * water) + 1):
            x = POND[0] - 200 * water + (k * 71) % max(1, int(400 * water)); y = POND[1] - 20 * water + (k * 23) % max(1, int(40 * water))
            p.line(V, [(x, y), (x + 40 * water, y)], "#a9d6e8", 1.6)

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
    fa_text(d, (w / 2 * SS, 98 * SS), "لاک‌پشت", 74 * SS, (28, 52, 99, 255))
    f2 = ImageFont.truetype(FB, 32 * SS)
    d.text((w / 2 * SS, 166 * SS), "laak-posht  =  tortoise", font=f2, fill=(90, 50, 12, 255), anchor="mm")
    return im

def init():
    ME.init_assets()
    A['border'] = ME.ASSETS['border']; A['card'] = ME.ASSETS['card']
    A['tree'] = build_tree_set().convert('RGBA')
    A['world'] = build_world().convert('RGBA')
    A['wcard'] = build_word_card()
    gold, cream = (226, 182, 74, 255), (250, 240, 214, 255)
    A['t1'] = text_img("KALILA & DIMNA", FB, 60, gold, 2, (90, 60, 12, 255))
    A['t2'] = text_img("The Tortoise and the Two Ducks", FI, 46, cream)
    A['t3'] = text_img("—  Episode 6  —", FR, 24, gold)
    A['e1'] = text_img("Next time", FI, 30, cream)
    A['e2'] = text_img("The Three Fish", FB, 44, gold, 2, (90, 60, 12, 255))
    A['e3'] = text_img("A new story every Saturday", FR, 26, cream)
    A['bang'] = text_img("!", FB, 54, (200, 40, 30, 255), 3, (255, 255, 255, 255))
    A['idea'] = text_img("!", FB, 60, (226, 182, 74, 255), 3, (40, 24, 10, 255))
    A['blah'] = text_img("blah blah blah...", FI, 30, (90, 50, 12, 255))
    A['shh'] = text_img("Shhh!", FB, 34, (250, 240, 214, 255), 3, (40, 24, 10, 255))
    A['flump'] = text_img("FLUMP!", FB, 56, (226, 182, 74, 255), 3, (90, 40, 12, 255))
    A['haha'] = text_img("ha ha!", FI, 32, (90, 50, 12, 255))
    A['mm'] = text_img("mm-hmm!", FI, 32, (90, 50, 12, 255))
    A['oops'] = text_img("Oh no!", FB, 40, (200, 40, 30, 255), 3, (255, 255, 255, 255))

# ------------------------------------------------------------------ actors
TORT = dict(beard=False, shell="#2f6f6a", band="#d4a63c")
def tort_po(t, **kw):
    po = dict(t=t, mouth=spk('T', t), blink=blink(t, 0.7), look=0.5); po.update(TORT); po.update(kw)
    return po

def tortoise(p, V, x, y, t, face=1, sc=TS, rot=0.0, **kw):
    return draw_tortoise(p, V @ T(x, y) @ R(rot) @ S(sc * face, sc), tort_po(t, **kw))

def tort_mouth_off(t, face=1, sc=TS, head=0.0, rot=0.0):
    """where the tortoise's mouth is, relative to its origin (so it can hang from the stick)"""
    nod = head + 2 * math.sin(t * 1.2)
    q = ap(R(rot) @ S(sc * face, sc) @ T(62, -44) @ R(nod) @ S(1.35) @ T(34, -3), [(0, 0)])[0]
    return q[0], q[1]

def duck(p, V, who, x, y, t, face=1, **kw):
    kind, sc, off = ("white", DA, 0.3) if who == 'A' else ("brown", DB, 1.9)
    po = dict(t=t, mouth=spk(who, t), blink=blink(t, off), look=0.4); po.update(kw)
    return draw_duck(p, V @ T(x, y) @ S(sc * face, sc), kind, po)

def child(p, V, kind, x, t, **kw):
    who = 'Y' if kind == "girl" else 'Z'
    po = dict(t=t, mouth=spk(who, t), blink=blink(t, 0.9 if who == 'Y' else 2.2)); po.update(kw)
    draw_child(p, V @ T(x, GY + 10) @ S(1.05), kind, po)

def pt(M): q = ap(M, [(0, 0)])[0]; return q[0] / SS, q[1] / SS

def stick(p, a, b):
    """the stick between two points (screen coords at 1x)"""
    for col, w in ((OUT, 9), ("#9c6a3a", 5.5)):
        p.line(S(SS), [a, b], col, w)
    p.line(S(SS), [(a[0] * 0.7 + b[0] * 0.3, a[1] * 0.7 + b[1] * 0.3 - 1.5), (a[0] * 0.4 + b[0] * 0.6, a[1] * 0.4 + b[1] * 0.6 - 1.5)], "#c49a6a", 1.4)

def trio(p, V, cam, gx, gy, t, flap_speed=8.0, tk=None, ak=None, bk=None, hold=True):
    """the two ducks flying with the stick and the tortoise hanging from its middle.
    gx, gy = world position of the group (gy = the ducks' body line). Returns (tortoise mouth point (screen), r_tort)."""
    tk = tk or {}; ak = ak or {}; bk = bk or {}
    bob = 5 * math.sin(t * 3.0)
    rb = duck(p, V, 'B', gx - BOFF, gy + bob + 6 * math.sin(t * 3 + 1), t, **{**dict(fly=1, flap=t * flap_speed + 1.3, head=38), **bk})
    rbb = pt(rb['mid'])
    # the white duck is drawn later (in front); work out its bill first by drawing it on a scratch pen
    ra = duck(Pen(Image.new('RGBA', (8, 8))), V, 'A', gx + AOFF, gy + bob, t, **{**dict(fly=1, flap=t * flap_speed, head=38), **ak})
    rab = pt(ra['mid'])
    mid = ((rbb[0] + rab[0]) / 2, (rbb[1] + rab[1]) / 2 + 3)
    r = None
    if hold:
        stick(p, rbb, rab)
        hd = tk.pop('head', -18); rot = tk.pop('rot', 0.0)
        ox, oy = tort_mouth_off(t, 1, TS, hd, rot)
        r = draw_tortoise(p, S(SS) @ T(mid[0] - ox, mid[1] - oy) @ R(rot) @ S(TS),
                          tort_po(t, head=hd, walk=t * 7, amp=1, **tk))
    if hold: duck(p, V, 'A', gx + AOFF, gy + bob, t, **{**dict(fly=1, flap=t * flap_speed, head=38), **ak})
    return mid, r, rbb, rab

def world_view(cam):
    cx = int(round(cam * SS))
    return A['world'].crop((cx, 0, cx + W * SS, H * SS)), S(SS) @ T(-cam, 0)

# ------------------------------------------------------------------ scenes
KX, DX, HS = 420, 850, 1.32
def tree_frame(name, t):
    fr = A['tree'].copy(); p = Pen(fr); V = S(SS)
    kpo = jackal_pose('kalila', t, spk('K', t), look=0.6)
    dpo = jackal_pose('dimna', t, spk('D', t), look=0.6)
    if name == "tree_close":
        c3 = cue('x3')
        if c3[1] < t < c3[1] + 1.0: dpo['hop'] = 30 * abs(math.sin(math.pi * (t - c3[1]) / 0.5))
    if name == "tree_open":
        o2 = cue('o2')
        if o2[1] < t < o2[1] + 0.8: kpo['hop'] = 22 * abs(math.sin(math.pi * (t - o2[1]) / 0.8))     # Kalila jumps: "A flying tortoise?"
    draw_jackal(p, V @ T(DX, 640) @ S(-HS, HS), 'dimna', dpo)
    bush(p, V, 1125, 650, 1.35, 0)
    draw_jackal(p, V @ T(KX, 640) @ S(HS), 'kalila', kpo)
    if name == "tree_close":
        a0, a1 = cue('x3')[1] - 0.3, cend('x4') + 1.2
        al = min(sm(a0, a0 + 0.5, t), 1 - sm(a1 - 0.4, a1, t))
        if al > 0:
            sc = 0.85 + 0.15 * sm(a0, a0 + 0.5, t)
            card = A['wcard'] if sc > 0.999 else A['wcard'].resize((int(A['wcard'].width * sc), int(A['wcard'].height * sc)), Image.LANCZOS)
            put_text(fr, card, W / 2 + 20, 165, al)
        # a duck flies by during the moral
        c2 = cue('x2'); u = (t - c2[1]) / 3.0
        if 0 < u < 1:
            draw_duck(p, V @ T(lerp(-80, 1360, u), 150 - 40 * math.sin(math.pi * u)) @ S(0.8), "white",
                      dict(t=t, fly=1, flap=t * 9, look=0.4))
    return fr

CARD_DUMMY = None

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

def stick_mid(gx, gy, t, cam):
    scratch = Pen(Image.new('RGBA', (8, 8))); V = S(SS) @ T(-cam, 0); bob = 5 * math.sin(t * 3.0)
    rb = duck(scratch, V, 'B', gx - BOFF, gy + bob + 6 * math.sin(t * 3 + 1), t, fly=1, flap=0, head=38)
    ra = duck(scratch, V, 'A', gx + AOFF, gy + bob, t, fly=1, flap=0, head=38)
    pb, pa = pt(rb['mid']), pt(ra['mid'])
    return ((pb[0] + pa[0]) / 2, (pb[1] + pa[1]) / 2 + 3)

def swim_duck(p, V, who, x, y, t, face=1, **kw):
    """a duck swimming: body sits in the water (a water patch hides the lower body)"""
    sc = DA if who == 'A' else DB
    bob = 2.5 * math.sin(t * 2.4 + (who == 'B'))
    r = duck(p, V, who, x, y + 14 * sc + bob, t, face=face, swim=1, **kw)
    p.poly(V, ell(x - 4 * face, y + 6 * sc + bob, 54 * sc, 9 * sc, 30), WATER, outline=None)
    p.line(V, ell(x - 4 * face, y + 2 * sc + bob, 50 * sc, 5 * sc, 26, 0, 180), "#a9d6e8", 2)
    return r

PCAM = POND[0] - 640          # camera that centres the little pond
TB = (330, GY + 4)            # the tortoise's spot on the left bank
def pond_frame(t):
    """the three friends at the little pond; the tortoise talks and talks"""
    a, b = SB("pond")
    fr, V = world_view(PCAM); fr = fr.copy(); p = Pen(fr)
    pond(p, V, t, 1.0)
    t1 = cue('t1'); a1 = cue('a1')
    swim_duck(p, V, 'B', POND[0] - 60 + 30 * math.sin(t * 0.4), POND[1] - 8, t, face=-1 if t > t1[1] else 1, look=0.6,
              sad=0.4 * sm(t1[1] + 2, t1[1] + 3, t))
    swim_duck(p, V, 'A', POND[0] + 120 - 20 * math.sin(t * 0.5), POND[1] + 10, t, face=-1, look=0.6,
              head=8 * env(t, a1[1], cend('a1'), 0.2, 0.3) * math.sin(t * 9))
    u = sm(word_time('n2', 'talk') - 0.4, t1[1] + 0.2, t)
    tortoise(p, V, lerp(TB[0] - 40, TB[0] + 40, u), TB[1], t, walk=t * 6, amp=1 if 0.01 < u < 0.99 else 0,
             hop=6 * spk('T', t) * abs(math.sin(t * 7)), head=-6 * spk('T', t))
    if t1[1] + 0.6 < t < cend('t1') + 0.4:
        put_text(fr, A['blah'], TB[0] + 120 - PCAM, 470 - 10 * math.sin(t * 3), env(t, t1[1] + 0.6, cend('t1') + 0.4, 0.2, 0.3))
    return fr

def dry_frame(t):
    """the hot summer: the pond dries up"""
    a, b = SB("dry")
    fr, V = world_view(PCAM); fr = fr.copy(); p = Pen(fr)
    n3 = cue('n3'); b1 = cue('b1'); a2 = cue('a2'); t2 = cue('t2'); b2 = cue('b2')
    hot = sm(a, word_time('n3', 'no rain'), t)
    sun(p, V, 1040, 110, 40 + 16 * hot, rot=t * 8, col="#f2b04e", ray="#e9893a")
    dry = sm(word_time('n3', 'Day by day') - 0.2, cend('n3') + 0.6, t)
    water = lerp(1.0, 0.2, dry)
    pond(p, V, t, water)
    # heat shimmer lines
    for k in range(4):
        ph = (t * 0.5 + k / 4) % 1
        x = POND[0] - 200 + 130 * k
        p.line(V, [(x, 560 - 60 * ph), (x + 6, 548 - 60 * ph), (x, 536 - 60 * ph), (x + 6, 524 - 60 * ph)], "#e9a93a", 1.4)
    sad = sm(b1[1] - 0.3, b1[1] + 0.3, t)
    if dry < 0.55:
        swim_duck(p, V, 'B', POND[0] - 60, POND[1] - 8, t, face=1, look=0.6)
        swim_duck(p, V, 'A', POND[0] + 120, POND[1] + 10, t, face=-1, look=0.6)
    else:
        # standing in the mud now; the little duck walks to the tortoise when she promises
        wb = sm(b2[1] - 0.4, b2[1] + 1.2, t)
        duck(p, V, 'B', lerp(POND[0] - 60, TB[0] + 250, wb), lerp(POND[1] + 6, GY + 4, wb), t, face=-1 if wb > 0.01 else 1,
             sad=sad * (1 - wb), walk=t * 10, amp=1 if 0.01 < wb < 0.99 else 0, look=0.6,
             wing=-30 * env(t, b2[1] + 0.3, cend('b2'), 0.3, 0.3))
        duck(p, V, 'A', POND[0] + 120, POND[1] + 12, t, face=-1, sad=sad, look=0.6,
             wing=-50 * env(t, word_time('a2', 'big'), cend('a2'), 0.3, 0.4), head=-12 * env(t, word_time('a2', 'far'), cend('a2'), 0.3, 0.3))
    tsad = sm(t2[1] - 0.2, t2[1] + 0.3, t) * (1 - 0.6 * sm(b2[1] + 0.5, cend('b2'), t))
    tortoise(p, V, TB[0] + 40, TB[1], t, sad=-1.2 * tsad, head=-10 * tsad, look=0.8,
             hop=16 * env(t, t2[1], t2[1] + 0.6, 0.15, 0.3))
    if b1[1] < t < cend('b1') + 0.3:
        put_text(fr, A['bang'], POND[0] - 60 - PCAM, 470, env(t, b1[1], cend('b1') + 0.3, 0.15, 0.3))
    return fr

IB, IT, IA = 470, 700, 910                   # idea scene: little duck, tortoise, white duck (world x)
def idea_frame(t):
    """the white duck's idea: a stick! and the warning: not one word"""
    a, b = SB("idea")
    fr, V = world_view(PCAM); fr = fr.copy(); p = Pen(fr)
    pond(p, V, t, 0.2)
    a3 = cue('a3'); b3 = cue('b3'); t3 = cue('t3')
    stick(p, (IT - 170 - PCAM, GY + 36), (IT + 150 - PCAM, GY + 30))
    duck(p, V, 'B', IB, GY + 4, t, face=1, look=0.6, wing=-40 * env(t, b3[1], cend('b3'), 0.3, 0.3),
         head=10 * env(t, word_time('b3', 'Not one'), cend('b3'), 0.2, 0.3) * math.sin(t * 8))
    happy = sm(t3[1], t3[1] + 0.5, t)
    tortoise(p, V, IT - 20, GY + 4, t, look=0.8 - 1.4 * (b3[1] < t < cend('b3')), hop=12 * happy * abs(math.sin(t * 5)) * (t < cend('t3')),
             head=-8 * spk('T', t))
    duck(p, V, 'A', IA, GY + 4, t, face=-1, look=0.6, wing=-45 * env(t, word_time('a3', 'stick') - 0.2, cend('a3'), 0.3, 0.4),
         head=18 * env(t, word_time('a3', 'bite'), cend('a3'), 0.3, 0.3))
    if a3[1] - 0.2 < t < a3[1] + 1.4:
        put_text(fr, A['idea'], IA - PCAM + 10, 470, env(t, a3[1] - 0.2, a3[1] + 1.4, 0.15, 0.3))
    if word_time('b3', 'Not one') < t < cend('b3') + 0.3:
        put_text(fr, A['shh'], IB - PCAM + 20, 470, env(t, word_time('b3', 'Not one'), cend('b3') + 0.3, 0.15, 0.3))
    return fr

def lift_frame(t):
    """the tortoise bites the stick, and up, up, up they fly, over the hills"""
    a, b = SB("lift")
    bite = word_time('n4', 'bit')
    fl = word_time('n4', 'flapped')
    up = word_time('n4', 'up, up')
    gx0 = (IB + BOFF + IA - AOFF) / 2 + 10
    u = sm(fl + 0.3, b, t)
    gx = lerp(gx0, gx0 + 1700, u * u * 0.4 + u * 0.6)
    cam = clamp(gx - 640, PCAM, CAMMAX)
    fr, V = world_view(cam); fr = fr.copy(); p = Pen(fr)
    pond(p, V, t, 0.2)
    if t < fl:
        # standing: they pick the stick up, then the tortoise hops up and bites its middle
        pick = sm(a + 0.2, bite - 0.3, t)
        hdn = 38 * pick + 60 * (1 - pick) * sm(a, a + 0.3, t)
        rb = duck(p, V, 'B', gx - BOFF, GY + 4, t, look=0.6, head=hdn)
        ra = duck(Pen(Image.new('RGBA', (8, 8))), V, 'A', gx + AOFF, GY + 4, t, look=0.6, head=hdn)
        pb, pa = pt(rb['mid']), pt(ra['mid'])
        g0, g1 = (IT - 170 - cam, GY + 36), (IT + 150 - cam, GY + 30)
        q0 = (lerp(g0[0], pb[0], pick), lerp(g0[1], pb[1], pick)); q1 = (lerp(g1[0], pa[0], pick), lerp(g1[1], pa[1], pick))
        stick(p, q0, q1)
        mid = ((q0[0] + q1[0]) / 2, (q0[1] + q1[1]) / 2 + 3)
        hb = sm(bite - 0.2, bite + 0.25, t)
        ox, oy = tort_mouth_off(t, 1, TS, -10 * hb)
        tx = lerp(IT - 20, mid[0] + cam - ox, hb); ty = lerp(GY + 4, mid[1] - oy, hb)
        tortoise(p, V, tx, ty, t, head=-10 * hb, mouth=0 if hb > 0.5 else spk('T', t), look=0.8)
        duck(p, V, 'A', gx + AOFF, GY + 4, t, look=0.6, head=hdn)
    else:
        rise = sm(fl, up + 1.6, t)
        gy = lerp(GY - 36, 250, rise)
        trio(p, V, cam, gx, gy, t, flap_speed=10, tk=dict(mouth=0, look=0.8, head=-18 + 8 * math.sin(t * 2)),
             ak=dict(look=0.6), bk=dict(look=0.6))
    return fr

def village_frame(t):
    """over the village: the children laugh; the tortoise gets cross... and opens his mouth"""
    a, b = SB("village")
    fr, V = world_view(VCAM); fr = fr.copy(); p = Pen(fr)
    y1 = cue('y1'); z1 = cue('z1'); n7 = cue('n7'); a4 = cue('a4'); t4 = cue('t4')
    gx = VCAM + lerp(230, 600, sm(a, word_time('n6', 'children'), t)) + 40 * sm(y1[1], b, t)
    gy = 230
    look_up = sm(word_time('n6', 'looked'), word_time('n6', 'looked') + 0.5, t)
    laugh = max(env(t, word_time('n6', 'laughed'), y1[1], 0.2, 0.2), env(t, z1[1], cend('z1') + 0.8, 0.2, 0.4))
    child(p, V, "girl", KIDX[0], t, head=-28 * look_up, look=-1 * look_up, arm2=-150 * sm(y1[1] - 0.3, y1[1] + 0.2, t) * (1 - sm(cend('n7') - 1, cend('n7'), t)) - 10,
          point=y1[1] < t < cend('n7') - 0.5, laugh=laugh * (t < y1[1] or t > cend('y1') + 0.1),
          hop=10 * abs(math.sin(t * 7)) * env(t, y1[1], cend('y1'), 0.1, 0.2))
    child(p, V, "boy", KIDX[1], t, head=-26 * look_up, look=-1, arm2=-130 * sm(z1[1] - 0.3, z1[1] + 0.2, t) * (1 - sm(cend('n7') - 1, cend('n7'), t)) - 10,
          point=z1[1] < t < cend('n7') - 0.5, laugh=laugh, hop=8 * abs(math.sin(t * 8)) * laugh)
    cross = sm(n7[1], n7[1] + 0.6, t)
    opened = t > t4[1] - 0.05
    drop = sm(t4[1] + 0.4, cend('t4') + 0.3, t)
    shake = env(t, a4[1], cend('a4') + 0.2, 0.2, 0.3)
    mid, r, pb, pa = trio(p, V, VCAM, gx, gy, t, flap_speed=8, hold=not opened,
                          tk=dict(mouth=0, sad=1.4 * cross, look=-0.6 + 1.4 * cross, head=-18 + 10 * cross * math.sin(t * 3)),
                          ak=dict(look=-1.0 * shake, head=38 + 12 * shake * math.sin(t * 11), mouth=0),
                          bk=dict(look=-0.5, brow=-0.6 * shake))
    if opened:
        stick(p, pb, pa)
        ox, oy = tort_mouth_off(t, 1, TS, -10)
        tortoise(p, S(SS), mid[0] - ox, mid[1] - oy + 60 * drop * drop, t, head=-10, sad=1.2, look=0.8,
                 mouth=max(spk('T', t), 0.3), walk=t * 14, amp=1)
        duck(p, V, 'A', gx + AOFF, gy + 5 * math.sin(t * 3.0), t, fly=1, flap=t * 8, head=38, mouth=0, look=-1.0)
    if word_time('n6', 'laughed') < t < cend('z1') + 0.6:
        put_text(fr, A['haha'], KIDX[1] - VCAM + 70, 420, env(t, word_time('n6', 'laughed'), cend('z1') + 0.6, 0.2, 0.3))
    if a4[1] - 0.1 < t < cend('a4') + 0.5:
        put_text(fr, A['shh'], gx - VCAM + 250, 140, env(t, a4[1] - 0.1, cend('a4') + 0.5, 0.15, 0.3))
    return fr

def hover_pos(t):
    """where the group is at the end of the village scene (it keeps hovering in the fall scene)"""
    a, b = SB("village"); y1 = cue('y1')
    return VCAM + 600 + 40 * sm(y1[1], b, t), 230

def fall_frame(t):
    """down, down, down... FLUMP! into the soft hay"""
    a, b = SB("fall")
    fr, V = world_view(VCAM); fr = fr.copy(); p = Pen(fr)
    n8 = cue('n8'); n9 = cue('n9'); b4 = cue('b4')
    child(p, V, "girl", KIDX[0], t, head=-28, look=-1, arm=-10, hop=0)
    child(p, V, "boy", KIDX[1], t, head=-26, look=-1, arm=-10)
    gx, gy = hover_pos(SB("village")[1])
    gx += 30 * sm(a, b, t)
    land_d = sm(cend('n9'), b4[1] + 1.2, t)                 # ducks fly down to the haystack
    v0 = word_time('n8', 'Down'); v1 = word_time('n9', 'hay') + 0.1
    # the tortoise: hangs a moment (cartoon pause), then falls and spins onto the hay
    ox, oy = tort_mouth_off(t, 1, TS, -10)
    # the tortoise starts where the village scene left him (60 px under the stick's middle)
    tv = SB("village")[1] - 0.01
    m0 = stick_mid(gx - 30 * sm(a, b, t), gy, tv, VCAM)
    hx0, hy0 = m0[0] + VCAM - ox, m0[1] - oy + 60
    u = clamp((t - v0) / (v1 - v0))
    ex, ey = HAY[0] - 40, HAY[1] - 150
    tx = lerp(hx0, ex, u); ty = lerp(hy0, ey, u * u)
    rot = 720 * (u * u) if u < 1 else 0
    landed = t >= v1
    sink = 10 * env(t, v1, v1 + 0.6, 0.05, 0.4)
    for k in range(8 if landed and t < v1 + 1.6 else 0):            # hay bits fly up
        ph = clamp((t - v1) / 1.4)
        ang = math.radians(200 + k * 20)
        p.poly(V @ T(ex + 30 + 140 * ph * math.cos(ang), ey - 20 - 120 * ph * -math.sin(ang) + 160 * ph * ph) @ R(t * 200 + k * 40),
               [(-8, -2), (8, -2), (8, 2), (-8, 2)], "#f2cf6a", w=1)
    tortoise(p, V, tx, ty + sink, t, rot=rot, head=-10 if not landed else 6 * math.sin(t * 6), sad=0 if landed else 1.2,
             mouth=0.5 if not landed else 0.0, walk=t * 16, amp=1 if not landed else 0, look=0.8 if not landed else -0.4 + 1.2 * math.sin(t * 4))
    if landed and t < b4[1] + 2.0:                           # dizzy stars
        for k in range(5):
            ang = t * 4 + k * 1.256
            M = S(SS) @ T(ex - VCAM + 110 + 40 * math.cos(ang), ey - 90 + 12 * math.sin(ang)) @ S(0.55)
            p.poly(M, khatam(0, 0, 12), "#f2c14e", outline="#b9802a", w=1)
    # the ducks: shocked, then they fly down
    if land_d < 0.01:
        bob = 5 * math.sin(t * 3.0)
        pb = duck(p, V, 'B', gx - BOFF, gy + bob, t, fly=1, flap=t * 9 + 1.3, head=38, look=-1.0, mouth=0)
        pa = duck(p, V, 'A', gx + AOFF, gy + bob, t, fly=1, flap=t * 9, head=38, look=-1.0, mouth=0)
        stick(p, pt(pb['mid']), pt(pa['mid']))
    else:
        flying = land_d < 0.98
        bx = lerp(gx - BOFF, HAY[0] - 240, land_d); by = lerp(gy, GY + 4, land_d)
        ax = lerp(gx + AOFF, HAY[0] + 210, land_d); ay = lerp(gy, GY + 4, land_d)
        duck(p, V, 'B', bx, by - (34 if flying else 0), t, fly=flying, flap=t * 9, look=0.6, face=1)
        duck(p, V, 'A', ax, ay - (34 if flying else 0), t, fly=flying, flap=t * 9, face=-1 if land_d > 0.5 else 1, look=0.6)
    if v1 - 0.05 < t < v1 + 1.4:
        put_text(fr, A['flump'], HAY[0] - VCAM, 330, env(t, v1 - 0.05, v1 + 1.4, 0.05, 0.4))
    if n8[1] < t < n8[1] + 1.2:
        put_text(fr, A['oops'], hx0 - VCAM + 60, hy0 + 70, env(t, n8[1], n8[1] + 1.2, 0.1, 0.3))
    return fr

HCAM = HAY[0] - 640
def hay_frame(t):
    """'I'm all right. My shell is strong.' Think first, then speak!"""
    a, b = SB("hay")
    cam = lerp(VCAM, HCAM, sm(a, a + 1.6, t))
    fr, V = world_view(cam); fr = fr.copy(); p = Pen(fr)
    t5 = cue('t5'); a5 = cue('a5')
    child(p, V, "girl", KIDX[0], t, look=0.8, arm2=-150 + 25 * math.sin(t * 6), head=-6)
    child(p, V, "boy", KIDX[1], t, look=0.8, arm=-10, head=-6, laugh=0.0)
    slide = sm(a + 0.2, t5[1] - 0.1, t)
    ex, ey = HAY[0] - 40, HAY[1] - 150
    tx = lerp(ex, HAY[0] - 10, slide); ty = lerp(ey, GY + 8, slide) - 40 * math.sin(math.pi * slide)
    sad = sm(word_time('t5', 'But'), word_time('t5', 'But') + 0.5, t) * (1 - sm(a5[1] + 0.5, cend('a5') + 0.3, t))
    duck(p, V, 'B', HAY[0] - 240, GY + 4, t, face=1, look=0.6, wing=-20 * env(t, a5[1], cend('a5'), 0.3, 0.3))
    tortoise(p, V, tx, ty, t, sad=-1.2 * sad, look=0.6 - 1.2 * (t > a5[1]), head=12 * sad - 8 * spk('T', t),
             hop=10 * env(t, word_time('t5', 'shell'), word_time('t5', 'But'), 0.2, 0.2) * abs(math.sin(t * 8)))
    duck(p, V, 'A', HAY[0] + 210, GY + 4, t, face=-1, look=0.6, wing=-50 * env(t, a5[1], cend('a5'), 0.3, 0.4),
         head=-8 * env(t, word_time('a5', 'think'), cend('a5'), 0.2, 0.3))
    if t < t5[1] + 0.5:                                       # the last dizzy stars
        al = 1 - sm(t5[1] - 0.5, t5[1] + 0.5, t)
        for k in range(5):
            ang = t * 4 + k * 1.256
            M = S(SS) @ T(tx - cam + 110 + 40 * math.cos(ang), ty - 90 + 12 * math.sin(ang)) @ S(0.55 * al)
            p.poly(M, khatam(0, 0, 12), "#f2c14e", outline="#b9802a", w=1)
    return fr

def lake_frame(t):
    """slowly, slowly, the three friends walk to the big blue lake"""
    a, b = SB("lake")
    n10 = cue('n10'); t6 = cue('t6'); n11 = cue('n11')
    w = sm(a + 0.3, cend('n10') + 0.3, t)
    tx = lerp(HAY[0] - 10, LK - 640, w)
    cam = clamp(tx - 520, HCAM, CAMMAX)
    fr, V = world_view(cam); fr = fr.copy(); p = Pen(fr)
    walking = 0.01 < w < 0.99
    # the ducks walk ahead, then slip into the water
    for who, off, wx in (('B', 150, LK - 250), ('A', 270, LK - 70)):
        dx = tx + off
        sw = sm(n11[1] - 3.0 + (who == 'A') * 0.4, n11[1] - 2.0 + (who == 'A') * 0.4, t)
        if sw <= 0:
            duck(p, V, who, dx, GY + 4, t, face=1, walk=t * 9, amp=1 if walking else 0, look=0.4,
                 head=-6 * math.sin(t * 2) * walking)
        elif sw < 0.5:                                           # a happy hop into the water
            duck(p, V, who, lerp(dx, wx, sw * 2), GY + 4 - 60 * math.sin(math.pi * sw * 2) + (620 - GY) * sw * 2, t, face=1,
                 look=0.4, wing=-60)
        else:
            swim_duck(p, V, who, wx + 30 * (sw - 0.5), 620 + (who == 'A') * 22, t, face=-1 if sw > 0.9 else 1, look=0.4)
    nod = env(t, t6[1], cend('t6') + 0.2, 0.1, 0.2)
    tortoise(p, V, tx, GY + 10, t, walk=t * 5, amp=1 if walking else 0, mouth=0, head=-12 * nod * abs(math.sin(t * 7)),
             look=0.8)
    if t6[1] < t < cend('t6') + 0.4:
        put_text(fr, A['mm'], tx - cam + 60, 470, env(t, t6[1], cend('t6') + 0.4, 0.2, 0.3))
    return fr

# Look pass (pipeline/look.py). NO_PUSH: titles, end card, and scenes that must flow continuously into the next.
from look import Look
LOOK = Look(W, H)
NO_PUSH = {"title", "end", "pond", "dry", "idea", "lift", "village", "fall", "hay"}

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
    if name in ("pond", "village"): f = clamp(lt / 0.35)                 # flows into the next scene: fade in only
    if name in ("lift", "hay"): f = clamp((sd - lt) / 0.35)              # flows in from the previous scene: fade out only
    if name in ("dry", "idea", "fall"): f = 1.0
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
    sad = ["A4", "-", "G4", "F4", "-", "Ek4", "D4", "-", "-", "C4", "D4", "-", "-", "-"]
    soar = ["D4", "F4", "A4", "D5", "C5", "A4", "Bb4", "A4", "G4", "F4", "G4", "A4"]
    a, b = sc['tree_open']; seq(a + 0.2, 0.32, playful, 0.7, end=b - 0.2); tombak(a + 0.2, b - 0.3, 0.64, 0.3)
    a, b = sc['title']; seq(a + 0.2, 0.3, ["A3", "D4", "Ek4", "F4", "Ek4", "D4", "C4", "D4", "-", "A4"], 0.9)
    a, b = sc['pond']; seq(a + 0.2, 0.36, flow, 0.55, 1.8, end=cue('t1')[1]); seq(cue('t1')[1], 0.16, playful, 0.4, 1.0, end=cend('t1'))
    seq(cue('a1')[1], 0.36, flow, 0.5, 1.8, end=b)
    a, b = sc['dry']; seq(a, 0.55, sad, 0.45, 2.0, end=b)
    a, b = sc['idea']; add(mus, a + 0.1, santur(NOTES['D5'], 1.4), 0.7); seq(a + 0.4, 0.3, happy, 0.5, 1.2, end=cue('b3')[1])
    riz(cue('b3')[1], cend('b3'), 'A3', 0.2); seq(cue('t3')[1], 0.3, playful, 0.5, 1.2, end=b)
    a, b = sc['lift']; fl = word_time('n4', 'flapped')
    seq(a + 0.1, 0.42, flow, 0.5, 1.6, end=fl); seq(fl, 0.24, soar, 0.6, 1.2, end=b - 0.2); tombak(fl, b - 0.3, 0.48, 0.35)
    a, b = sc['village']; seq(a + 0.1, 0.3, playful, 0.5, 1.2, end=cue('n7')[1])
    riz(cue('n7')[1], cue('t4')[1], 'A3', 0.28, swell=True)
    a, b = sc['fall']; v0 = word_time('n8', 'Down'); v1 = word_time('n9', 'hay') + 0.1
    seq(v0, (v1 - v0) / 12, ["D5", "C5", "Bb4", "A4", "G4", "F4", "Ek4", "D4", "C4", "Bb3", "A3", "G3"], 0.6, 0.9)
    add(mus, v1, dum(0.6), 1.0); seq(cue('b4')[1], 0.3, happy, 0.45, 1.2, end=b)
    a, b = sc['hay']; seq(a + 0.2, 0.36, flow, 0.5, 1.8, end=b - 0.2)
    a, b = sc['lake']; seq(a + 0.2, 0.3, playful, 0.55, 1.2, end=b - 0.2); tombak(cue('t6')[1] - 0.3, b - 0.3, 0.5, 0.35)
    a, b = sc['tree_close']; seq(a + 0.2, 0.36, ["D4", "-", "F4", "G4", "A4", "-", "Bb4", "A4", "G4", "-", "F4", "Ek4", "D4", "-", "-", "-"], 0.6, end=b - 0.2)
    c3 = cue('x3'); seq(c3[1] - 0.3, 0.1, ["D5", "A4", "D5", "F4"], 0.5, 1.6)
    a, b = sc['end']
    seq(a + 0.2, 0.3, ["D4", "F4", "A4", "D5", "-", "C5", "A4", "Bb4", "A4", "-", "-", "D4"], 0.85)
    for nn in ("D3", "A3", "D4"): add(mus, a + 3.3, santur(NOTES[nn], 2.0), 0.8)
    mus += (np.sin(2 * np.pi * NOTES['D2'] * t) + 0.5 * np.sin(2 * np.pi * NOTES['A2'] * t)) * 0.05
    # sfx
    a, b = sc['lift']; fl = word_time('n4', 'flapped'); add(sfx, fl, flutter(b - fl, 10, 3), 0.55)
    add(sfx, word_time('n4', 'bit'), tak(0.06, seed=5), 1.2)
    a, b = sc['village']; add(sfx, a, flutter(b - a, 8, 6), 0.35)
    a, b = sc['fall']; v0 = word_time('n8', 'Down'); v1 = word_time('n9', 'hay') + 0.1
    add(sfx, a, flutter(v1 - a, 8, 8), 0.3); add(sfx, v0, hiss(v1 - v0, 5), 0.5)
    add(sfx, v1, noise(int(0.6 * SR), 7, 40) * np.exp(-np.arange(int(0.6 * SR)) / SR / 0.15), 1.4)
    add(sfx, cend('n9') + 0.2, flutter(2.4, 12, 9), 0.5)
    a, b = sc['lake']
    for k in range(12): add(sfx, a + 0.4 + k * 0.55, tak(0.05, seed=k + 30), 0.35)
    add(sfx, cue('n11')[1] - 2.6, splash(1.0), 0.5)
    br = noise(N, 3) * (0.55 + 0.45 * np.sin(2 * np.pi * t / 6.5) ** 2)
    gate = np.zeros(N)
    for nm in ("pond", "dry", "idea", "lift", "village", "fall", "hay", "lake"):
        a, b = sc[nm]; gate[int(a * SR):int(b * SR)] = 1
    gate = np.convolve(gate, np.ones(int(0.5 * SR)) / int(0.5 * SR), 'same')
    sfx += br * gate * 0.12
    vo = tl.mix_voice(N)
    rev = mus.copy()
    for dly, g in ((0.071, 0.3), (0.113, 0.22), (0.197, 0.15), (0.311, 0.1)):
        k = int(dly * SR); rev[k:] += mus[:-k] * g
    ve = np.convolve(np.abs(vo), np.ones(int(0.25 * SR)) / int(0.25 * SR), 'same')
    duck_ = 1 - 0.62 * np.clip(ve / (ve.max() * 0.15 + 1e-9), 0, 1)
    duck_ = np.convolve(duck_, np.ones(int(0.2 * SR)) / int(0.2 * SR), 'same')
    rev = rev / (np.abs(rev).max() + 1e-9) * 0.5 * duck_
    sfx = sfx / (np.abs(sfx).max() + 1e-9) * 0.22 * (0.5 + 0.5 * duck_)
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
    tl.srt(os.path.join(EP, "ep06.en.srt"), NAMES_EN)
    write_fa_srt(os.path.join(EP, "ep06.fa.srt"))
    out = os.path.join(EP, "render_ep06.mp4")
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

