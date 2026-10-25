#!/usr/bin/env python3
"""Kalila & Dimna — Episode 2: The Monkey and the Tortoise (~3.5 min). Adapted from ep01/ep1.py."""
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
tl.scene("shore", ["n1", 0.3, "m1"], lead=1.6, tail=1.0)
tl.scene("meet", ["n2", 0.8, "m2", 1.3, "t1"], lead=0.8, tail=1.0)
tl.scene("friends", ["n3"], lead=0.8, tail=1.8)
tl.scene("home", ["n4", "w1", "n5", 0.3, "w2"], lead=1.6, tail=1.0)
tl.scene("worry", ["t2", 0.4, "n6"], lead=1.0, tail=1.2)
tl.scene("invite", ["t3", "m3"], lead=1.0, tail=2.4)
tl.scene("sea", ["n7"], lead=0.8, tail=2.2)
tl.scene("middle", ["n8", "t4", 0.3, "m4", 0.5, "n9", 0.5, "m5"], lead=0.6, tail=1.0)
tl.scene("back", ["n10", 0.8, "t5", "m6", 0.5, "t6", 0.3, "n11"], lead=1.2, tail=2.2)
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

A = {}
SEA_W = 2700
WL = 600            # water line where the tortoise swims
SAND_Y = 590        # feet on the sand
TREE_X, TREE_B = 230, 574
SEAT = (TREE_X + 128, TREE_B - 190)
TS = 1.22           # tortoise scale
MS = 1.0            # monkey scale
SEA3 = "#3f82b5"

# ------------------------------------------------------------------ backgrounds
def sky(hh, ww, top=(236, 200, 120), bot=(250, 238, 206)):
    g = np.linspace(0, 1, hh)[:, None]
    col = (np.array(top, float) * (1 - g) + np.array(bot, float) * g).astype(np.uint8)
    return Image.fromarray(np.ascontiguousarray(np.broadcast_to(col[:, None, :], (hh, ww, 3))), 'RGB')

def sea_bands(p, M, x0, x1, rng, dark=False):
    cols = ["#8cbdd8", "#5b9cc8", SEA3] if not dark else ["#6c7fae", "#4d6a9e", "#33558a"]
    p.poly(M, [(x0, 400), (x1, 400), (x1, 472), (x0, 472)], cols[0], outline=None)
    p.poly(M, [(x0, 470), (x1, 470), (x1, 562), (x0, 562)], cols[1], outline=None)
    p.poly(M, [(x0, 560), (x1, 560), (x1, H), (x0, H)], cols[2], outline=None)
    p.line(M, [(x0, 400), (x1, 400)], "#2f6a94", 2)
    for _ in range(int((x1 - x0) / 9)):
        x, y = rng.uniform(x0, x1), rng.uniform(410, 700)
        w = 6 + (y - 400) / 22
        p.line(M, [(x - w, y), (x - w / 2, y - 3), (x, y), (x + w / 2, y - 3), (x + w, y)],
               "#bfe0f2" if y < 560 else "#9cc8e6", 1.2 + (y - 400) / 300)

