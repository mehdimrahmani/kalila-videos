# The Guest House (@theguesthouse.poetry) — automatic Reels

`make_reel.py spec.json out.mp4` renders a 16 s vertical Reel (1080x1920) in the page's house style:
navy + double gold border, Persian verse (Vazirmatn, raqm-shaped) then the English translation appearing
line by line, source line, @theguesthouse.poetry, with a synthesized ney melody in Dastgah-e Shur.
Reels are committed to `guesthouse/reels/partNN.mp4` and scheduled in Metricool (brand 7510338) as
Instagram type REEL with media = the raw.githubusercontent.com URL, so nothing needs Mehdi's internet.
Specs (verse text) live in `guesthouse/specs/`. Font: Vazirmatn (OFL, see fonts/Vazirmatn-OFL.txt).

YouTube Shorts (The Guest House channel): `yt_endcard.py REEL SPEC OUT` makes a YouTube-only copy with a
"Part N+1 is coming / Subscribe to follow the story" card over the last 3 s (the Instagram Reel is unchanged).
Every Short is added to the "Rumi & Shams" playlist (youtube.json → playlists.rumi).
