#!/usr/bin/env python3
"""Long-form Rumi video for YouTube (The Guest House): narration + music + a timeline the Remotion scene reads.

usage: python3 longform/build_audio.py longform/specs/lfNN_x.json
writes longform/remotion/public/<id>/audio.wav and timeline.json

Timeline events (seconds): intro / chapter / fa / en / tafsir / breath / outro, each {kind, t0, t1, ...}.
Narrator and music are the page's approved ones (guesthouse/make_reel_cinematic.py: narrate(), music()).
Per poem: chapter card -> each line: the Persian appears and is "heard" in music for a moment, then the
English is read -> a pause -> tafsir sentences -> a breath of music with the Persian shown again.
"""
import os, sys, json, wave
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "guesthouse"))
import make_reel_cinematic as MC
SR = MC.SR

def say(text):
    a = MC.narrate(text)
    if a is None: raise SystemExit("TTS not available (Kokoro model missing)")
    return a

def build(spec_path):
    spec = json.load(open(spec_path, encoding="utf-8"))
    out = os.path.join(HERE, "remotion", "public", spec["id"]); os.makedirs(out, exist_ok=True)
    ev, clips = [], []                     # timeline events, (t, audio)
    t = 2.0
    def speak(kind, text, gap, **kw):
        nonlocal t
        a = say(text); clips.append((t, a))
        ev.append(dict(kind=kind, t0=round(t, 3), t1=round(t + len(a) / SR, 3), text=text, **kw))
        t += len(a) / SR + gap
    ev.append(dict(kind="title", t0=0.0, t1=0.0, text=spec["title"], sub=spec["subtitle"], fa=spec["fa_title"]))
    for s in spec["intro"]: speak("intro", s, 0.6)
    ev[0]["t1"] = round(t, 3); t += 1.5
    sections = []                          # (start, end) per poem for the music
    for i, p in enumerate(spec["poems"]):
        s0 = t
        ev.append(dict(kind="chapter", t0=round(t, 3), t1=round(t + 4.0, 3), n=i + 1, name=p["name"], source=p["source"]))
        t += 4.5
        for k, ln in enumerate(p["lines"]):
            fa_t0 = t
            t += 2.6                       # the Persian sits on screen with the music first
            a = say(ln["en"]); clips.append((t, a)); en_t0 = t; t += len(a) / SR + 0.9
            ev.append(dict(kind="line", t0=round(fa_t0, 3), t1=round(t, 3), en_t0=round(en_t0, 3), fa=ln["fa"], en=ln["en"],
                           poem=i, k=k))
        t += 1.2
        for j, s in enumerate(p["tafsir"]):
            speak("tafsir", s, 0.45, poem=i, first=(j == 0))
        t += 0.6
        ev.append(dict(kind="breath", t0=round(t, 3), t1=round(t + 7.0, 3), fa=[l["fa"] for l in p["lines"]], source=p["source"]))
        t += 7.5
        sections.append((s0, t))
    o0 = t
    for s in spec["outro"]: speak("outro", s, 0.5)
    t += 3.0
    ev.append(dict(kind="end", t0=round(o0, 3), t1=round(t, 3)))
    dur = t
    N = int(dur * SR); voice = np.zeros(N)
    for t0, a in clips:
        i = int(t0 * SR); voice[i:i + len(a)] += a[:N - i]
    # music: one bed per poem (different seeds) + intro/outro beds; each bed fades itself in/out, overlapping 2.5 s
    from scipy.ndimage import gaussian_filter
    bounds = [(0.0, sections[0][0])] + sections + [(sections[-1][1], dur)]
    bed = np.zeros(N); ov = 2.5
    for k, (a0, a1) in enumerate(bounds):
        i0 = max(0, int((a0 - (ov if k else 0)) * SR)); i1 = min(N, int((a1 + (ov if k < len(bounds) - 1 else 0)) * SR))
        m = MC.music((i1 - i0) / SR, spec["seed"] + k, None)[:i1 - i0]
        bed[i0:i0 + len(m)] += m
    act = gaussian_filter(np.abs(voice), 0.25 * SR)
    act = np.clip(act / (act.max() * 0.15 + 1e-9), 0, 1)
    act = gaussian_filter(act, 0.15 * SR)
    mix = bed * (1 - 0.68 * act) * 0.85 + voice
    mix = mix / max(1.0, np.abs(mix).max() / 0.95)
    mix = np.clip(mix, -1, 1)
    with wave.open(os.path.join(out, "audio.wav"), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((mix * 32767).astype(np.int16).tobytes())
    json.dump({"id": spec["id"], "duration": round(dur, 3), "fps": 30, "events": ev}, open(os.path.join(out, "timeline.json"), "w"),
              ensure_ascii=False, indent=1)
    print(out, round(dur, 1), "s")

if __name__ == "__main__":
    build(sys.argv[1])
