#!/usr/bin/env python3
"""English .srt for the YouTube full-episode video (same timing as the burned-in captions).

usage: python3 podcast/make_srt.py N   ->  podcast/video/epNN.en.srt
Upload: python3 ops/yt.py caption <video_id> en podcast/video/epNN.en.srt English
"""
import os, sys, json
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import make_video as MV

def ts(t):
    h, r = divmod(t, 3600); m, s = divmod(r, 60)
    return "%02d:%02d:%02d,%03d" % (h, m, int(s), int(round((s % 1) * 1000)) % 1000)

def main(n):
    ep = json.load(open(os.path.join(HERE, "episodes", f"ep{n:02d}.json")))
    tm = MV.timing(ep)
    out = os.path.join(HERE, "video", f"ep{n:02d}.en.srt"); os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        for i, (a, b, text, _) in enumerate(MV.cues([tuple(x) for x in tm["timeline"]], 84), 1):
            f.write(f"{i}\n{ts(a)} --> {ts(b)}\n{text.replace(chr(92) + 'N', chr(10))}\n\n")
    print(out)

if __name__ == "__main__":
    main(int(sys.argv[1]))
