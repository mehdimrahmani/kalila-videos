#!/usr/bin/env python3
"""The Honest Historian — weekly English podcast from the History of Beyhaqi (Tarikh-e Beyhaqi).

Pipeline: episode script (podcast/episodes/epNN.json) -> Kokoro TTS (am_onyx, English)
-> FreeVC voice conversion to Mehdi's voice (stored speaker embedding, no raw recording in the repo)
-> Shur-mode music intro/outro -> loudness -16 LUFS -> docs/podcast/episodes/epNN.mp3
-> docs/podcast/episodes.json -> docs/podcast/feed.xml (+ index.html). Served by GitHub Pages (main /docs).

usage: python3 podcast/make_podcast.py podcast/episodes/ep01.json      # render + publish one episode
       python3 podcast/make_podcast.py --feed                           # rebuild feed/index only
Model files (downloaded automatically from GitHub releases if missing, git-ignored):
  podcast/models/freevc24/{model.pth,config.json}   coqui-ai/TTS v0.13.0_models freevc24 (MIT)
  Kokoro: guesthouse/tts or pipeline/tts kokoro-v1.0.onnx + voices-v1.0.bin
Deps: pip install --break-system-packages torch torchaudio "coqui-tts[codec]" kokoro-onnx soundfile scipy
"""
import os, sys, json, re, subprocess, tempfile, zipfile, datetime, email.utils, html, shutil
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
PUB = os.path.join(REPO, "docs", "podcast")
BASE_URL = "https://mehdimrahmani.github.io/kalila-videos/podcast"
SR = 24000
SHOW = {
    "title": "The Honest Historian: Stories from Beyhaqi",
    "author": "Mehdi Rahmani",
    "email": "mehdimrahmani@yahoo.com",
    "language": "en",
    "category": "History",
    "explicit": "false",
    "description": (
        "A thousand years ago, a court secretary in Ghazni named Abolfazl Beyhaqi wrote down what he saw — "
        "kings, viziers, plots and courage — and promised to tell only the truth. "
        "Each week, Mehdi Rahmani retells one of his stories in English, straight from the Persian original. "
        "Narrated with an AI rendering of Mehdi's own voice."),
}

# ------------------------------------------------------------------ models
def freevc_dir():
    d = os.path.join(HERE, "models", "freevc24")
    if not os.path.exists(os.path.join(d, "model.pth")):
        os.makedirs(d, exist_ok=True)
        z = os.path.join(tempfile.mkdtemp(), "fvc.zip")
        subprocess.run(["curl", "-sSL", "-o", z, "https://github.com/coqui-ai/TTS/releases/download/v0.13.0_models/"
                        "voice_conversion_models--multilingual--vctk--freevc24.zip"], check=True)
        with zipfile.ZipFile(z) as f:
            for n in f.namelist():
                if n.endswith(("model.pth", "config.json")) and "__MACOSX" not in n:
                    with f.open(n) as src, open(os.path.join(d, os.path.basename(n)), "wb") as dst:
                        shutil.copyfileobj(src, dst)
    return d

def kokoro():
    from kokoro_onnx import Kokoro
    for d in (os.path.join(REPO, "guesthouse", "tts"), os.path.join(REPO, "pipeline", "tts"), "/home/claude/kalila_test/tts"):
        m, v = os.path.join(d, "kokoro-v1.0.onnx"), os.path.join(d, "voices-v1.0.bin")
        if os.path.exists(m) and os.path.exists(v):
            return Kokoro(m, v)
    d = os.path.join(REPO, "guesthouse", "tts"); os.makedirs(d, exist_ok=True)
    for f in ("kokoro-v1.0.onnx", "voices-v1.0.bin"):
        subprocess.run(["curl", "-sSL", "-o", os.path.join(d, f),
                        f"https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/{f}"], check=True)
    return Kokoro(os.path.join(d, "kokoro-v1.0.onnx"), os.path.join(d, "voices-v1.0.bin"))

