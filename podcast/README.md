# Podcast: The Honest Historian — Stories from Beyhaqi
- Build an episode: write `podcast/episodes/epNN.json` (n, title, description, source, paragraphs; `---` = section break), then `python3 podcast/make_podcast.py podcast/episodes/epNN.json` → renders `docs/podcast/episodes/epNN.mp3`, updates `docs/podcast/episodes.json`, `feed.xml`, `index.html`. Commit + push; GitHub Pages (main /docs) serves it and Spotify/Apple pick it up from the feed.
- Voice: Kokoro am_onyx (English) converted with FreeVC24 to Mehdi's voice using the stored embedding `podcast/voice/mehdi_freevc24_se.npy` (Mehdi approved, 1 Nov 2026). The raw voice recording is deliberately NOT in the repo.
- Plan and rules: `podcast/SERIES.md`. Cover: `python3 podcast/make_cover.py`.
