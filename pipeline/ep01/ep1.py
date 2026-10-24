#!/usr/bin/env python3
"""Kalila & Dimna — Episode 1: The Lion and the Hare (full version, ~3.5 min)."""
import os, sys, math, wave, subprocess
import numpy as np
from PIL import Image, ImageDraw
import multiprocessing as mp
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from kd_lib import *
import make_episode as ME
EP = os.path.dirname(os.path.abspath(__file__))

# ------------------------------------------------------------------ timeline
tl = Timeline(os.path.join(EP, "vo"))
tl.scene("tree_open", ["o1", "o2", "o3"], lead=1.2, tail=0.7)
tl.scene("title", [], lead=3.4, tail=0)
tl.scene("forest", ["n1"], lead=1.6, tail=1.6)
tl.scene("lion", [1.0, "n2", "l1", 0.5, "n3"], lead=2.4, tail=1.4)
tl.scene("council", ["e1", "f1", 0.3, "t1"], lead=1.8, tail=1.2)
tl.scene("cave", ["t2", "l2", 0.4, "n4"], lead=1.4, tail=1.2)
tl.scene("lots", ["h1", 1.4, "h2"], lead=1.8, tail=1.0)
tl.scene("angry", ["l3", "h3", "l4", "h4"], lead=3.2, tail=1.0)
tl.scene("walk", ["n5"], lead=0.6, tail=3.0)
tl.scene("well", ["h5", "l5", 1.2, "n6"], lead=1.0, tail=3.4)
tl.scene("party", ["h6", 0.3, "t3"], lead=1.6, tail=2.2)
tl.scene("tree_close", ["c1", "c2", "c3"], lead=0.8, tail=1.0)
tl.scene("end", [], lead=4.6, tail=0)
DUR = tl.t
NF = int(DUR * FPS)
ENV = tl.envelopes(NF)
def spk(who, t): return ENV.get(who, np.zeros(NF + 1))[min(NF, int(t * FPS))]
def SB(name): return [(a, b) for n, a, b in tl.scenes if n == name][0]
def cue(k): return tl.cue(k)
def word_time(key, word, frac=0.0):
    k, st, d, _, txt = tl.cue(key)
    i = txt.lower().find(word.lower())
    return st + d * (max(i, 0) / len(txt)) * 0.97 + frac
def blink(t, off=0.0): return 1.0 if ((t + off) % 3.9) < 0.12 else 0.0

GROUND = 605
A = {}

# ------------------------------------------------------------------ backgrounds
def crop_world(cam):
    cx = int(cam * SS)
    return ME.ASSETS['world'].crop((cx, 0, cx + W * SS, H * SS)).convert('RGBA')

def tint(img, rgb, amt):
    ov = Image.new('RGBA', img.size, rgb + (255,))
    return Image.blend(img, ov, amt)

def build_forest():
    im = crop_world(0); p = Pen(im); V = S(SS)
    top = [(x, 655 + 6 * math.sin(x / 70)) for x in range(0, W + 10, 10)]
    bot = [(x, 700 + 5 * math.sin(x / 55 + 1)) for x in range(W, -10, -10)]
    p.poly(V, top + bot, "#5b9cc8", outline="#2f6a94", w=2)
    for k in range(9):
        x = 60 + k * 140
        p.line(V, [(x, 676), (x + 22, 672), (x + 44, 676)], "#bfe0f2", 2)
    return im

def build_night():
    im = crop_world(1150)
    arr = np.array(im).astype(np.float32)
    arr[..., :3] = arr[..., :3] * np.array([0.30, 0.34, 0.58]) + np.array([8, 10, 30])
    im = Image.fromarray(arr.clip(0, 255).astype(np.uint8), 'RGBA')
    p = Pen(im); V = S(SS); rng = np.random.default_rng(2)
    for _ in range(70):
        x, y = rng.uniform(30, 1250), rng.uniform(30, 330)
        r = rng.uniform(1.2, 2.6)
        p.poly(V, ell(x, y, r, r, 8), (255, 244, 210), outline=None)
    p.poly(V, ell(1030, 110, 46, 46, 40), "#fff4c8", outline=None)
    p.poly(V, ell(1050, 98, 40, 40, 40), (30, 40, 80), outline=None)        # crescent
    return im

