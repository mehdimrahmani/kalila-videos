#!/usr/bin/env python3
"""Kalila & Dimna — Episode 5: The Heron and the Crab (~3.2 min).
Adapted from ep04/ep04.py (itself from ep03) (same timeline helper, hosts, cards, word card, LOOK pass, render + audio)."""
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
tl.scene("lake", ["n1", 0.3, "n2", 0.4, "h1", 0.5, "h2"], lead=1.4, tail=1.0)
tl.scene("trick", ["n3", 0.3, "c1", 0.3, "h3"], lead=0.6, tail=0.4)
tl.scene("fear", ["f1", 0.2, "l1", 0.4, "h4", 0.4, "n4"], lead=0.2, tail=1.0)
tl.scene("carry", ["n5", 0.4, "h5", 0.3, "l2"], lead=0.8, tail=1.0)
tl.scene("ask", ["c2", 0.3, "h6"], lead=0.6, tail=1.6)
tl.scene("flight", ["n6", 0.3, "c3"], lead=0.6, tail=0.2)
tl.scene("pinch", ["n7", 0.3, "h7", 0.3, "c4", 0.3, "h8", 0.4, "n8"], lead=0.2, tail=1.0)
tl.scene("home", ["n9", 0.4, "f2", 0.3, "c5"], lead=0.6, tail=1.6)
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
CW = 2900                    # one wide world: the lake (left), the big rocks, the muddy puddle (right)
HERX = 660                   # where the heron stands in the shallows
ROCK = (420, 612)            # the crab's rock (top centre)
PUD = (2260, 626)            # the muddy puddle
PCAM = PUD[0] - 640          # camera that centres the puddle
LAKE_R = 1390                # right edge of the lake at the channel height
WATER = "#5fa6c9"; MUD = "#9a8a5c"

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

LAKE_POLY = [(560, 600), (600, 548), (760, 530), (1100, 524), (1330, 534), (1400, 580), (1420, 650), (1400, 720), (540, 720)]
def build_world():
    img = sky(H * SS, CW * SS); p = Pen(img); V = S(SS); rng = np.random.default_rng(55)
    sun(p, V, 1110, 110)
    for x in range(160, CW, 460):
        cloud(p, V, x + rng.uniform(-60, 60), rng.uniform(80, 200), rng.uniform(0.7, 1.0))
    hills(p, V, CW, 430, 70, 0.9, 220, "#d9b6a3", "#9c7a68")
    hills(p, V, CW, 505, 55, 2.4, 150, "#b9ba86", "#7f8156")
    for x in (90, 250, 1500, 2700, 2820):
        cypress(p, V, x, 580, rng.uniform(170, 220), 22)
    blossom_tree(p, V, 160, 586, rng); blossom_tree(p, V, 2560, 588, rng)
    gp = [(x, 572 + 6 * math.sin(x / 90)) for x in range(0, CW + 10, 10)] + [(CW + 10, H), (0, H)]
    p.poly(V, gp, "#93ad62", outline="#5f7a3a", w=2)
    # the lake
    p.poly(V, LAKE_POLY, "#d8cdb6", outline=OUT, w=2.5)
    p.poly(V, [(q[0] + (8 if q[0] < 900 else -8), q[1] + 8) for q in LAKE_POLY[:-2]] + [(1390, 720), (556, 720)], WATER, outline=None)
    for k in range(10):
        x = 640 + (k * 83) % 700; y = 560 + (k * 37) % 140
        p.line(V, [(x, y), (x + 50, y)], "#a9d6e8", 1.6)
    for x in (566, 590, 1372, 1396):
        reeds(p, V, x, 640 if x < 1000 else 620, rng, 3)
    # the crab's flat rock at the shore
    p.poly(V, [(ROCK[0] - 80, GY + 22), (ROCK[0] - 66, ROCK[1] + 6), (ROCK[0] - 30, ROCK[1] - 6), (ROCK[0] + 40, ROCK[1] - 6),
               (ROCK[0] + 72, ROCK[1] + 8), (ROCK[0] + 84, GY + 22)], "#b3a48e", outline=OUT, w=3)
    p.poly(V, [(ROCK[0] - 50, ROCK[1] + 2), (ROCK[0] + 30, ROCK[1] - 2), (ROCK[0] + 56, ROCK[1] + 8), (ROCK[0] - 20, ROCK[1] + 10)], "#cbbfa9", outline=None)
    # the big rocks (they hide the puddle from the lake)
    for x0, top, w in ((1560, 380, 200), (1700, 300, 240), (1880, 400, 180)):
        p.poly(V, [(x0, 600), (x0 + 20, top + 60), (x0 + w * 0.35, top), (x0 + w * 0.7, top + 24), (x0 + w, 600)], "#a68c6e", outline=OUT, w=3)
        p.poly(V, [(x0 + w * 0.35, top + 8), (x0 + w * 0.5, top + 20), (x0 + w * 0.4, top + 110), (x0 + w * 0.3, top + 60)], "#c2aa8a", outline=None)
    # the muddy puddle behind the rocks
    p.poly(V, ell(PUD[0], PUD[1], 160, 44, 40), "#7a6440", outline=OUT, w=2.5)
    p.poly(V, ell(PUD[0], PUD[1] + 3, 146, 36, 40), MUD, outline=None)
    for k in range(4):
        p.line(V, [(PUD[0] - 70 + 40 * k, PUD[1] - 6 + 6 * (k % 2)), (PUD[0] - 46 + 40 * k, PUD[1] - 6 + 6 * (k % 2))], "#b3a77c", 1.5)
    for x in (1990, 2500):
        bush(p, V, x, 630, 0.8, 0)
    grass(p, V, rng, 0, CW, 900, lambda x, y: (530 < x < 1430 and y < 730) or (PUD[0] - 170 < x < PUD[0] + 170 and 570 < y < 680)
          or (ROCK[0] - 90 < x < ROCK[0] + 90 and y < 670))
    return img

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
    fa_text(d, (w / 2 * SS, 98 * SS), "ماهی", 74 * SS, (28, 52, 99, 255))
    f2 = ImageFont.truetype(FB, 32 * SS)
    d.text((w / 2 * SS, 166 * SS), "maahi  =  fish", font=f2, fill=(90, 50, 12, 255), anchor="mm")
    return im

