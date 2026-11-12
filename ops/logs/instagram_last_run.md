# Instagram run 2026-11-12 10:00:28 +0330
- 06:30:28 setup: checkout main + pull OK
- 06:31 setup: TTS model downloaded (onnx 325 MB, voices 28 MB); ffmpeg present; kokoro_onnx pip install started
- 06:32 ledger: next ig_post = 2026-11-26 20:30 -> week = echo Tue 24 Nov, Part 6 card Thu 26 Nov, Part 6 Reel Sat 28 Nov
- 06:33 verse check: candidate Part 6 = Divan Ghazal 36 "بروید ای حریفان"; echo = "دلا نزد کسی بنشین" (both unused in guesthouse/ and longform/ specs)
- 06:38 ganjoor WebFetch FAILED: "PROVENANCE_REQUIRED. The permission request for this URL was not answered in time. The fetch tool said not to retry." (https://ganjoor.net/moulavi/shams/ghazalsh/sh36). Not retrying via curl (forbidden); trying WebSearch for verification.
- 06:45 Metricool getScheduledPosts OK: Part 5 card 19 Nov + story, echo 17 Nov, Part 5 Reel 21 Nov present; nothing for 24-28 Nov -> Part 6 week
- 06:47 Wikipedia/wikisource WebFetch also FAILED: "PROVENANCE_REQUIRED (source: target). The user did not answer an earlier permission request in time, so the request for this URL was not sent to them. Do not retry."
- 06:50 DECISION: WebFetch is blocked in this unattended run; verified wording with exact-phrase WebSearch instead: Ghazal 163 c1 (ganjoor ?p=2787 title + query match) and c2 (exact-phrase -> Wikipedia "Rumi ghazal 163"); Ghazal 563 c1 (ganjoor ?p=3187 title, fa.wikisource) and c2 (exact-phrase -> quotewise/goodreads Rumi). Numbering from ganjoor post-id offset (2787->163 matches Wikipedia "Rumi ghazal 163"; 3187->563).
- 06:37:44 specs committed; both Reel renders started
- 06:39:04 card part06.png rendered and checked (Nastaliq joined, text exact); seg 3 changed to hemistich 4 for a complete sentence, part06 Reel render restarted
- 06:40 Metricool: Part 6 card scheduled 2026-11-26 20:30 uuid 2584359343789850739 (re-hosted static.metricool.com) https://app.metricool.com/planner/calendar?blogId=7510338&openWithPostUuid=2584359343789850739
- 06:40 Metricool: Story scheduled 2026-11-26 20:40 uuid -7795661469500092793 https://app.metricool.com/planner/calendar?blogId=7510338&openWithPostUuid=-7795661469500092793
- 06:41 ledger: ig_post 2026-11-26 20:30 added
- 06:48:38 renders done: part06 69.4 s (too long), echo 58.1 s; part06 tafsir shortened, re-rendering
- 06:54:15 Reels checked: part06 60.6 s, mean -16.8 dB; echo_20261124 58.0 s, mean -17.6 dB; no 3 s silences; frames OK (hook, verses, tafsir, outro)
- 06:54 Metricool: Part 6 Reel scheduled 2026-11-28 20:30 uuid -6100459285388439598 https://app.metricool.com/planner/calendar?blogId=7510338&openWithPostUuid=-6100459285388439598
- 06:54 Metricool: echo Reel scheduled 2026-11-24 20:30 uuid -5479903102007621251 https://app.metricool.com/planner/calendar?blogId=7510338&openWithPostUuid=-5479903102007621251
- 06:56 ledger: ig_part_reel 28 Nov (part06.mp4), ig_echo_reel 24 Nov (echo_20261124.mp4) added (negative uuid parsed as option by slots.py CLI -> fixed by editing schedule.json directly)

## گزارش
هفته‌ی ۳ تا ۷ آذر ۱۴۰۵ (۲۴ تا ۲۸ نوامبر ۲۰۲۶) پر شد — قسمت ۶ «بازگشت، و ناپدید شدن نهایی».
- ریل اکو، سه‌شنبه ۳ آذر ۲۰:۳۰: «دلا نزد کسی بنشین که او از دل خبر دارد» (غزل ۵۶۳) — https://app.metricool.com/planner/calendar?blogId=7510338&openWithPostUuid=-5479903102007621251
- کارت قسمت ۶، پنجشنبه ۵ آذر ۲۰:۳۰: «بروید ای حریفان بکشید یار ما را» (غزل ۱۶۳) — https://app.metricool.com/planner/calendar?blogId=7510338&openWithPostUuid=2584359343789850739
- استوری، ۵ آذر ۲۰:۴۰ — https://app.metricool.com/planner/calendar?blogId=7510338&openWithPostUuid=-7795661469500092793
- ریل قسمت ۶، شنبه ۷ آذر ۲۰:۳۰ — https://app.metricool.com/planner/calendar?blogId=7510338&openWithPostUuid=-6100459285388439598
انبار: ig_post تا ۲۶ نوامبر، ig_part_reel تا ۲۸ نوامبر، ig_echo_reel تا ۲۴ نوامبر.
مشکل: WebFetch به ganjoor/ویکی‌پدیا در اجرای خودکار مجاز نبود (PROVENANCE_REQUIRED)؛ متن ابیات با جست‌وجوی عبارت دقیق تأیید شد، نه با خواندن کامل صفحه‌ی گنجور.