def build_cave():
    im = crop_world(500); p = Pen(im); V = S(SS)
    rock = [(820, 610), (850, 420), (930, 330), (1060, 290), (1190, 320), (1290, 380), (1290, 610)]
    p.poly(V, rock, "#a58a6c", outline="#5e4a36", w=3)
    p.poly(V, [(900, 610), (930, 470), (1010, 410), (1110, 420), (1170, 480), (1190, 610)], "#3a2c22", outline="#24190f", w=2)
    for (x, y) in [(870, 470), (1220, 360), (1150, 330), (960, 360)]:
        p.line(V, [(x, y), (x + 30, y + 8), (x + 50, y + 2)], "#7c6550", 2)
    return im

def init():
    ME.init_assets()
    A['border'] = ME.ASSETS['border']; A['card'] = ME.ASSETS['card']
    A['tree'] = build_tree_set().convert('RGBA')
    A['forest'] = build_forest()
    A['night'] = build_night()
    A['cave'] = build_cave()
    gold, cream = (226, 182, 74, 255), (250, 240, 214, 255)
    A['t1'] = text_img("KALILA & DIMNA", FB, 60, gold, 2, (90, 60, 12, 255))
    A['t2'] = text_img("The Lion and the Hare", FI, 46, cream)
    A['t3'] = text_img("—  Episode 1  —", FR, 24, gold)
    A['e1'] = text_img("Next time", FI, 30, cream)
    A['e2'] = text_img("The Monkey and the Tortoise", FB, 50, gold, 2, (90, 60, 12, 255))
    A['e3'] = text_img("A new story every Saturday", FR, 26, cream)
    A['zzz'] = text_img("z z z", FI, 26, (60, 60, 90, 255))
    A['bang'] = text_img("!", FB, 54, (200, 40, 30, 255), 3, (255, 255, 255, 255))

# ------------------------------------------------------------------ actors
def lion_po(t, angry=0.6, look=0.0, extra_mouth=0.0):
    s = spk('L', t)
    return dict(t=t, mouth=max(min(1, 1.2 * s), extra_mouth), shake=s, angry=max(angry, s), head=-10 * s + look)

def hare(p, V, x, t, face=1, hop=0.0, sc=1.15, ear_down=0.0, extra=None):
    s = spk('H', t)
    po = dict(t=t, hop=hop, head=7 * s * math.sin(t * 11), ear=4 * s + 9 * s * math.sin(t * 7) - ear_down)
    if extra: po.update(extra)
    draw_hare(p, V @ T(x, GROUND + 2) @ S(sc * face, sc), po)

def hop_cycle(t, period=0.42, h=28):
    ph = (t % period) / period
    return h * math.sin(math.pi * ph), ph

def deer(p, V, x, t, face=1, neck=0.0, walk=0.0, amp=0.0, sc=0.92):
    draw_deer(p, V @ T(x, GROUND + 2) @ S(sc * face, sc),
              dict(t=t, neck=neck, mouth=spk('E', t), blink=blink(t, 0.7), walk=walk, amp=amp))

def fox(p, V, x, t, face=1, sleep=False, walk=0.0, amp=0.0, sc=1.0):
    po = jackal_pose('fox', t, spk('F', t), look=0.4)
    if sleep: po['blink'] = 1.0; po['head'] = 14; po['wag'] = 0.1
    po['walk'] = walk; po['amp'] = amp
    draw_jackal(p, V @ T(x, GROUND + 2) @ S(sc * face, sc), 'fox', po)

def tortoise(p, V, x, t, face=1, walk=0.0, amp=0.0, sc=1.0):
    draw_tortoise(p, V @ T(x, GROUND + 2) @ S(sc * face, sc),
                  dict(t=t, mouth=spk('T', t), blink=blink(t, 1.9), walk=walk, amp=amp))