def init():
    ME.init_assets()
    A['border'] = ME.ASSETS['border']; A['card'] = ME.ASSETS['card']
    A['tree'] = build_tree_set().convert('RGBA')
    A['world'] = build_world().convert('RGBA')
    A['wcard'] = build_word_card()
    gold, cream = (226, 182, 74, 255), (250, 240, 214, 255)
    A['t1'] = text_img("KALILA & DIMNA", FB, 60, gold, 2, (90, 60, 12, 255))
    A['t2'] = text_img("The Heron and the Crab", FI, 46, cream)
    A['t3'] = text_img("—  Episode 5  —", FR, 24, gold)
    A['e1'] = text_img("Next time", FI, 30, cream)
    A['e2'] = text_img("The Tortoise and the Two Ducks", FB, 44, gold, 2, (90, 60, 12, 255))
    A['e3'] = text_img("A new story every Saturday", FR, 26, cream)
    A['bang'] = text_img("!", FB, 54, (200, 40, 30, 255), 3, (255, 255, 255, 255))
    A['idea'] = text_img("!", FB, 60, (226, 182, 74, 255), 3, (40, 24, 10, 255))
    A['pinch'] = text_img("PINCH!", FB, 54, (200, 40, 30, 255), 3, (255, 255, 255, 255))
    A['ow'] = text_img("OW! OW!", FB, 40, (200, 40, 30, 255), 3, (255, 255, 255, 255))
    A['help'] = text_img("Help!", FB, 34, (250, 240, 214, 255), 3, (40, 24, 10, 255))
    A['hee'] = text_img("hee hee!", FI, 32, (90, 50, 12, 255))
    A['splash'] = text_img("splash!", FI, 30, (30, 80, 130, 255))
    A['hooray'] = text_img("Hooray!", FB, 44, (250, 240, 214, 255), 3, (40, 24, 10, 255))

# ------------------------------------------------------------------ actors
def heron(p, V, x, y, t, face=1, sc=1.12, **kw):
    s = spk('H', t)
    po = dict(t=t, mouth=s, blink=blink(t, 0.4), look=0.4, head=5 * s * math.sin(t * 8), neck=1.0)
    hd = kw.pop('head', 0); po.update(kw); po['head'] += hd
    return draw_heron(p, V @ T(x, y) @ S(sc * face, sc), po)

