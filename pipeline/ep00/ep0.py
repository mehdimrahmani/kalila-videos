#!/usr/bin/env python3
"""Kalila & Dimna — Episode 0: "What is Kalila & Dimna?" (channel trailer)."""
import os, sys, math, wave, subprocess
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import multiprocessing as mp
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
from kd_lib import *
import make_episode as ME
HERE = os.path.dirname(os.path.abspath(__file__))

# ------------------------------------------------------------------ timeline
tl = Timeline(os.path.join(HERE, "vo"))
tl.scene("tree1", ["d1", "k1", "d2", "k2", 0.3, "k3", "d3"], lead=3.0, tail=0.9)
tl.scene("map",   ["n1", 0.4, "n2", 0.4, "n3"], lead=2.2, tail=1.4)
tl.scene("tree2", ["d4", "k4"], lead=0.7, tail=0.9)
tl.scene("tiles", ["k5", 0.3, "d5", 0.3, "k6"], lead=0.8, tail=1.2)
tl.scene("tree3", ["k7", "d6", 0.2, "k8"], lead=0.7, tail=1.2)
tl.scene("end",   [], lead=4.6, tail=0.0)
DUR = tl.t
NF = int(DUR * FPS)
ENV = tl.envelopes(NF)
def spk(who, t): return ENV.get(who, np.zeros(NF + 1))[min(NF, int(t * FPS))]

def word_time(key, word, frac=0.0):
    k, st, d, _, txt = tl.cue(key)
    i = txt.lower().find(word.lower())
    return st + d * (max(i, 0) / len(txt)) * 0.97 + frac

def scene_bounds(name, nth=0):
    hits = [(a, b) for n, a, b in tl.scenes if n == name]
    return hits[nth]

# ------------------------------------------------------------------ assets
A = {}
def init():
    ME.init_assets()
    A['border'] = ME.ASSETS['border']; A['card'] = ME.ASSETS['card']
    A['tree'] = build_tree_set().convert('RGBA')
    gold, cream, ink = (226, 182, 74, 255), (250, 240, 214, 255), (70, 44, 20, 255)
    A['map_title'] = text_img("The Journey of the Stories", FI, 30, ink)
    labels = {"INDIA": 30, "PERSIA": 30, "Arabic": 26, "Hebrew": 26, "Latin": 26, "Spanish": 26,
              "...and many more!": 24}
    A['lab'] = {k: text_img(k, FB, v, ink) for k, v in labels.items()}
    A['e1'] = text_img("KALILA & DIMNA", FB, 64, gold, 2, (90, 60, 12, 255))
    A['e2'] = text_img("Persian Fables for Kids", FI, 40, cream)
    A['e3'] = text_img("A new story every Saturday", FR, 28, gold)
    A['pill'] = {s: text_img(s, FB, 28, (40, 30, 10, 255)) for s in ["Be kind", "Be a good friend", "Think before you act"]}
    A['tile_lab'] = {s: text_img(s, FB, 24, cream) for s in ["hares", "monkeys", "mice", "lions"]}

