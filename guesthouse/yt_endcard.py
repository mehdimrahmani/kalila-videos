#!/usr/bin/env python3
"""YouTube-only copy of a Guest House Reel with a subscribe call-to-action over the outro.
The Instagram Reel itself is never changed: the output goes to a separate (temp) file.

usage: python3 guesthouse/yt_endcard.py REEL.mp4 SPEC.json OUT.mp4
Part reels ("Shams & Rumi · Part N"): "Part N+1 is coming" + "Subscribe to follow the story".
Other (echo) reels: "The story of Shams & Rumi" + "Subscribe to follow the story".
"""
import sys, os, re, json, subprocess, tempfile
from PIL import Image, ImageDraw, ImageFont, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
SERIF = "/usr/share/fonts/truetype/freefont/FreeSerif.ttf"
SERIF_I = "/usr/share/fonts/truetype/freefont/FreeSerifItalic.ttf"
if not os.path.exists(SERIF):
    SERIF = SERIF_I = "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf"
GOLD = (214, 178, 106)

def card(line1, line2, path):
    W, H = 1080, 360
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    f1, f2 = ImageFont.truetype(SERIF_I, 50), ImageFont.truetype(SERIF, 44)
    # line 1: italic, warm white
    w1 = d.textlength(line1, font=f1); d.text(((W - w1) / 2, 40), line1, font=f1, fill=(250, 240, 220, 255))
    # line 2: in a gold-outlined pill with a small red "play" mark, like a subscribe button
    w2 = d.textlength(line2, font=f2); pw, ph = w2 + 140, 96
    x0, y0 = (W - pw) / 2, 150
    d.rounded_rectangle([x0, y0, x0 + pw, y0 + ph], radius=48, fill=(12, 8, 30, 200), outline=GOLD + (255,), width=4)
    cx, cy = x0 + 52, y0 + ph / 2
    d.rounded_rectangle([cx - 24, cy - 17, cx + 24, cy + 17], radius=9, fill=(204, 32, 32, 255))
    d.polygon([(cx - 7, cy - 10), (cx - 7, cy + 10), (cx + 11, cy)], fill=(255, 255, 255, 255))
    d.text((x0 + 92, y0 + 22), line2, font=f2, fill=GOLD + (255,))
    glow = im.filter(ImageFilter.GaussianBlur(10)); glow.putalpha(glow.getchannel("A").point(lambda a: a * 0.5))
    out = Image.alpha_composite(glow, im); out.save(path)

def light_outro(reel, dur):
    """True if the Reel's final frames are light (parchment design): the white line 1 would be unreadable
    and would collide with the Reel's own outro text, so only the subscribe pill is drawn."""
    fr = os.path.join(tempfile.mkdtemp(), "f.png")
    subprocess.check_call(["ffmpeg", "-v", "error", "-y", "-ss", f"{max(0, dur - 1.0):.2f}", "-i", reel,
                           "-frames:v", "1", fr])
    im = Image.open(fr).convert("L"); w, h = im.size
    band = im.crop((int(w * .15), int(h * .69), int(w * .85), int(h * .74)))
    return sum(band.getdata()) / (band.size[0] * band.size[1]) > 140

def main(reel, spec_path, out):
    spec = json.load(open(spec_path, encoding="utf-8"))
    m = re.search(r"Part\s+(\d+)", spec.get("header", ""))
    line1 = f"Part {int(m.group(1)) + 1} is coming" if m else "The story of Shams & Rumi"
    dur = float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                                         "-of", "csv=p=0", reel]).decode())
    if light_outro(reel, dur):   # parchment-style Reels: their own outro text sits where line 1 would go
        line1 = ""
    png = os.path.join(tempfile.mkdtemp(), "cta.png"); card(line1, "Subscribe to follow the story", png)
    t0 = max(0.0, dur - 3.0)
    flt = (f"[1:v]format=rgba,fade=t=in:st={t0:.2f}:d=0.6:alpha=1[c];"
           f"[0:v][c]overlay=0:H*0.69:enable='gte(t,{t0:.2f})'[v]")
    subprocess.check_call(["ffmpeg", "-v", "error", "-y", "-i", reel, "-loop", "1", "-t", f"{dur:.2f}", "-i", png,
                           "-filter_complex", flt, "-map", "[v]", "-map", "0:a", "-c:v", "libx264", "-crf", "19",
                           "-preset", "medium", "-pix_fmt", "yuv420p", "-c:a", "copy", "-movflags", "+faststart", out])
    print(out, round(dur, 2), line1)

if __name__ == "__main__":
    main(*sys.argv[1:4])