def lion(p, V, x, t, face=1, po=None, walk=0.0, amp=0.0, y=GROUND, sc=1.05, lean=0.0):
    po = po or lion_po(t)
    po.setdefault('walk', walk); po.setdefault('amp', amp)
    po['walk'] = walk; po['amp'] = amp
    M = V @ T(x, y) @ S(sc * face, sc) @ T(62, 0) @ R(lean) @ T(-62, 0)
    draw_lion(p, M, po)

# ------------------------------------------------------------------ scenes
KX, DX, HS = 420, 850, 1.32
def tree_frame(name, t):
    fr = A['tree'].copy(); p = Pen(fr); V = S(SS)
    kpo = jackal_pose('kalila', t, spk('K', t), look=0.6)
    dpo = jackal_pose('dimna', t, spk('D', t), look=0.6)
    if name == "tree_close":
        c2 = cue('c2')
        if c2[1] < t < c2[1] + 1.0: dpo['hop'] = 30 * abs(math.sin(math.pi * (t - c2[1]) / 0.5))
    draw_jackal(p, V @ T(DX, 640) @ S(-HS, HS), 'dimna', dpo)
    bush(p, V, 1125, 650, 1.35, 0)
    draw_jackal(p, V @ T(KX, 640) @ S(HS), 'kalila', kpo)
    return fr

def title_frame(t):
    a, b = SB("title"); lt = t - a
    fr = A['card'].copy()
    ME.card_rosette(fr, t, 190)
    put_text(fr, A['t1'], W / 2, 330, sm(0.2, 0.9, lt))
    put_text(fr, A['t2'], W / 2, 410, sm(0.6, 1.3, lt))
    put_text(fr, A['t3'], W / 2, 470, sm(1.0, 1.7, lt))
    return fr

def forest_frame(t):
    a, b = SB("forest"); lt = t - a
    fr = A['forest'].copy(); p = Pen(fr); V = S(SS)
    deer(p, V, 170, t, neck=115 if (lt % 6) < 4.5 else 10)
    fox(p, V, 480, t, sleep=True)
    if (lt % 2.4) < 0.1 or True:
        put_text(fr, A['zzz'], 560 + 6 * math.sin(t * 2), 420 - 10 * ((t * 0.6) % 1), 0.6 + 0.4 * math.sin(t * 3))
    tortoise(p, V, 700 + 6 * lt, t, walk=t * 2, amp=1)
    hx = 1030 + 90 * math.sin(lt * 0.9)
    h, _ = hop_cycle(t, 0.5, 26)
    face = 1 if math.cos(lt * 0.9) > 0 else -1
    hare(p, V, hx, t, face=face, hop=h)
    return fr

def lion_frame(t):
    a, b = SB("lion"); lt = t - a
    base = A['forest'].copy()
    dark = 0.28 * sm(0.0, 1.5, lt)
    fr = tint(base, (60, 30, 30), dark); p = Pen(fr); V = S(SS)
    n3 = cue('n3'); run = sm(n3[1] + 0.5, n3[1] + 3.5, t)
    roar1 = env(lt, 1.0, 2.6, 0.2, 0.4)
    # animals: freeze, then flee left
    fl = -1 if run > 0 else 1
    deer(p, V, 170 - 600 * run, t, face=fl if run > 0 else 1, neck=0 if lt > 1.0 else 115,
         walk=t * 6, amp=26 * (run > 0 and run < 1))
    fox(p, V, 450 - 800 * run, t, face=-1 if run > 0 else 1, sleep=lt < 1.0, walk=t * 8, amp=24 * (run > 0 and run < 1))
    tortoise(p, V, 640 - 260 * run, t, face=-1 if run > 0 else 1, walk=t * 4, amp=1)
    h = hop_cycle(t, 0.3, 30)[0] if run > 0 else 0
    hare(p, V, 860 - 900 * run, t, face=-1 if run > 0 else 1, hop=h, ear_down=12 * (lt > 1.0))
    # lion walks in from the right
    lx = 1560 - 440 * sm(0.0, 2.2, lt)
    moving = lt < 2.2
    po = lion_po(t, angry=0.8, extra_mouth=roar1)
    po['shake'] = max(po['shake'], roar1)
    lion(p, V, lx, t, face=-1, po=po, walk=lx / 30, amp=24 if moving else 0)
    return fr