def build_sea_world():
    ww, hh = SEA_W * SS, H * SS
    img = sky(hh, ww); p = Pen(img); M = S(SS); rng = np.random.default_rng(21)
    for k in range(16):
        a = math.radians(k * 22.5)
        p.poly(M, [(1010 + 40 * math.cos(a - 0.12), 105 + 40 * math.sin(a - 0.12)),
                   (1010 + 62 * math.cos(a), 105 + 62 * math.sin(a)),
                   (1010 + 40 * math.cos(a + 0.12), 105 + 40 * math.sin(a + 0.12))], "#e9a93a", outline=None)
    p.poly(M, ell(1010, 105, 40, 40), "#f2c14e", outline="#b9802a", w=2)
    for x in range(150, SEA_W, 420):
        cloud(p, M, x + rng.uniform(-60, 60), rng.uniform(80, 220), rng.uniform(0.75, 1.1))
    for _ in range(10):                                   # gulls
        bx, by = rng.uniform(0, SEA_W), rng.uniform(150, 300)
        p.line(M, [(bx - 9, by - 4), (bx, by), (bx + 9, by - 5)], "#5a4a3a", 1.6)
    sea_bands(p, M, 0, SEA_W, rng)
    # far island on the horizon (the tortoise's home)
    p.poly(M, ell(2380, 404, 170, 26, 40, 180, 360) + [(2550, 404), (2210, 404)], "#d9b98a", outline="#9c7a58", w=2)
    for x in (2330, 2410): cypress(p, M, x, 392, 60, 9)
    # shore (left)
    sand = [(0, 548), (300, 556), (470, 566), (580, 582), (660, 606), (720, 640), (770, 690), (790, H + 5), (0, H + 5)]
    p.poly(M, sand, "#e8cf96", outline="#b99a5c", w=2.5)
    p.line(M, [(600, 588), (668, 612), (724, 646), (760, 690)], "#fbf4e2", 3)          # foam
    for _ in range(60):
        sx, sy = rng.uniform(10, 640), rng.uniform(600, 700)
        if rng.random() < 0.5: p.poly(M, ell(sx, sy, 4, 2.5, 10), "#c9ab72", outline=None)
    for sx, sy in ((120, 650), (380, 676), (560, 640)):
        p.poly(M @ T(sx, sy), [(-8, 4), (0, -8), (8, 4)], "#f2b8a0", outline="#b97a60", w=1.2)      # shells
    fig_tree(p, M, TREE_X, TREE_B, rng)
    for x in (40, 520):
        for k in range(4):
            p.line(M, [(x + k * 6, 560), (x + k * 6 + 6 * math.sin(k), 520 - 6 * k)], "#6f8a4a", 2)
    return img

def crop_sea(cam):
    cx = int(round(cam * SS))
    return A['sea'].crop((cx, 0, cx + W * SS, H * SS)).convert('RGBA')

def build_island():
    img = sky(H * SS, W * SS, (96, 82, 140), (243, 178, 128)); p = Pen(img); V = S(SS)
    rng = np.random.default_rng(8)
    for _ in range(40):
        x, y = rng.uniform(30, 1250), rng.uniform(30, 260); r = rng.uniform(1.0, 2.2)
        p.poly(V, ell(x, y, r, r, 8), (255, 244, 220), outline=None)
    p.poly(V, ell(1070, 120, 38, 38, 40), "#fff4c8", outline=None)
    p.poly(V, ell(1088, 108, 33, 33, 40), (118, 98, 150), outline=None)          # crescent
    p.poly(V, ell(250, 390, 120, 40, 30), (232, 160, 140), outline=None)        # sunset glow
    sea_bands(p, V, 0, W, rng, dark=True)
    p.poly(V, ell(640, 668, 600, 150, 60, 180, 360) + [(1240, 668), (40, 668)], "#dcbc84", outline="#9c7a58", w=2.5)
    p.poly(V, ell(640, 676, 560, 120, 60, 180, 360) + [(1200, 676), (80, 676)], "#e8cf96", outline=None)
    for x in (130, 1150):
        for k in range(5):
            p.line(V, [(x + k * 7, 640), (x + k * 7 + 8 * math.sin(k * 2), 570 - 9 * k)], "#5f7a3a", 2.2)
    cypress(p, V, 1060, 545, 150, 20); cypress(p, V, 1110, 552, 120, 16)
    # little Persian rug
    rug = [(700, 600), (980, 600), (1010, 650), (680, 650)]
    p.poly(V, rug, "#a8322c", outline="#5e1a14", w=2)
    p.poly(V, [(712, 606), (968, 606), (992, 644), (694, 644)], None, outline="#e2b64a", w=2)
    for k in range(5):
        cx = 735 + k * 55
        p.poly(V, khatam(cx, 625, 9), "#e2b64a", outline=None)
    for x in range(684, 1012, 12):
        p.line(V, [(x, 650), (x - 2, 658)], "#e2b64a", 1.2)
    # lantern
    p.line(V, [(200, 610), (200, 530)], "#6b4226", 3)
    p.poly(V, [(186, 530), (214, 530), (218, 558), (182, 558)], "#f2c14e", outline="#8a6418", w=2)
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
    fa_text(d, (w / 2 * SS, 98 * SS), "دوست", 74 * SS, (28, 52, 99, 255))
    f2 = ImageFont.truetype(FB, 32 * SS)
    d.text((w / 2 * SS, 166 * SS), "doost  =  friend", font=f2, fill=(90, 50, 12, 255), anchor="mm")
    return im

