#!/usr/bin/env python3
"""
تبدیل یک مدل Whisper فارسیِ آموزش‌دیده (Hugging Face / transformers) به فرمت sherpa-onnx
تا روی گوشی اندروید (برنامهٔ جلسه‌نگار) اجرا شود.

پیش‌فرض: vhdm/whisper-large-fa-v1  (Whisper large-v3-turbo آموزش‌دیده روی گفتار فارسی)

نمونهٔ اجرا:
    pip install -r requirements.txt
    python convert_persian_whisper.py
    python convert_persian_whisper.py --hf-model vhdm/whisper-large-fa-v1 --out fa_whisper

خروجی (در پوشهٔ --out):
    whisper-encoder.onnx   (int8)
    whisper-decoder.onnx   (int8)
    whisper-tokens.txt
این سه فایل را در صفحهٔ «مدل‌ها»ی برنامه انتخاب کنید (یا در پوشهٔ models برنامه کپی کنید).

نکته: مدل‌هایی که توکنایزر Whisper را عوض کرده‌اند (مثل BuzzASR/persian) با این روش سازگار نیستند.
"""
import argparse
import importlib.util
import os
import shutil
import sys
import tempfile
import urllib.request
from pathlib import Path

EXPORT_URL = "https://raw.githubusercontent.com/k2-fsa/sherpa-onnx/master/scripts/whisper/export-onnx.py"


def hf_to_openai_state_dict(hf_sd: dict) -> dict:
    """نگاشت نام وزن‌ها از transformers به openai-whisper"""
    out = {}
    for k, v in hf_sd.items():
        if k.startswith("proj_out."):
            continue  # با token_embedding گره خورده است
        n = k
        if n.startswith("model."):
            n = n[len("model."):]
        n = (n.replace("encoder.layers.", "encoder.blocks.")
              .replace("decoder.layers.", "decoder.blocks.")
              .replace(".self_attn.q_proj", ".attn.query")
              .replace(".self_attn.k_proj", ".attn.key")
              .replace(".self_attn.v_proj", ".attn.value")
              .replace(".self_attn.out_proj", ".attn.out")
              .replace(".self_attn_layer_norm", ".attn_ln")
              .replace(".encoder_attn.q_proj", ".cross_attn.query")
              .replace(".encoder_attn.k_proj", ".cross_attn.key")
              .replace(".encoder_attn.v_proj", ".cross_attn.value")
              .replace(".encoder_attn.out_proj", ".cross_attn.out")
              .replace(".encoder_attn_layer_norm", ".cross_attn_ln")
              .replace(".final_layer_norm", ".mlp_ln")
              .replace(".fc1", ".mlp.0")
              .replace(".fc2", ".mlp.2"))
        if n == "encoder.layer_norm.weight":
            n = "encoder.ln_post.weight"
        elif n == "encoder.layer_norm.bias":
            n = "encoder.ln_post.bias"
        elif n == "decoder.layer_norm.weight":
            n = "decoder.ln.weight"
        elif n == "decoder.layer_norm.bias":
            n = "decoder.ln.bias"
        elif n == "encoder.embed_positions.weight":
            n = "encoder.positional_embedding"
        elif n == "decoder.embed_positions.weight":
            n = "decoder.positional_embedding"
        elif n == "decoder.embed_tokens.weight":
            n = "decoder.token_embedding.weight"
        out[n] = v
    return out


def dims_from_hf_config(cfg):
    from whisper.model import ModelDimensions
    return ModelDimensions(
        n_mels=cfg.num_mel_bins,
        n_audio_ctx=cfg.max_source_positions,
        n_audio_state=cfg.d_model,
        n_audio_head=cfg.encoder_attention_heads,
        n_audio_layer=cfg.encoder_layers,
        n_vocab=cfg.vocab_size,
        n_text_ctx=cfg.max_target_positions,
        n_text_state=cfg.d_model,
        n_text_head=cfg.decoder_attention_heads,
        n_text_layer=cfg.decoder_layers,
    )


def base_name_for(dims) -> str:
    """نام مدل پایه برای اسکریپت sherpa-onnx (تعیین n_mels و ذخیرهٔ external data)"""
    if dims.n_mels == 128:
        return "turbo" if dims.n_text_layer <= 4 else "large-v3"
    return {384: "tiny", 512: "base", 768: "small", 1024: "medium", 1280: "large-v2"}.get(dims.n_audio_state, "medium")


