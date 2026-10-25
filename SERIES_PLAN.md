# Kalila & Dimna — Series plan

Channel: "Kalila & Dimna - Persian Fables for Kids" (YouTube channel UCpEqwTLTqdfDcLyocjlf1bA, connected in Metricool brand 7510338).
Audience: children 4-10 and parents. Simple English. Made for Kids = Yes.
Release: every Saturday 16:30 Asia/Tehran (09:00 US Eastern in summer time).

## Format (every episode)
- 0:00 Hosts open (15-20 s): Kalila (wise, calm, older; voice am_michael 0.92) and Dimna (clever, playful; voice am_puck 1.0) under their tree. Dimna teases the story with a question.
- Title card (3 s).
- The story: 8-10 short scenes, warm narrator (af_heart 0.92) + character voices with lip sync. 3-4 minutes total.
- Hosts close: they say the moral in kids' words; Kalila announces next episode.
- End card: "Next time - <next story>" + "A new story every Saturday".
- Style: cut-out puppets (Python/Pillow, kd_lib.py), Persian-miniature palette, khatam-star border, santur music in Dastgah-e Shur synthesized in code. No paid AI video.

## Episode order
| # | Story | Persian | Moral |
|---|---|---|---|
| 0 | What is Kalila & Dimna? (trailer) | | |
| 1 | The Lion and the Hare | شیر و خرگوش | Wisdom is stronger than strength |
| 2 | The Monkey and the Tortoise | بوزینه و باخه | A true friend uses their head; trust wisely |
| 3 | The Ring-Dove and the Hunter's Net | کبوتر طوقدار | Together we are strong |
| 4 | The Crow and the Snake | زاغ و مار | Cleverness beats a bully |
| 5 | The Heron and the Crab | ماهیخوار و خرچنگ | Don't believe sweet lies |
| 6 | The Tortoise and the Two Ducks | باخه و دو مرغابی | Think before you speak |
| 7 | The Three Fish | سه ماهی | Plan ahead |
| 8 | The Monkey and the Carpenter's Wedge | بوزینه و درودگر | Don't meddle in what you don't understand |
| 9 | The Hares and the Elephants (the moon in the lake) | خرگوشان و پیلان | The small can be brave and smart |
| 10 | The Mouse and the Cat | موش و گربه | Friends in need |
| 11 | The Lion and the Ox (Shanzabeh) | شیر و گاو | Beware of gossip (Dimna learns a lesson) |
| 12 | The Ascetic and the Mongoose | زاهد و راسو | Don't act in haste |

## Growth features (every episode from Ep 2 on)
- **Persian word of the day**: in the hosts' closing, Dimna teaches ONE Persian word from the story ("In Persian, lion is *shir*!"). Show it on screen in a gold card: the Persian word in Persian script (Pillow has raqm, so Persian text renders correctly; use a font with Persian glyphs, e.g. install fonts-vazirmatn or fonts-noto via pip/apt if available, else DejaVu Sans), the transliteration and the English meaning. Kalila repeats it once. Keep it 8-10 s.
- **Bilingual title**: `<English story> | <Persian story> | Kalila & Dimna Ep N` (<= 70 chars). Description: English hook first, then one Persian line: "قصه‌ی «...» از کلیله و دمنه، به زبان انگلیسی با انیمیشن و موسیقی سنتور؛ برای بچه‌های ایرانی در سراسر دنیا و همه‌ی بچه‌هایی که قصه دوست دارند." Tags include the Persian story name, «کلیله و دمنه», «قصه کودکانه». Last hashtag `#کلیله_و_دمنه`.
- **Persian subtitles**: write `epNN/epNN.fa.srt` (same timings as the .en.srt, natural spoken Persian for kids). Captions are uploaded in YouTube Studio by hand when Mehdi has internet; Metricool can't upload them.
- **Two Shorts per episode** with `pipeline/make_short.py SRC START DUR "Title" "Story" OUT` (20-45 s each, vertical 1080x1920, saved in `shorts/`): Short A = a teaser that stops on a cliffhanger, published the Thursday BEFORE the episode; Short B = the best moment, published the Tuesday AFTER the episode. Both 16:30 Asia/Tehran, YouTube type "short", madeForKids true, title "<hook> | <Persian story> #Shorts".

## Special episodes
- **Yalda (Shab-e Yalda) — publish Saturday 2026-12-19**: Kalila & Dimna sit by a korsi with pomegranates, watermelon and a book of Hafez; they explain Yalda simply (the longest night; families stay up together, eat fruit and tell stories) and then tell that week's story. Persian word: «یلدا» (yalda) / «انار» (anar = pomegranate). Title should include "Yalda Night Special | شب یلدا".
- **Nowruz — publish Saturday 2027-03-13**: Haft-sin table, spring, goldfish; Persian word «نوروز» (Nowruz = new day).

Retell each tale in a child-safe way (no gore; villains fall/flee/learn).

## Roadmap (agreed with Mehdi, 2026-10-25)
Strategy: start simple and slowly raise the depth, so children's understanding and interest grow with the channel.
1. **Kalila & Dimna** (Ep 1-12, this table) — short animal fables, one clear moral.
2. **One Thousand and One Nights** (هزار و یک شب) — child-safe picks only: Aladdin, Ali Baba, Sindbad, etc.
3. **Shahnameh** (شاهنامه) — heavily child-safe retellings: Zal and the Simorgh, Rostam's Seven Labours (no violence), Kaveh the Blacksmith. The Nowruz special (Jamshid and the first Nowruz) is the first taste of it.
4. **Masnavi** (مثنوی) — its short, funny tales: the Merchant and the Parrot, the Elephant in the Dark, the Mouse and the Camel.
- Kalila & Dimna stay the hosts of every series ("Kalila & Dimna present: ...") so the channel brand stays the same.
- Before switching series (around Ep 8-10), check YouTube data in Metricool (retention, subscribers per episode) and decide the switch date from the data.
