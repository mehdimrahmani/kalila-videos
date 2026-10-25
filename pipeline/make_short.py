#!/usr/bin/env python3
"""Cut a vertical 1080x1920 YouTube Short from an episode.
usage: make_short.py SRC.mp4 START DUR "Big title" "Story name" OUT.mp4"""
import sys, os, subprocess, tempfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from kd_lib import *
from PIL import Image, ImageDraw, ImageFont
src, st, du, title, story, out = sys.argv[1], float(sys.argv[2]), float(sys.argv[3]), sys.argv[4], sys.argv[5], sys.argv[6]
Wv, Hv = 1080, 1920
im = Image.new('RGBA', (Wv * 2, Hv * 2), (21, 48, 90, 255)); p = Pen(im); M = S(2)
for yy in range(0, Hv + 120, 120):
    for xx in range(0, Wv + 120, 120):
        ox = 60 if (yy // 120) % 2 else 0
        p.poly(M, khatam(xx + ox, yy, 34), None, outline=(36, 70, 122, 255), w=2)
d = ImageDraw.Draw(im)
def ct(t, y, font, size, fill, stroke=0):
    f = ImageFont.truetype(font, size * 2); l, tp, r, b = d.textbbox((0, 0), t, font=f, stroke_width=stroke * 2)
    while r - l > (Wv - 80) * 2 and size > 20:
        size -= 4; f = ImageFont.truetype(font, size * 2); l, tp, r, b = d.textbbox((0, 0), t, font=f, stroke_width=stroke * 2)
    d.text(((Wv * 2 - (r - l)) // 2 - l, y * 2), t, font=f, fill=fill, stroke_width=stroke * 2, stroke_fill=(40, 22, 8, 255))
ct("KALILA & DIMNA", 250, FB, 70, (226, 182, 74, 255), 2)
ct(title, 370, FB, 62, (250, 240, 214, 255), 2)
ct(story, 470, FI, 46, (226, 182, 74, 255))
ct("Watch the full story", 1440, FI, 46, (250, 240, 214, 255))
ct("on our channel", 1505, FI, 46, (250, 240, 214, 255))
p.poly(M @ T(Wv / 2, 1690), khatam(0, 0, 60), "#d4a63c", outline="#8a6418", w=2)
p.poly(M @ T(Wv / 2, 1690), khatam(0, 0, 42, 22.5), "#1d3f73", outline="#d4a63c", w=2)
d.rectangle([0, (656 - 8) * 2, Wv * 2, (656 + 608 + 8) * 2], fill=(212, 166, 60, 255))
bg = os.path.join(tempfile.mkdtemp(), "bg.png")
im.convert('RGB').resize((Wv, Hv), Image.LANCZOS).save(bg)
fo = du - 0.5
subprocess.run(["ffmpeg", "-v", "error", "-y", "-loop", "1", "-i", bg, "-ss", str(st), "-t", str(du), "-i", src,
    "-filter_complex", f"[1:v]scale=1080:608[v];[0:v][v]overlay=0:656:shortest=1,fade=t=in:st=0:d=0.3,fade=t=out:st={fo}:d=0.5[o];"
    f"[1:a]afade=t=in:st=0:d=0.2,afade=t=out:st={fo}:d=0.5[a]",
    "-map", "[o]", "-map", "[a]", "-c:v", "libx264", "-crf", "20", "-pix_fmt", "yuv420p", "-r", "24",
    "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", out], check=True)
print(out)