# ------------------------------------------------------------------ TREE scenes (hosts)
KX, DX = 420, 850
HS = 1.32   # host scale on the tree set
def tree_frame(name, t):
    fr = A['tree'].copy(); p = Pen(fr); V = S(SS)
    kpo = jackal_pose('kalila', t, spk('K', t), look=0.6)
    dpo = jackal_pose('dimna', t, spk('D', t), look=0.6)
    kx, dx = KX, DX; bush_shake = 0.0; d_hidden = False
    if name == "tree1":
        a, b = scene_bounds("tree1")
        lt = t - a
        # Dimna: rustle in the bush, then pops out
        if lt < 2.0:
            d_hidden = True; bush_shake = env(lt, 1.0, 2.0, 0.2, 0.2)
        else:
            u = clamp((lt - 2.0) / 0.55)
            dx = 1125 + (DX - 1125) * u
            dpo['hop'] = 70 * math.sin(math.pi * u) if u < 1 else 0
        # Kalila walks in during Dimna's first line
        ws = tl.cue('d1')[1] + 0.6
        u = clamp((t - ws) / 2.4)
        kx = -160 + (KX + 160) * sm(0, 1, u)
        if 0 < u < 1:
            kpo['walk'] = kx / 22; kpo['amp'] = 20
        # Dimna rolls eyes on "...the wise one"
        k2 = tl.cue('k2')
        if k2[1] < t < k2[1] + 1.8:
            dpo['look'] = -1.5; dpo['head'] -= 8
    if name == "tree2":
        d4 = tl.cue('d4')
        if d4[1] < t < d4[1] + 1.2:                        # "We're famous!" hop
            dpo['hop'] = 40 * abs(math.sin(math.pi * (t - d4[1]) / 0.6))
        k4 = tl.cue('k4')
        if k4[1] < t < k4[1] + k4[2]:
            kpo['head'] += 6 * math.sin((t - k4[1]) * 7)  # head shake
    if name == "tree3":
        d6 = tl.cue('d6')
        if d6[1] + d6[2] - 1.2 < t < d6[1] + d6[2] + 0.4:  # "Guess who wins!"
            dpo['hop'] = 30 * abs(math.sin(math.pi * (t - d6[1]) / 0.5))
    if not d_hidden or True:
        if not d_hidden:
            draw_jackal(p, V @ T(dx, 640) @ S(-HS, HS), 'dimna', dpo)
    bush(p, V, 1125, 650, 1.35, bush_shake)
    if kx > -150:
        draw_jackal(p, V @ T(kx, 640) @ S(HS), 'kalila', kpo)
    return fr

# ------------------------------------------------------------------ MAP scene (book + journey)
def monkey_head(p, M):
    for ex in (-34, 34):
        p.poly(M, ell(ex, 0, 14, 14, 20), "#8a5a33"); p.poly(M, ell(ex, 0, 7, 7, 14), "#e8c39a", outline=None)
    p.poly(M, ell(0, 0, 32, 30, 36), "#8a5a33")
    p.poly(M, ell(0, 8, 24, 20, 30), "#e8c39a", outline=None)
    p.poly(M, ell(-9, -6, 9, 9, 16), "#e8c39a", outline=None); p.poly(M, ell(9, -6, 9, 9, 16), "#e8c39a", outline=None)
    for ex in (-9, 9):
        p.poly(M, ell(ex, -5, 4, 4.5, 12), (40, 26, 12), outline=None)
        p.poly(M, ell(ex + 1.2, -6.5, 1.3, 1.3, 8), "white", outline=None)
    p.line(M, [(-10, 14), (0, 19), (10, 14)], (40, 26, 12), 2)

def mouse_head(p, M):
    for ex in (-26, 26):
        p.poly(M, ell(ex, -22, 18, 18, 24), "#9aa0a6"); p.poly(M, ell(ex, -22, 10, 10, 18), "#e7a6a0", outline=None)
    p.poly(M, [(-26, -8), (26, -8), (0, 34)], "#9aa0a6")
    p.poly(M, ell(0, -6, 27, 22, 32), "#9aa0a6")
    p.poly(M, ell(0, 32, 5, 4, 12), "#e7a6a0", outline=None)
    for ex in (-10, 10):
        p.poly(M, ell(ex, -4, 4.5, 5, 12), (30, 30, 34), outline=None)
        p.poly(M, ell(ex + 1.2, -5.5, 1.4, 1.4, 8), "white", outline=None)
    for s_ in (-1, 1):
        for dy in (24, 30):
            p.line(M, [(s_ * 6, dy), (s_ * 34, dy - 6 + (dy - 24))], (60, 60, 60), 1)

def crown(p, M):
    p.poly(M, [(-20, 10), (20, 10), (24, -12), (10, 0), (0, -18), (-10, 0), (-24, -12)], "#e2b64a", outline="#8a6418", w=2)
    for x in (-24, 0, 24):
        p.poly(M, ell(x, -14 if x else -20, 3.5, 3.5, 10), "#c8423a", outline=None)

PLACES = {"INDIA": (960, 450), "PERSIA": (770, 290), "Arabic": (520, 430), "Hebrew": (430, 300),
          "Latin": (330, 205), "Spanish": (250, 360), "...and many more!": (360, 540)}