def council_frame(t):
    fr = A['night'].copy(); p = Pen(fr); V = S(SS)
    deer(p, V, 260, t, sc=0.88)
    fox(p, V, 480, t, sc=0.95)
    hare(p, V, 1010, t, face=-1, ear_down=8)
    tortoise(p, V, 760, t, face=-1, sc=1.15)
    return fr

def cave_frame(name, t):
    fr = A['cave'].copy(); p = Pen(fr); V = S(SS)
    if name == "cave":
        tremble = 2.0 * math.sin(t * 40)
        deer(p, V, 230 + tremble, t, sc=0.88)
        fox(p, V, 400 - tremble, t, sc=0.95)
        hare(p, V, 520 + tremble, t, ear_down=10)
        tortoise(p, V, 680, t, sc=1.1)
        lion(p, V, 1000, t, face=-1, po=lion_po(t, angry=0.5, look=8))
    return fr

def lots_frame(t):
    fr = tint(crop_world(900), (255, 240, 200), 0.05); p = Pen(fr); V = S(SS)
    a, b = SB("lots"); lt = t - a
    h1, h2 = cue('h1'), cue('h2')
    # stone with sticks
    p.poly(V, ell(640, GROUND - 12, 70, 22, 30), "#9a8a74", outline="#5e4a36", w=2)
    for k in range(5):
        x = 600 + k * 20
        p.line(V, [(x, GROUND - 26), (x + 4, GROUND - 70 + (12 if k == 2 else 0))], "#7a4a26", 4)
    deer(p, V, 300, t, sc=0.85)
    fox(p, V, 450, t, sc=0.9)
    tortoise(p, V, 980, t, face=-1, sc=1.05)
    drew = t > h1[1] - 0.6
    sad = 1.0 if (drew and t < word_time('h2', 'Wait') + 0.2) else 0.0
    idea = sm(word_time('h2', 'idea') - 0.2, word_time('h2', 'idea') + 0.3, t)
    hare(p, V, 760, t, face=-1, ear_down=16 * sad, extra=dict(tilt=-6 * sad))
    if drew:   # the short stick held up
        p.line(V, [(742, GROUND - 60), (738, GROUND - 92)], "#7a4a26", 5)
    if idea > 0:
        M = V @ T(760, GROUND - 170 - 10 * math.sin(t * 4)) @ S(idea) @ R(t * 40)
        p.poly(M, khatam(0, 0, 22), "#f2c14e", outline="#b9802a", w=2)
    if h1[1] - 0.6 < t < h1[1] + 0.6:
        put_text(fr, A['bang'], 760, GROUND - 175, env(t, h1[1] - 0.6, h1[1] + 0.6, 0.1, 0.2))
    return fr

def angry_frame(t):
    a, b = SB("angry"); lt = t - a
    fr = A['cave'].copy(); p = Pen(fr); V = S(SS)
    for k in range(16):    # noon sun
        ang = math.radians(k * 22.5)
        p.poly(V, [(640 + 34 * math.cos(ang - 0.12), 70 + 34 * math.sin(ang - 0.12)), (640 + 54 * math.cos(ang), 70 + 54 * math.sin(ang)),
                   (640 + 34 * math.cos(ang + 0.12), 70 + 34 * math.sin(ang + 0.12))], "#e9a93a", outline=None)
    p.poly(V, ell(640, 70, 34, 34), "#f2c14e", outline="#b9802a", w=2)
    l3 = cue('l3')
    pacing = t < l3[1]
    if pacing:
        ph = lt * 0.55
        lx = 960 + 110 * math.sin(ph)
        face = -1 if math.cos(ph) > 0 else 1
        lion(p, V, lx, t, face=face, po=lion_po(t, angry=1.0), walk=lt * 3, amp=22)
    else:
        lion(p, V, 900, t, face=-1, po=lion_po(t, angry=1.0, look=6))
    hx = -80 + 560 * sm(0.4, 3.0, lt)
    hop = hop_cycle(t, 0.7, 14)[0] if lt < 3.0 else 0
    h4 = cue('h4')
    if t > h4[1] + h4[2] - 1.2: hop = hop_cycle(t, 0.35, 22)[0]
    hare(p, V, hx, t, face=1, hop=hop)
    return fr