def crab(p, M, t, sc=0.9, **kw):
    s = spk('C', t)
    po = dict(t=t, mouth=s, blink=blink(t, 1.3), look=0.0, arm=0.25 + 0.5 * s * abs(math.sin(t * 5)), claw=0.3 + 0.5 * s)
    po.update(kw)
    draw_crab(p, M @ S(sc), po)

def fish(p, M, t, col, who='F', **kw):
    s = spk(who, t) if who else 0.0
    po = dict(t=t, mouth=s, blink=blink(t, col * 0.7), look=0.5); po.update(kw)
    draw_fish(p, M, po, col)

def peek(p, V, x, y, t, col, up, water=WATER, rim="#a9d6e8", who='F', ang=-62, sc=1.6, **kw):
    """a fish peeking out of the water (lower half hidden by a water patch)"""
    if up <= 0.02: return
    bob = 3 * math.sin(t * 3 + col)
    k = sc / 1.6
    fish(p, V @ T(x, y + 30 * k * (1 - up) + bob) @ R(ang) @ S(sc), t, col, who, **kw)
    p.poly(V, ell(x - 12 * k, y + 34 * k, 44 * k, 26 * k, 24), water, outline=None)
    p.line(V, ell(x - 6 * k, y + 10 * k, 28 * k, 6 * k, 20, 0, 180), rim, 2)

LAKE_FISH = [(840, 596, 0), (950, 648, 1), (1060, 588, 2), (1170, 640, 3), (1270, 600, 4)]
PUD_FISH = [(PUD[0] - 96, PUD[1] - 6, 1), (PUD[0] - 30, PUD[1] + 2, 4), (PUD[0] + 40, PUD[1] - 8, 2), (PUD[0] + 104, PUD[1] - 2, 0)]

def ripples(p, V, x, y, t):
    for k in range(2):
        r = 18 + 10 * ((t * 0.6 + k * 0.5) % 1)
        p.line(V, ell(x, y, r * 1.6, r * 0.35, 24, 0, 180), "#a9d6e8", 1.6)

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
        if o2[1] < t < o2[1] + 0.8: kpo['hop'] = 22 * abs(math.sin(math.pi * (t - o2[1]) / 0.8))     # Kalila jumps: "Oh no!"
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
        # a fish leaps by during the moral
        c2 = cue('x2'); u = (t - c2[1]) / 2.4
        if 0 < u < 1:
            fish(p, V @ T(lerp(560, 760, u), 600 - 200 * math.sin(math.pi * u)) @ R(-60 + 120 * u) @ S(1.3), t, 3, None, happy=1)
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

def lake_frame(t):
    """the old heron tries to catch fish, misses, then gets his sly idea"""
    a, b = SB("lake")
    fr, V = world_view(0); fr = fr.copy(); p = Pen(fr)
    n2 = cue('n2'); h1 = cue('h1'); h2 = cue('h2')
    # fish jump past him, too fast (twice during n2)
    jumps = [word_time('n1', 'caught'), word_time('n2', 'swam')]
    for k, j0 in enumerate(jumps):
        u = (t - j0) / 1.3
        if 0 < u < 1:
            x = lerp(760, 1180, u); y = 600 - 170 * math.sin(math.pi * u)
            fish(p, V @ T(x, y) @ R(-55 + 110 * u) @ S(1.4), t, k + 1, None, scared=0.6)
    miss = max(env(t, jumps[0] + 0.2, jumps[0] + 1.0, 0.2, 0.4), env(t, jumps[1] + 0.2, jumps[1] + 1.0, 0.2, 0.4))
    sad = sm(h1[1] - 0.6, h1[1] + 0.4, t) * (1 - sm(h2[1] - 0.2, h2[1] + 0.4, t))
    sly = sm(h2[1] + 0.2, h2[1] + 0.8, t)
    heron(p, V, HERX, GY, t, face=1, neck=1 - 0.4 * miss - 0.3 * sad, head=30 * miss, sad=sad, sly=sly, look=0.6,
          lean=6 * miss)
    ripples(p, V, HERX, GY + 2, t)
    for x, y, c in LAKE_FISH[1:4]:
        peek(p, V, x + 40, y, t, c, env(t, a + 1.5 + c, a + 4 + c, 0.4, 0.4) * (t < n2[1]), who=None)
    if h2[1] + 0.3 < t < cend('h2') + 0.6:
        put_text(fr, A['idea'], HERX + 60, 250, env(t, h2[1] + 0.3, cend('h2') + 0.6, 0.2, 0.3))
    return fr