def init():
    ME.init_assets()
    A['border'] = ME.ASSETS['border']; A['card'] = ME.ASSETS['card']
    A['tree'] = build_tree_set().convert('RGBA')
    A['sea'] = build_sea_world()
    A['island'] = build_island().convert('RGBA')
    A['wcard'] = build_word_card()
    gold, cream = (226, 182, 74, 255), (250, 240, 214, 255)
    A['t1'] = text_img("KALILA & DIMNA", FB, 60, gold, 2, (90, 60, 12, 255))
    A['t2'] = text_img("The Monkey and the Tortoise", FI, 46, cream)
    A['t3'] = text_img("—  Episode 2  —", FR, 24, gold)
    A['e1'] = text_img("Next time", FI, 30, cream)
    A['e2'] = text_img("The Ring-Dove and the Hunter's Net", FB, 42, gold, 2, (90, 60, 12, 255))
    A['e3'] = text_img("A new story every Saturday", FR, 26, cream)
    A['q'] = text_img("?", FB, 50, (250, 240, 214, 255), 3, (40, 24, 10, 255))
    A['bang'] = text_img("!", FB, 54, (200, 40, 30, 255), 3, (255, 255, 255, 255))
    A['ha'] = text_img("ha ha!", FI, 26, (90, 50, 12, 255))

# ------------------------------------------------------------------ actors
def monkey(p, V, x, y, t, face=1, sit=1, **kw):
    s = spk('M', t)
    po = dict(t=t, mouth=s, sit=sit, blink=blink(t, 0.4), look=kw.pop('look', 0.3),
              head=kw.pop('head', 0) + 6 * s * math.sin(t * 9), arm=6 + 10 * s * math.sin(t * 5))
    po.update(kw)
    draw_monkey(p, V @ T(x, y) @ S(MS * face, MS), po)

def tortoise(p, V, x, y, t, face=1, wife=False, sc=TS, **kw):
    who = 'W' if wife else 'T'
    s = spk(who, t)
    po = dict(t=t, mouth=s, blink=blink(t, 1.9 if not wife else 0.9), beard=False,
              shell="#5d8a3a" if not wife else "#8a4f7a", band="#d4a63c" if not wife else "#e8b4c8",
              head=6 * s * math.sin(t * 7))
    if wife: po.update(lash=True, flower="#fff7ea")
    hd = kw.pop('head', 0); po.update(kw); po['head'] += hd
    draw_tortoise(p, V @ T(x, y) @ S(sc * face, sc), po)

def water_front(fr, V, x0, x1, t, clip=None):
    """opaque strip of sea in front of a swimming tortoise (hides legs and lower shell)"""
    p = Pen(fr)
    if clip is not None: x0 = max(x0, clip)
    if x1 <= x0: return
    xs = list(np.arange(x0, x1 + 1, 8))
    top = [(x, WL + 4 * math.sin(x / 34 + t * 3.2)) for x in xs]
    p.poly(V, top + [(x1, H + 5), (x0, H + 5)], SEA3, outline=None)
    p.line(V, top, "#d6ecf7", 2.2)

