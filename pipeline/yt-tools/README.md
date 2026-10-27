# yt-tools
From https://github.com/Jakeschincariol/youtube-agent-skill (MIT, see LICENSE). Offline Python tools, no network.

Used by the weekly episode task:
- `python3 -I yt-package/title.py --title "..." --thumb "..."` — every episode title must score >= 80 and stay <= 60 characters; thumbnail text must not repeat the title.
- `python3 -I yt-chapters/chapters.py epNN/epNN.en.srt --target 8` — boundary suggestions; final chapters must start at 0:00, be >= 3 entries, each >= 10 s; retitle every line in kids' words.
- `yt-script/hookscore.py --hook "..."` — score Dimna's opening line (the hook); a heuristic, not a predictor.
- `yt-shorts/SKILL.md` — how to pick the Shorts inside an episode and write a new first line for each.
- `yt-retention/retention.py retention.csv` — when Mehdi exports a retention CSV from YouTube Studio, read where kids leave and fix the next scripts.
Skills that don't fit a Made-for-Kids channel (comments are off) or need YouTube access from the server (yt-viral uses yt-dlp, blocked here) were not copied.