def trick_frame(t):
    a, b = SB("trick")
    fr, V = world_view(0); fr = fr.copy(); p = Pen(fr)
    c1 = cue('c1'); h3 = cue('h3')
    talk = sm(h3[1] - 0.2, h3[1] + 0.3, t)
    heron(p, V, HERX, GY, t, face=-1 if c1[1] - 0.5 < t < h3[1] + 2.5 else 1, sad=1 - 0.5 * talk, neck=0.7, look=0.5,
          wing=-30 * env(t, word_time('h3', 'big nets'), cend('h3'), 0.3, 0.4))
    ripples(p, V, HERX, GY + 2, t)
    # the crab walks out onto her rock, looks up at the heron
    u = sm(a + 0.4, word_time('n3', 'little crab') + 0.4, t)
    cx = lerp(160, ROCK[0], u)
    crab(p, V @ T(cx, ROCK[1] + 2 + 4 * (u < 0.99) * abs(math.sin(t * 9))), t, walk=t * 12, amp=1 if 0.01 < u < 0.99 else 0,
         look=0.8, brow=-0.3 * (t > c1[1]))
    # the fish listen, peeking up near the end
    for x, y, c in LAKE_FISH:
        peek(p, V, x, y, t, c, sm(word_time('h3', 'fishermen') + c * 0.2, word_time('h3', 'fishermen') + 0.6 + c * 0.2, t),
             who=None, look=-0.8, scared=sm(word_time('h3', 'nets'), word_time('h3', 'nets') + 0.4, t))
    if word_time('h3', 'big nets') < t < cend('h3') + 0.4:
        put_text(fr, A['bang'], 1040, 500, env(t, word_time('h3', 'big nets'), cend('h3') + 0.4, 0.15, 0.3))
    return fr

def fear_frame(t):
    a, b = SB("fear")
    fr, V = world_view(0); fr = fr.copy(); p = Pen(fr)
    f1 = cue('f1'); l1 = cue('l1'); h4 = cue('h4'); n4 = cue('n4')
    sweet = sm(h4[1], h4[1] + 0.5, t)
    heron(p, V, HERX, GY, t, face=1, sly=0.5 * sweet, neck=0.8, look=0.8, head=-10 * sweet,
          wing=-50 * env(t, word_time('h4', 'Behind'), word_time('h4', 'carry'), 0.4, 0.4))
    ripples(p, V, HERX, GY + 2, t)
    crab(p, V @ T(ROCK[0], ROCK[1] + 2), t, look=0.8, brow=0.6 * sm(n4[1], n4[1] + 0.5, t))
    happy = sm(n4[1], n4[1] + 0.6, t)
    for x, y, c in LAKE_FISH:
        jump = 0
        if c == 3: jump = env(t, l1[1] - 0.1, cend('l1') + 0.1, 0.25, 0.3)
        peek(p, V, x, y - 30 * jump, t, c, 1.0, who='L' if c == 3 else 'F', look=-0.8, scared=(1 - happy) * (1 - sweet * 0.6),
             happy=happy > 0.5, ang=-62 + 8 * math.sin(t * 4 + c) * happy)
    if f1[1] < t < cend('f1') + 0.3:
        put_text(fr, A['bang'], 1000, 470, env(t, f1[1], cend('f1') + 0.3, 0.15, 0.3))
    # the sweet words: little gold stars float up while he promises the "beautiful new lake"
    if t > word_time('h4', 'beautiful'):
        for j in range(5):
            ph = ((t - word_time('h4', 'beautiful')) * 0.4 + j / 5) % 1
            M = V @ T(HERX + 120 + j * 34, 300 - 120 * ph) @ R(t * 60) @ S(0.4 + 0.4 * math.sin(math.pi * ph))
            p.poly(M, khatam(0, 0, 10), "#f2c14e", outline="#b9802a", w=1)
    return fr

