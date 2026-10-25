"""Split files >1.9GB into parts and write manifest.json (names, sizes, sha256)."""
import hashlib, json, os, sys
src, dst = sys.argv[1], sys.argv[2]
os.makedirs(dst, exist_ok=True)
PART = 1900 * 1024 * 1024
roles = {
    "whisper-encoder.onnx": "asr", "whisper-decoder.onnx": "asr", "whisper-tokens.txt": "asr",
    "segmentation.onnx": "diarization", "speaker-embedding.onnx": "diarization",
    "llm.litertlm": "llm",
}
files = []
for name, group in roles.items():
    p = os.path.join(src, name)
    if not os.path.exists(p):
        print("missing", name); continue
    size = os.path.getsize(p)
    h = hashlib.sha256()
    parts = []
    with open(p, "rb") as f:
        i = 0
        while True:
            chunk = f.read(PART)
            if not chunk: break
            h.update(chunk)
            pn = name if size <= PART else f"{name}.part{i}"
            with open(os.path.join(dst, pn), "wb") as o: o.write(chunk)
            parts.append({"name": pn, "size": len(chunk)})
            i += 1
    files.append({"name": name, "group": group, "size": size, "sha256": h.hexdigest(), "parts": parts})
    print(name, size, len(parts))
json.dump({"version": 1, "files": files}, open(os.path.join(dst, "manifest.json"), "w"), indent=1)
