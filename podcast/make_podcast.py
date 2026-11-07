#!/usr/bin/env python3
"""The Honest Historian — weekly English podcast from the History of Beyhaqi (Tarikh-e Beyhaqi).

Pipeline: episode script (podcast/episodes/epNN.json) -> Kokoro TTS (am_onyx, English)
-> FreeVC voice conversion to Mehdi's voice (stored speaker embedding, no raw recording in the repo)
-> Shur-mode music intro/outro -> loudness -16 LUFS -> docs/podcast/episodes/epNN.mp3
-> docs/podcast/episodes.json -> docs/podcast/feed.xml (+ index.html). Served by GitHub Pages (main /docs).

usage: python3 podcast/make_podcast.py podcast/episodes/ep01.json      # render + publish one episode
       (with "release": "YYYY-MM-DD HH:MM" Tehran time in the episode JSON it is queued and goes live then)
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
def ambience(n_samples, seed=5):
    """Soft night wind: slowly breathing low-passed noise."""
    from scipy.signal import butter, sosfilt
    rng = np.random.default_rng(seed); t = np.arange(n_samples) / SR
    w = sosfilt(butter(2, [150, 900], "bandpass", fs=SR, output="sos"), rng.standard_normal(n_samples))
    w *= 0.55 + 0.45 * np.sin(2 * np.pi * 0.07 * t + 1.3) * np.sin(2 * np.pi * 0.023 * t)
    return (w / (np.abs(w).max() + 1e-9)).astype(np.float32)

def render(ep):
    """Structure (modelled on narrative history podcasts such as Gazette):
    cold open (one striking line over night wind) -> theme music swell -> narration over a soft
    continuous Shur-mode bed (never dead silence) -> 14 s musical interlude at every '---' -> outro swell."""
    v = Voice()
    sil = lambda s: np.zeros(int(s * SR), np.float32)
    lay = []                                  # (start_sec, audio) voice clips
    timeline = []                             # (start, end, text, section) for video captions/chapters
    section = 0
    marks = []                                # (start, end, kind) for the music envelope
    t = 0.8
    if ep.get("cold_open"):
        for c in chunks(ep["cold_open"]):
            y = v.say(c); lay.append((t, y)); timeline.append((t, t + len(y) / SR, c, -1)); t += len(y) / SR + 0.35
        marks.append((0.0, t + 0.6, "cold"))
        t += 1.0
    t_theme = t; t += 9.0                     # theme swell, then voice enters over its tail
    marks.append((t_theme, t, "theme"))
    for i, par in enumerate(ep["paragraphs"]):
        if par.strip() == "---":
            marks.append((t + 0.4, t + 14.0, "interlude")); t += 14.5; section += 1; continue
        for c in chunks(par):
            y = v.say(c); lay.append((t, y)); timeline.append((t, t + len(y) / SR, c, section)); t += len(y) / SR + 0.28
        t += 0.5
        print(f"  paragraph {i + 1}/{len(ep['paragraphs'])}", flush=True)
    del v; import gc; gc.collect()             # free TTS/VC models before mixing (avoids OOM on 8 GB machines)
    json.dump({"timeline": timeline, "total": t + 12.5}, open(os.path.join(HERE, "episodes", f"ep{ep['n']:02d}.timing.json"), "w"), indent=0)
    t_out = t; t += 12.0
    marks.append((t_out, t, "outro"))
    total = t + 0.5
    N = int(total * SR)
    voice = np.zeros(N, np.float32)
    for st, y in lay:
        i0 = int(st * SR); voice[i0:i0 + len(y)] += y[: max(0, min(len(y), N - i0))]
    # music bed for the whole episode (Shur mode: pad, ney, sama pulse)
    bed = music_bed(total + 1.0, ep.get("n", 1))[:N]
    if len(bed) < N: bed = np.pad(bed, (0, N - len(bed)))
    bed = bed / (np.abs(bed).max() + 1e-9)
    # level envelope: low under narration, up for theme/interludes/outro, ducked when the voice speaks
    lvl = np.full(N, 0.075, np.float32)
    from scipy.ndimage import uniform_filter1d
    for a0, a1, kind in marks:
        i0, i1 = int(a0 * SR), min(N, int(a1 * SR))
        lvl[i0:i1] = {"cold": 0.0, "theme": 0.55, "interlude": 0.42, "outro": 0.55}[kind]
    lvl = uniform_filter1d(lvl, int(1.6 * SR))                    # smooth 1.6 s ramps
    act = uniform_filter1d(np.abs(voice), int(0.25 * SR)); act = np.clip(act / (act.max() * 0.12 + 1e-9), 0, 1)
    act = uniform_filter1d(act, int(0.4 * SR))
    lvl = np.minimum(lvl, 0.075 + (1 - act) * 1.0)                # never louder than a bed while talking
    mix = voice + bed * lvl
    if ep.get("cold_open"):                                       # night wind under the cold open
        cold_end = int(marks[0][1] * SR); w = ambience(cold_end + int(2 * SR))
        env = np.clip(np.minimum(np.arange(len(w)) / (0.8 * SR), (len(w) - np.arange(len(w))) / (2 * SR)), 0, 1)
        mix[: len(w)] += w * env * 0.06
    end_fade = np.clip((N - np.arange(N)) / (3 * SR), 0, 1); mix *= end_fade
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
def released(e, now=None):
    """Episodes can be queued ahead with a future pubDate (the 3-month buffer); they stay out of the feed and the
    site until that time. .github/workflows/podcast-release.yml rebuilds the feed daily, so they go live on time
    without anyone (or Claude) being online."""
    now = now or datetime.datetime.now(datetime.timezone.utc)
    return email.utils.parsedate_to_datetime(e["pubDate"]) <= now

def build_feed():
    eps = json.load(open(os.path.join(PUB, "episodes.json"), encoding="utf-8")) if os.path.exists(os.path.join(PUB, "episodes.json")) else []
    eps = sorted([e for e in eps if released(e)], key=lambda e: e["n"], reverse=True)
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
    open(os.path.join(PUB, "index.html"), "w", encoding="utf-8").write(site(eps))

def site(eps):
    """Gazette-style show page: paper tones, seal logo, latest Folio with its 'ID card', all Folios."""
    x = html.escape
    def card(e):
        d = int(e["duration"]); dt = email.utils.parsedate_to_datetime(e["pubDate"]).strftime("%d %B %Y")
        return (f'<table class="id"><tr><th>Volume</th><td>{e.get("volume", 1)}</td></tr>'
                f'<tr><th>Folio</th><td>{e["n"]}</td></tr><tr><th>Narrator</th><td>Mehdi Rahmani</td></tr>'
                f'<tr><th>Length</th><td>{d // 60} min</td></tr><tr><th>Published</th><td>{dt}</td></tr>'
                f'<tr><th>Source</th><td>{x(e.get("source", "Tarikh-e Beyhaqi"))}</td></tr></table>')
    latest = eps[0] if eps else None
    hero = ""
    if latest:
        hero = (f'<section class="hero"><img class="cover" src="cover.jpg" alt="Cover of The Honest Historian">'
                f'<div><p class="kicker">Latest folio</p><h2>{x(latest["title"])}</h2><p class="lede">{x(latest["description"])}</p>'
                f'<audio controls preload="none" src="episodes/ep{latest["n"]:02d}.mp3"></audio>{card(latest)}</div></section>')
    rows = "".join(f'<li><span class="no">Folio {e["n"]}</span><div><h3>{x(e["title"])}</h3><p>{x(e["description"])}</p>'
                   f'<audio controls preload="none" src="episodes/ep{e["n"]:02d}.mp3"></audio></div></li>' for e in eps)
    mins = sum(int(e["duration"]) for e in eps) // 60
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{x(SHOW['title'])}</title><meta name="description" content="{x(SHOW['description'])}">
<link rel="alternate" type="application/rss+xml" title="{x(SHOW['title'])}" href="feed.xml">
<link rel="preconnect" href="https://fonts.googleapis.com"><link href="https://fonts.googleapis.com/css2?family=EB+Garamond:ital,wght@0,400;0,600;1,400&display=swap" rel="stylesheet">
<style>
:root{{--paper:#efe9dc;--ink:#1f2421;--green:#22392e;--gold:#a8843f;--rule:#c9bfa9}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--paper);color:var(--ink);font:19px/1.6 "EB Garamond",Georgia,serif}}
header{{display:flex;align-items:center;gap:16px;padding:18px 24px;border-bottom:3px double var(--rule)}}
header img{{width:56px;height:56px}}header .t{{font-size:18px}}header nav{{margin-left:auto;display:flex;gap:18px}}
a{{color:var(--green)}}main{{max-width:1040px;margin:0 auto;padding:28px 20px 60px}}
.hero{{display:grid;grid-template-columns:minmax(0,340px) 1fr;gap:36px;align-items:start}}
.cover{{width:100%;border:1px solid var(--rule)}}.kicker{{margin:0;color:var(--gold);letter-spacing:.08em;text-transform:uppercase;font-size:14px}}
h2{{font-size:40px;line-height:1.15;margin:.2em 0}}.lede{{font-size:21px}}audio{{width:100%;margin:10px 0}}
table.id{{width:100%;border-collapse:collapse;margin-top:10px}}.id th,.id td{{text-align:left;padding:8px 4px;border-bottom:1px solid var(--rule);font-weight:400}}.id th{{color:#6b6556;width:32%}}
.stats{{display:grid;grid-template-columns:repeat(4,1fr);border-top:1px solid var(--rule);border-bottom:1px solid var(--rule);margin:44px 0}}
.stats div{{text-align:center;padding:18px 6px;border-left:1px solid var(--rule)}}.stats div:first-child{{border-left:0}}.stats b{{display:block;font-size:34px}}
blockquote{{font-size:26px;text-align:center;margin:40px auto;max-width:760px;font-style:italic}}
ul.folios{{list-style:none;padding:0}}ul.folios li{{display:grid;grid-template-columns:110px 1fr;gap:18px;padding:18px 0;border-bottom:1px solid var(--rule)}}
.no{{color:var(--gold);font-weight:600}}h3{{margin:0;font-size:24px}}
.btn{{display:inline-block;background:var(--green);color:#fff;padding:10px 18px;text-decoration:none}}
footer{{text-align:center;color:#6b6556;font-size:15px;padding:20px}}
@media (max-width:760px){{.hero{{grid-template-columns:1fr}}.stats{{grid-template-columns:repeat(2,1fr)}}ul.folios li{{grid-template-columns:1fr}}h2{{font-size:32px}}header nav{{display:none}}}}
</style></head><body>
<header><img src="logo.png" alt="Beyhaqi seal"><div class="t"><b>{x(SHOW['title'])}</b><br>Persian history, told in English</div>
<nav><a href="#folios">All folios</a><a href="#about">About</a><a href="feed.xml">RSS</a></nav></header>
<main>{hero}
<section class="stats"><div><b>{len(eps)}</b>folios</div><div><b>1</b>volume</div><div><b>{mins}</b>minutes</div><div><b>1,000</b>years old</div></section>
<blockquote>"I write only what I saw with my own eyes, or heard from someone I trust."<br><small>in the spirit of Abolfazl Beyhaqi</small></blockquote>
<h2 id="folios">All folios</h2><ul class="folios">{rows}</ul>
<section id="about"><h2>About</h2><p>{x(SHOW['description'])}</p>
<p>Subscribe in any podcast app with this RSS feed: <a href="feed.xml">{BASE_URL}/feed.xml</a></p></section></main>
<footer>The History of Beyhaqi is in the public domain. Retellings and audio © Mehdi Rahmani.</footer></body></html>"""

def publish(ep, mp3):
    path = os.path.join(PUB, "episodes.json")
    eps = json.load(open(path, encoding="utf-8")) if os.path.exists(path) else []
    eps = [e for e in eps if e["n"] != ep["n"]]
    pub = ep.get("pubDate") or email.utils.format_datetime(datetime.datetime.now(datetime.timezone.utc))
    if ep.get("release"):        # "YYYY-MM-DD HH:MM" Asia/Tehran (UTC+03:30): queue the episode for that time
        d = datetime.datetime.fromisoformat(ep["release"].replace(" ", "T")).replace(
            tzinfo=datetime.timezone(datetime.timedelta(hours=3, minutes=30)))
        pub = email.utils.format_datetime(d.astimezone(datetime.timezone.utc))
    eps.append({"n": ep["n"], "title": ep["title"], "description": ep["description"], "pubDate": pub,
                "duration": duration(mp3), "bytes": os.path.getsize(mp3),
                "volume": ep.get("volume", 1), "source": ep.get("source", "")})
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