def carry_frame(t):
    """the heron flies a fish over the rocks and drops it into the muddy puddle"""
    a, b = SB("carry")
    h5 = cue('h5'); l2 = cue('l2')
    drop = word_time('n5', 'dropped')
    u = sm(a + 0.3, drop - 0.3, t)
    hx = lerp(HERX, PUD[0] - 10, u); hy = lerp(330, 470, u) - 90 * math.sin(math.pi * u)
    land = sm(drop + 0.6, drop + 2.4, t)
    hx, hy = lerp(hx, PUD[0] - 190, land), lerp(hy, GY, land)
    cam = clamp(hx - 640, 0, PCAM)
    fr, V = world_view(cam); fr = fr.copy(); p = Pen(fr)
    nin = 3 + (t > drop + 0.6)
    for x, y, c in PUD_FISH[:nin]:
        sc = env(t, l2[1] - 0.2, cend('l2') + 0.3, 0.2, 0.3)
        peek(p, V, x, y, t, c, 0.55 + 0.45 * sc, water=MUD, rim="#b3a77c", who='L' if c == 4 else None, sc=1.35,
             scared=0.7, look=-0.5)
    flying = land < 0.98
    r = heron(p, V, hx, hy if flying else GY, t, face=1, fly=flying, flap=t * 9, sly=1,
              look=0.8, hop=12 * abs(math.sin(t * 8)) * env(t, h5[1], cend('h5'), 0.2, 0.3), neck=0.9)
    if t < drop:
        fish(p, r['head'] @ T(64, 8) @ R(80), t, 4, None, scared=1, wag=18)
    else:
        fu = clamp((t - drop) / 0.5)
        if fu < 1:
            sx, sy = PUD[0] + 64, lerp(hy - 30, PUD[1], fu * fu)
            fish(p, V @ T(sx, sy) @ R(80), t, 4, None, scared=1, wag=18)
        put_text(fr, A['splash'], PUD[0] + 64 - cam, PUD[1] - 90, env(t, drop + 0.4, drop + 1.6, 0.05, 0.4))
    if h5[1] < t < cend('h5') + 0.3:
        put_text(fr, A['hee'], hx - cam + 190, 230, env(t, h5[1], cend('h5') + 0.3, 0.2, 0.3))
    if l2[1] < t < cend('l2') + 0.3:
        put_text(fr, A['help'], PUD[0] - cam, PUD[1] - 120, env(t, l2[1], cend('l2') + 0.3, 0.1, 0.3))
    return fr

def ask_frame(t):
    a, b = SB("ask")
    fr, V = world_view(0); fr = fr.copy(); p = Pen(fr)
    c2 = cue('c2'); h6 = cue('h6')
    bend = sm(h6[1] - 0.2, h6[1] + 0.6, t)
    r = heron(p, V, HERX - 60 * bend, GY, t, face=-1, sly=sm(h6[1], h6[1] + 0.5, t), neck=1 - 0.6 * bend, head=10 * bend,
              look=0.6, lean=10 * bend)
    ripples(p, V, HERX - 60 * bend, GY + 2, t)
    for x, y, c in LAKE_FISH[1:4]:
        peek(p, V, x, y, t, c, 0.6, who=None, look=-0.8, scared=0.4)
    # the crab hops from her rock onto the heron's neck at the end
    hop = sm(cend('h6') + 0.1, b - 0.1, t)
    q = ap(r['back'] @ S(-1, 1), [(0, 0)])[0]
    bx, by = q[0] / SS, q[1] / SS
    cx, cy = lerp(ROCK[0], bx, hop), lerp(ROCK[1] + 2, by, hop) - 80 * math.sin(math.pi * hop)
    crab(p, V @ T(cx, cy), t, sc=0.9 - 0.35 * hop, look=0.7, arm=0.25 + 0.6 * (t > c2[1]) * spk('C', t) + 0.6 * hop)
    return fr