class Voice:
    """English TTS in Kokoro am_onyx, converted to Mehdi's timbre with FreeVC."""
    def __init__(self):
        import torch
        from TTS.config import load_config
        from TTS.vc.models.freevc import FreeVC
        d = freevc_dir()
        cfg = load_config(os.path.join(d, "config.json"))
        self.m = FreeVC.init_from_config(cfg); self.m.load_checkpoint(cfg, os.path.join(d, "model.pth"), eval=True)
        self.se = torch.from_numpy(np.load(os.path.join(HERE, "voice", "mehdi_freevc24_se.npy")))
        self.k = kokoro(); self.torch = torch

    def say(self, text):
        import librosa
        a, r = self.k.create(text, voice="am_onyx", speed=0.9, lang="en-us")
        a16 = librosa.resample(np.asarray(a, np.float32), orig_sr=r, target_sr=16000)
        with self.torch.inference_mode():
            wav = self.torch.from_numpy(a16).float().unsqueeze(0)
            c = self.m.extract_wavlm_features(wav)
            out = self.m.inference(c, g=self.se)
        y = out[0][0].data.cpu().float().numpy()
        return y / (np.abs(y).max() + 1e-9) * 0.9          # 24 kHz

def chunks(par, maxlen=320):
    """Split a paragraph into sentence groups short enough for Kokoro."""
    sents = re.split(r"(?<=[.!?…])\s+", par.strip()); out, cur = [], ""
    for s in sents:
        if len(cur) + len(s) + 1 > maxlen and cur:
            out.append(cur); cur = s
        else:
            cur = (cur + " " + s).strip()
    if cur: out.append(cur)
    return out

# ------------------------------------------------------------------ music
def music_bed(dur, seed):
    sys.path.insert(0, os.path.join(REPO, "guesthouse"))
    import make_reel_cinematic as R
    y = R.music(dur, seed, None)                         # 44.1 kHz
    import librosa
    return librosa.resample(np.asarray(y, np.float32), orig_sr=R.SR, target_sr=SR)

# ------------------------------------------------------------------ render
def render(ep):
    v = Voice()
    parts = []
    sil = lambda s: np.zeros(int(s * SR), np.float32)
    for i, par in enumerate(ep["paragraphs"]):
        if par.strip() == "---":
            parts.append(sil(1.4)); continue
        for c in chunks(par):
            parts.append(v.say(c)); parts.append(sil(0.28))
        parts.append(sil(0.55))
        print(f"  paragraph {i + 1}/{len(ep['paragraphs'])}", flush=True)
    voice = np.concatenate(parts)
    INTRO, OUTRO = 7.0, 9.0
    total = INTRO + len(voice) / SR + OUTRO
    intro = music_bed(INTRO + 4.0, ep.get("n", 1))[: int((INTRO + 4.0) * SR)]
    outro = music_bed(OUTRO + 3.0, ep.get("n", 1) + 50)[: int((OUTRO + 3.0) * SR)]
    mix = np.zeros(int(total * SR) + SR, np.float32)
    # intro music, fading under the first words
    env = np.ones(len(intro)); f0 = int(INTRO * SR); env[f0:] = np.linspace(1, 0, len(intro) - f0)
    mix[: len(intro)] += intro * env * 0.5
    v0 = int(INTRO * SR); mix[v0: v0 + len(voice)] += voice
    # outro music rising after the last words
    o0 = v0 + len(voice) - int(3.0 * SR)
    env = np.ones(len(outro)); env[: int(3.0 * SR)] = np.linspace(0, 1, int(3.0 * SR))
    mix[o0: o0 + len(outro)] += outro * env * 0.5
    mix = mix[: o0 + len(outro)]
    tmp = tempfile.mkdtemp(); wav = os.path.join(tmp, "ep.wav")
    import soundfile as sf
    sf.write(wav, mix / (np.abs(mix).max() + 1e-9) * 0.95, SR)
    os.makedirs(os.path.join(PUB, "episodes"), exist_ok=True)
    out = os.path.join(PUB, "episodes", f"ep{ep['n']:02d}.mp3")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", wav, "-af", "highpass=f=60,loudnorm=I=-16:TP=-1.5:LRA=11",
                    "-ar", "44100", "-ac", "1", "-b:a", "128k", "-id3v2_version", "3",
                    "-metadata", f"title={ep['title']}", "-metadata", f"artist={SHOW['author']}",
                    "-metadata", f"album={SHOW['title']}", out], check=True)
    return out

def duration(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path],
                       capture_output=True, text=True)
    return float(r.stdout.strip())

