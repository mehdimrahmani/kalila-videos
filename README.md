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

## Long-form Rumi videos (The Guest House YouTube, weekly)
- `longform/specs/lfNN_*.json` — one episode: title, subtitle, fa_title, seed, intro[], poems[{name, source, lines[{fa,en}], tafsir[]}], outro[].
  Persian lines must be checked word-for-word against ganjoor.net; poems already used are listed under `longform` in `guesthouse/youtube.json`.
- Ready queue (9 Nov 2026): lf04–lf15 are pre-made specs, Persian checked word-for-word on ganjoor.net (key "verified"); they fill the Fridays 27 Nov 2026 – 12 Feb 2027 in id order (lf07 = Shab-e Arus, Fri 18 Dec). Unattended runs use them as-is, no ganjoor access needed.
- Build: `python3 longform/make_assets.py` → `python3 longform/build_audio.py SPEC` → in `longform/remotion`: `npm install` then
  `npx remotion render src/index.ts Longform out/<id>.mp4 --props='{"id":"<id>"}' --concurrency=2 --crf=20` (≈16× real time on 2 CPUs)
  → `python3 longform/make_meta.py SPEC` (title/description with chapters, English .srt, thumbnail) → `ops/yt.py upload/caption/playlist-add`.
