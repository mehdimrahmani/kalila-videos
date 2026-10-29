#!/usr/bin/env python3
"""Cut a near-full-screen vertical 1080x1920 YouTube Short from an episode, with big burned-in English
captions (many people watch Shorts muted) and a hook question on screen from the first frame.

usage: make_short.py SRC.mp4 START DUR "Hook question?" "Story name" OUT.mp4 [SRC.en.srt]
  - the episode is zoomed so the action fills the middle of the screen (centre 72% of the width),
    over a blurred copy of itself (no empty bars)
  - captions come from the episode's .en.srt (default: SRC with .en.srt), shifted to the clip;
    speaker names ("DIMNA:") are dropped
  - last 2.5 s: "Full story on our channel"
"""
import sys, os, re, subprocess, tempfile
from PIL import Image, ImageDraw, ImageFont

FB = "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf"
FI = "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Italic.ttf"
W, H = 1080, 1920
FG_W, FG_H, FG_Y = 1778, 1000, 500         # zoomed episode: 1778x1000, centre 61% of the width kept

def ts(t):
    h = int(t // 3600); m = int(t % 3600 // 60); s = t % 60
    return f"{h}:{m:02d}:{s:05.2f}"

def srt_cues(path):
    txt = open(path, encoding="utf-8").read().replace("\r", "")
    out = []
    for block in re.split(r"\n\s*\n", txt.strip()):
        lines = block.split("\n")
        if len(lines) < 3 or "-->" not in lines[1]: continue
        a, b = [x.strip() for x in lines[1].split("-->")]
        tt = lambda x: int(x[:2]) * 3600 + int(x[3:5]) * 60 + float(x[6:].replace(",", "."))
        text = " ".join(lines[2:]).strip()
        text = re.sub(r"^[A-Z][A-Z .']{1,20}:\s*", "", text)        # drop "OLD TORTOISE: "
        out.append((tt(a), tt(b), text))
    return out

def split_cue(a, b, text, maxw=34):
    """Split a long cue into short 1-2 line chunks timed by length."""
    words = text.split(); chunks, cur = [], ""
    for w in words:
        if len(cur) + len(w) + 1 > 50 and cur:
            chunks.append(cur); cur = w
        else:
            cur = (cur + " " + w).strip()
    if cur: chunks.append(cur)
    total = sum(len(c) for c in chunks); t = a; res = []
    for c in chunks:
        d = (b - a) * len(c) / total; res.append((t, t + d, c)); t += d
    return res

def ass_file(cues, start, dur, path):
    head = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {W}
PlayResY: {H}
WrapStyle: 0

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Cap,DejaVu Sans,62,&H00FFFFFF,&H00FFFFFF,&H00141414,&H64000000,1,0,0,0,100,100,0,0,1,5,2,2,70,70,250,1
Style: Key,DejaVu Sans,62,&H0050D7FF,&H0050D7FF,&H00141414,&H64000000,1,0,0,0,100,100,0,0,1,5,2,2,70,70,330,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    ev = []
    for a, b, text in cues:
        end = start + max(0.5, dur - 2.6)                      # no captions under the end card
        if b <= start or a >= end: continue
        for ca, cb, c in split_cue(max(a, start), min(b, end), text):
            ev.append(f"Dialogue: 0,{ts(ca - start)},{ts(cb - start)},Cap,,0,0,0,,{{\\fad(80,80)}}{c}")
    open(path, "w", encoding="utf-8").write(head + "\n".join(ev) + "\n")

def overlay_png(hook, story, path):
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    # dark gradient panels top and bottom so text is always readable
    for y in range(0, FG_Y):
        d.line([(0, y), (W, y)], fill=(8, 14, 30, int(235 * (1 - (y / FG_Y) ** 3))))
    for y in range(FG_Y + FG_H - 40, H):
        a = min(1, (y - (FG_Y + FG_H - 40)) / 160)
        d.line([(0, y), (W, y)], fill=(8, 14, 30, int(225 * a)))
    def ct(t, y, font, size, fill, stroke=3, maxw=W - 90):
        f = ImageFont.truetype(font, size)
        while d.textlength(t, font=f) > maxw and size > 60:
            size -= 3; f = ImageFont.truetype(font, size)
        # wrap into two lines if still too long
        lines = [t]
        if d.textlength(t, font=f) > maxw:
            words = t.split(); best = None
            for i in range(1, len(words)):
                l1, l2 = " ".join(words[:i]), " ".join(words[i:])
                m = max(d.textlength(l1, font=f), d.textlength(l2, font=f))
                if best is None or m < best[0]: best = (m, [l1, l2])
            lines = best[1]
        for k, ln in enumerate(lines):
            wv = d.textlength(ln, font=f)
            d.text(((W - wv) / 2, y + k * size * 1.15), ln, font=f, fill=fill, stroke_width=stroke, stroke_fill=(20, 12, 4))
        return y + len(lines) * size * 1.15
    ct("KALILA & DIMNA", 95, FB, 46, (226, 182, 74))
    y = ct(hook, 170, FB, 76, (255, 255, 255), 4)
    ct(story, y + 18, FI, 44, (226, 182, 74), 2)
    # thin gold frame lines around the clip
    d.rectangle([0, FG_Y - 6, W, FG_Y - 1], fill=(212, 166, 60, 255))
    d.rectangle([0, FG_Y + FG_H + 1, W, FG_Y + FG_H + 6], fill=(212, 166, 60, 255))
    im.save(path)

def end_png(path):
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.rounded_rectangle([110, 1470, W - 110, 1700], 40, fill=(212, 166, 60, 245))
    for k, (t, y) in enumerate((("Watch the full story", 1500), ("on our channel  ▶", 1590))):
        f = ImageFont.truetype(FB, 60); wv = d.textlength(t, font=f)
        d.text(((W - wv) / 2, y), t, font=f, fill=(20, 30, 60))
    im.save(path)

def main():
    src, st, du, hook, story, out = sys.argv[1], float(sys.argv[2]), float(sys.argv[3]), sys.argv[4], sys.argv[5], sys.argv[6]
    srt = sys.argv[7] if len(sys.argv) > 7 else os.path.splitext(src)[0] + ".en.srt"
    tmp = tempfile.mkdtemp()
    ov, en, ass = os.path.join(tmp, "ov.png"), os.path.join(tmp, "end.png"), os.path.join(tmp, "cap.ass")
    overlay_png(hook, story, ov); end_png(en)
    ass_file(srt_cues(srt) if os.path.exists(srt) else [], st, du, ass)
    fo = du - 0.5; e0 = max(0.0, du - 2.5)
    fc = (f"[0:v]split[a][b];"
          f"[a]scale=-2:{H},crop={W}:{H},boxblur=28:2,eq=brightness=-0.18:saturation=0.8[bg];"
          f"[b]scale={FG_W}:{FG_H},crop={W}:{FG_H}[fg];"
          f"[bg][fg]overlay=0:{FG_Y}[v1];[v1][1:v]overlay=0:0[v2];"
          f"[v2]subtitles='{ass}'[v3];"
          f"[2:v]format=rgba,fade=t=in:st={e0}:d=0.4:alpha=1[endo];[v3][endo]overlay=0:0:enable='gte(t,{e0})'[v4];"
          f"[v4]fade=t=in:st=0:d=0.25,fade=t=out:st={fo}:d=0.5[o];"
          f"[0:a]afade=t=in:st=0:d=0.2,afade=t=out:st={fo}:d=0.5[aud]")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", str(st), "-t", str(du), "-i", src,
                    "-loop", "1", "-t", str(du), "-i", ov, "-loop", "1", "-t", str(du), "-i", en,
                    "-filter_complex", fc, "-map", "[o]", "-map", "[aud]", "-c:v", "libx264", "-crf", "20",
                    "-pix_fmt", "yuv420p", "-r", "24", "-c:a", "aac", "-b:a", "160k", "-shortest",
                    "-movflags", "+faststart", out], check=True)
    print(out)

if __name__ == "__main__":
    main()
