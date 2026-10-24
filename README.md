# Kalila & Dimna — Persian Fables for Kids

Video files and the production pipeline for the YouTube channel.

- `epNN/` — finished episodes (`epNN.mp4`, English subtitles `.srt`). Metricool schedules them to YouTube from the raw GitHub URL.
- `pipeline/` — code: cut-out puppet animation (Python + Pillow), synthesized santur music, Kokoro TTS voices, ffmpeg render.
  - `make_episode.py` — the pilot (Lion and Hare, 67 s) and shared drawing/audio primitives
  - `kd_lib.py` — host puppets (Kalila & Dimna), sets, voice timeline helper
  - `ep00/` — Episode 0 "What is Kalila & Dimna?"
- TTS model: `kokoro-v1.0.onnx` + `voices-v1.0.bin` from github.com/thewh1teagle/kokoro-onnx releases (model-files-v1.0), placed in `tts/`.