def swimmer(fr, V, x, t, face=1, land=0.0, rider=None, clip=650, wife=False, **kw):
    """tortoise swimming (land=0) or on the sand (land=1); optional monkey rider (dict of monkey kwargs)"""
    bob = 3 * math.sin(t * 2.6) * (1 - land)
    y = (WL + 24) * (1 - land) + SAND_Y * land + bob
    p = Pen(fr)
    tortoise(p, V, x, y, t, face=face, walk=t * (5 if land < 1 else 3), amp=1, wife=wife, **kw)
    if rider is not None:
        monkey(p, V, x - 4 * face, y - 78 * TS, t, face=rider.pop('face', face), **rider)
    if land < 1:
        water_front(fr, V, x - 120, x + 120, t, clip=clip)

def falling_fig(p, V, t, t0, x0, y0, x1, y1, dur=0.9):
    u = (t - t0) / dur
    if 0 <= u <= 1:
        x = x0 + (x1 - x0) * u; y = y0 + (y1 - y0) * u * u - 30 * math.sin(math.pi * u)
        fig(p, V, x, y, 8)

# ------------------------------------------------------------------ scenes
KX, DX, HS = 420, 850, 1.32
def tree_frame(name, t):
    fr = A['tree'].copy(); p = Pen(fr); V = S(SS)
    kpo = jackal_pose('kalila', t, spk('K', t), look=0.6)
    dpo = jackal_pose('dimna', t, spk('D', t), look=0.6)
    if name == "tree_close":
        c3 = cue('c3')
        if c3[1] < t < c3[1] + 1.0: dpo['hop'] = 30 * abs(math.sin(math.pi * (t - c3[1]) / 0.5))
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

def shore_frame(t):
    a, b = SB("shore"); lt = t - a
    fr = crop_sea(0); p = Pen(fr); V = S(SS)
    m1 = cue('m1')
    sigh = env(t, m1[1] - 0.3, cend('m1') + 0.6, 0.4, 0.6)
    look = math.sin(lt * 0.7)
    monkey(p, V, *SEAT, t, look=look, head=-4 * look + 8 * sigh, arm=20 + 30 * sigh, arm2=-10)
    return fr

def meet_frame(t):
    a, b = SB("meet"); lt = t - a
    fr = crop_sea(0); V = S(SS)
    arr = cend('n2') + 0.2
    u = sm(a + 0.2, arr, t)
    x = 1180 - (1180 - 690) * u
    land = sm(arr, arr + 1.0, t)
    x -= 170 * land
    swimmer(fr, V, x, t, face=-1, land=land, head=-6 if t > cue('m2')[1] else 0)
    p = Pen(fr)
    m2 = cue('m2'); drop = cend('m2') + 0.15
    waving = env(t, m2[1], cend('m2'), 0.3, 0.3)
    holding = m2[1] + 0.8 < t < drop
    monkey(p, V, *SEAT, t, look=1.0, head=10, arm=-60 - 50 * waving * (0.6 + 0.4 * math.sin(t * 9)) if not holding else -70,
           fig=holding)
    hx = x - 62 * TS * 1.3
    falling_fig(p, V, t, drop, SEAT[0] + 40, SEAT[1] - 40, hx + 8, SAND_Y - 70, 0.85)
    if t > drop + 0.85 and t < cue('t1')[1] + 0.6:
        fig(p, V, hx + 8, SAND_Y - 70, 8)
    return fr

def friends_frame(t):
    a, b = SB("friends"); lt = t - a; u = lt / (b - a)
    fr = crop_sea(0)
    warm = math.sin(math.pi * u * 3) ** 2
    fr = tint(fr, (255, 150, 90), 0.20 * warm)
    p = Pen(fr); V = S(SS)
    laugh = max(0.0, math.sin(lt * 2.1)) ** 2
    tx = 540
    tortoise(p, V, tx, SAND_Y, t, face=-1, mouth=max(spk('T', t), 0.8 * laugh * (0.5 + 0.5 * math.sin(t * 14))),
             head=-8 - 6 * laugh)
    period = 2.6; k = int(lt / period); t0 = a + k * period + 0.6
    throw = env(t, t0 - 0.5, t0 + 0.1, 0.2, 0.1)
    monkey(p, V, *SEAT, t, look=1.0, head=10 - 8 * laugh, arm=-40 - 80 * throw,
           mouth=max(spk('M', t), 0.8 * laugh * (0.5 + 0.5 * math.sin(t * 13 + 1))))
    falling_fig(p, V, t, t0, SEAT[0] + 40, SEAT[1] - 50, tx - 70, SAND_Y - 80, 0.9)
    if laugh > 0.5:
        put_text(fr, A['ha'], 640, 300 + 8 * math.sin(t * 3), (laugh - 0.5) * 2)
    for j in range(6):                                  # little floating stars of friendship
        ph = (lt * 0.25 + j / 6) % 1
        M = V @ T(400 + j * 60 + 20 * math.sin(lt + j), 520 - 220 * ph) @ R(t * 50) @ S(0.5 + 0.5 * math.sin(math.pi * ph))
        p.poly(M, khatam(0, 0, 10), "#f2c14e", outline="#b9802a", w=1)
    return fr