def walk_frame(t):
    a, b = SB("walk"); u = (t - a) / (b - a)
    cam = 2060 * sm(0.0, 1.0, u)
    fr = crop_world(cam); p = Pen(fr); V = S(SS) @ T(-cam, 0)
    draw_tortoise(p, V @ T(1350, GROUND - 28) @ S(-0.7, 0.7), dict(t=t, blink=blink(t)))   # watching from the back
    draw_deer(p, V @ T(1900, GROUND - 30) @ S(-0.62, 0.62), dict(t=t, blink=blink(t, 1)))
    lx = 420 + (2440 - 420) * sm(0.0, 1.0, u)
    hx = 780 + (2950 - 780) * sm(0.0, 0.97, u)
    moving = u < 0.98
    lion(p, V, lx, t, po=lion_po(t, angry=1.0), walk=lx / 30, amp=24 if moving else 0)
    h = hop_cycle(t, 0.42, 30)[0] if moving else 0
    hare(p, V, hx, t, face=1 if u < 0.97 else -1, hop=h)
    return fr

LEAP_LEN = 1.15
def leap_t():
    return word_time('n6', 'leap') + 0.25

def well_frame(t, party=False):
    cam = 2060
    fr = crop_world(cam); V = S(SS) @ T(-cam, 0)
    WX, RY = ME.WELLX, ME.RIMY
    lt0 = leap_t()
    # reflection
    if not party:
        a, b = SB("well")
        al = sm(a + 0.3, a + 1.0, t) * (1 - sm(lt0 + 0.4, lt0 + 0.8, t))
        if al > 0:
            bw, bh = 2 * ME.WAT_RX * SS, 2 * ME.WAT_RY * SS
            tmp = Image.new('RGBA', (bw, bh), (0, 0, 0, 0)); q = Pen(tmp)
            po = lion_po(t, angry=1.0)
            M = S(SS) @ T(ME.WAT_RX + 2.5 * math.sin(t * 3.1), ME.WAT_RY + 3) @ S(0.42, -0.42) @ T(-16, 12)
            lion_head(q, M, po)
            arr = np.array(tmp).astype(np.float32)
            arr[..., :3] = arr[..., :3] * 0.72 + np.array([60, 110, 150]) * 0.28
            m = Image.new('L', (bw, bh), 0); ImageDraw.Draw(m).ellipse([6, 6, bw - 6, bh - 6], fill=255)
            arr[..., 3] *= (np.array(m) / 255.0) * 0.85 * al
            fr.alpha_composite(Image.fromarray(arr.astype(np.uint8), 'RGBA'),
                               dest=(int((WX - ME.WAT_RX - cam) * SS), int((RY - ME.WAT_RY) * SS)))
    # lion
    if not party:
        u = clamp((t - lt0) / LEAP_LEN)
        po = lion_po(t, angry=1.0)
        if t < lt0:
            a, b = SB("well")
            l = sm(a, a + 0.8, t)
            M = V @ T(2440, GROUND) @ T(62, 0) @ R(18 * l) @ T(-62, 0) @ S(1.05)
            po['head'] = po.get('head', 0) + 16 * l
            draw_lion(Pen(fr), M, po)
        elif u < 1:
            x = 2440 + 290 * u
            y = GROUND * (1 - u) + (RY + 260) * u - 800 * u * (1 - u)
            rot = -18 + 80 * u
            po['stretch'] = 32 * math.sin(math.pi * min(1, u * 1.3)); po['mouth'] = 0.5
            M = V @ T(x, y) @ T(0, -80) @ R(rot) @ T(0, 80) @ S(1.05)
            if u > 0.3:
                layer = Image.new('RGBA', fr.size, (0, 0, 0, 0)); draw_lion(Pen(layer), M, po)
                layer.paste((0, 0, 0, 0), box=(int((WX - ME.WAT_RX - cam) * SS), int(RY * SS),
                                               int((WX + ME.WAT_RX - cam) * SS), H * SS))
                fr.alpha_composite(layer)
            else:
                draw_lion(Pen(fr), M, po)
    wx0, wy0 = ME.ASSETS['well_xy']
    wf = ME.ASSETS['well']; fr.paste(wf, (int((wx0 - cam) * SS), int(wy0 * SS)), wf)
    p = Pen(fr)
    if not party:
        ts = lt0 + LEAP_LEN * 0.9
        if ts < t < ts + 1.9:
            dt = t - ts
            water, white = np.array([42, 91, 133]), np.array([225, 242, 250])
            for k in range(3):
                d = dt - k * 0.25
                if 0 < d < 1.3:
                    r = 20 + 112 * d / 1.3; al = 1 - d / 1.3
                    c = tuple(int(v) for v in water * (1 - al) + white * al)
                    pts = ap(V, ell(WX, RY, r, r * ME.WAT_RY / ME.WAT_RX, 40))
                    p.d.line(pts + [pts[0]], fill=c, width=2 * SS)
            for ox, vx, vy, sz in ME.ASSETS['drops']:
                x = WX + ox + vx * dt; y = RY + vy * dt + 0.5 * 1100 * dt * dt
                if y > RY + 10 and dt > 0.1: continue
                p.poly(V, ell(x, y, sz, sz * 1.3, 14), (190, 228, 244), outline=(44, 109, 148), w=1.5)
        h5 = cue('h5')
        excited = h5[1] < t < h5[1] + h5[2]
        cower = lt0 - 0.2 < t < lt0 + 2.6
        hare(p, V, 2950, t, face=-1, hop=hop_cycle(t, 0.4, 16)[0] if excited else 0, ear_down=12 if cower else 0)
    else:
        a, b = SB("party"); lt = t - a
        come = sm(0, 1.6, lt)
        deer(p, V, 2060 + 120 - 300 * (1 - come), t, face=1, sc=0.88, walk=t * 6, amp=20 * (lt < 1.6))
        fox(p, V, 2060 + 330 - 300 * (1 - come), t, face=1, walk=t * 8, amp=20 * (lt < 1.6))
        tortoise(p, V, 2060 + 1090 + 300 * (1 - come), t, face=-1)
        h = hop_cycle(t, 0.45, 40)[0]
        hare(p, V, 2950 - 120, t, face=1 if (lt % 1.8) < 0.9 else -1, hop=h)
        rng = np.random.default_rng(int(lt * 2) + 5)
        for k in range(40):     # petals
            px = 2060 + (k * 97 + lt * 30 * (1 + k % 3)) % 1280
            py = (k * 53 + lt * 120 * (1 + k % 2)) % 560
            p.poly(V, ell(px, py, 4, 3, 8), ["#f2b8c6", "#fff5f0", "#e98aa5", "#f3c94a"][k % 4], outline=None)
    return fr

