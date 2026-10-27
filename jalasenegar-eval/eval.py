#!/usr/bin/env python3
"""
Diagnose Jalasenegar transcription quality on real Persian speech (FLEURS fa_ir test set).

1) Single utterances, plain decode, for several Whisper models (WER/CER).
2) Synthetic 2-speaker ~50 s "conversations" built from FLEURS utterances, decoded:
   a) plain 25 s windows                         (baseline)
   b) the app pipeline: diarization -> <=14 s chunks -> silence padding x2
   c) app pipeline without the silence padding
   d) app pipeline without diarization (energy VAD only)
"""
import csv, json, os, random, re, sys, tarfile, time, io
from pathlib import Path
import numpy as np, soundfile as sf, sherpa_onnx

SR = 16000
W = Path(sys.argv[1])          # work dir with models/ and fleurs/
OUT = Path(sys.argv[2]); OUT.mkdir(parents=True, exist_ok=True)

def norm(t):
    t = t.replace('ي', 'ی').replace('ك', 'ک').replace('‌', ' ')
    t = re.sub(r'[^\w\s]', ' ', t)
    t = re.sub(r'[ً-ْ]', '', t)
    return re.sub(r'\s+', ' ', t).strip()

def ed(a, b):
    d = list(range(len(b) + 1))
    for i, x in enumerate(a, 1):
        p, d[0] = d[0], i
        for j, y in enumerate(b, 1):
            p, d[j] = d[j], min(d[j] + 1, d[j-1] + 1, p + (x != y))
    return d[len(b)]

def wer(ref, hyp):
    r, h = norm(ref).split(), norm(hyp).split()
    return ed(r, h) / max(1, len(r))

def cer(ref, hyp):
    r, h = norm(ref).replace(' ', ''), norm(hyp).replace(' ', '')
    return ed(list(r), list(h)) / max(1, len(r))

def load(p):
    x, sr = sf.read(p, dtype='float32', always_2d=True); x = x.mean(1)
    if sr != SR:
        n = int(len(x) * SR / sr); x = np.interp(np.linspace(0, len(x)-1, n), np.arange(len(x)), x).astype('float32')
    return x

# ---- FLEURS test set
rows = []
with open(W / 'fleurs/test.tsv', encoding='utf-8') as f:
    for r in csv.reader(f, delimiter='\t', quoting=csv.QUOTE_NONE):
        # id, file, raw transcription, normalized, chars, num_samples, gender
        rows.append(dict(file=r[1], text=r[2], gender=r[-1]))
audio_dir = W / 'fleurs/test'
rows = [r for r in rows if (audio_dir / r['file']).exists()]
random.seed(7); random.shuffle(rows)
print('fleurs utterances:', len(rows))

def recognizer(d, lang='fa'):
    return sherpa_onnx.OfflineRecognizer.from_whisper(
        encoder=str(d / 'enc.onnx'), decoder=str(d / 'dec.onnx'), tokens=str(d / 'tok.txt'),
        language=lang, task='transcribe', num_threads=4)

def decode(rec, x):
    s = rec.create_stream(); s.accept_waveform(SR, x); rec.decode_stream(s); return s.result.text.strip()

models = [m for m in sorted((W / 'models').iterdir()) if (m / 'enc.onnx').exists()]
report = {}

# ---- 1) single utterances
N = int(os.environ.get('N_UTT', '40'))
for m in models:
    rec = recognizer(m); refs = []; hyps = []; t0 = time.time()
    for r in rows[:N]:
        x = load(audio_dir / r['file']); refs.append(r['text']); hyps.append(decode(rec, x))
    tot_w = sum(len(norm(a).split()) for a in refs)
    W_ = sum(ed(norm(a).split(), norm(b).split()) for a, b in zip(refs, hyps)) / tot_w
    C_ = np.mean([cer(a, b) for a, b in zip(refs, hyps)])
    report[f'utt/{m.name}'] = dict(wer=round(W_, 3), cer=round(float(C_), 3), sec=round(time.time()-t0, 1))
    print(m.name, report[f'utt/{m.name}'], flush=True)
    with open(OUT / f'utt-{m.name}.txt', 'w', encoding='utf-8') as f:
        for a, b in list(zip(refs, hyps))[:15]: f.write(f'REF: {a}\nHYP: {b}\n\n')

# ---- 2) conversations
males = [r for r in rows[N:] if r['gender'].upper().startswith('M')]
fems = [r for r in rows[N:] if r['gender'].upper().startswith('F')]
convs = []
for k in range(int(os.environ.get('N_CONV', '4'))):
    a, b = males[k*4:(k+1)*4], fems[k*4:(k+1)*4]
    seq = [u for pair in zip(a, b) for u in pair]
    parts, text = [], []
    for u in seq:
        parts += [load(audio_dir / u['file']), np.zeros(int(0.4 * SR), 'float32')]; text.append(u['text'])
    convs.append((np.concatenate(parts), ' '.join(text)))