def home_frame(t):
    a, b = SB("home"); lt = t - a
    fr = A['island'].copy(); p = Pen(fr); V = S(SS)
    n5 = cue('n5'); pret = word_time('n5', 'pretended')
    lie = sm(pret, pret + 0.8, t)
    peek = (word_time('n5', 'terrible') - 0.4 < t < cend('n5') + 0.1)
    wpo = dict(sick=lie > 0.5, head=26 * lie - 8 * spk('W', t) * (1 - lie) + 10 * spk('W', t) * lie,
               blink=1.0 if (lie > 0.5 and not peek) else blink(t, 0.9), sad=lie)
    if spk('W', t) > 0.05 and lie < 0.5: wpo['head'] -= 6
    tortoise(p, V, 830, 628 + 10 * lie, t, face=-1, wife=True, **wpo)
    hx = -120 + 560 * sm(a + 0.2, cue('w1')[1], t)
    walking = t < cue('w1')[1]
    tortoise(p, V, hx, 628, t, face=1, walk=t * 4 if walking else 0, amp=1 if walking else 0,
             head=8 * sm(cue('w1')[1], cue('w1')[1] + 0.5, t), sad=sm(cue('w2')[1], cend('w2'), t))
    if t > cend('w2') - 0.4:
        put_text(fr, A['bang'], hx + 70, 470, env(t, cend('w2') - 0.4, b, 0.2, 0.4))
    return fr

def worry_frame(t):
    a, b = SB("worry"); lt = t - a
    fr = A['island'].copy(); p = Pen(fr); V = S(SS)
    tortoise(p, V, 900, 636, t, face=-1, wife=True, sc=0.95, sick=True, blink=1.0, head=26)
    n6 = cue('n6')
    down = sm(word_time('n6', 'sadly'), word_time('n6', 'sadly') + 0.8, t)
    x = 520 + 60 * math.sin(lt * 0.8) * (1 - down)
    face = 1 if math.cos(lt * 0.8) > 0 or down > 0 else -1
    tortoise(p, V, x, 640, t, face=face, walk=lt * 3, amp=1 if down < 0.5 else 0, head=6 + 18 * down, sad=1)
    for j in range(3):
        ph = (lt * 0.4 + j / 3) % 1
        put_text(fr, A['q'], x - 40 + j * 40, 470 - 60 * ph, math.sin(math.pi * ph) * (1 - down))
    return fr

def invite_frame(t):
    a, b = SB("invite"); lt = t - a
    fr = crop_sea(0); p = Pen(fr); V = S(SS)
    tx = 560
    j0 = cend('m3') + 0.15; JD_ = 1.0
    u = clamp((t - j0) / JD_)
    tortoise(p, V, tx, SAND_Y, t, face=-1, head=-12 if t < j0 else 0)
    bx, by = tx + 4, SAND_Y - 78 * TS
    if u <= 0:
        monkey(p, V, *SEAT, t, look=1.0, head=10, arm=-30 - 60 * env(t, cue('m3')[1], cend('m3'), 0.2, 0.3))
    else:
        x = SEAT[0] + (bx - SEAT[0]) * u; y = SEAT[1] + (by - SEAT[1]) * u - 140 * math.sin(math.pi * u)
        monkey(p, V, x, y, t, face=1 if u < 0.6 else -1, sit=1 if u > 0.85 else 0, arm=-150, arm2=-140, look=0)
    return fr

