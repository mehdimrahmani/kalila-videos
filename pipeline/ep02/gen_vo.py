"""Episode 2 voices (Kokoro). Run from pipeline/ep02: python3 gen_vo.py
Big animals are pitched down, small ones up (resampled here, so lines.json durations are exact)."""
import os, json
import numpy as np, soundfile as sf
from kokoro_onnx import Kokoro
HERE = os.path.dirname(os.path.abspath(__file__))
TTS = os.path.join(os.path.dirname(HERE), "tts")
k = Kokoro(os.path.join(TTS, "kokoro-v1.0.onnx"), os.path.join(TTS, "voices-v1.0.bin"))
V = {"K": ("am_michael", 0.92), "D": ("am_puck", 1.0), "N": ("af_heart", 0.92),
     "M": ("am_echo", 1.02), "T": ("bm_lewis", 0.9), "W": ("bf_emma", 0.95)}
PITCH = {"M": 1.10, "T": 0.92, "W": 1.04}
from lines import LINES
os.makedirs(os.path.join(HERE, "vo"), exist_ok=True)
out = []
for key, sp, txt, _fa in LINES:
    v, s = V[sp]
    a, sr = k.create(txt, voice=v, speed=s, lang="en-us")
    f = PITCH.get(sp, 1.0)
    if f != 1.0:
        n = int(len(a) / f)
        a = np.interp(np.arange(n) * f, np.arange(len(a)), a).astype(np.float32)
    sf.write(os.path.join(HERE, "vo", key + ".wav"), a, sr)
    out.append(dict(key=key, spk=sp, text=txt, dur=round(len(a) / sr, 2)))
json.dump(out, open(os.path.join(HERE, "vo", "lines.json"), "w"), indent=1)
print(round(sum(o['dur'] for o in out), 1))
