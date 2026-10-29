# Kalila & Dimna — Persian Fables for Kids

Video files and the production pipeline for the YouTube channel.

- `epNN/` — finished episodes (`epNN.mp4`, English subtitles `.srt`). Metricool schedules them to YouTube from the raw GitHub URL.
- `pipeline/` — code: cut-out puppet animation (Python + Pillow), synthesized santur music, Kokoro TTS voices, ffmpeg render.
  - `make_episode.py` — the pilot (Lion and Hare, 67 s) and shared drawing/audio primitives
  - `kd_lib.py` — host puppets (Kalila & Dimna), sets, voice timeline helper
  - `ep00/` — Episode 0 "What is Kalila & Dimna?"
- TTS model: `kokoro-v1.0.onnx` + `voices-v1.0.bin` from github.com/thewh1teagle/kokoro-onnx releases (model-files-v1.0), placed in `tts/`.

## Skills used by the automated tasks
- `.claude/skills/social/` (MIT, from coreyhaines31/marketingskills): read `SKILL.md` and `references/short-form-video.md` before writing hooks, Shorts/Reels titles, captions and first comments. Context for both brands is in `.claude/product-marketing.md`. Use it for wording only; it never overrides SERIES_PLAN.md or the task prompt (authenticity, kids' safety, schedule).