def sea_frame(t):
    a, b = SB("sea"); lt = t - a
    cam = 1300 * sm(a + 0.3, b - 0.2, t)
    fr = crop_sea(cam); V = S(SS) @ T(-cam, 0)
    swimmer(fr, V, cam + 760, t, face=1, rider=dict(look=0.5, arm=-100 - 30 * math.sin(t * 3), arm2=-60,
                                                    head=-6 * math.sin(t * 1.3)), clip=None)
    return fr

def middle_frame(t):
    a, b = SB("middle"); lt = t - a
    cam = 1300
    fr = crop_sea(cam); V = S(SS) @ T(-cam, 0)
    m4 = cue('m4'); shock = env(t, m4[1] - 0.1, m4[1] + 0.8, 0.1, 0.3)
    idea_t = word_time('n9', 'used his head')
    idea = sm(idea_t - 0.2, idea_t + 0.3, t) * (1 - sm(cue('m5')[1] + 1.5, cue('m5')[1] + 2.0, t))
    look = -1.0 if cue('t4')[1] < t < cend('m4') + 1 else 0.3
    rider = dict(look=look, hop=22 * math.sin(math.pi * clamp((t - m4[1]) / 0.5)) if m4[1] < t < m4[1] + 0.5 else 0,
                 head=14 if look < 0 else -8 * idea, arm=-120 * shock - 40 * spk('M', t) * (1 + math.sin(t * 4)),
                 arm2=-150 * shock)
    sad = cue('t4')[1] < t
    swimmer(fr, V, cam + 640, t, face=1, rider=rider, clip=None, head=-14 if cue('t4')[1] < t < cend('t4') else 0,
            sad=1 if sad else 0)
    p = Pen(fr)
    if shock > 0:
        put_text(fr, A['bang'], 640, 330, shock)
    if idea > 0:
        M = V @ T(cam + 650, 300 - 10 * math.sin(t * 4)) @ S(idea) @ R(t * 40)
        p.poly(M, khatam(0, 0, 22), "#f2c14e", outline="#b9802a", w=2)
    return fr

def back_frame(t):
    a, b = SB("back"); lt = t - a
    arrive = word_time('n10', 'moment') + 0.2
    cam = 1300 * (1 - sm(a + 0.2, arrive, t))
    fr = crop_sea(cam); V = S(SS) @ T(-cam, 0)
    leap = word_time('n10', 'leapt') + 0.1
    n11 = cue('n11'); leave = n11[1] + 0.3
    land = sm(arrive, arrive + 1.0, t) * (1 - sm(leave + 0.3, leave + 1.6, t))
    if t < leave:
        x = cam + 640 - 90 * sm(arrive, arrive + 1.0, t)
        face = -1
    else:
        x = 550 + 900 * sm(leave, b, t); face = 1
    u = clamp((t - leap) / 0.9)
    rider = None
    if t < leap:
        rider = dict(face=-1, look=0, arm=-110, arm2=-40)
    tsad = 1 if t > cue('m6')[1] else 0
    swimmer(fr, V, x, t, face=face, land=land, rider=rider, head=-14 if cue('t5')[1] < t < cend('t6') else 6 * tsad,
            sad=tsad)
    p = Pen(fr)
    if t >= leap:
        bx, by = 554, SAND_Y - 78 * TS
        if u < 1:
            mx = bx + (SEAT[0] - bx) * u; my = by + (SEAT[1] - by) * u - 170 * math.sin(math.pi * u)
            monkey(p, V, mx, my, t, face=-1 if u < 0.7 else 1, sit=0 if u < 0.85 else 1, arm=-160, arm2=-150, look=0)
        else:
            m6 = cue('m6'); talking = m6[1] < t < cend('m6')
            wave_ = env(t, leave, b - 0.5, 0.4, 0.4)
            monkey(p, V, *SEAT, t, look=1.0, head=12, arm=(-70 if talking else 8) - 90 * wave_ * (0.6 + 0.4 * math.sin(t * 8)),
                   arm2=-30 if talking else 6)
    return fr

