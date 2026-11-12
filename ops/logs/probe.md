# Probe log — 2026-11-12

1 clone: ok (no add_repo tool available in this session — ToolSearch found none; repo was already in scope and pre-cloned; first `git pull` failed with "You are not currently on a branch." from detached HEAD, then `git checkout main && git pull origin main` succeeded)
2 push: ok (bbd45a9..9b8b940 main -> main)
3 metricool tools: mcp__Metricool_Social_Media_Management__createScheduledPost, createScheduledPostForReview, getAnalyticsDataByMetrics, getBrandSettings, getScheduledPosts, sendScheduledPostForReview, updateScheduledPost, getAnalyticsAvailableMetrics, getBestTimeToPostByNetwork (all same prefix; 9 tools)
4 metricool read: with exact dates "2026-11-12T00:00:00"/"2026-11-30T23:59:59" → error: "Text '2026-11-12T00:00:00' could not be parsed at index 19". Retried with "+03:30" offset → ok, 10 posts (3 youtube: Nov 12, 14, 17; 7 instagram: Nov 12 post+story, Nov 14 reel, Nov 17 reel, Nov 19 post+story, Nov 21 reel)
5 slots:
ig_post         filled through 2026-11-19 20:30  next free 2026-11-26 20:30
ig_part_reel    filled through 2026-11-21 20:30  next free 2026-11-28 20:30
ig_echo_reel    filled through 2026-11-17 20:30  next free 2026-11-24 20:30
6 final push: see below