def map_frame(t):
    a, b = scene_bounds("map"); lt = t - a
    fr = A['card'].copy(); p = Pen(fr); V = S(SS)
    # book spread
    L, Rr, Tp, Bt, SP = 150, 1130, 105, 640, 640
    p.poly(V, [(L - 16, Tp - 14), (Rr + 16, Tp - 14), (Rr + 16, Bt + 16), (L - 16, Bt + 16)], "#1d3f73", outline="#d4a63c", w=3)
    p.poly(V, [(L, Tp), (SP, Tp + 8), (SP, Bt + 6), (L, Bt)], "#f4e6c4", outline="#8a6418", w=2)
    p.poly(V, [(SP, Tp + 8), (Rr, Tp), (Rr, Bt), (SP, Bt + 6)], "#f6e9c9", outline="#8a6418", w=2)
    for x0, x1 in ((L + 14, SP - 10), (SP + 10, Rr - 14)):
        p.d.rectangle([x0 * SS, (Tp + 20) * SS, x1 * SS, (Bt - 14) * SS], outline=(200, 160, 80), width=2 * SS)
    p.line(V, [(SP, Tp + 8), (SP, Bt + 6)], (120, 80, 30), 3)
    u = sm(0.5, 1.7, lt)                      # cover opens
    reveal = sm(1.5, 2.2, lt)
    if reveal > 0.01:
        lay = Image.new('RGBA', fr.size, (0, 0, 0, 0)); q = Pen(lay)
        put_text(lay, A['map_title'], 640, Tp + 46, 1.0)
        # land blobs
        for (x, y, rx, ry) in [(960, 450, 120, 80), (770, 300, 110, 70), (470, 380, 190, 150), (300, 250, 110, 80)]:
            q.poly(V, ell(x, y, rx, ry, 40), (214, 222, 170, 255), outline=(160, 168, 120, 255), w=1.5)
        c1, c2, c3 = tl.cue('n1'), tl.cue('n2'), tl.cue('n3')
        def place(name, t0, pulse=0.0):
            al = sm(t0, t0 + 0.5, t)
            if al <= 0: return
            x, y = PLACES[name]
            r = 9 + 3 * pulse
            q.poly(V, ell(x, y, r, r, 20), (200, 66, 58, int(255 * al)), outline=(90, 30, 20, int(255 * al)), w=2)
            put_text(lay, A['lab'][name], x, y - 30, al)
        # India + animals + crown
        place("INDIA", c1[1] + 1.8, pulse=env(t, c1[1] + 1.8, c2[1], 0.3, 0.3) * abs(math.sin(t * 4)))
        sc = sm(word_time('n1', 'animal'), word_time('n1', 'animal') + 0.5, t)
        if sc > 0:
            draw_lion(q, V @ T(1030, 600) @ S(0.32 * sc), dict(t=t, mouth=0, angry=0.3))
            draw_hare(q, V @ T(905, 600) @ S(0.75 * sc), dict(t=t))
        sc = sm(word_time('n1', 'princes'), word_time('n1', 'princes') + 0.4, t)
        if sc > 0: crown(q, V @ T(1060, 380) @ S(sc))
        # path India -> Persia
        place("PERSIA", c2[1] + 0.8)
        pu = sm(word_time('n2', 'traveled'), c2[1] + c2[2] - 0.3, t)
        if pu > 0:
            P0, P1 = np.array(PLACES["INDIA"]), np.array(PLACES["PERSIA"])
            mid = (P0 + P1) / 2 + np.array([40, -90])
            pts = [tuple((1 - s_) ** 2 * P0 + 2 * (1 - s_) * s_ * mid + s_ ** 2 * P1) for s_ in np.linspace(0, pu, 40)]
            for i in range(0, len(pts) - 1, 2):
                q.line(V, [pts[i], pts[i + 1]], (160, 60, 40, 255), 3)
            if pu < 1:   # tiny scroll travelling
                x, y = pts[-1]
                q.poly(V, [(x - 12, y - 8), (x + 12, y - 8), (x + 12, y + 8), (x - 12, y + 8)], "#f9f0d8", outline="#8a6418", w=2)
        # Persia -> world
        for name, w in [("Arabic", "Arabic"), ("Hebrew", "Hebrew"), ("Latin", "Latin"), ("Spanish", "Spanish"),
                        ("...and many more!", "many more")]:
            t0 = word_time('n3', w) - 0.15
            au = sm(t0, t0 + 0.45, t)
            if au > 0:
                P0, P1 = np.array(PLACES["PERSIA"]), np.array(PLACES[name])
                e = P0 + (P1 - P0) * (0.12 + 0.76 * au)
                q.line(V, [tuple(P0 + (P1 - P0) * 0.12), tuple(e)], (40, 90, 140, 255), 3)
                place(name, t0 + 0.2)
        if t > word_time('n3', 'Persian') - 0.1 and t < word_time('n3', 'Persian') + 0.7:
            place("PERSIA", 0, pulse=1.5)
        al = lay.getchannel('A').point(lambda v: int(v * reveal)); lay.putalpha(al)
        fr.alpha_composite(lay)
    # cover on top while opening
    if u < 1:
        cx = SP + (Rr - SP) * math.cos(math.pi * u)
        p.poly(V, [(SP, Tp - 6), (cx, Tp - 10), (cx, Bt + 10), (SP, Bt + 6)], "#1d3f73", outline="#d4a63c", w=3)
        if u < 0.45:
            mx = (SP + cx) / 2; sx = max(0.05, (cx - SP) / (Rr - SP))
            p.poly(V @ T(mx, 370) @ S(sx, 1), khatam(0, 0, 90), "#d4a63c", outline="#8a6418", w=2)
            p.poly(V @ T(mx, 370) @ S(sx, 1), khatam(0, 0, 60, 22.5), "#1d3f73", outline="#d4a63c", w=2)
    return fr