def render(i):
    t = i / FPS
    name, lt, sd = tl.scene_at(t)
    if name is None: name, lt, sd = "end", 4.0, 4.6
    if name.startswith("tree"): fr = tree_frame(name, t)
    elif name in ("title", "end"): fr = card_frame(t, name)
    elif name == "shore": fr = shore_frame(t)
    elif name == "meet": fr = meet_frame(t)
    elif name == "friends": fr = friends_frame(t)
    elif name == "home": fr = home_frame(t)
    elif name == "worry": fr = worry_frame(t)
    elif name == "invite": fr = invite_frame(t)
    elif name == "sea": fr = sea_frame(t)
    elif name == "middle": fr = middle_frame(t)
    elif name == "back": fr = back_frame(t)
    else: fr = card_frame(t, "end")
    fr.alpha_composite(A['border'])
    img = fr.convert('RGB').resize((W, H), Image.LANCZOS)
    f = min(clamp(lt / 0.35), clamp((sd - lt) / 0.35))
    if name == "tree_open": f = min(clamp(lt / 0.7), clamp((sd - lt) / 0.35))
    if name == "end": f = min(clamp(lt / 0.35), clamp((sd - lt) / 0.8))
    if name == "sea": f = clamp(lt / 0.35)                  # the ride flows straight into the middle of the sea
    if name == "middle": f = min(1.0, clamp((sd - lt) / 0.35))
    if f < 0.999: img = Image.blend(Image.new('RGB', (W, H)), img, f)
    return img.tobytes()