def flight_frame(t):
    a, b = SB("flight")
    c3 = cue('c3')
    u = sm(a, word_time('n6', 'looked') - 0.2, t)
    hx = lerp(HERX, PUD[0] - 90, u); hy = lerp(300, 330, u) - 60 * math.sin(math.pi * u)
    cam = clamp(hx - 550, 0, PCAM)
    fr, V = world_view(cam); fr = fr.copy(); p = Pen(fr)
    for x, y, c in PUD_FISH:
        peek(p, V, x, y, t, c, 0.8, water=MUD, rim="#b3a77c", who=None, sc=1.35, scared=0.8, look=-0.5)
    hy += 6 * math.sin(t * 3)
    r = heron(p, V, hx, hy, t, face=1, fly=1, flap=t * 8, sly=1, look=0.8, sc=1.12)
    look = sm(word_time('n6', 'looked'), word_time('n6', 'looked') + 0.6, t)
    angry = sm(c3[1] - 0.2, c3[1] + 0.3, t)
    crab(p, r['back'] @ S(0.55), t, sc=1.0, look=0.0, brow=1.4 * angry, snap=angry > 0.5 and t < cend('c3'),
         arm=0.3 + 0.6 * angry, hop=4 * look * abs(math.sin(t * 6)))
    if c3[1] < t < cend('c3') + 0.3:
        put_text(fr, A['bang'], hx - cam - 30, hy - 180, env(t, c3[1], cend('c3') + 0.3, 0.15, 0.3))
    return fr

def pinch_frame(t):
    a, b = SB("pinch")
    fr, V = world_view(PCAM); fr = fr.copy(); p = Pen(fr)
    h7 = cue('h7'); c4 = cue('c4'); h8 = cue('h8'); n8 = cue('n8')
    pin = word_time('n7', 'pinch')
    for x, y, c in PUD_FISH:
        peek(p, V, x, y, t, c, 0.8 + 0.2 * (t > pin), water=MUD, rim="#b3a77c", who=None, sc=1.35, scared=0.8 * (t < pin),
             look=-0.5, happy=t > cue('h8')[1])
    jolt = env(t, pin, cend('h7') + 0.2, 0.05, 0.4)
    land = sm(c4[1] - 0.4, c4[1] + 1.6, t)
    away = sm(n8[1] + 1.0, cend('n8') + 0.6, t)
    hx = lerp(PUD[0] - 90, PUD[0] - 270, land) + 10 * jolt * math.sin(t * 30)
    hy = lerp(370, GY, land) - 30 * jolt
    hx, hy = lerp(hx, PUD[0] - 1100, away), lerp(hy, 60, away) - 100 * math.sin(math.pi * away)
    flying = land < 0.98 or away > 0.01
    off = sm(cend('c4') - 0.2, cend('c4') + 0.8, t)                          # the crab hops down after "never trick the fish again"
    r = heron(p, V, hx, hy, t, face=-1 if away > 0.01 else 1, fly=flying, flap=t * (9 + 14 * jolt + 6 * away), sly=1 - jolt,
              sad=max(jolt, sm(h8[1], h8[1] + 0.4, t) * (1 - away)) if not flying else 0, look=0.8,
              head=-25 * jolt * math.sin(t * 14), mouth=max(spk('H', t), 0.8 * jolt))
    if off < 1:
        q = ap(r['back'], [(0, 0)])[0]
        bx, by = q[0] / SS + PCAM, q[1] / SS
        cx, cy = lerp(bx, PUD[0] - 175, off), lerp(by, GY + 46, off) - 70 * math.sin(math.pi * off)
        crab(p, V @ T(cx, cy), t, sc=0.55 + 0.35 * off, brow=1.2, snap=pin - 0.1 < t < pin + 1.2, arm=0.7, look=0.5)
    else:
        crab(p, V @ T(PUD[0] - 175, GY + 46), t, sc=0.9, brow=0.8 - 0.8 * sm(n8[1], n8[1] + 1, t), look=-0.6,
             happy=t > n8[1] + 1)
    if pin - 0.05 < t < pin + 1.4:
        put_text(fr, A['pinch'], 640, 190, env(t, pin - 0.05, pin + 1.4, 0.05, 0.4))
    if jolt > 0.05 and not away:
        for k in range(5):
            ang = t * 4 + k * 1.256
            q = ap(r['head'], [(0, 0)])[0]
            M = S(SS) @ T(q[0] / SS + 40 * math.cos(ang), q[1] / SS - 30 + 14 * math.sin(ang)) @ S(0.5 * jolt)
            p.poly(M, khatam(0, 0, 12), "#f2c14e", outline="#b9802a", w=1)
    if h7[1] < t < cend('h7') + 0.3:
        put_text(fr, A['ow'], 980, 260, env(t, h7[1], cend('h7') + 0.3, 0.1, 0.3))
    return fr