# ------------------------------------------------------------------ feed
def build_feed():
    eps = json.load(open(os.path.join(PUB, "episodes.json"), encoding="utf-8")) if os.path.exists(os.path.join(PUB, "episodes.json")) else []
    eps = sorted(eps, key=lambda e: e["n"], reverse=True)
    now = email.utils.format_datetime(datetime.datetime.now(datetime.timezone.utc))
    x = html.escape
    items = []
    for e in eps:
        d = int(e["duration"])
        items.append(f"""    <item>
      <title>{x(e['title'])}</title>
      <description>{x(e['description'])}</description>
      <itunes:summary>{x(e['description'])}</itunes:summary>
      <enclosure url="{BASE_URL}/episodes/ep{e['n']:02d}.mp3" length="{e['bytes']}" type="audio/mpeg"/>
      <guid isPermaLink="false">honest-historian-ep{e['n']:02d}</guid>
      <pubDate>{e['pubDate']}</pubDate>
      <itunes:duration>{d // 3600:02d}:{d % 3600 // 60:02d}:{d % 60:02d}</itunes:duration>
      <itunes:episode>{e['n']}</itunes:episode>
      <itunes:episodeType>full</itunes:episodeType>
      <itunes:explicit>false</itunes:explicit>
    </item>""")
    feed = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd" xmlns:atom="http://www.w3.org/2005/Atom" xmlns:podcast="https://podcastindex.org/namespace/1.0">
  <channel>
    <title>{x(SHOW['title'])}</title>
    <link>{BASE_URL}/</link>
    <atom:link href="{BASE_URL}/feed.xml" rel="self" type="application/rss+xml"/>
    <language>{SHOW['language']}</language>
    <copyright>Mehdi Rahmani</copyright>
    <description>{x(SHOW['description'])}</description>
    <itunes:summary>{x(SHOW['description'])}</itunes:summary>
    <itunes:author>{x(SHOW['author'])}</itunes:author>
    <itunes:owner><itunes:name>{x(SHOW['author'])}</itunes:name><itunes:email>{SHOW['email']}</itunes:email></itunes:owner>
    <itunes:image href="{BASE_URL}/cover.jpg"/>
    <image><url>{BASE_URL}/cover.jpg</url><title>{x(SHOW['title'])}</title><link>{BASE_URL}/</link></image>
    <itunes:category text="History"/>
    <itunes:explicit>false</itunes:explicit>
    <itunes:type>episodic</itunes:type>
    <lastBuildDate>{now}</lastBuildDate>
{chr(10).join(items)}
  </channel>
</rss>
"""
    open(os.path.join(PUB, "feed.xml"), "w", encoding="utf-8").write(feed)
    li = "\n".join(f'<li><b>Episode {e["n"]}: {x(e["title"])}</b><br>{x(e["description"])}<br>'
                   f'<audio controls preload="none" src="episodes/ep{e["n"]:02d}.mp3"></audio></li>' for e in eps)
    page = f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{x(SHOW['title'])}</title><link rel="alternate" type="application/rss+xml" href="feed.xml">
<style>body{{font-family:Georgia,serif;background:#141a33;color:#efe6d2;max-width:720px;margin:40px auto;padding:0 16px;line-height:1.6}}
a{{color:#d6b26a}}img{{width:220px;border-radius:8px}}li{{margin:22px 0}}audio{{width:100%;margin-top:6px}}</style></head>
<body><img src="cover.jpg" alt=""><h1>{x(SHOW['title'])}</h1><p>{x(SHOW['description'])}</p>
<p>RSS: <a href="feed.xml">{BASE_URL}/feed.xml</a></p><ul>{li}</ul></body></html>"""
    open(os.path.join(PUB, "index.html"), "w", encoding="utf-8").write(page)

def publish(ep, mp3):
    path = os.path.join(PUB, "episodes.json")
    eps = json.load(open(path, encoding="utf-8")) if os.path.exists(path) else []
    eps = [e for e in eps if e["n"] != ep["n"]]
    pub = ep.get("pubDate") or email.utils.format_datetime(datetime.datetime.now(datetime.timezone.utc))
    eps.append({"n": ep["n"], "title": ep["title"], "description": ep["description"], "pubDate": pub,
                "duration": duration(mp3), "bytes": os.path.getsize(mp3)})
    json.dump(eps, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    build_feed()

if __name__ == "__main__":
    if sys.argv[1] == "--feed":
        build_feed()
    else:
        ep = json.load(open(sys.argv[1], encoding="utf-8"))
        mp3 = render(ep)
        print(mp3, round(duration(mp3), 1), "s")
        if "--no-publish" not in sys.argv:
            publish(ep, mp3)