def end_frame(t):
    a, b = SB("end"); lt = t - a
    fr = A['card'].copy()
    ME.card_rosette(fr, t, 200)
    put_text(fr, A['e1'], W / 2, 330, sm(0.2, 0.8, lt))
    put_text(fr, A['e2'], W / 2, 395, sm(0.5, 1.1, lt))
    put_text(fr, A['e3'], W / 2, 480, sm(0.9, 1.5, lt))
    return fr

def render(i):
    t = i / FPS
    name, lt, sd = tl.scene_at(t)
    if name is None: name, lt, sd = "end", 4.0, 4.6
    if name.startswith("tree"): fr = tree_frame(name, t)
    elif name == "title": fr = title_frame(t)
    elif name == "forest": fr = forest_frame(t)
    elif name == "lion": fr = lion_frame(t)
    elif name == "council": fr = council_frame(t)
    elif name in ("cave",): fr = cave_frame(name, t)
    elif name == "lots": fr = lots_frame(t)
    elif name == "angry": fr = angry_frame(t)
    elif name == "walk": fr = walk_frame(t)
    elif name == "well": fr = well_frame(t)
    elif name == "party": fr = well_frame(t, party=True)
    else: fr = end_frame(t)
    fr.alpha_composite(A['border'])
    img = fr.convert('RGB').resize((W, H), Image.LANCZOS)
    f = min(clamp(lt / 0.35), clamp((sd - lt) / 0.35))
    if name == "tree_open": f = min(clamp(lt / 0.7), clamp((sd - lt) / 0.35))
    if name == "end": f = min(clamp(lt / 0.35), clamp((sd - lt) / 0.8))
    if name == "walk": f = clamp(lt / 0.35)                      # walk flows straight into the well
    if name == "well": f = min(1.0, clamp((sd - lt) / 0.35))
    if f < 0.999: img = Image.blend(Image.new('RGB', (W, H)), img, f)
    return img.tobytes()