def home_frame(t):
    """the crab digs a stream from the puddle to the lake; the fish swim home"""
    a, b = SB("home")
    f2 = cue('f2'); c5 = cue('c5')
    dig = sm(a + 0.4, word_time('n9', 'And all') - 0.2, t)
    head = lerp(PUD[0] - 120, LAKE_R - 10, dig)                 # front of the stream (world x)
    cam = clamp(head - 560, 600, PCAM)
    fr, V = world_view(cam); fr = fr.copy(); p = Pen(fr)
    # the stream
    xs = np.arange(head, PUD[0] - 100, 10)
    if len(xs) > 1:
        top = [(x, 644 + 5 * math.sin(x / 60)) for x in xs]
        bot = [(x, 666 + 5 * math.sin(x / 60)) for x in xs[::-1]]
        p.poly(V, top + bot, WATER, outline="#6b4a2a", w=2)
        for x in xs[::9]:
            p.line(V, [(x, 655 + 5 * math.sin(x / 60)), (x + 26, 655 + 5 * math.sin((x + 26) / 60))], "#a9d6e8", 1.4)
    # puddle fish wait, then swim along the stream behind the crab, then into the lake
    swim = sm(word_time('n9', 'swam') - 0.6, cend('n9') + 0.4, t)
    happy = t > word_time('n9', 'swam')
    for k, (x, y, c) in enumerate(PUD_FISH + [(PUD[0] + 20, PUD[1] + 2, 3)]):
        if swim < 0.01:
            peek(p, V, x, y, t, c, 0.7, water=MUD, rim="#b3a77c", who=None, sc=1.35, look=-0.8, happy=dig > 0.5)
        else:
            fx = lerp(x, 1000 + 70 * k, swim); fy = lerp(y, 610 + 18 * (k % 3), swim) if swim > 0.85 else 655 + 5 * math.sin(fx / 60)
            j = env(t, f2[1] + 0.12 * k, f2[1] + 0.9 + 0.12 * k, 0.2, 0.3)
            fish(p, V @ T(fx, fy - 70 * j) @ S(-1.1, 1.1) @ R(-30 * j), t, c, 'F', happy=happy, wag=14)
    # the crab, digging at the front of the stream, then talking at the lake shore
    done = dig > 0.99
    crab(p, V @ T(head - 30, 684), t, sc=0.95, walk=t * 14, amp=0 if done else 1, arm=0.2 + 0.5 * abs(math.sin(t * 7)) * (not done)
         + 0.6 * spk('C', t), claw=0.5, look=-0.6 if not done else 0.4, happy=done, hop=3 * abs(math.sin(t * 9)) * (not done))
    if not done and int(t * 6) % 2 == 0:                       # little clods of earth flying
        for k in range(3):
            ph = (t * 3 + k / 3) % 1
            p.poly(V @ T(head - 30 + 40 * ph * (1 + k), 660 - 60 * math.sin(math.pi * ph)), ell(0, 0, 4, 3, 8), "#7a5634", outline=None)
    if f2[1] < t < cend('f2') + 0.4:
        put_text(fr, A['hooray'], 1000 - cam + 140, 430, env(t, f2[1], cend('f2') + 0.4, 0.1, 0.3))
    return fr

