"""Download a .litertlm chat model (Gemma 4 E2B preferred) into the given folder as llm.litertlm."""
import os, shutil, sys
from huggingface_hub import HfApi, hf_hub_download
out = sys.argv[1]
token = os.environ.get("HF_TOKEN") or None
for repo in ["litert-community/gemma-4-E2B-it-litert-lm", "google/gemma-3n-E2B-it-litert-lm", "litert-community/Gemma3-1B-IT"]:
    try:
        files = HfApi().list_repo_files(repo, token=token)
        cands = [f for f in files if f.endswith(".litertlm")]
        bad = ("web", "npu", "qualcomm", "mediatek", "sm8", "mt6", "tensor", "qnn")
        generic = [f for f in cands if not any(b in f.lower() for b in bad)] or cands
        if not generic:
            print("no litertlm in", repo, files); continue
        f = sorted(generic, key=len)[0]
        print("downloading", repo, f, flush=True)
        p = hf_hub_download(repo, f, token=token)
        shutil.copy(p, os.path.join(out, "llm.litertlm"))
        open(os.path.join(out, "llm.source.txt"), "w").write(f"{repo}/{f}\n")
        print("ok", os.path.getsize(os.path.join(out, "llm.litertlm")))
        break
    except Exception as e:
        print("failed", repo, type(e).__name__, str(e)[:300], flush=True)
