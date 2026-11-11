"""
Kalila & Dimna — shared library for all episodes.
Re-exports the drawing / audio primitives of the pilot (make_episode.py) and adds:
  * the two host puppets (Kalila & Dimna, jackals)
  * reusable sets (hosts' tree)
  * a voice-over timeline helper (lines -> start times, per-frame speech envelopes)
"""
import os, sys, math, json
import numpy as np
from PIL import Image, ImageDraw, ImageFont
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from make_episode import (W, H, SS, FPS, OUT, FB, FR, FI, T, R, S, ap, ell, khatam, clamp, sm, env, Pen,
                          draw_lion, lion_head, draw_hare, cloud, cypress, blossom_tree, flower,
                          text_img, put_text, santur, dum, tak, roar, splash, NOTES, SR)

# ------------------------------------------------------------------ voice timeline
class Timeline:
    """Places voice clips one after another; scenes are groups of lines."""
    def __init__(self, vo_dir, lines_json="lines.json"):
        import soundfile as sf
        self.vo_dir = vo_dir
        meta = json.load(open(os.path.join(vo_dir, lines_json)))
        self.meta = {m['key']: m for m in meta}
        self.audio = {}
        for k in self.meta:
            a, sr = sf.read(os.path.join(vo_dir, k + ".wav"), dtype='float32')
            if a.ndim > 1: a = a.mean(1)
            self.audio[k] = (a, sr)
        self.cues = []      # (key, start, dur, speaker, text)
        self.scenes = []    # (name, start, end)
        self.t = 0.0
    def pause(self, s): self.t += s
    def scene(self, name, keys, lead=0.6, gap=0.35, tail=0.6):
        st = self.t; self.t += lead
        for k in keys:
            if isinstance(k, (int, float)): self.t += k; continue
            d = self.meta[k]['dur']
            self.cues.append((k, self.t, d, self.meta[k]['spk'], self.meta[k]['text']))
            self.t += d + gap
        self.t += tail - gap
        self.scenes.append((name, st, self.t))
        return st, self.t
    def cue(self, key):
        for c in self.cues:
            if c[0] == key: return c
    def scene_at(self, t):
        for name, a, b in self.scenes:
            if a <= t < b: return name, t - a, b - a
        return None, 0, 0
    def envelopes(self, nframes, pitch=None):
        """speaker -> per-frame mouth envelope (0..1)"""
        pitch = pitch or {}
        out = {}
        for k, st, d, spk, _ in self.cues:
            a, sr = self.audio[k]
            hop = sr // FPS
            e = out.setdefault(spk, np.zeros(nframes + 1))
            for i in range(len(a) // hop):
                fi = int(st * FPS) + i
                if fi <= nframes: e[fi] = np.abs(a[i * hop:(i + 1) * hop]).mean()
        for spk, e in out.items():
            e /= (np.percentile(e[e > 0], 95) if (e > 0).any() else 1) + 1e-9
            out[spk] = np.clip(e, 0, 1)
        return out
    def mix_voice(self, N, pitch=None):
        pitch = pitch or {}
        vo = np.zeros(N)
        for k, st, d, spk, _ in self.cues:
            a, sr = self.audio[k]
            f = pitch.get(spk, 1.0) * sr / SR
            n = int(len(a) / f)
            sig = np.interp(np.arange(n) * f, np.arange(len(a)), a)
            i = int(st * SR); j = min(N, i + n)
            if i < N: vo[i:j] += sig[:j - i]
        return vo
    def srt(self, path, names=None):
        names = names or {}
        def ts(x):
            ms = int(round(x * 1000)); return f"{ms//3600000:02d}:{ms//60000%60:02d}:{ms//1000%60:02d},{ms%1000:03d}"
        with open(path, "w", encoding="utf-8") as f:
            for i, (k, st, d, spk, txt) in enumerate(self.cues, 1):
                lab = names.get(spk)
                f.write(f"{i}\n{ts(st)} --> {ts(st + d + 0.2)}\n{(lab + ': ') if lab else ''}{txt}\n\n")

# ------------------------------------------------------------------ JACKAL hosts
JACKALS = {
    "kalila": dict(body="#bfa47c", dark="#8f7651", belly="#f0e2c4", ear="#d9a3a0", scale=1.12,
                   tail_tip="#efe4cc", brow=0.0, lid=0.35),
    "dimna":  dict(body="#d98c4a", dark="#a35f2a", belly="#f7e6cc", ear="#e7a6a0", scale=0.94,
                   tail_tip="#fff7ea", brow=1.0, lid=0.0),
}
JD = (43, 26, 12)

def jackal_head(p, Mh, c, po):
    m = po.get('mouth', 0); t = po['t']
    # back ear
    p.poly(Mh @ T(-4, -16) @ R(-14 + po.get('ear', 0)), [(-9, 0), (9, 0), (2, -40)], c['dark'])
    # skull + snout
    p.poly(Mh, ell(0, 0, 25, 21, 36), c['body'])
    # lower jaw (rotates open)
    Mj = Mh @ T(14, 9) @ R(18 * m)
    p.poly(Mj, [(-6, -3), (36, -2), (34, 5), (-4, 8)], c['belly'])
    if m > 0.08:
        p.poly(Mh, [(14, 8), (48, 4), (14 + 36 * math.cos(math.radians(18 * m)), 9 + 36 * math.sin(math.radians(18 * m)))],
               "#7a1c14", outline=None)
    p.poly(Mh, [(8, -14), (46, -3), (50, 4), (14, 9), (2, 4)], c['body'])     # snout
    p.poly(Mh, [(10, 2), (48, 3), (14, 9)], c['belly'], outline=None)          # muzzle white
    p.poly(Mh, ell(50, -1, 6, 5, 16), JD, outline=None)                        # nose
    p.poly(Mh, ell(-6, 8, 13, 9, 24), c['belly'], outline=None)                # cheek ruff
    # front ear
    Me = Mh @ T(-12, -14) @ R(-4 + po.get('ear', 0))
    p.poly(Me, [(-10, 2), (10, 2), (1, -44)], c['body'])
    p.poly(Me, [(-5, -1), (5, -1), (1, -34)], c['ear'], outline=None)
    # eye (blink + lid)
    blink = po.get('blink', 0)
    ey = 1 - max(blink, c['lid'] * 0.6)
    p.poly(Mh, ell(10, -6, 8, 8 * max(0.12, ey), 20), "white", w=1.5)
    if ey > 0.25:
        lx = po.get('look', 0)
        p.poly(Mh, ell(12 + 1.5 * lx, -5.5, 4.3, 4.8 * ey, 16), JD, outline=None)
        p.poly(Mh, ell(13.5 + 1.5 * lx, -7.5, 1.5, 1.5, 8), "white", outline=None)
    if c['lid'] > 0:     # calm half-lid line (Kalila)
        p.line(Mh, [(2, -10), (18, -11)], JD, 1.8)
    br = c['brow'] * (0.6 + 0.4 * po.get('sly', 0))
    p.line(Mh, [(2, -16 - 3 * br), (18, -15 + 2 * br)], JD, 2.5)

def jackal_tail(p, Mb, c, t, wag, bushy):
    pts_top, pts_bot = [], []
    x, y = -52.0, -108.0; ang = math.radians(178)
    for i in range(12):
        ang -= 0.10 - wag * math.sin(t * 7 - i * 0.5) * 0.05
        x += 8.5 * math.cos(ang); y += 8.5 * math.sin(ang)
        w = bushy * (4 + 13 * math.sin(math.pi * min(1, (i + 1) / 10.5)))
        nx, ny = -math.sin(ang), math.cos(ang)
        pts_top.append((x + nx * w, y + ny * w)); pts_bot.append((x - nx * w, y - ny * w))
    p.poly(Mb, pts_top + pts_bot[::-1], c['body'])
    tip = pts_top[-4:] + pts_bot[-4:][::-1]
    p.poly(Mb, tip, c['tail_tip'], w=2)

def jackal_leg(p, Mb, jx, jy, ang, col, c):
    Ml = Mb @ T(jx, jy) @ R(ang)
    p.poly(Ml, [(-7, -4), (7, -4), (5, 66), (-5, 66)], col)
    p.poly(Ml, ell(3, 69, 9, 5, 16), col)

def draw_jackal(p, M, who, po):
    """M: transform at the feet (facing right). po: t, walk, amp, mouth, head, blink, ear, wag, sit"""
    c = JACKALS[who]; t = po['t']
    ph = po.get('walk', 0); amp = po.get('amp', 0)
    br = 1 + 0.02 * math.sin(t * 2.4 + (1 if who == 'dimna' else 0))
    M = M @ S(c['scale'])
    Mb = M @ T(0, -po.get('hop', 0)) @ T(0, -95) @ S(1, br) @ T(0, 95)
    far = c['dark']
    jackal_leg(p, Mb, -38, -82, amp * math.sin(ph), far, c)
    jackal_leg(p, Mb, 40, -82, -amp * math.sin(ph), far, c)
    jackal_tail(p, Mb, c, t, po.get('wag', 0.4), 1.15 if who == 'dimna' else 1.0)
    p.poly(Mb, ell(0, -98, 60, 25, 44), c['body'])
    p.poly(Mb, ell(8, -84, 40, 9, 28, 0, 180), c['belly'], outline=None)
    jackal_leg(p, Mb, -50, -82, -amp * math.sin(ph), c['body'], c)
    jackal_leg(p, Mb, 30, -82, amp * math.sin(ph), c['body'], c)
    # neck
    p.poly(Mb, [(28, -116), (50, -138), (74, -124), (58, -86)], c['body'])
    p.poly(Mb, [(50, -126), (70, -120), (58, -90), (44, -100)], c['belly'], outline=None)
    jackal_head(p, Mb @ T(62, -142) @ R(po.get('head', 0)) @ S(1.45), c, po)

def jackal_pose(who, t, speak, base_head=0.0, look=0.0):
    """idle + talking animation driven by speech envelope"""
    blink_ph = (t + (1.3 if who == 'dimna' else 0)) % 3.7
    blink = 1.0 if blink_ph < 0.12 else 0.0
    po = dict(t=t, mouth=0.9 * speak, blink=blink, look=look,
              head=base_head + 4 * math.sin(t * 1.3) + speak * 6 * math.sin(t * 9),
              ear=3 * math.sin(t * 2.1) + 6 * speak * math.sin(t * 6),
              wag=(0.9 if who == 'dimna' else 0.35) + speak * 0.5,
              sly=speak)
    return po

# ------------------------------------------------------------------ hosts' tree set
def big_tree(p, M, x, base):
    trunk = [(x - 26, base), (x + 30, base), (x + 18, base - 120), (x + 60, base - 210), (x + 44, base - 218),
             (x + 8, base - 150), (x - 10, base - 230), (x - 26, base - 226), (x - 14, base - 140), (x - 70, base - 200),
             (x - 82, base - 192), (x - 22, base - 110)]
    p.poly(M, trunk, "#6b4226", w=3)
    for k in range(5):
        yy = base - 20 - k * 22
        p.line(M, [(x - 14, yy), (x + 2, yy - 8), (x + 16, yy - 2)], "#4e2f18", 1.5)
    blobs = [(-150, -250, 70), (-60, -300, 85), (50, -310, 80), (140, -255, 70), (-100, -205, 55), (95, -200, 58),
             (0, -240, 70)]
    for cx, cy, r in blobs:
        p.poly(M, ell(x + cx, base + cy, r + 4, r * 0.82 + 4, 40), "#3e6533", outline=None)
    for cx, cy, r in blobs:
        p.poly(M, ell(x + cx, base + cy, r, r * 0.82, 40), "#6c9a52", outline=None)
    rng = np.random.default_rng(3)
    for _ in range(70):
        a = rng.uniform(0, 2 * math.pi); r = rng.uniform(0, 1) ** 0.6 * 170
        bx, by = x + r * math.cos(a) * 1.15, base - 255 + r * 0.55 * math.sin(a)
        p.poly(M, ell(bx, by, 4, 4, 10), ["#f2b8c6", "#fff5f0", "#e98aa5", "#f3c94a"][rng.integers(4)], outline=None)

def bush(p, M, x, base, s=1.0, shake=0.0):
    for k, (dx, dy, r) in enumerate([(-50, -30, 40), (0, -50, 52), (52, -30, 42), (-20, -18, 34), (30, -16, 34)]):
        ox = shake * math.sin(k * 2 + shake * 40) * 4
        p.poly(M, ell(x + (dx + ox) * s, base + dy * s, r * s + 3, r * s * 0.8 + 3, 30), "#3e6533", outline=None)
    for k, (dx, dy, r) in enumerate([(-50, -30, 40), (0, -50, 52), (52, -30, 42), (-20, -18, 34), (30, -16, 34)]):
        ox = shake * math.sin(k * 2 + shake * 40) * 4
        p.poly(M, ell(x + (dx + ox) * s, base + dy * s, r * s, r * s * 0.8, 30), "#5f8c47", outline=None)
    for k in range(9):
        p.poly(M, ell(x + (-60 + k * 15) * s, base - (20 + 30 * math.sin(k)) * s - 10, 3.5, 3.5, 8), "#f3c94a", outline=None)

def build_tree_set(seed=5):
    ww, hh = W * SS, H * SS
    g = np.linspace(0, 1, hh)[:, None]
    top, bot = np.array([236, 200, 120.]), np.array([250, 238, 206.])
    col = (top * (1 - g) + bot * g).astype(np.uint8)
    img = Image.fromarray(np.ascontiguousarray(np.broadcast_to(col[:, None, :], (hh, ww, 3))), 'RGB')
    p = Pen(img); M = S(SS); rng = np.random.default_rng(seed)
    for k in range(16):
        a = math.radians(k * 22.5)
        p.poly(M, [(1080 + 40 * math.cos(a - 0.12), 110 + 40 * math.sin(a - 0.12)),
                   (1080 + 62 * math.cos(a), 110 + 62 * math.sin(a)),
                   (1080 + 40 * math.cos(a + 0.12), 110 + 40 * math.sin(a + 0.12))], "#e9a93a", outline=None)
    p.poly(M, ell(1080, 110, 40, 40), "#f2c14e", outline="#b9802a", w=2)
    cloud(p, M, 560, 120, 1.0); cloud(p, M, 820, 190, 0.8)
    xs = np.arange(0, W + 20, 8)
    def hill(base, amp, sd, wl):
        y = base - amp * (0.55 + 0.45 * np.sin(xs / wl + sd) * np.sin(xs / (wl * 0.41) + sd * 2))
        return list(zip(xs, y)) + [(W + 20, H), (0, H)]
    p.poly(M, hill(410, 70, 0.7, 210), "#d9b6a3", outline="#9c7a68", w=2)
    p.poly(M, hill(482, 55, 2.1, 150), "#b9ba86", outline="#7f8156", w=2)
    for x in (1010, 1180):
        cypress(p, M, x, 566, rng.uniform(200, 230), 24)
    gp = [(x, 560 + 6 * math.sin(x / 90)) for x in range(0, W + 10, 10)] + [(W + 10, H), (0, H)]
    p.poly(M, gp, "#93ad62", outline="#5f7a3a", w=2)
    big_tree(p, M, 210, 600)
    for _ in range(320):
        fx, fy = rng.uniform(0, W), rng.uniform(575, 700)
        if rng.random() < 0.55: p.line(M, [(fx - 3, fy), (fx, fy - 7), (fx + 3, fy)], "#5f7a3a", 1.2)
        else: flower(p, M, fx, fy, ["#c8423a", "#fff7ea", "#3d6db5", "#d96f9a"][rng.integers(4)])
    return img

# ------------------------------------------------------------------ forest friends (Episode 1+)
JACKALS["fox"] = dict(body="#c9552b", dark="#3a2216", belly="#fbf1e2", ear="#2b1a10", scale=0.82,
                      tail_tip="#fbf1e2", brow=0.4, lid=0.15)

def draw_deer(p, M, po):
    """doe, facing right, feet at origin. po: t, walk, amp, neck (deg, + = down to drink), mouth, blink"""
    t = po['t']; ph = po.get('walk', 0); amp = po.get('amp', 0)
    body, dark, belly = "#c98e55", "#9a6a3c", "#f6e8d0"
    Mb = M @ T(0, -po.get('hop', 0))
    def leg(jx, ang, col):
        Ml = Mb @ T(jx, -112) @ R(ang)
        p.poly(Ml, [(-6, 0), (6, 0), (4, 110), (-4, 110)], col)
        p.poly(Ml, [(-5, 104), (6, 104), (6, 114), (-6, 114)], "#3b2a1a", outline=None)
    leg(-40, amp * math.sin(ph), dark); leg(42, -amp * math.sin(ph), dark)
    p.poly(Mb @ T(-62, -138) @ R(-30 + 10 * math.sin(t * 5)), ell(-8, 0, 12, 7, 16), "white")   # tail
    p.poly(Mb, ell(0, -128, 66, 30, 44), body)
    p.poly(Mb, ell(6, -112, 44, 10, 28, 0, 180), belly, outline=None)
    for sx, sy in ((-30, -140), (-12, -146), (8, -142), (-22, -128), (20, -134)):
        p.poly(Mb, ell(sx, sy, 3.5, 3, 10), "#fbf1e2", outline=None)
    leg(-52, -amp * math.sin(ph), body); leg(30, amp * math.sin(ph), body)
    Mn = Mb @ T(46, -140) @ R(po.get('neck', 0))
    p.poly(Mn, [(-15, 8), (15, 8), (22, -62), (0, -66)], body)
    Mh = Mn @ T(14, -70) @ R(-po.get('neck', 0) * 0.3) @ S(1.55)
    p.poly(Mh @ T(-6, -10) @ R(-40), ell(0, -14, 7, 16, 18), body)
    p.poly(Mh @ T(-2, -12) @ R(-15), ell(0, -14, 7, 16, 18), body)
    p.poly(Mh @ T(-2, -12) @ R(-15), ell(0, -13, 3.5, 11, 14), "#e7a6a0", outline=None)
    m = po.get('mouth', 0)
    p.poly(Mh, [(-10, -8), (10, -12), (36, 2 + 2 * m), (30, 10 + 4 * m), (0, 10)], body)
    p.poly(Mh, ell(34, 3, 4.5, 4, 12), (40, 26, 12), outline=None)
    bl = po.get('blink', 0)
    p.poly(Mh, ell(6, -2, 6, 6 * max(0.15, 1 - bl), 16), (40, 26, 12), outline=None)
    if bl < 0.5: p.poly(Mh, ell(7.5, -4, 2, 2, 8), "white", outline=None)

def draw_tortoise(p, M, po):
    """tortoise with a Persian-tile shell, facing right, feet at origin.
    Defaults = the old elder of Ep 1. Options: beard, shell, band, flower (colour), sick (head cloth), lash, peek"""
    t = po['t']; ph = po.get('walk', 0); amp = po.get('amp', 0)
    skin, sdark = po.get('skin', "#8fae6a"), po.get('skin_dark', "#5f7a3a")
    shell, band = po.get('shell', "#2f6f6a"), po.get('band', "#d4a63c")
    beard = po.get('beard', True)
    for jx, s_ in ((-40, 1), (34, -1)):
        p.poly(M @ T(jx + 6 * math.sin(ph) * s_ * (amp > 0), -14), ell(0, 0, 13, 16, 18), sdark)
    # head + neck
    nod = po.get('head', 0) + 2 * math.sin(t * 1.2)
    Mh = M @ T(62, -44) @ R(nod) @ S(1.35)
    p.poly(Mh, [(-20, 6), (-20, -14), (8, -18), (8, 6)], skin)
    p.poly(Mh, ell(18, -16, 22, 18, 30), skin)
    m = po.get('mouth', 0)
    p.poly(Mh, [(6, -4), (36, -8), (36, -4 + 8 * m), (8, 0 + 6 * m)], "#5f3a2a" if m > 0.1 else skin, w=2)
    if beard:
        bw = 3 * math.sin(t * 2)
        p.poly(Mh, [(12, 0), (32, -2), (31, 10), (26 + bw * 0.3, 24), (22, 30 + bw), (17, 22), (13, 10)], "#f4f1e8", w=1.5)
    else:
        p.poly(Mh, ell(30, -9, 3.5, 2.5, 10), "#e98a8a", outline=None)          # rosy cheek
    bl = po.get('blink', 0)
    p.poly(Mh, ell(22, -22, 5.5, 5.5 * max(0.2, 1 - bl), 14), "white", w=1.5)
    if bl < 0.5:
        p.poly(Mh, ell(23.5 + po.get('look', 0), -21, 2.7, 2.7, 10), (40, 26, 12), outline=None)
        p.poly(Mh, ell(24.5 + po.get('look', 0), -22.5, 0.9, 0.9, 6), "white", outline=None)
    if po.get('lash'):
        for k in range(3):
            p.line(Mh, [(19 + 3 * k, -27), (17 + 4 * k, -31)], (40, 26, 12), 1.2)
    if beard:
        p.line(Mh, [(14, -30), (30, -29)], "#f4f1e8", 3)      # white eyebrow
    else:
        p.line(Mh, [(16, -30 - 2 * po.get('sad', 0)), (28, -29 + 2 * po.get('sad', 0))], (40, 26, 12), 1.8)
    if po.get('sick'):
        p.poly(Mh, [(2, -34), (34, -38), (35, -31), (3, -27)], "#fbf7ee", w=1.5)
        p.poly(Mh, [(3, -31), (-8, -24), (-6, -20), (4, -27)], "#fbf7ee", w=1.2)
    if po.get('flower'):
        flower(p, Mh, 8, -36, po['flower']); flower(p, Mh, 14, -38, po['flower'])
    # shell (dome with tile pattern)
    p.poly(M, ell(0, -34, 70, 46, 48, 180, 360) + [(70, -28), (-70, -28)], shell)
    p.poly(M, [(-74, -24), (74, -24), (70, -16), (-70, -16)], band, w=2)
    for k in range(-2, 3):
        cx = k * 26; cy = -48 + 8 * abs(k)
        p.poly(M, khatam(cx, cy, 11), band, outline="#8a6418", w=1)
        p.poly(M, ell(cx, cy, 3, 3, 8), "#f4e6c4", outline=None)
    for jx, s_ in ((-26, -1), (48, 1)):
        p.poly(M @ T(jx + 6 * math.sin(ph) * s_ * (amp > 0), -10), ell(0, 0, 13, 16, 18), skin)
    return dict(head=Mh, mouth=Mh @ T(34, -3))

# ------------------------------------------------------------------ sea friends (Episode 2+)
MK = dict(fur="#8a5a33", dark="#5e3a1f", face="#f0d2a8", ear="#d99a8a", grey="#e9e2d2")

def draw_monkey(p, M, po):
    """old monkey (ex-king, little crown), facing right, origin at the feet (standing) or seat (sit=1).
    po: t, mouth, blink, look, sit (0..1), hop, arm (near arm deg, 0 = down, -150 = up/forward),
        arm2 (far arm), head (deg), walk, amp, crown (bool)"""
    t = po['t']; m = po.get('mouth', 0); sit = po.get('sit', 0)
    ph = po.get('walk', 0); amp = po.get('amp', 0)
    Mb = M @ T(0, -po.get('hop', 0))
    br = 1 + 0.025 * math.sin(t * 2.6)
    Mu = Mb @ T(0, -38 * (1 - sit)) @ S(1, br)          # upper body (hips at origin)
    # tail (behind everything)
    pts = []; x, y = -24.0, -14.0; ang = math.radians(200)
    for i in range(17):
        ang += 0.19 + 0.05 * math.sin(t * 2.2 - i * 0.4)
        x += 7.5 * math.cos(ang); y += 7.5 * math.sin(ang); pts.append((x, y))
    p.line(Mu, [(-20, -14)] + pts, OUT, 9); p.line(Mu, [(-20, -14)] + pts, MK['fur'], 5)
    # far arm
    Ma2 = Mu @ T(4, -66) @ R(po.get('arm2', 8) + 4 * math.sin(t * 1.7))
    p.poly(Ma2, [(-5, 0), (5, 0), (4, 46), (-4, 46)], MK['dark']); p.poly(Ma2, ell(0, 49, 7, 6, 14), MK['dark'])
    # legs
    if sit > 0.5:
        p.poly(Mu, ell(14, -8, 21, 10, 24), MK['dark'])
        p.poly(Mu, ell(16, -6, 21, 10, 24), MK['fur'])
        p.poly(Mu, ell(34, -2, 9, 5, 14), MK['face'])
    else:
        for jx, sgn, col in ((-8, 1, MK['dark']), (8, -1, MK['fur'])):
            Ml = Mb @ T(jx, -40) @ R(amp * math.sin(ph) * sgn)
            p.poly(Ml, [(-6, 0), (6, 0), (5, 38), (-5, 38)], col)
            p.poly(Ml, ell(5, 39, 10, 4.5, 14), MK['face'])
    # body
    p.poly(Mu, ell(0, -42, 30, 40, 36), MK['fur'])
    p.poly(Mu, ell(7, -38, 17, 25, 28), MK['face'], outline=None)
    # head
    Mh = Mu @ T(8, -86) @ R(po.get('head', 0) + 3 * math.sin(t * 1.4))
    p.poly(Mh, ell(24, -28, 9, 10, 16), MK['dark'])                      # far ear
    p.poly(Mh, ell(0, -26, 28, 27, 36), MK['fur'])
    p.poly(Mh, ell(-23, -26, 11, 12, 18), MK['fur'])                     # near ear
    p.poly(Mh, ell(-23, -26, 6, 7, 14), MK['ear'], outline=None)
    p.poly(Mh, ell(9, -31, 19, 15, 30), MK['face'], w=1.5)               # face mask
    p.poly(Mh, ell(13, -15, 16, 12, 28), MK['face'], w=1.5)              # muzzle
    p.poly(Mh, ell(9, -26, 17, 9, 24), MK['face'], outline=None)         # join mask + muzzle
    bl = po.get('blink', 0); ey = max(0.12, 1 - bl); lx = po.get('look', 0)
    for ex in (3, 18):
        p.poly(Mh, ell(ex, -32, 6, 7.5 * ey, 16), "white", w=1.2)
        if ey > 0.3:
            p.poly(Mh, ell(ex + 1.5 + 1.5 * lx, -31.5, 3.4, 4.2 * ey, 12), JD, outline=None)
            p.poly(Mh, ell(ex + 2.6 + 1.5 * lx, -33.5, 1.2, 1.2, 8), "white", outline=None)
    p.line(Mh, [(-4, -43), (9, -41)], MK['grey'], 3.2)                    # old grey brows
    p.line(Mh, [(13, -41), (25, -43)], MK['grey'], 3.2)
    p.poly(Mh, ell(14, -21, 1.6, 1.3, 8), JD, outline=None)
    p.poly(Mh, ell(19, -21, 1.6, 1.3, 8), JD, outline=None)
    p.poly(Mh, ell(26, -18, 4, 2.6, 10), "#ec9b8e", outline=None)        # blush
    if m > 0.08:
        p.poly(Mh, ell(15, -11, 6 + 2 * m, 1.8 + 5 * m, 16), "#7a1c14", w=1.5)
    else:
        p.line(Mh, [(8, -12), (15, -9), (22, -12)], JD, 1.6)
    if po.get('crown', True):
        Mc = Mh @ T(-4, -50) @ R(-14)
        p.poly(Mc, [(-12, 0), (12, 0), (14, -14), (7, -6), (0, -17), (-7, -6), (-14, -14)], "#e2b64a", w=1.5)
        p.poly(Mc, ell(0, -4, 2.2, 2.2, 8), "#c8423a", outline=None)
    # near arm (in front)
    Ma = Mu @ T(10, -64) @ R(po.get('arm', 6) + 3 * math.sin(t * 1.9))
    p.poly(Ma, [(-6, 0), (6, 0), (5, 48), (-5, 48)], MK['fur'])
    p.poly(Ma, ell(0, 51, 8, 7, 14), MK['face'])
    if po.get('fig'):                                                       # holding a fig
        p.poly(Ma, ell(0, 60, 7, 8, 14), "#7a3b6e", w=1.5)

def fig(p, M, x, y, r=7):
    p.poly(M, ell(x, y, r, r * 1.15, 14), "#7a3b6e", outline="#3f1d3a", w=1.5)
    p.line(M, [(x, y - r * 1.1), (x + 2, y - r * 1.6)], "#4e6b2a", 2)

def fig_tree(p, M, x, base, rng):
    """big fig tree with a long branch to the right (seat at x+130, base-196)"""
    trunk = [(x - 30, base), (x + 34, base), (x + 20, base - 120), (x + 60, base - 210), (x + 44, base - 218),
             (x + 8, base - 150), (x - 10, base - 236), (x - 26, base - 232), (x - 14, base - 140), (x - 70, base - 200),
             (x - 82, base - 192), (x - 24, base - 110)]
    p.poly(M, trunk, "#6b4226", w=3)
    for k in range(5):
        yy = base - 20 - k * 22
        p.line(M, [(x - 14, yy), (x + 2, yy - 8), (x + 16, yy - 2)], "#4e2f18", 1.5)
    blobs = [(-150, -260, 72), (-60, -310, 88), (50, -320, 84), (150, -280, 70), (-110, -215, 55),
             (0, -250, 72), (200, -330, 50)]
    for cx, cy, r in blobs:
        p.poly(M, ell(x + cx, base + cy, r + 4, r * 0.82 + 4, 40), "#2f5a2c", outline=None)
    for cx, cy, r in blobs:
        p.poly(M, ell(x + cx, base + cy, r, r * 0.82, 40), "#5a8a45", outline=None)
    for _ in range(40):                                  # big fig leaves
        a = rng.uniform(0, 2 * math.pi); r = rng.uniform(0, 1) ** 0.6 * 170
        lx, ly = x + 20 + r * math.cos(a) * 1.2, base - 280 + r * 0.5 * math.sin(a)
        p.poly(M @ T(lx, ly) @ R(rng.uniform(0, 360)), [(0, -9), (6, -3), (9, 4), (0, 9), (-9, 4), (-6, -3)],
               "#74a456", outline="#3e6533", w=1)
    for _ in range(26):
        a = rng.uniform(0, 2 * math.pi); r = rng.uniform(0, 1) ** 0.6 * 160
        fig(p, M, x + 20 + r * math.cos(a) * 1.2, base - 270 + r * 0.5 * math.sin(a), 6)
    # the monkey's branch
    p.poly(M, [(x + 10, base - 176), (x + 120, base - 194), (x + 200, base - 210), (x + 206, base - 202),
               (x + 120, base - 182), (x + 14, base - 158)], "#6b4226", w=2.5)
    p.poly(M, [(x + 196, base - 208), (x + 222, base - 230), (x + 226, base - 224), (x + 204, base - 203)], "#6b4226", w=2)
    p.poly(M @ T(x + 226, base - 232) @ R(30), [(0, -9), (6, -3), (9, 4), (0, 9), (-9, 4), (-6, -3)], "#74a456",
           outline="#3e6533", w=1)

# ------------------------------------------------------------------ meadow friends (Episode 3+)
BIRDS = {
    # Ring-Dove: cream with a golden ring (the leader)
    "ringdove": dict(body="#efe6d6", dark="#c2ae8e", breast="#fbf4e8", head="#e9dcc6", wing="#d9c7a6",
                     tip="#9c8466", beak="#d98a6a", foot="#e98a7a", ring=True, blen=12, crest=False),
    "dove_grey": dict(body="#c9cbd6", dark="#8d90a8", breast="#ece6ee", head="#b7bccd", wing="#aeb2c6",
                      tip="#6e7290", beak="#d98a6a", foot="#e98a7a", ring=False, blen=11, crest=False),
    "dove_white": dict(body="#f4f1ea", dark="#c9c3b6", breast="#fffdf8", head="#f0ece2", wing="#e3ddd0",
                       tip="#a69e8e", beak="#e09a7a", foot="#e98a7a", ring=False, blen=11, crest=False),
    "dove_brown": dict(body="#d8b99a", dark="#a8825e", breast="#f3e2cf", head="#cfae8c", wing="#c39c76",
                       tip="#7e5e40", beak="#d98a6a", foot="#e98a7a", ring=False, blen=11, crest=False),
    "dove_blue": dict(body="#b9cbd9", dark="#7f98ad", breast="#e6eef4", head="#a9bfd0", wing="#9fb6c9",
                      tip="#5d7890", beak="#d98a6a", foot="#e98a7a", ring=False, blen=11, crest=False),
    "crow": dict(body="#33364a", dark="#1f2130", breast="#474b63", head="#3a3d52", wing="#2a2c3e",
                 tip="#15161f", beak="#6b6b6b", foot="#5a5a5a", ring=False, blen=20, crest=True),
}

WING = [(6, 2), (4, -26), (-2, -50), (-10, -70), (-18, -72), (-20, -62), (-28, -60), (-28, -48),
        (-34, -42), (-30, -26), (-20, -8), (-10, 4)]

def draw_bird(p, M, kind, po):
    """dove / crow cut-out, facing right, origin at the feet.
    po: t, mouth, blink, look, fly (0/1), flap (radians), head (deg), peck (0..1 head down), hop"""
    c = BIRDS[kind]; t = po['t']; fly = po.get('fly', 0)
    Mb = M @ T(0, -po.get('hop', 0))
    flap = po.get('flap', 0)
    br = 1 + 0.03 * math.sin(t * 3 + len(kind))
    Mu = Mb @ T(0, -16) @ R(-8 * fly + po.get('tilt', 0)) @ S(1, br) @ T(0, 16)
    # far wing (flying only)
    if fly:
        Mw = Mu @ T(4, -42) @ R(-5 - 55 * (1 - math.sin(flap)))
        p.poly(Mw, WING, c['dark'])
    # legs
    if not fly:
        for jx in (-5, 7):
            p.line(Mb, [(jx, -16), (jx - 1, -1)], OUT, 4.5); p.line(Mb, [(jx, -16), (jx - 1, -1)], c['foot'], 2.5)
            p.line(Mb, [(jx - 7, 0), (jx + 6, 0)], OUT, 4.5); p.line(Mb, [(jx - 7, 0), (jx + 6, 0)], c['foot'], 2.5)
    else:
        p.line(Mu, [(-6, -18), (-22, -12)], OUT, 4.5); p.line(Mu, [(-6, -18), (-22, -12)], c['foot'], 2.5)
    # tail
    p.poly(Mu, [(-20, -36), (-56, -46), (-60, -38), (-58, -28), (-20, -24)], c['wing'])
    p.line(Mu, [(-28, -34), (-56, -40)], c['tip'], 1.5); p.line(Mu, [(-28, -30), (-57, -32)], c['tip'], 1.5)
    # neck + body
    p.poly(Mu, [(6, -46), (22, -60), (32, -44), (22, -26)], c['body'])
    p.poly(Mu, ell(0, -32, 30, 19, 40), c['body'])
    p.poly(Mu, [(8, -44), (20, -58), (30, -44), (20, -30)], c['body'], outline=None)
    p.poly(Mu, ell(10, -26, 18, 11, 28), c['breast'], outline=None)
    Mh = Mu @ T(20, -50) @ R(po.get('head', 0) + 50 * po.get('peck', 0))
    if kind.startswith("dove"):
        p.poly(Mu, [(14, -52), (24, -50), (28, -40), (20, -42)], "#8fb8ac", outline=None)   # shiny neck
    m = po.get('mouth', 0)
    bl = c['blen']
    p.poly(Mh, [(10, -4), (10 + bl, 0), (10, 3)], c['beak'], w=1.5)                          # upper beak
    p.poly(Mh, [(10, 2), (8 + bl * 0.85, 3 + 7 * m), (10, 6 + 2 * m)], c['beak'], w=1.5)    # lower beak
    p.poly(Mh, ell(0, -2, 15, 14, 32), c['head'])
    if c['crest']:
        p.poly(Mh, [(-10, -11), (-20, -18), (-16, -8)], c['head'], w=1.5)
    if c['ring']:                                    # the golden ring (collar) under her chin
        rp = ell(-1, 9, 15, 6, 14, 10, 170)
        p.line(Mh, rp, OUT, 9); p.line(Mh, rp, "#f2c14e", 5.5)
        for q in rp[2::4]:
            p.poly(Mh, khatam(q[0], q[1], 2.4), "#c8423a", outline=None)
    p.poly(Mh, [(10, -4), (10 + bl, 0), (10, 2)], c['beak'], w=1.5)
    p.poly(Mh, ell(10 + bl * 0.15, -2.5, 1.2, 1, 6), OUT, outline=None)                      # nostril
    blk = po.get('blink', 0); ey = max(0.12, 1 - blk); lx = po.get('look', 0)
    p.poly(Mh, ell(3, -4, 6.5, 7 * ey, 18), "white", w=1.4)
    if ey > 0.3:
        p.poly(Mh, ell(4.5 + 1.6 * lx, -3.5, 3.6, 4.2 * ey, 14), JD, outline=None)
        p.poly(Mh, ell(5.8 + 1.6 * lx, -5.5, 1.3, 1.3, 8), "white", outline=None)
    if kind == "crow":
        p.line(Mh, [(-4, -12), (9, -10 + 2 * po.get('sly', 0))], "#9aa0b8", 2)
    else:
        p.poly(Mh, ell(7, 5, 3.2, 2, 10), "#f0a8a0", outline=None)                              # blush
    # near wing
    if fly:
        Mw = Mu @ T(-2, -38) @ R(-15 - 60 * (1 - math.sin(flap)))
        p.poly(Mw, WING, c['wing'])
        for k in range(3):
            p.line(Mw, [(-8 - 6 * k, -18 - 10 * k), (-22 - 5 * k, -44 - 8 * k)], c['tip'], 1.4)
    else:
        Mw = Mu @ T(4, -40) @ R(po.get('wing', 0))
        p.poly(Mw, [(0, 0), (-26, -4), (-46, 4), (-28, 14), (2, 10)], c['wing'])
        p.line(Mw, [(-20, 4), (-40, 5)], c['tip'], 1.4); p.line(Mw, [(-16, 8), (-34, 9)], c['tip'], 1.4)

MO = dict(fur="#9a8b7a", dark="#6e6152", belly="#efe4d4", ear="#eaa6a6", vest="#b0342c", trim="#e2b64a")

def draw_mouse(p, M, po):
    """Zirak the mouse, standing on his hind legs, facing right, origin at the feet.
    po: t, mouth, blink, look, head (deg), arm (deg), chew (0..1), hop, head_only (peek from a hole)"""
    t = po['t']; m = po.get('mouth', 0)
    Mb = M @ T(0, -po.get('hop', 0))
    br = 1 + 0.03 * math.sin(t * 3.1)
    chew = po.get('chew', 0)
    if not po.get('head_only'):
        # tail
        pts = []; x, y = -14.0, -10.0; ang = math.radians(170)
        for i in range(12):
            ang += 0.12 * math.sin(t * 2 + i * 0.4) - 0.09
            x += 6 * math.cos(ang); y += 6.5 * math.sin(ang); pts.append((x, y))
        p.line(Mb, [(-12, -10)] + pts, OUT, 6); p.line(Mb, [(-12, -10)] + pts, MO['ear'], 3)
        # far arm
        Ma2 = Mb @ T(4, -50) @ R(po.get('arm2', -20) + 20 * chew * math.sin(t * 18))
        p.poly(Ma2, [(-3, 0), (3, 0), (3, 22), (-3, 22)], MO['dark']); p.poly(Ma2, ell(0, 24, 4.5, 4, 10), MO['ear'])
        # feet
        p.poly(Mb, ell(-6, -2, 11, 4.5, 16), MO['ear']); p.poly(Mb, ell(12, -2, 12, 4.5, 16), MO['ear'])
        Mu = Mb @ T(0, -4) @ S(1, br)
        p.poly(Mu, ell(0, -30, 20, 30, 32), MO['fur'])
        p.poly(Mu, ell(6, -26, 12, 20, 24), MO['belly'], outline=None)
        # little Persian vest
        p.poly(Mu, ell(1, -32, 19, 21, 28), MO['vest'], w=2)
        p.poly(Mu, [(8, -52), (16, -50), (18, -16), (8, -14)], MO['belly'], outline=None)
        p.line(Mu, [(8, -52), (8, -14)], MO['trim'], 2.2); p.line(Mu, [(16, -50), (18, -16)], MO['trim'], 2.2)
        p.poly(Mu, khatam(-6, -32, 4), MO['trim'], outline=None)
        Mh = Mu @ T(6, -62) @ R(po.get('head', 0) + 3 * math.sin(t * 1.6) + 8 * chew * math.sin(t * 16))
    else:
        Mh = Mb @ T(6, -14) @ R(po.get('head', 0) + 3 * math.sin(t * 1.6))
    # head
    p.poly(Mh, ell(-6, -26, 13, 14, 24), MO['dark'])                                   # far ear
    p.poly(Mh, ell(-6, -26, 8, 9, 16), MO['ear'], outline=None)
    p.poly(Mh, [(-14, -6), (-10, -18), (6, -20), (30, -6), (32, -2), (8, 8), (-10, 6)], MO['fur'])
    p.poly(Mh, ell(32, -4, 4.5, 4, 12), "#e07a8a", w=1.2)                              # nose
    if m > 0.08:
        p.poly(Mh, ell(22, 4, 4 + m, 1 + 4 * m, 12), "#7a1c14", w=1.2)
    else:
        p.line(Mh, [(18, 3), (22, 5), (26, 3)], JD, 1.4)
    p.poly(Mh, [(20, 4), (24, 4), (24, 9), (20, 9)], "white", w=1)                    # buck teeth
    p.line(Mh, [(22, 4), (22, 9)], OUT, 0.8)
    for dy, ang in ((-2, -8), (2, 4), (5, 14)):
        p.line(Mh, [(26, dy), (46, dy + ang * 0.6)], "#5e5244", 1.0)
    blk = po.get('blink', 0); ey = max(0.12, 1 - blk); lx = po.get('look', 0)
    p.poly(Mh, ell(10, -8, 7, 7.5 * ey, 18), "white", w=1.3)
    if ey > 0.3:
        p.poly(Mh, ell(11.5 + 1.5 * lx, -7.5, 4, 4.6 * ey, 14), JD, outline=None)
        p.poly(Mh, ell(13 + 1.5 * lx, -10, 1.4, 1.4, 8), "white", outline=None)
    p.poly(Mh, ell(20, -1, 3.5, 2.2, 10), "#f0a8a0", outline=None)
    Me = Mh @ T(-12, -16) @ R(-10 + 6 * math.sin(t * 2.2))                               # near ear
    p.poly(Me, ell(0, -12, 15, 16, 28), MO['fur'])
    p.poly(Me, ell(1, -12, 9.5, 10.5, 20), MO['ear'], outline=None)
    if not po.get('head_only'):
        Ma = Mb @ T(10, -48) @ R(po.get('arm', -30) + 20 * chew * math.sin(t * 18 + 1))
        p.poly(Ma, [(-3.5, 0), (3.5, 0), (3, 24), (-3, 24)], MO['fur']); p.poly(Ma, ell(0, 26, 5, 4.5, 10), MO['ear'])

HU = dict(skin="#e8b98f", coat="#7d8a3e", coat2="#5f6b2c", sash="#e2b64a", trou="#4a3a2a", hat="#7a5634",
          hat2="#5a3d22", shoe="#efe4cc", must="#3a2216")
HU_DEFAULT = HU
# palace guard (Episode 4): same puppet, blue qaba, red sash and hat; po['pal'] = GUARD
GUARD = dict(HU, coat="#2f5f9e", coat2="#244a7c", sash="#c8423a", trou="#3a2c1e", hat="#c8423a", hat2="#8e2a22",
             must="#2a1a10")

def draw_hunter(p, M, po):
    """a grumpy-but-harmless hunter in a felt hat, facing right, origin at the feet (~255 px tall).
    po: t, mouth, blink, look, walk, amp, arm (near arm deg, 0 = down, -90 = forward), arm2, head (deg),
        lean (deg), crouch (0..1), sit (0..1 tired), brow (0 calm .. 1 cross)"""
    HU = po.get('pal', HU_DEFAULT)
    t = po['t']; ph = po.get('walk', 0); amp = po.get('amp', 0); m = po.get('mouth', 0)
    cr = po.get('crouch', 0)
    Mb = M @ T(0, -po.get('hop', 0))
    br = 1 + 0.015 * math.sin(t * 2.2)
    L = 98 - 46 * cr
    def leg(sgn, col):
        Ml = Mb @ T(0, -6 - L) @ R(amp * 26 * math.sin(ph) * sgn)
        p.poly(Ml, [(-11, 0), (11, 0), (9, L), (-9, L)], col)
        p.poly(Ml, [(-10, L - 6), (14, L - 6), (26, L), (22, L + 8), (-11, L + 8)], HU['shoe'], w=2)
    leg(1, "#3a2c1e")
    Mu = Mb @ T(0, 46 * cr) @ T(0, -100) @ R(po.get('lean', 0)) @ S(1, br) @ T(0, 100)
    Ma2 = Mu @ T(-6, -186) @ R(po.get('arm2', 10) + 3 * math.sin(t * 1.5))
    p.poly(Ma2, [(-9, 0), (9, 0), (7, 70), (-7, 70)], HU['coat2']); p.poly(Ma2, ell(0, 76, 9, 9, 14), HU['skin'])
    leg(-1, HU['trou'])
    # coat (qaba) with a golden sash
    p.poly(Mu, [(-30, -196), (30, -196), (44, -78), (-42, -78)], HU['coat'])
    p.poly(Mu, [(4, -196), (14, -196), (22, -78), (10, -78)], HU['coat2'], outline=None)
    p.poly(Mu, [(-36, -128), (38, -128), (40, -112), (-38, -112)], HU['sash'], w=2)
    p.poly(Mu, [(-34, -116), (-46, -92), (-36, -90), (-28, -112)], HU['sash'], w=1.5)
    # head
    Mh = Mu @ T(4, -222) @ R(po.get('head', 0) + 2 * math.sin(t * 1.3) + 4 * m * math.sin(t * 8))
    p.poly(Mh, [(-10, 18), (10, 18), (10, 32), (-10, 32)], HU['skin'])                       # neck
    p.poly(Mh, ell(0, 0, 27, 29, 36), HU['skin'])
    p.poly(Mh, ell(-20, 2, 7, 9, 14), HU['skin'])                                            # ear
    p.poly(Mh, ell(27, 4, 9, 8, 16), "#e2a57c", w=2)                                         # big round nose
    if m > 0.08:
        p.poly(Mh, ell(12, 20, 8 + 2 * m, 2 + 7 * m, 16), "#7a1c14", w=1.5)
    else:
        p.line(Mh, [(4, 20), (12, 22), (20, 20)], JD, 1.6)
    p.poly(Mh, [(4, 10), (14, 8), (26, 10), (36, 16), (30, 18), (20, 14), (12, 16), (2, 18), (-6, 14)], HU['must'], w=1.5)
    p.poly(Mh, ell(-6, 12, 4, 2.6, 10), "#e8968a", outline=None)                             # cheek
    blk = po.get('blink', 0); ey = max(0.12, 1 - blk); lx = po.get('look', 0)
    p.poly(Mh, ell(12, -6, 7, 8 * ey, 18), "white", w=1.4)
    if ey > 0.3:
        p.poly(Mh, ell(13.5 + 1.8 * lx, -5.5, 3.8, 4.6 * ey, 14), JD, outline=None)
        p.poly(Mh, ell(14.8 + 1.8 * lx, -7.8, 1.3, 1.3, 8), "white", outline=None)
    bw = po.get('brow', 0.5)
    p.line(Mh, [(4, -16 + 3 * bw), (20, -17 - 3 * bw)], HU['must'], 3)
    # felt hat (kolah namadi)
    p.poly(Mh, ell(-4, -20, 25, 46, 30, 180, 360) + [(21, -16), (-29, -16)], HU['hat'])
    p.line(Mh, [(-14, -50), (-6, -60), (4, -52)], HU['hat2'], 1.6)
    p.poly(Mh, [(-31, -22), (27, -22), (29, -12), (-32, -12)], HU['hat2'], w=2)
    # near arm (in front)
    Ma = Mu @ T(6, -186) @ R(po.get('arm', 6) + 3 * math.sin(t * 1.8))
    p.poly(Ma, [(-10, 0), (10, 0), (8, 72), (-8, 72)], HU['coat'])
    if po.get('stick') is not None:                  # a long wooden staff held in the near hand
        Ms = Ma @ T(0, 78) @ R(po['stick'])
        p.line(Ms, [(0, -70), (0, 120)], OUT, 8); p.line(Ms, [(0, -70), (0, 120)], "#9c6a3a", 4.5)
    p.poly(Ma, ell(0, 78, 10, 10, 14), HU['skin'])


# ------------------------------------------------------------------ the crow family and the snake (Episode 4)
BIRDS["crow_mom"] = dict(BIRDS["crow"], body="#3c3f58", breast="#5a5f7c", head="#44486a", crest=False, blen=17)
BIRDS["crow_baby"] = dict(BIRDS["crow"], body="#55596f", dark="#3a3d50", breast="#7d8196", head="#5d6178",
                          wing="#474a5e", beak="#e7b54a", crest=False, blen=12)
JACKALS["wise"] = dict(body="#a9a49a", dark="#77726a", belly="#ece8de", ear="#d9a3a0", scale=1.08,
                       tail_tip="#f4f1ea", brow=0.2, lid=0.45)

SN = dict(body="#7aa23e", dark="#4f7425", belly="#e9d77a", spot="#4d6e22", tongue="#d0343a")

def snake_points(x, y, ang, length, t, amp=10, wl=70, speed=6, n=34, curl=0.0):
    """centreline of a slithering snake: head at (x, y) heading `ang` degrees (0 = right, -90 = up);
    the body trails behind with a travelling wave. curl bends the body (deg per segment)."""
    pts = []; a = math.radians(ang + 180); px, py = x, y; step = length / n
    for i in range(n + 1):
        u = i * step
        w = amp * math.sin(u / wl * 2 * math.pi - t * speed) * min(1, u / 60)
        nx, ny = -math.sin(a), math.cos(a)
        pts.append((px + nx * w, py + ny * w))
        px += step * math.cos(a); py += step * math.sin(a); a += math.radians(curl)
    return pts

def draw_snake(p, V, pts, po):
    """cartoon snake (grumpy, not scary). pts: centreline, head first (screen units, already placed).
    po: t, mouth, blink, look, width, brow (0 calm .. 1 cross), scared (0..1 big eyes), tongue (0..1)"""
    t = po['t']; wmax = po.get('width', 15); P = np.asarray(pts, float); n = len(P)
    if n < 3: return
    d = np.gradient(P, axis=0); d /= (np.linalg.norm(d, axis=1)[:, None] + 1e-9)
    nrm = np.stack([-d[:, 1], d[:, 0]], 1)
    u = np.linspace(0, 1, n)
    wid = wmax * np.where(u < 0.12, 0.72 + 0.28 * u / 0.12, 1.0) * np.clip((1 - u) / 0.55, 0.08, 1) ** 0.8
    L = P + nrm * wid[:, None]; Rr = P - nrm * wid[:, None]
    p.poly(V, [tuple(q) for q in L] + [tuple(q) for q in Rr[::-1]], SN['body'], w=2.5)
    B = P - nrm * (wid * 0.45)[:, None]
    if n > 7: p.line(V, [tuple(q) for q in B[2:-3]], SN['belly'], 3.2)
    for i in range(4, n - 4, 3):
        p.poly(V, ell(P[i][0] + nrm[i][0] * wid[i] * 0.2, P[i][1] + nrm[i][1] * wid[i] * 0.2,
                      wid[i] * 0.42, wid[i] * 0.42, 4), SN['spot'], outline=None)
    # head, oriented along the first segment; kept upright (top of head up)
    hx, hy = P[0]; dx, dy = P[0] - P[2]
    ang = math.degrees(math.atan2(dy, dx)); flip = -1 if abs(ang) > 90 else 1
    sc = wmax / 15
    Mh = V @ T(hx, hy) @ R(ang) @ S(sc, sc * flip) @ R(po.get('head', 0) * flip)
    m = po.get('mouth', 0)
    tg = po.get('tongue', 0.5 + 0.5 * math.sin(t * 9))
    if tg > 0.3:
        L2 = 18 + 14 * tg
        p.line(Mh, [(24, 6), (24 + L2, 6), (30 + L2, 1)], SN['tongue'], 2.2)
        p.line(Mh, [(24 + L2, 6), (30 + L2, 11)], SN['tongue'], 2.2)
    p.poly(Mh @ T(4, 6) @ R(14 * m), [(-10, -2), (24, 0), (22, 8), (-6, 8)], SN['belly'])       # lower jaw
    if m > 0.1:
        p.poly(Mh, [(4, 4), (26, 2), (4 + 22 * math.cos(math.radians(14 * m)), 6 + 22 * math.sin(math.radians(14 * m)))],
               "#7a1c14", outline=None)
    p.poly(Mh, ell(6, -4, 24, 14, 32), SN['body'])
    p.poly(Mh, ell(26, -6, 2, 1.4, 6), OUT, outline=None)                                    # nostril
    sca = po.get('scared', 0); blk = po.get('blink', 0); ey = max(0.12, 1 - blk); lx = po.get('look', 0.4)
    er = 7 + 3 * sca
    p.poly(Mh, ell(10, -14, er, er * ey, 18), "#fff8d8", w=1.5)
    if ey > 0.3:
        p.poly(Mh, ell(11.5 + 1.8 * lx, -13.5, 2.6 + 1.2 * sca, 5.2 * ey, 14), JD, outline=None)
        p.poly(Mh, ell(12.5 + 1.8 * lx, -16, 1.2, 1.2, 8), "white", outline=None)
    bw = po.get('brow', 0.6) * (1 - sca)
    p.line(Mh, [(2, -22 + 4 * sca - 2 * bw), (18, -22 + 3 * bw - 2 * sca)], SN['dark'], 3)

NK = dict(gold="#f2c14e", gold2="#b9802a", ruby="#c8423a", sky="#3d6db5")

def draw_necklace(p, M, t=0.0, hang=0.0):
    """golden necklace with gems; origin at its middle. hang 0 = lying in a loop, 1 = hanging from a beak (origin = top)"""
    if hang < 0.5:
        pts = ell(0, 0, 30, 12, 22)
    else:
        pts = [(18 * math.sin(a) * (1 - 0.3 * abs(math.cos(a))), 10 + 34 * (1 - math.cos(a)) / 2 + 3 * math.sin(t * 6))
               for a in np.linspace(-math.pi, math.pi, 22)]
    p.line(M, pts + [pts[0]], NK['gold2'], 4.4); p.line(M, pts + [pts[0]], NK['gold'], 2.4)
    for k, q in enumerate(pts[::3]):
        p.poly(M, ell(q[0], q[1], 3.6, 3.6, 10), [NK['ruby'], NK['sky']][k % 2], outline=NK['gold2'], w=1)
    lo = max(pts, key=lambda q: q[1])
    p.poly(M, khatam(lo[0], lo[1] + 5, 8, t * 20), NK['ruby'], outline=NK['gold2'], w=1.4)
    s = 0.5 + 0.5 * math.sin(t * 5)
    if s > 0.6:                                                     # sparkle
        q = pts[5]
        for a in range(4):
            r = math.radians(a * 90 + 45)
            p.line(M, [(q[0], q[1]), (q[0] + 11 * s * math.cos(r), q[1] + 11 * s * math.sin(r))], "#fffbe6", 2)


# ------------------------------------------------------------------ the heron, the crab and the fish (Episode 5)
HR = dict(body="#c9d0d8", dark="#7d8796", breast="#f1f2f0", wing="#a9b3c0", tip="#4e5668", beak="#e2b64a",
          beak2="#b9802a", leg="#c9a24a", plume="#3a3f52", neck="#dfe3e6")

def draw_heron(p, M, po):
    """old grey heron, facing right, origin at the feet (standing) / body centre-bottom (flying).
    po: t, mouth, blink, look, head (deg), neck (0 tucked .. 1 tall), fly (0/1), flap (rad), sly (0..1 sneaky brow),
        sad (0..1), hop, lean (deg). Returns dict(head=Mh, back=Mback) for attaching things (fish in the beak, a rider)."""
    t = po['t']; fly = po.get('fly', 0); c = HR
    Mb = M @ T(0, -po.get('hop', 0))
    br = 1 + 0.02 * math.sin(t * 2.6)
    if not fly:
        # legs (thin, with knees) and toes
        for jx, ph in ((-8, 0.0), (8, 1.0)):
            kx = jx + 4 + 2 * math.sin(t * 1.3 + ph)
            for col, w in ((OUT, 6), (c['leg'], 3.6)):
                p.line(Mb, [(jx, 0), (kx, -62), (jx - 2, -118)], col, w)
                p.line(Mb, [(jx - 14, 0), (jx + 16, 0)], col, w); p.line(Mb, [(jx, 0), (jx - 6, 6)], col, w)
        Mu = Mb @ T(0, -128) @ R(po.get('lean', 0) - 12)
    else:
        Mu = Mb @ R(po.get('lean', 0) - 4)
        for col, w in ((OUT, 6), (c['leg'], 3.6)):
            p.line(Mu, [(-40, -6), (-120, 4)], col, w); p.line(Mu, [(-34, -2), (-116, 12)], col, w)
        Mw = Mu @ T(4, -24) @ R(-10 - 60 * (1 - math.sin(po.get('flap', 0))))
        p.poly(Mw, [(20, 0), (10, -50), (-20, -110), (-60, -130), (-70, -112), (-50, -60), (-30, -10)], c['dark'])
    Mu = Mu @ S(1, br)
    # tail
    p.poly(Mu, [(-44, -18), (-92, 4), (-88, 14), (-40, 4)], c['dark'])
    # body
    p.poly(Mu, ell(0, -14, 56, 30, 40), c['body'])
    p.poly(Mu, ell(16, -4, 34, 16, 30, 0, 180) + [(-18, -4)], c['breast'], outline=None)
    # neck: an S-curve; neck=1 tall, 0 tucked
    nk = po.get('neck', 1.0); sad = po.get('sad', 0)
    if fly:
        pts = [(36, -26), (62, -40), (74, -52), (96, -52)]
    else:
        pts = [(34, -30), (52 + 6 * nk, -58 - 20 * nk), (34 + 4 * nk, -90 - 34 * nk + 26 * sad), (52, -110 - 50 * nk + 40 * sad)]
    for col, w in ((OUT, 19), (c['neck'], 14)):
        p.line(Mu, pts, col, w)
    p.line(Mu, [(q[0] + 4, q[1] + 2) for q in pts[1:3]], "#b7c0ca", 2)
    hx, hy = pts[-1]
    Mh = Mu @ T(hx, hy) @ R(po.get('head', 0) + 18 * sad)
    m = po.get('mouth', 0)
    # long beak (lower part opens)
    p.poly(Mh @ T(8, 2) @ R(10 * m), [(0, 0), (60, 1), (0, 6)], c['beak2'], w=1.8)
    p.poly(Mh, ell(0, -2, 17, 14, 30), c['neck'])
    p.poly(Mh, [(10, -6), (74, 0), (10, 4)], c['beak'], w=1.8)
    # plume (two long black feathers at the back of the head)
    for k, a in enumerate((0, 10)):
        sw = 4 * math.sin(t * 2 + k)
        p.line(Mh, [(-8, -10), (-30, -14 + a * 0.4 + sw * 0.3), (-48, -10 + a + sw)], OUT, 4.6)
        p.line(Mh, [(-8, -10), (-30, -14 + a * 0.4 + sw * 0.3), (-48, -10 + a + sw)], c['plume'], 2.6)
    p.line(Mh, [(-6, -8), (8, -4)], c['plume'], 3)                                 # black eye stripe
    blk = po.get('blink', 0); ey = max(0.12, 1 - blk); lx = po.get('look', 0)
    p.poly(Mh, ell(4, -6, 5.5, 5.5 * ey, 16), "#fff4c8", w=1.4)
    if ey > 0.3:
        p.poly(Mh, ell(5.2 + 1.5 * lx, -5.6, 2.8, 3.2 * ey, 12), JD, outline=None)
        p.poly(Mh, ell(6.2 + 1.5 * lx, -7.2, 1, 1, 6), "white", outline=None)
    sly = po.get('sly', 0)
    p.line(Mh, [(-2, -13 + 2 * sly - 2 * sad), (11, -12 - 3 * sly + 3 * sad)], c['plume'], 2.4)   # brow
    # near wing
    if fly:
        Mw = Mu @ T(0, -24) @ R(-20 - 62 * (1 - math.sin(po.get('flap', 0))))
        p.poly(Mw, [(20, 0), (10, -54), (-18, -118), (-58, -142), (-72, -122), (-52, -64), (-30, -8)], c['wing'])
        for k in range(4):
            p.line(Mw, [(-10 - 10 * k, -40 - 18 * k), (-26 - 12 * k, -86 - 14 * k)], c['tip'], 1.6)
    else:
        Mw = Mu @ T(18, -26) @ R(po.get('wing', 0))
        p.poly(Mw, [(0, 0), (-40, -6), (-74, 12), (-50, 22), (-6, 16)], c['wing'])
        for k in range(3):
            p.line(Mw, [(-30 - 12 * k, 4 + 3 * k), (-56 - 8 * k, 14 + 2 * k)], c['tip'], 1.5)
    return dict(head=Mh, back=Mu @ T(40, -34) if fly else Mu @ T(30, -36))

CR = dict(shell="#d9573a", dark="#9e3324", light="#f08a5a", belly="#f4c69a", spot="#f2b07a")

def draw_crab(p, M, po):
    """little crab, front view, origin at the bottom centre (about 120 wide at scale 1).
    po: t, mouth, blink, look, walk (phase), amp, arm (0 down .. 1 up), claw (0 closed .. 1 open), snap, brow, hop, happy"""
    t = po['t']; ph = po.get('walk', 0); amp = po.get('amp', 0); c = CR
    Mb = M @ T(0, -po.get('hop', 0))
    # legs, 3 per side
    for s_ in (-1, 1):
        for k in range(3):
            wob = 5 * math.sin(ph + k * 2.1 + (s_ > 0) * 1.0) * amp
            x0, y0 = s_ * (22 + 6 * k), -18 + 3 * k
            kx, ky = s_ * (44 + 10 * k), -30 + 6 * k + wob
            fx, fy = s_ * (52 + 12 * k), 0 - abs(wob) * 0.6
            for col, w in ((OUT, 6.4), (c['dark'], 3.8)):
                p.line(Mb, [(x0, y0), (kx, ky), (fx, fy)], col, w)
    # arms + claws
    arm = po.get('arm', 0.3); cl = po.get('claw', 0.3)
    if po.get('snap'): cl = 0.5 + 0.5 * math.sin(t * 22)
    for s_ in (-1, 1):
        Ma = Mb @ T(s_ * 28, -30) @ S(s_, 1) @ R(-20 - 70 * arm + 6 * math.sin(t * 2 + s_))
        for col, w in ((OUT, 8), (c['shell'], 5)):
            p.line(Ma, [(0, 0), (22, -4), (34, -16)], col, w)
        Mc = Ma @ T(36, -20) @ R(-30)
        p.poly(Mc @ R(30 * cl), [(0, 4), (34, 6), (30, 12), (2, 12)], c['dark'], w=2)          # moving finger
        p.poly(Mc, ell(12, -2, 20, 13, 24), c['shell'], w=2.2)
        p.poly(Mc, [(20, -6), (40, -2), (24, 4)], c['shell'], w=2)
        p.poly(Mc, ell(8, -6, 6, 3, 10), c['spot'], outline=None)
    # eye stalks
    blk = po.get('blink', 0); ey = max(0.12, 1 - blk); lx = po.get('look', 0)
    for s_ in (-1, 1):
        sw = 2 * math.sin(t * 2.4 + s_)
        for col, w in ((OUT, 6), (c['shell'], 3.4)):
            p.line(Mb, [(s_ * 10, -40), (s_ * 13 + sw, -64)], col, w)
        ex, eyy = s_ * 13 + sw, -70
        p.poly(Mb, ell(ex, eyy, 8, 8 * ey, 16), "white", w=1.6)
        if ey > 0.3:
            p.poly(Mb, ell(ex + 2.4 * lx, eyy + 0.5, 4, 4.4 * ey, 12), JD, outline=None)
            p.poly(Mb, ell(ex + 2.4 * lx + 1.3, eyy - 1.6, 1.3, 1.3, 6), "white", outline=None)
        bw = po.get('brow', 0)
        p.line(Mb, [(ex - 7 * s_, eyy - 10.5 + 3 * bw), (ex + 6 * s_, eyy - 10.5 - 1 * bw)], c['dark'], 2.6)
    # body (shell)
    p.poly(Mb, ell(0, -26, 40, 22, 40), c['shell'], w=2.8)
    p.poly(Mb, ell(0, -34, 30, 9, 30, 180, 360), c['light'], outline=None)
    for q in ((-18, -34), (16, -36), (0, -42)):
        p.poly(Mb, ell(q[0], q[1], 3.4, 2.4, 10), c['spot'], outline=None)
    # face
    m = po.get('mouth', 0)
    if m > 0.08 or po.get('happy'):
        p.poly(Mb, ell(0, -18, 7 + 2 * m, 2 + 6 * max(m, 0.3 * bool(po.get('happy'))), 16, 0, 180) + [(-7, -18)], "#7a1c14", w=1.5)
    else:
        p.line(Mb, [(-6, -19), (0, -16), (6, -19)], JD, 1.8)
    for s_ in (-1, 1):
        p.poly(Mb, ell(s_ * 18, -20, 4.2, 2.6, 10), "#f6a08a", outline=None)

FISH = [dict(body="#f2a03a", fin="#d9572a", belly="#fbe0a6"), dict(body="#5fa6c9", fin="#2f6db0", belly="#d9eef6"),
        dict(body="#e2b64a", fin="#c8423a", belly="#fff1c4"), dict(body="#d96f9a", fin="#9e3a68", belly="#f8d6e2"),
        dict(body="#8fc06a", fin="#4f7a3a", belly="#e4f2c8")]

def draw_fish(p, M, po, col=0):
    """little fish, facing right, origin at its centre (about 56 long at scale 1).
    po: t, mouth, blink, look, wag (speed), scared, happy"""
    t = po['t']; c = FISH[col % len(FISH)]
    wag = math.sin(t * po.get('wag', 8) + col) * 14
    Mt = M @ T(-20, 0) @ R(wag)
    p.poly(Mt, [(2, 0), (-18, -14), (-14, 0), (-18, 14)], c['fin'], w=2)
    p.poly(M, [(-4, -12), (6, -22), (12, -11)], c['fin'], w=1.8)
    p.poly(M, ell(2, 0, 24, 14, 30), c['body'], w=2.2)
    p.poly(M, ell(6, 5, 15, 6, 20, 0, 180) + [(-9, 5)], c['belly'], outline=None)
    for k in range(2):
        p.line(M, [(-6 + 7 * k, -9), (-9 + 7 * k, 0), (-6 + 7 * k, 9)], c['fin'], 1.4)
    p.poly(M @ T(-2, 6) @ R(20 * math.sin(t * 6 + col)), [(0, 0), (-8, -4), (-8, 4)], c['fin'], w=1.2)
    blk = po.get('blink', 0); ey = max(0.12, 1 - blk); lx = po.get('look', 0.5)
    er = 5.6 + 2.4 * po.get('scared', 0)
    p.poly(M, ell(13, -3, er, er * ey, 16), "white", w=1.4)
    if ey > 0.3:
        p.poly(M, ell(14 + 1.4 * lx, -2.6, 2.8, 3.2 * ey, 12), JD, outline=None)
        p.poly(M, ell(15 + 1.4 * lx, -4.2, 1, 1, 6), "white", outline=None)
    m = po.get('mouth', 0)
    if m > 0.1 or po.get('scared', 0) > 0.5:
        p.poly(M, ell(24, 4, 2.5 + 2 * m, 2 + 3 * m, 10), "#7a1c14", w=1.2)
    elif po.get('happy'):
        p.line(M, [(19, 3), (22, 6), (25, 4)], JD, 1.5)
    else:
        p.line(M, [(20, 4), (25, 4)], JD, 1.5)


# ------------------------------------------------------------------ the two ducks, village children, haystack (Episode 6)
DUCKS = {
    "white": dict(body="#f6f1e4", dark="#d8cfb8", wing="#e6dcc4", tip="#a89c80", head="#f8f4ea", bill="#f0a030",
                  bill2="#d98420", foot="#f0a030", cheek="#f3b0a0", ring=None),
    "brown": dict(body="#c49a6c", dark="#946c44", wing="#a87c52", tip="#6e4c2c", head="#3f8a64", bill="#e8b84a",
                  bill2="#c8962e", foot="#f0a030", cheek=None, ring="#fbf7ee"),
}

def draw_duck(p, M, kind, po):
    """duck cut-out, facing right, origin at the feet (standing, ~100 tall at scale 1) or at the body centre (fly=1).
    po: t, mouth, blink, look, fly (0/1), flap (rad), head (deg, + = down), hop, swim (0/1: no legs), wing (deg), sad, happy, brow.
    Returns dict(head=Mh, bill=matrix at the bill tip, mid=matrix at the middle of the bill)."""
    c = DUCKS[kind]; t = po['t']; fly = po.get('fly', 0); m = po.get('mouth', 0)
    if fly:
        Mb = M @ T(0, 30)
    else:
        Mb = M @ T(0, -po.get('hop', 0))
    br = 1 + 0.03 * math.sin(t * 3 + len(kind))
    Mu = Mb @ T(0, -30) @ R(-6 * fly + po.get('tilt', 0)) @ S(1, br) @ T(0, 30)
    if fly:
        Mw = Mu @ T(2, -40) @ R(-5 - 60 * (1 - math.sin(po.get('flap', 0))))
        p.poly(Mw, [(14, 0), (6, -40), (-14, -82), (-40, -96), (-46, -80), (-30, -40), (-16, -4)], c['dark'])
    if not fly and not po.get('swim'):
        ph = po.get('walk', 0); amp = po.get('amp', 0)
        for jx, s_ in ((-8, 1), (8, -1)):
            Ml = Mb @ T(jx, -16) @ R(28 * amp * math.sin(ph) * s_)
            for col, w in ((OUT, 6), (c['foot'], 3.5)):
                p.line(Ml, [(0, 0), (0, 14)], col, w)
            p.poly(Ml, [(-6, 12), (14, 12), (18, 17), (-6, 17)], c['foot'], w=1.6)
    elif fly:
        for col, w in ((OUT, 5.5), (c['foot'], 3.2)):
            p.line(Mu, [(-30, -22), (-50, -16)], col, w)
    # tail (points up and back)
    p.poly(Mu, [(-30, -40), (-58, -62), (-54, -44), (-34, -24)], c['body'])
    p.line(Mu, [(-36, -38), (-52, -54)], c['tip'], 1.4)
    # body
    p.poly(Mu, ell(0, -34, 42, 22, 40), c['body'])
    p.poly(Mu, ell(4, -24, 30, 9, 28, 0, 180) + [(-26, -24)], c['dark'], outline=None)
    # neck + head
    hd = po.get('head', 0)
    if fly:
        Mh = Mu @ T(50, -46) @ R(hd + 10)
        p.poly(Mu, [(24, -48), (46, -56), (54, -40), (30, -26)], c['head'] if c['ring'] else c['body'])
    else:
        Mh = Mu @ T(30, -74) @ R(hd + 3 * math.sin(t * 1.6))
        p.poly(Mu, [(14, -44), (24, -76), (40, -72), (36, -38)], c['head'] if c['ring'] else c['body'])
    if c['ring']:
        if fly: rp = [(32, -54), (36, -30)]
        else: rp = [(22, -60), (38, -58)]
        p.line(Mu, rp, OUT, 6); p.line(Mu, rp, c['ring'], 3.5)
    # bill: flat, rounded; lower half opens
    p.poly(Mh @ T(10, 2) @ R(16 * m), [(0, 0), (26, 0), (28, 4), (0, 7)], c['bill2'], w=1.6)
    p.poly(Mh, ell(0, -2, 16, 15, 32), c['head'])
    p.poly(Mh, [(10, -6), (34, -4), (38, 0), (34, 4), (10, 3)], c['bill'], w=1.8)
    p.poly(Mh, ell(18, -3, 1.2, 1, 6), OUT, outline=None)
    blk = po.get('blink', 0); ey = max(0.12, 1 - blk); lx = po.get('look', 0); sad = po.get('sad', 0)
    p.poly(Mh, ell(2, -6, 5.6, 6.2 * ey, 16), "white", w=1.4)
    if ey > 0.3:
        p.poly(Mh, ell(3.4 + 1.5 * lx, -5.5, 3.1, 3.7 * ey, 12), JD, outline=None)
        p.poly(Mh, ell(4.4 + 1.5 * lx, -7.4, 1.1, 1.1, 6), "white", outline=None)
    bw = po.get('brow', 0)
    p.line(Mh, [(-4, -14 - 2 * sad + 2 * bw), (8, -14 + 2 * sad - 2 * bw)], OUT, 1.8)
    if c['cheek']: p.poly(Mh, ell(-2, 4, 3.5, 2.2, 10), c['cheek'], outline=None)
    # near wing
    if fly:
        Mw = Mu @ T(-2, -38) @ R(-15 - 62 * (1 - math.sin(po.get('flap', 0))))
        p.poly(Mw, [(16, 0), (8, -44), (-12, -90), (-42, -106), (-50, -88), (-32, -42), (-16, -2)], c['wing'])
        for k in range(3):
            p.line(Mw, [(-6 - 8 * k, -30 - 16 * k), (-22 - 8 * k, -66 - 12 * k)], c['tip'], 1.4)
    else:
        Mw = Mu @ T(16, -40) @ R(po.get('wing', 0))
        p.poly(Mw, [(0, 0), (-30, -6), (-52, 4), (-34, 16), (-2, 12)], c['wing'])
        p.line(Mw, [(-24, 4), (-44, 6)], c['tip'], 1.4); p.line(Mw, [(-18, 9), (-36, 11)], c['tip'], 1.4)
    return dict(head=Mh, bill=Mh @ T(36, 0), mid=Mh @ T(24, 0))

KIDS = {
    "girl": dict(skin="#efc39a", dress="#c8423a", trim="#e2b64a", scarf="#3d6db5", scarf2="#f2c14e", trou="#2f6f6a",
                 shoe="#5e3a1f", hair="#3b2416"),
    "boy": dict(skin="#e3b48a", dress="#3d6db5", trim="#e2b64a", scarf=None, hat="#8a5a33", trou="#6e5a44",
                shoe="#3b2a1a", hair="#2b1a10"),
}

def draw_child(p, M, kind, po):
    """village child, facing right, origin at the feet (~150 tall at scale 1).
    po: t, mouth, blink, look (-1..1), arm (near arm deg: 0 down, -150 up/forward), arm2, head (deg, - = looking up),
        hop, laugh (0..1)"""
    c = KIDS[kind]; t = po['t']; m = po.get('mouth', 0); lg = po.get('laugh', 0)
    Mb = M @ T(0, -po.get('hop', 0))
    Ma2 = Mb @ T(-4, -104) @ R(po.get('arm2', 12) + 3 * math.sin(t * 1.7))
    p.poly(Ma2, [(-6, 0), (6, 0), (5, 42), (-5, 42)], c['dress']); p.poly(Ma2, ell(0, 46, 6.5, 6.5, 12), c['skin'])
    for jx in (-8, 8):
        p.poly(Mb, [(jx - 6, -48), (jx + 6, -48), (jx + 5, -6), (jx - 5, -6)], c['trou'])
        p.poly(Mb, [(jx - 6, -8), (jx + 10, -8), (jx + 12, 0), (jx - 7, 0)], c['shoe'], w=1.5)
    if kind == "girl":
        p.poly(Mb, [(-16, -108), (16, -108), (30, -40), (-28, -40)], c['dress'])
        p.poly(Mb, [(-28, -46), (30, -46), (30, -40), (-28, -40)], c['trim'], w=1.5)
    else:
        p.poly(Mb, [(-18, -108), (18, -108), (22, -50), (-20, -50)], c['dress'])
        p.poly(Mb, [(-20, -74), (21, -74), (22, -66), (-20, -66)], c['trim'], w=1.5)
    for k in range(3):
        p.poly(Mb, khatam(2, -96 + 14 * k, 2.6), c['trim'], outline=None)
    Mh = Mb @ T(2, -124) @ R(po.get('head', 0) + 2 * math.sin(t * 1.4) + 8 * lg * math.sin(t * 9)) @ S(1.22)
    if kind == "girl":
        p.poly(Mh, ell(-4, 4, 25, 29, 30), c['scarf'])                                    # headscarf (back)
    p.poly(Mh, ell(0, 0, 21, 22, 32), c['skin'])
    if kind == "girl":
        p.poly(Mh, ell(-2, -6, 24, 22, 30, 180, 360) + [(22, -4), (12, -12), (-6, -8), (-24, -2)], c['scarf'])
        for k in range(4):
            p.poly(Mh, ell(-16 + 10 * k, -18 + 2 * abs(k - 1.5), 2.2, 2.2, 8), c['scarf2'], outline=None)
        p.poly(Mh, [(-6, -10), (14, -12), (8, -6), (-4, -4)], c['hair'], outline=None)
    else:
        p.poly(Mh, [(-20, -6), (-14, -16), (8, -18), (20, -10), (10, -8), (-6, -6)], c['hair'], outline=None)
        p.poly(Mh, ell(-2, -14, 19, 12, 24, 180, 360) + [(17, -14), (-21, -14)], c['hat'])
        p.poly(Mh, [(-22, -16), (18, -16), (19, -11), (-23, -11)], "#e2b64a", w=1.5)
    p.poly(Mh, ell(-14, 2, 5, 6, 12), c['skin'])                                         # ear
    blk = po.get('blink', 0); ey = max(0.12, 1 - blk); lx = po.get('look', 0)
    if lg > 0.5:
        p.line(Mh, [(4, -2), (9, -6), (14, -2)], JD, 1.8)
    else:
        p.poly(Mh, ell(9, -3, 4.6, 5.4 * ey, 14), "white", w=1.2)
        if ey > 0.3:
            p.poly(Mh, ell(10 + 1.4 * lx, -3 - 1.6 * (lx < -0.5), 2.6, 3.2 * ey, 12), JD, outline=None)
    p.poly(Mh, ell(20, 3, 2.6, 2.2, 8), c['skin'], w=1.2)
    mo = max(m, 0.6 * lg)
    if mo > 0.1:
        p.poly(Mh, ell(12, 11, 4 + 2 * mo, 1.5 + 5 * mo, 14), "#7a1c14", w=1.2)
    else:
        p.line(Mh, [(8, 10), (12, 12), (16, 10)], JD, 1.5)
    p.poly(Mh, ell(2, 8, 4, 2.6, 10), "#e8968a", outline=None)
    Ma = Mb @ T(4, -104) @ R(po.get('arm', 10) + 3 * math.sin(t * 1.9))
    p.poly(Ma, [(-6, 0), (6, 0), (5, 42), (-5, 42)], c['dress'], w=2)
    p.poly(Ma, ell(0, 46, 6.5, 6.5, 12), c['skin'], w=2)
    if po.get('point'): p.poly(Ma, [(-2, 48), (2, 48), (1.5, 60), (-1.5, 60)], c['skin'], w=1.2)

def haystack(p, M, x, base, s=1.0, dent=0.0):
    """golden haystack, origin at its bottom centre. dent: a tortoise-shaped hollow on top (0..1)"""
    V = M @ T(x, base) @ S(s)
    top = [(-150, 0), (-140, -60), (-110, -116), (-60, -150 + 12 * dent), (0, -160 + 22 * dent), (60, -150 + 12 * dent),
           (110, -116), (140, -60), (150, 0)]
    p.poly(V, top, "#e2b64a", w=3)
    p.poly(V, [(-120, -40), (-90, -110), (-40, -138), (-60, -100), (-100, -30)], "#f2cf6a", outline=None)
    for k in range(14):
        a = -150 + k * 22; yy = -20 - 110 * math.sin(math.pi * (k + 0.5) / 14)
        p.line(V, [(a + 6, -6), (a + 12, yy * 0.6), (a + 16, yy * 0.95)], "#b9862a", 1.4)