# Look pass (pipeline/look.py). NO_PUSH: titles, end card, and scenes that must flow continuously into the next.
from look import Look
LOOK = Look(W, H)
NO_PUSH = {"title", "end", "lake", "trick", "fear", "flight", "pinch"}

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
    if name in ("lake", "flight"): f = clamp(lt / 0.35)                  # flows into the next scene: fade in only
    if name in ("fear", "pinch"): f = clamp((sd - lt) / 0.35)           # flows in from the previous scene: fade out only
    if name == "trick": f = 1.0
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
    a, b = sc['lake']; seq(a + 0.2, 0.36, flow, 0.55, 1.8, end=cue('h1')[1])
    seq(cue('h1')[1], 0.55, sad, 0.45, 2.0, end=cue('h2')[1]); seq(cue('h2')[1] + 0.6, 0.42, sneaky, 0.55, 1.6, end=b)
    a, b = sc['trick']; seq(a, 0.55, sad, 0.45, 2.0, end=word_time('h3', 'big nets'))
    riz(word_time('h3', 'big nets'), cend('h3'), 'A3', 0.3, swell=True)
    a, b = sc['fear']; riz(a, cend('l1'), 'D4', 0.22); seq(cue('h4')[1], 0.3, happy, 0.45, 1.2, end=b - 0.2)
    a, b = sc['carry']; seq(a + 0.1, 0.42, sneaky, 0.6, 1.6, end=b)
    drop = word_time('n5', 'dropped'); add(mus, drop + 0.45, dum(0.5), 0.6)
    a, b = sc['ask']; seq(a + 0.2, 0.36, flow, 0.5, 1.8, end=cue('h6')[1]); seq(cue('h6')[1], 0.42, sneaky, 0.55, 1.6, end=b)
    a, b = sc['flight']; seq(a + 0.1, 0.24, ["D4", "F4", "A4", "F4", "G4", "A4", "Bb4", "A4", "G4", "F4", "Ek4", "F4"], 0.6, 1.0, end=cue('c3')[1])
    tombak(a + 0.1, cue('c3')[1], 0.4, 0.4); riz(cue('c3')[1], b + 1.0, 'A3', 0.3, swell=True)
    a, b = sc['pinch']; pin = word_time('n7', 'pinch'); add(mus, pin, dum(0.5), 0.9)
    seq(pin + 0.2, 0.07, ["D5", "C5", "Bb4", "A4", "G4", "F4"], 0.7, 0.9)
    riz(cue('h7')[1], cend('h8'), 'D4', 0.22); seq(cue('n8')[1], 0.26, happy, 0.6, 1.2, end=b - 0.2)
    a, b = sc['home']; seq(a + 0.2, 0.3, playful, 0.55, 1.2, end=b - 0.2); tombak(cue('f2')[1] - 0.3, b - 0.3, 0.5, 0.4)
    a, b = sc['tree_close']; seq(a + 0.2, 0.36, ["D4", "-", "F4", "G4", "A4", "-", "Bb4", "A4", "G4", "-", "F4", "Ek4", "D4", "-", "-", "-"], 0.6, end=b - 0.2)
    c3 = cue('x3'); seq(c3[1] - 0.3, 0.1, ["D5", "A4", "D5", "F4"], 0.5, 1.6)
    a, b = sc['end']
    seq(a + 0.2, 0.3, ["D4", "F4", "A4", "D5", "-", "C5", "A4", "Bb4", "A4", "-", "-", "D4"], 0.85)
    for nn in ("D3", "A3", "D4"): add(mus, a + 3.3, santur(NOTES[nn], 2.0), 0.8)
    mus += (np.sin(2 * np.pi * NOTES['D2'] * t) + 0.5 * np.sin(2 * np.pi * NOTES['A2'] * t)) * 0.05
    # sfx
    add(sfx, word_time('n1', 'caught'), splash(1.0), 0.5); add(sfx, word_time('n2', 'swam') + 1.2, splash(1.0), 0.5)
    a, b = sc['carry']; add(sfx, a + 0.3, flutter(3.0, 10, 3), 0.6)
    add(sfx, word_time('n5', 'dropped') + 0.45, splash(1.2), 0.9)
    a, b = sc['ask']; add(sfx, cend('h6') + 0.1, tak(0.08, seed=4), 1.2)
    a, b = sc['flight']; add(sfx, a, flutter(b - a, 8, 6), 0.5)
    pin = word_time('n7', 'pinch')
    for k in range(3): add(sfx, pin + k * 0.12, tak(0.06, seed=k + 11), 2.0)
    add(sfx, pin + 0.1, flutter(2.5, 20, 5), 0.8); add(sfx, cue('n8')[1] + 1.0, flutter(2.4, 12, 7), 0.6)
    a, b = sc['home']
    for k in range(10): add(sfx, a + 0.6 + k * 0.7, tak(0.05, seed=k + 30), 0.6)
    add(sfx, word_time('n9', 'swam'), splash(1.4), 0.5)
    br = noise(N, 3) * (0.55 + 0.45 * np.sin(2 * np.pi * t / 6.5) ** 2)
    gate = np.zeros(N)
    for nm in ("lake", "trick", "fear", "carry", "ask", "flight", "pinch", "home"):
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
    tl.srt(os.path.join(EP, "ep05.en.srt"), NAMES_EN)
    write_fa_srt(os.path.join(EP, "ep05.fa.srt"))
    out = os.path.join(EP, "render_ep05.mp4")
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