# ------------------------------------------------------------------ audio
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
    a, b = sc['tree_open']; seq(a + 0.2, 0.32, playful, 0.7, end=b - 0.2); tombak(a + 0.2, b - 0.3, 0.64, 0.3)
    a, b = sc['title']; seq(a + 0.2, 0.3, ["A3", "D4", "Ek4", "F4", "Ek4", "D4", "C4", "D4", "-", "A4"], 0.9)
    a, b = sc['forest']; seq(a + 0.2, 0.26, happy, 0.6, 1.2, end=b - 0.2)
    a, b = sc['lion']
    seq(a + 1.2, 0.6, ["D3", "Ek3", "D3", "-", "F3", "Ek3", "D3", "-"], 1.0, 2.2, end=b - 0.3)
    add(mus, a + 1.0, dum(0.8), 1.0); add(mus, cue('l1')[1], dum(0.8), 0.8)
    add(sfx, a + 1.0, roar(1.6), 1.0)
    n3 = cue('n3'); tombak(n3[1] + 0.5, b - 0.3, 0.3, 0.35)
    a, b = sc['council']; riz(a + 0.2, b - 0.2, 'A3', 0.12); seq(a + 0.5, 0.9, ["D4", "-", "F4", "Ek4", "D4", "-", "C4", "D4"], 0.55, 2.4, end=b - 0.5)
    a, b = sc['cave']; seq(a + 0.2, 0.7, ["D3", "-", "Ek3", "-", "D3", "C3", "D3", "-"], 0.8, 2.4, end=b - 0.3)
    add(sfx, cue('l2')[1] + cue('l2')[2] - 0.2, roar(0.9, seed=6), 0.5)
    a, b = sc['lots']
    seq(a + 0.2, 0.55, ["A4", "G4", "F4", "Ek4", "D4", "-", "-"], 0.6, 2.0)
    it = word_time('h2', 'idea') - 0.2
    seq(it, 0.08, ["D4", "F4", "A4", "D5"], 0.6, 1.0)
    seq(it + 0.8, 0.28, ["A4", "Bb4", "C5", "A4", "G4", "A4"], 0.5, 1.2, end=b - 0.2)
    a, b = sc['angry']; tombak(a + 0.2, b - 0.2, 0.6, 0.4)
    seq(a + 0.2, 0.6, ["D3", "Ek3", "F3", "Ek3"], 0.7, 2.0, end=b - 0.2)
    add(sfx, cue('l3')[1] - 0.6, roar(0.8, seed=7), 0.5)
    a, b = sc['walk']
    seq(a + 0.1, 0.3, ["D4", "-", "F4", "Ek4", "D4", "-", "A3", "C4", "D4", "-", "F4", "G4", "A4", "-", "G4", "F4", "Ek4", "-", "D4", "C4"], 0.85, end=b)
    tombak(a + 0.1, b, 0.6, 0.55)
    a, b = sc['well']
    lt0 = leap_t()
    riz(a + 0.2, lt0 - 0.1, 'A3', 0.35, swell=True)
    l5 = cue('l5')
    add(sfx, l5[1] + l5[2] - 0.1, roar(1.1, seed=8), 0.6)
    seq(lt0, 0.07, ["D4", "Ek4", "F4", "G4", "A4", "Bb4", "C5", "D5"], 0.7, 0.8)
    seq(lt0 + 0.55, 0.06, ["D5", "C5", "Bb4", "A4", "G4", "F4", "Ek4", "D4"], 0.7, 0.8)
    add(mus, lt0 + LEAP_LEN * 0.9, dum(0.8), 1.0)
    add(sfx, lt0 + LEAP_LEN * 0.9, splash(), 1.0)
    a, b = sc['party']; seq(a + 0.2, 0.25, happy + ["D5", "-", "A4", "-"], 0.75, 1.2, end=b - 0.3); tombak(a + 0.2, b - 0.4, 0.5, 0.45)
    a, b = sc['tree_close']; seq(a + 0.2, 0.36, ["D4", "-", "F4", "G4", "A4", "-", "Bb4", "A4", "G4", "-", "F4", "Ek4", "D4", "-", "-", "-"], 0.6, end=b - 0.2)
    a, b = sc['end']
    seq(a + 0.2, 0.3, ["D4", "F4", "A4", "D5", "-", "C5", "A4", "Bb4", "A4", "-", "-", "D4"], 0.85)
    for nn in ("D3", "A3", "D4"): add(mus, a + 3.3, santur(NOTES[nn], 2.0), 0.8)
    mus += (np.sin(2 * np.pi * NOTES['D2'] * t) + 0.5 * np.sin(2 * np.pi * NOTES['A2'] * t)) * 0.05
    vo = tl.mix_voice(N)
    # echo from the well: the end of the lion's shout comes back
    import soundfile as sf
    la, lsr = tl.audio['l5']
    tail = la[-int(1.1 * lsr):]
    tail = np.interp(np.arange(int(len(tail) * SR / lsr)) * lsr / SR, np.arange(len(tail)), tail)
    tail = np.convolve(tail, np.ones(6) / 6, 'same')
    for dly, g in ((0.45, 0.45), (0.9, 0.22)):
        add(vo, l5[1] + l5[2] - 1.1 + dly + 0.4, tail, g)
    rev = mus.copy()
    for dly, g in ((0.071, 0.3), (0.113, 0.22), (0.197, 0.15), (0.311, 0.1)):
        k = int(dly * SR); rev[k:] += mus[:-k] * g
    ve = np.convolve(np.abs(vo), np.ones(int(0.25 * SR)) / int(0.25 * SR), 'same')
    duck = 1 - 0.62 * np.clip(ve / (ve.max() * 0.15 + 1e-9), 0, 1)
    duck = np.convolve(duck, np.ones(int(0.2 * SR)) / int(0.2 * SR), 'same')
    rev = rev / (np.abs(rev).max() + 1e-9) * 0.5 * duck
    sfx = sfx / (np.abs(sfx).max() + 1e-9) * 0.55
    vo = vo / (np.abs(vo).max() + 1e-9) * 0.9
    k = int(0.013 * SR)
    L = rev + sfx + vo; Rr = np.r_[np.zeros(k), rev[:-k]] + sfx + vo
    st = np.stack([L, Rr], 1) * (np.minimum(1, t / 0.3) * np.clip((DUR - t) / 0.8, 0, 1))[:, None]
    pk = np.abs(st).max()
    if pk > 0.95: st *= 0.95 / pk
    with wave.open(path, 'wb') as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((st * 32767).astype(np.int16).tobytes())

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "info":
        print("DUR", round(DUR, 2)); [print(n, round(a, 1), round(b, 1)) for n, a, b in tl.scenes]; sys.exit()
    init()
    if len(sys.argv) > 1 and sys.argv[1] == "stills":
        for ts in [float(x) for x in sys.argv[2:]]:
            Image.frombytes('RGB', (W, H), render(int(ts * FPS))).save(os.path.join(EP, f"still_{ts:05.1f}.png"))
        sys.exit()
    wav = os.path.join(EP, "audio.wav"); build_audio(wav)
    tl.srt(os.path.join(EP, "Kalila_Dimna_Ep1.en.srt"),
           {"K": "KALILA", "D": "DIMNA", "L": "LION", "H": "HARE", "E": "DEER", "F": "FOX", "T": "OLD TORTOISE"})
    out = os.path.join(EP, "Kalila_Dimna_Ep1_The_Lion_and_the_Hare.mp4")
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