# ------------------------------------------------------------------ audio
def waves_noise(n, seed=3):
    wn = np.random.default_rng(seed).standard_normal(n)
    k = 400; lp = np.convolve(wn, np.ones(k) / k, 'same')
    lp /= np.abs(lp).max() + 1e-9
    tt = np.arange(n) / SR
    return lp * (0.55 + 0.45 * np.sin(2 * np.pi * tt / 5.5) ** 2)

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
    a, b = sc['tree_open']; seq(a + 0.2, 0.32, playful, 0.7, end=b - 0.2); tombak(a + 0.2, b - 0.3, 0.64, 0.3)
    a, b = sc['title']; seq(a + 0.2, 0.3, ["A3", "D4", "Ek4", "F4", "Ek4", "D4", "C4", "D4", "-", "A4"], 0.9)
    a, b = sc['shore']; seq(a + 0.2, 0.42, flow, 0.55, 1.8, end=b - 0.2)
    a, b = sc['meet']; seq(a + 0.2, 0.3, happy, 0.55, 1.2, end=b - 0.2)
    drop = cend('m2') + 0.15
    seq(drop, 0.09, ["A4", "F4", "D4"], 0.6, 0.8); add(mus, drop + 0.85, santur(NOTES['D5'], 1.0), 0.7)
    a, b = sc['friends']; seq(a + 0.2, 0.25, happy + ["D5", "-", "A4", "-"], 0.7, 1.2, end=b - 0.3); tombak(a + 0.2, b - 0.4, 0.5, 0.4)
    a, b = sc['home']; seq(a + 0.3, 0.7, ["D4", "-", "C4", "Bb3", "A3", "-", "Bb3", "C4", "D4", "-", "-", "-"], 0.55, 2.2, end=b - 0.3)
    w2 = cue('w2'); add(mus, cend('w2') - 0.2, dum(0.8), 0.9)
    seq(cend('w2') - 0.2, 0.18, ["Ek4", "D4", "C4", "Bb3"], 0.5, 1.4)
    a, b = sc['worry']; riz(a + 0.2, b - 0.3, 'D3', 0.18); seq(a + 0.4, 0.9, ["D3", "Ek3", "D3", "-", "C3", "D3", "-", "-"], 0.8, 2.4, end=b - 0.4)
    a, b = sc['invite']; seq(a + 0.2, 0.34, ["D4", "F4", "A4", "-", "G4", "F4", "Ek4", "D4", "-", "-"], 0.55, 1.4, end=b - 0.2)
    j0 = cend('m3') + 0.15; seq(j0, 0.08, ["D4", "F4", "A4", "D5"], 0.6, 1.0)
    a, b = sc['sea']; seq(a + 0.1, 0.3, ["D4", "-", "F4", "Ek4", "D4", "-", "A3", "C4", "D4", "-", "F4", "G4", "A4", "-", "G4", "F4"], 0.75, end=b)
    tombak(a + 0.1, b, 0.6, 0.4)
    a, b = sc['middle']
    riz(a + 0.2, cue('m4')[1], 'A3', 0.3, swell=True)
    add(mus, cue('m4')[1], dum(0.8), 1.0); seq(cue('m4')[1], 0.12, ["Ek4", "D4", "C4", "A3"], 0.7, 1.4)
    riz(cend('m4') + 0.3, word_time('n9', 'used his head') - 0.2, 'D3', 0.25, swell=True)
    it = word_time('n9', 'used his head') - 0.2
    seq(it, 0.08, ["D4", "F4", "A4", "D5"], 0.6, 1.0)
    seq(cue('m5')[1], 0.3, ["A4", "Bb4", "C5", "A4", "G4", "A4", "-", "F4", "G4", "A4", "-", "-"], 0.45, 1.2, end=b - 0.2)
    a, b = sc['back']
    seq(a + 0.1, 0.3, flow, 0.6, 1.4, end=word_time('n10', 'leapt'))
    lp = word_time('n10', 'leapt') + 0.1
    seq(lp, 0.07, ["D4", "Ek4", "F4", "G4", "A4", "Bb4", "C5", "D5"], 0.7, 0.8)
    seq(cue('m6')[1], 0.6, ["D4", "-", "C4", "D4", "F4", "-", "Ek4", "D4", "-", "-"], 0.5, 2.0, end=cend('t6'))
    seq(cue('n11')[1], 0.7, ["A3", "-", "C4", "Bb3", "A3", "-", "G3", "A3", "-", "D3", "-", "-"], 0.6, 2.4, end=b - 0.2)
    a, b = sc['tree_close']; seq(a + 0.2, 0.36, ["D4", "-", "F4", "G4", "A4", "-", "Bb4", "A4", "G4", "-", "F4", "Ek4", "D4", "-", "-", "-"], 0.6, end=b - 0.2)
    c3 = cue('c3'); seq(c3[1] - 0.3, 0.1, ["D5", "A4", "D5", "F4"], 0.5, 1.6)
    a, b = sc['end']
    seq(a + 0.2, 0.3, ["D4", "F4", "A4", "D5", "-", "C5", "A4", "Bb4", "A4", "-", "-", "D4"], 0.85)
    for nn in ("D3", "A3", "D4"): add(mus, a + 3.3, santur(NOTES[nn], 2.0), 0.8)
    mus += (np.sin(2 * np.pi * NOTES['D2'] * t) + 0.5 * np.sin(2 * np.pi * NOTES['A2'] * t)) * 0.05
    # sea ambience
    wv = waves_noise(N)
    gate = np.zeros(N)
    for nm in ("shore", "meet", "friends", "invite", "sea", "middle", "back"):
        a, b = sc[nm]; i, j = int(a * SR), int(b * SR); gate[i:j] = 1
    for nm in ("home", "worry"):
        a, b = sc[nm]; i, j = int(a * SR), int(b * SR); gate[i:j] = 0.5
    gate = np.convolve(gate, np.ones(int(0.5 * SR)) / int(0.5 * SR), 'same')
    sfx += wv * gate * 0.35
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
    tl.srt(os.path.join(EP, "ep02.en.srt"), NAMES_EN)
    write_fa_srt(os.path.join(EP, "ep02.fa.srt"))
    out = os.path.join(EP, "render_ep02.mp4")
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