print('conversation lengths (s):', [round(len(c[0]) / SR, 1) for c in convs])

def splitter_regions(x):
    fr = SR // 50; n = len(x) // fr
    rms = np.sqrt((x[:n*fr].reshape(n, fr) ** 2).mean(1))
    thr = max(np.sort(rms)[int(n*0.15)] * 2.5, 0.003)
    regs, st, last = [], -1, -1
    for i, v in enumerate(rms):
        if v > thr:
            if st < 0: st = i
            last = i
        elif st >= 0 and i - last > 25: regs.append((st, last+1)); st = -1
    if st >= 0: regs.append((st, last+1))
    merged = []
    for r in regs:
        if merged and r[0] - merged[-1][1] < 50: merged[-1] = (merged[-1][0], r[1])
        else: merged.append(r)
    return [(max(0, a*fr - SR//5), min(len(x), b*fr + SR//5)) for a, b in merged if b - a >= 15], rms, fr

def split(rms, fr, s, e, maxs=14, mins=7):
    out = []; mx, mn = maxs*SR, mins*SR
    while e - s > mx:
        a, b = (s+mn)//fr, min((s+mx)//fr, len(rms)-1)
        best = min(range(a, b+1), key=lambda i: rms[max(0, i-5):i+6].mean())
        cut = min(max(best*fr, s+mn), s+mx); out.append((s, cut)); s = cut
    if e - s > SR//4: out.append((s, e))
    return out

def diar(x, nspk, seg, emb):
    cfg = sherpa_onnx.OfflineSpeakerDiarizationConfig(
        segmentation=sherpa_onnx.OfflineSpeakerSegmentationModelConfig(
            pyannote=sherpa_onnx.OfflineSpeakerSegmentationPyannoteModelConfig(model=str(seg)), num_threads=4),
        embedding=sherpa_onnx.SpeakerEmbeddingExtractorConfig(model=str(emb), num_threads=4),
        clustering=sherpa_onnx.FastClusteringConfig(num_clusters=nspk), min_duration_on=0.3, min_duration_off=0.5)
    sd = sherpa_onnx.OfflineSpeakerDiarization(cfg)
    turns = [(int(s.start*SR), int(s.end*SR), s.speaker) for s in sd.process(x).sort_by_start_time()]
    merged = []
    for t in turns:
        if merged and merged[-1][2] == t[2] and t[0] - merged[-1][1] < 1.2*SR:
            merged[-1] = (merged[-1][0], max(merged[-1][1], t[1]), t[2])
        else: merged.append(t)
    return merged

def app_pipeline(rec, x, use_diar=True, pad=True, maxs=14, mins=7):
    _, rms, fr = splitter_regions(x)
    turns = diar(x, 2, W/'seg.onnx', W/'emb.onnx') if use_diar else [(a, b, -1) for a, b in splitter_regions(x)[0]]
    chunks = []
    for s, e, spk in turns:
        s, e = max(0, s - SR//5), min(len(x), e + SR//5)
        chunks += [(a, b) for a, b in split(rms, fr, s, e, maxs, mins)]
    chunks = [(a, b) for a, b in chunks if b - a >= SR//2]
    out = []
    for a, b in chunks:
        piece = x[a:b]
        if pad:
            L = len(piece); P = max(L, min(L*2 + SR//2, int(29.4*SR)))
            piece = np.concatenate([piece, np.zeros(P - L, 'float32')])
        out.append(decode(rec, piece))
    return ' '.join(out), [round((b-a)/SR, 1) for a, b in chunks], len(turns)

for m in models:
    rec = recognizer(m)
    for name, fn in [
        ('plain-25s', lambda x: (' '.join(decode(rec, x[i:i+25*SR]) for i in range(0, len(x), 25*SR)), [], 0)),
        ('app', lambda x: app_pipeline(rec, x)),
        ('app-nopad', lambda x: app_pipeline(rec, x, pad=False)),
        ('app-nodiar', lambda x: app_pipeline(rec, x, use_diar=False)),
        ('app-nodiar-nopad-25s', lambda x: app_pipeline(rec, x, use_diar=False, pad=False, maxs=25, mins=12)),
    ]:
        ws, cs, info = [], [], []
        with open(OUT / f'conv-{m.name}-{name}.txt', 'w', encoding='utf-8') as f:
            for x, ref in convs:
                hyp, lens, nturns = fn(x)
                ws.append(wer(ref, hyp)); cs.append(cer(ref, hyp)); info.append((nturns, lens))
                f.write(f'REF: {ref}\nHYP: {hyp}\nturns={nturns} chunks={lens}\n\n')
        report[f'conv/{m.name}/{name}'] = dict(wer=round(float(np.mean(ws)), 3), cer=round(float(np.mean(cs)), 3))
        print(m.name, name, report[f'conv/{m.name}/{name}'], info[0], flush=True)

json.dump(report, open(OUT / 'report.json', 'w'), indent=1, ensure_ascii=False)