# ------------------------------------------------------------------ TILES scene
TILES = [("hares", 'hares'), ("monkeys", 'monkeys'), ("mice", 'mice'), ("lions", 'lions')]
def tiles_frame(t):
    fr = A['card'].copy(); p = Pen(fr); V = S(SS)
    d5, k6 = tl.cue('d5'), tl.cue('k6')
    lift = 40 * sm(d5[1], d5[1] + 0.8, t)
    for i, (lab, word) in enumerate(TILES):
        t0 = word_time('k5', word) - 0.1
        u = clamp((t - t0) / 0.35)
        if u <= 0: continue
        s_ = 1 + 0.18 * math.sin(math.pi * u) if u < 1 else 1
        s_ *= sm(0, 0.6, u) * 0.4 + 0.6
        cx, cy = 235 + i * 270, 300 - lift
        M = V @ T(cx, cy) @ S(s_) @ R(3 * math.sin(t * 1.5 + i))
        p.poly(M, [(-112, -112), (112, -112), (112, 112), (-112, 112)], "#d4a63c", outline="#8a6418", w=2)
        p.poly(M, [(-100, -100), (100, -100), (100, 100), (-100, 100)], "#f4e6c4", outline="#8a6418", w=2)
        bob = 4 * math.sin(t * 3 + i)
        if lab == "hares": draw_hare(p, M @ T(-5, 70 + bob) @ S(1.6), dict(t=t, ear=6 * math.sin(t * 4)))
        if lab == "monkeys": monkey_head(p, M @ T(0, 5 + bob) @ S(1.7))
        if lab == "mice": mouse_head(p, M @ T(0, 0 + bob) @ S(1.6))
        if lab == "lions": lion_head(p, M @ T(-22, 18 + bob) @ S(1.05), dict(t=t, mouth=0, angry=0.3))
        put_text(fr, A['tile_lab'][lab], cx, cy + 140, sm(0, 1, u))
    # wisdom star
    st = sm(word_time('d5', 'secret'), word_time('d5', 'secret') + 0.7, t)
    if st > 0:
        fade = 1 - sm(k6[1] + k6[2] + 0.2, k6[1] + k6[2] + 0.9, t)
        M = V @ T(640, 560 - lift * 0.5) @ S(st * (1 + 0.05 * math.sin(t * 5))) @ R(t * 15)
        for k in range(16):
            a = math.radians(k * 22.5)
            p.poly(M, [(48 * math.cos(a - 0.1), 48 * math.sin(a - 0.1)), (78 * math.cos(a), 78 * math.sin(a)),
                       (48 * math.cos(a + 0.1), 48 * math.sin(a + 0.1))], "#f2c14e", outline=None)
        p.poly(M, khatam(0, 0, 52), "#f2c14e", outline="#b9802a", w=2)
        p.poly(M, khatam(0, 0, 32, 22.5), "#fff4d0", outline="#b9802a", w=2)
    # three lessons
    if t > k6[1] - 0.2:
        for (txt, w), x in zip([("Be kind", "kind"), ("Be a good friend", "friend"), ("Think before you act", "think")],
                               (215, 575, 1000)):
            u = sm(word_time('k6', w) - 0.15, word_time('k6', w) + 0.3, t)
            if u <= 0: continue
            im = A['pill'][txt]; wpx = im.width / SS + 40
            y = 648
            M = V @ T(x, y) @ S(0.8 + 0.2 * u)
            p.poly(M, [(-wpx / 2, -26), (wpx / 2, -26), (wpx / 2, 26), (-wpx / 2, 26)], "#f4e6c4", outline="#d4a63c", w=3)
            put_text(fr, im, x, y, u)
    return fr

