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