def build_openai_model(hf_model) -> "whisper.model.Whisper":
    import torch
    from whisper.model import Whisper
    dims = dims_from_hf_config(hf_model.config)
    model = Whisper(dims)
    sd = hf_to_openai_state_dict(hf_model.state_dict())
    missing, unexpected = model.load_state_dict(sd, strict=False)
    missing = [m for m in missing if m != "alignment_heads"]
    if missing or unexpected:
        raise RuntimeError(f"نگاشت وزن‌ها ناقص است.\nmissing={missing}\nunexpected={unexpected}")
    model.eval()
    return model


def load_export_module(path: Path):
    spec = importlib.util.spec_from_file_location("sherpa_whisper_export", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def export(model, base: str, workdir: Path, export_script: Path):
    import torch
    mod = load_export_module(export_script)
    mod.load_model = lambda name: model  # به‌جای دانلود مدل اصلی، مدل فارسی را بده

    # نسخه‌های جدید PyTorch به‌طور پیش‌فرض از خروجی‌گیر dynamo استفاده می‌کنند؛
    # اسکریپت sherpa-onnx برای خروجی‌گیر قدیمی (TorchScript) نوشته شده است.
    import inspect
    orig_export = torch.onnx.export
    if "dynamo" in inspect.signature(orig_export).parameters:
        def legacy_export(*a, **kw):
            kw.setdefault("dynamo", False)
            return orig_export(*a, **kw)
        mod.torch.onnx.export = legacy_export
    old_argv, old_cwd = sys.argv, os.getcwd()
    sys.argv = ["export-onnx.py", "--model", base]
    os.chdir(workdir)
    try:
        torch.set_num_threads(max(1, os.cpu_count() or 1))
        from whisper.model import disable_sdpa
        with disable_sdpa():
            mod.main()
    finally:
        sys.argv = old_argv
        os.chdir(old_cwd)
        torch.onnx.export = orig_export


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--hf-model", default="vhdm/whisper-large-fa-v1",
                    help="نام مدل در Hugging Face یا مسیر پوشهٔ محلی مدل")
    ap.add_argument("--out", default="fa_whisper", help="پوشهٔ خروجی")
    ap.add_argument("--export-script", default=None,
                    help="مسیر export-onnx.py از مخزن sherpa-onnx (اگر ندهید دانلود می‌شود)")
    ap.add_argument("--keep-fp32", action="store_true", help="نسخهٔ float32 را هم نگه دار (حجیم)")
    args = ap.parse_args()

    import torch
    from transformers import WhisperForConditionalGeneration

    out = Path(args.out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    work = Path(tempfile.mkdtemp(prefix="fa_whisper_"))

    export_script = Path(args.export_script) if args.export_script else work / "export-onnx.py"
    if not args.export_script:
        print("دانلود اسکریپت تبدیل sherpa-onnx …")
        urllib.request.urlretrieve(EXPORT_URL, export_script)

    print(f"بارگذاری مدل {args.hf_model} … (بار اول دانلود می‌شود؛ حدود ۱.۶ گیگابایت برای turbo)")
    hf = WhisperForConditionalGeneration.from_pretrained(args.hf_model, torch_dtype=torch.float32)
    model = build_openai_model(hf)
    del hf
    base = base_name_for(model.dims)
    print(f"ساختار مدل: {base}  {model.dims}")

    export(model, base, work, export_script)

    mapping = {
        f"{base}-encoder.int8.onnx": "whisper-encoder.onnx",
        f"{base}-decoder.int8.onnx": "whisper-decoder.onnx",
        f"{base}-tokens.txt": "whisper-tokens.txt",
    }
    for src, dst in mapping.items():
        p = work / src
        if not p.exists():
            raise SystemExit(f"فایل {src} ساخته نشد؛ پیغام‌های بالا را بررسی کنید.")
        shutil.move(str(p), out / dst)

    # بررسی: نسخهٔ int8 نباید به فایل وزن جداگانه وابسته باشد
    import onnx
    for f in ("whisper-encoder.onnx", "whisper-decoder.onnx"):
        m = onnx.load(str(out / f), load_external_data=False)
        ext = [t.name for t in m.graph.initializer if t.data_location == onnx.TensorProto.EXTERNAL]
        if ext:
            print(f"هشدار: {f} به فایل وزن جداگانه نیاز دارد؛ فایل .weights را هم کنارش بگذارید.")

    if args.keep_fp32:
        for p in work.glob(f"{base}-*"):
            shutil.move(str(p), out / p.name)
    shutil.rmtree(work, ignore_errors=True)

    print("\nتمام شد. فایل‌ها:")
    for p in sorted(out.iterdir()):
        print(f"  {p.name:28s} {p.stat().st_size / 1048576:8.1f} MB")
    print("\nبرای آزمایش روی کامپیوتر:  python test_on_pc.py --whisper-dir", out, "--wav نمونه.wav")


if __name__ == "__main__":
    main()