def end_frame(t):
    a, b = scene_bounds("end"); lt = t - a
    fr = A['card'].copy()
    ME.card_rosette(fr, t, 200)
    put_text(fr, A['e1'], W / 2, 350, sm(0.2, 0.9, lt))
    put_text(fr, A['e2'], W / 2, 425, sm(0.6, 1.3, lt))
    put_text(fr, A['e3'], W / 2, 500, sm(1.0, 1.7, lt))
    return fr

# ------------------------------------------------------------------ frame
def render(i):
    t = i / FPS
    name, lt, sd = tl.scene_at(t)
    if name is None: name, lt, sd = "end", 0, 1
    if name.startswith("tree"): fr = tree_frame(name, t)
    elif name == "map": fr = map_frame(t)
    elif name == "tiles": fr = tiles_frame(t)
    else: fr = end_frame(t)
    fr.alpha_composite(A['border'])
    img = fr.convert('RGB').resize((W, H), Image.LANCZOS)
    f = min(clamp(lt / 0.35), clamp((sd - lt) / 0.35))
    if name == "tree1": f = min(clamp(lt / 0.8), clamp((sd - lt) / 0.35))
    if name == "end": f = min(clamp(lt / 0.35), clamp((sd - lt) / 0.8))
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
            n = notes[k % len(notes)]
            if end is None and k >= len(notes): break
            if end is not None and tt >= end: break
            if n != '-': add(mus, tt, santur(NOTES[n], dur), vel)
            tt += step; k += 1
    def riz(st, end, note, vel=0.4, rate=0.075):
        tt = st; k = 0
        while tt < end:
            add(mus, tt, santur(NOTES[note], 0.5), vel * (0.8 + 0.2 * (k % 2))); tt += rate; k += 1
    sc = {n: (a, b) for n, a, b in tl.scenes}
    sc2 = [(n, a, b) for n, a, b in tl.scenes]
    playful = ["D4", "F4", "A4", "G4", "F4", "Ek4", "D4", "-", "A3", "D4", "F4", "G4", "A4", "-", "G4", "F4"]
    warm = ["D4", "-", "F4", "G4", "A4", "-", "Bb4", "A4", "G4", "-", "F4", "Ek4", "D4", "-", "-", "-"]
    for n, a, b in sc2:
        if n.startswith("tree"):
            seq(a + 0.2, 0.32, playful if n != "tree3" else warm, 0.75, end=b - 0.3)
            k = 0; tt = a + 0.2
            while tt < b - 0.4:
                add(mus, tt, dum(), 0.35); add(mus, tt + 0.32, tak(seed=k), 0.6); add(mus, tt + 0.48, tak(seed=k + 9), 0.4)
                tt += 0.64; k += 1
        if n == "map":
            riz(a + 0.4, a + 2.2, 'A3', 0.3)
            seq(a + 2.2, 0.6, ["D4", "Ek4", "F4", "-", "Ek4", "D4", "C4", "D4", "-", "-"], 0.8, 2.2, end=b - 0.5)
        if n == "tiles":
            seq(a + 0.3, 0.24, ["D5", "A4", "F4", "A4", "C5", "A4", "Bb4", "A4", "G4", "A4", "F4", "-"], 0.55, 1.2, end=b - 0.3)
        if n == "end":
            seq(a + 0.2, 0.3, ["D4", "F4", "A4", "D5", "-", "C5", "A4", "Bb4", "A4", "-", "-", "D4"], 0.85)
            for nn in ("D3", "A3", "D4"): add(mus, a + 3.2, santur(NOTES[nn], 2.0), 0.8)
    drone = (np.sin(2 * np.pi * NOTES['D2'] * t) + 0.5 * np.sin(2 * np.pi * NOTES['A2'] * t)) * 0.05
    mus += drone
    # sfx
    rng = np.random.default_rng(4)
    a1 = sc['tree1'][0]
    n = int(0.9 * SR); wn = rng.standard_normal(n); tt = np.arange(n) / SR
    rustle = np.convolve(wn, np.ones(30) / 30, 'same') * (0.5 + 0.5 * np.sin(2 * np.pi * 9 * tt)) * np.sin(np.pi * tt / 0.9)
    add(sfx, a1 + 1.05, rustle, 1.0)
    add(sfx, a1 + 2.0, santur(NOTES['D5'], 0.6), 1.2)           # pop!
    am = sc['map'][0]
    n = int(1.2 * SR); tt = np.arange(n) / SR
    whoosh = np.convolve(rng.standard_normal(n), np.ones(60) / 60, 'same') * np.sin(np.pi * tt / 1.2) ** 2
    add(sfx, am + 0.5, whoosh, 1.4)
    for _, w in TILES:
        add(sfx, word_time('k5', w) - 0.1, santur(NOTES['A4'], 0.6), 0.9)
    riz(word_time('d5', 'secret'), word_time('d5', 'secret') + 0.8, 'D5', 0.25)
    vo = tl.mix_voice(N)
    rev = mus.copy()
    for dly, g in ((0.071, 0.3), (0.113, 0.22), (0.197, 0.15), (0.311, 0.1)):
        k = int(dly * SR); rev[k:] += mus[:-k] * g
    ve = np.convolve(np.abs(vo), np.ones(int(0.25 * SR)) / int(0.25 * SR), 'same')
    duck = 1 - 0.62 * np.clip(ve / (ve.max() * 0.15 + 1e-9), 0, 1)
    duck = np.convolve(duck, np.ones(int(0.2 * SR)) / int(0.2 * SR), 'same')
    rev = rev / (np.abs(rev).max() + 1e-9) * 0.5 * duck
    sfx = sfx / (np.abs(sfx).max() + 1e-9) * 0.45
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
    init()
    if len(sys.argv) > 1 and sys.argv[1] == "stills":
        for ts in [float(x) for x in sys.argv[2:]]:
            Image.frombytes('RGB', (W, H), render(int(ts * FPS))).save(os.path.join(HERE, f"still_{ts:05.1f}.png"))
        sys.exit()
    if len(sys.argv) > 1 and sys.argv[1] == "info":
        print("DUR", round(DUR, 2)); [print(s) for s in tl.scenes]; sys.exit()
    wav = os.path.join(HERE, "audio.wav"); build_audio(wav)
    tl.srt(os.path.join(HERE, "Kalila_Dimna_Ep0.en.srt"), {"K": "KALILA", "D": "DIMNA"})
    out = os.path.join(HERE, "Kalila_Dimna_Ep0_What_is_Kalila_and_Dimna.mp4")
    ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
                           "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-i", wav,
                           "-c:v", "libx264", "-preset", "medium", "-crf", "19", "-pix_fmt", "yuv420p",
                           "-c:a", "aac", "-b:a", "160k", "-shortest", "-movflags", "+faststart", out],
                          stdin=subprocess.PIPE)
    with mp.get_context("fork").Pool(os.cpu_count()) as pool:
        for k, buf in enumerate(pool.imap(render, range(NF), chunksize=4)):
            ff.stdin.write(buf)
            if k % 240 == 0: print(f"frame {k}/{NF}", flush=True)
    ff.stdin.close(); ff.wait()
    print("done:", out)
