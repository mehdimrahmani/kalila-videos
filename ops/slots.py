#!/usr/bin/env python3
"""The 3-month content buffer (Mehdi, 7 Nov 2026: Iran's internet may be cut for 2-3 months, and Claude may stop).

Everything is produced AHEAD and handed to a platform that publishes it on its own:
YouTube (upload with publishAt), Metricool (Instagram, autoPublish), GitHub Actions (podcast feed release).
This file is the shared calendar: which weekly slots exist per stream, which are already filled, and the
daily YouTube upload budget (all uploads of both channels share ONE Google Cloud project quota: 10,000 units/day,
an upload costs ~1,600, so at most 6 uploads per Pacific-time day; we keep 1 spare).

  python3 ops/slots.py status                       # coverage per stream (filled up to which date)
  python3 ops/slots.py next STREAM                  # earliest free slot ("YYYY-MM-DD HH:MM" Tehran) or FULL
  python3 ops/slots.py free STREAM [N]              # the next N free slots
  python3 ops/slots.py add STREAM "YYYY-MM-DD HH:MM" ID [NOTE]   # record a filled slot (ID = video id / Metricool uuid / epNN)
  python3 ops/slots.py budget [STREAM]              # YouTube uploads still allowed today (0 for a stream far ahead while Shorts/Kalila lag)
  python3 ops/slots.py upload-done STREAM ID        # count one YouTube upload against today's budget

Times are Asia/Tehran (UTC+03:30, no DST). Ledger: ops/schedule.json (commit + push after every change;
git pull before reading). A slot closer than MIN_LEAD to now is never offered.
"""
import os, sys, json, datetime as dt

HERE = os.path.dirname(os.path.abspath(__file__))
LEDGER = os.path.join(HERE, "schedule.json")
TEH = dt.timezone(dt.timedelta(hours=3, minutes=30))
PT = dt.timezone(dt.timedelta(hours=-8))            # YouTube quota resets at midnight Pacific (PST; close enough)
HORIZON = dt.datetime(2027, 2, 13, 23, 59, tzinfo=TEH)   # ~3 months from 7 Nov 2026
DAILY_UPLOADS = 5
MIN_LEAD = dt.timedelta(hours=2)
LEAD = {"podcast": dt.timedelta(hours=-10)}   # a podcast slot earlier today can still be filled: it simply goes live at once
MON, TUE, WED, THU, FRI, SAT, SUN = range(7)

# stream -> list of (weekday, "HH:MM"). Kept identical to the old weekly schedule so nothing changes for viewers.
STREAMS = {
    # Kalila & Dimna channel (YouTube API, publishAt)
    "kd_episode":     [(SAT, "21:30")],
    "kd_short":       [(SUN, "21:30")],      # buffer: 1/week (kids' Shorts get 1-4 views; quota goes to long-form)
    "kd_compilation": [(WED, "18:30")],      # one per ~4 weeks: use `free`, pick the first Wednesday >= 25 days after the last one
    # The Guest House channel (YouTube API, publishAt)
    "gh_longform":    [(FRI, "13:41")],
    "gh_pod_full":    [(SUN, "16:37")],
    "gh_pod_short":   [(SUN, "16:47"), (TUE, "16:37"), (THU, "16:37")],
    "gh_rumi_short":  [(SAT, "20:47"), (TUE, "20:47")],   # the Instagram Part Reel / echo Reel of the same day
    "gh_lf_short":    [(MON, "20:47"), (WED, "20:47"), (FRI, "20:47")],   # one poem of a long-form Rumi video (guesthouse/lf_short.py), links to it (Mehdi 9 Nov 2026: Rumi Shorts first)
    # Podcast feed (GitHub Actions releases it)
    "podcast":        [(SUN, "11:13")],
    # Instagram via Metricool (autoPublish)
    "ig_post":        [(THU, "20:30")],      # card + Story 10 min later
    "ig_part_reel":   [(SAT, "20:30")],
    "ig_echo_reel":   [(TUE, "20:30")],
}

def now(): return dt.datetime.now(TEH)

def load():
    if os.path.exists(LEDGER): return json.load(open(LEDGER, encoding="utf-8"))
    return {"filled": [], "uploads": []}

def save(d):
    json.dump(d, open(LEDGER, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

def fmt(t): return t.strftime("%Y-%m-%d %H:%M")
def parse(s): return dt.datetime.fromisoformat(s.replace(" ", "T")).replace(tzinfo=TEH)

def slots(stream, start=None):
    start = start or (now() + LEAD.get(stream, MIN_LEAD))
    day = start.date()
    while True:
        for wd, hm in STREAMS[stream]:
            if day.weekday() == wd:
                t = parse(f"{day} {hm}")
                if t >= start:
                    if t > HORIZON: return
                    yield t
        day += dt.timedelta(days=1)

def filled(d, stream):
    return {f["at"] for f in d["filled"] if f["stream"] == stream}

def free(stream, n=1):
    d = load(); taken = filled(d, stream); out = []
    for t in slots(stream):
        if fmt(t) not in taken:
            out.append(fmt(t))
            if len(out) >= n: break
    return out

def coverage(d, stream):
    """Last date up to which every slot (from now) is filled."""
    taken = filled(d, stream); last = None
    for t in slots(stream):
        if fmt(t) not in taken: break
        last = t
    return fmt(last) if last else "—"

def today_pt():
    return dt.datetime.now(PT).date().isoformat()

# Fairness (13 Nov 2026): the podcast->YouTube task (runs ~16:37 Tehran, early in the Pacific quota day) and the
# long-form task (~10:41) were using the shared upload budget for slots 3-4 weeks ahead while the Rumi Shorts (the
# growth engine) and Kalila were starved. A stream already far ahead now gets nothing while a priority stream lags.
PRIORITY = ("gh_rumi_short", "gh_lf_short", "kd_episode", "kd_short")
AHEAD, LAGGING = dt.timedelta(days=21), dt.timedelta(days=10)
WINDOW_STREAM = [((16, 20), (18, 45), "gh_pod_full"), ((10, 20), (11, 35), "gh_longform")]   # caller by clock

def _cov(d, s):
    c = coverage(d, s)
    return parse(c) if c != "—" else now()

def budget(stream=None):
    d = load(); used = sum(1 for u in d["uploads"] if u["day"] == today_pt())
    left = max(0, DAILY_UPLOADS - used)
    if stream is None:   # infer the calling task from the time of day (the tasks call plain `budget`)
        hm = (now().hour, now().minute)
        stream = next((st for a, b, st in WINDOW_STREAM if a <= hm < b), None)
    if stream and stream not in PRIORITY and _cov(d, stream) > now() + AHEAD \
            and any(_cov(d, p) < now() + LAGGING for p in PRIORITY):
        return 0
    return left

if __name__ == "__main__":
    a = sys.argv[1:]
    if not a or a[0] in ("-h", "--help"): print(__doc__); sys.exit()
    cmd = a[0]
    if cmd == "status":
        d = load()
        print(f"horizon {fmt(HORIZON)} | YouTube uploads left today: {budget()}")
        for s in STREAMS:
            print(f"{s:15s} filled through {coverage(d, s):17s} next free {(free(s) or ['FULL'])[0]}")
    elif cmd == "next":
        print((free(a[1]) or ["FULL"])[0])
    elif cmd == "free":
        print("\n".join(free(a[1], int(a[2]) if len(a) > 2 else 5)) or "FULL")
    elif cmd == "add":
        stream, at, ident = a[1], a[2], a[3]
        if stream not in STREAMS: sys.exit("unknown stream " + stream)
        parse(at)
        d = load()
        if at in filled(d, stream): sys.exit(f"{stream} {at} already filled")
        d["filled"].append({"stream": stream, "at": at, "id": ident, "note": a[4] if len(a) > 4 else "",
                            "recorded": fmt(now())})
        d["filled"].sort(key=lambda f: (f["stream"], f["at"])); save(d); print("ok")
    elif cmd == "budget":
        print(budget(a[1] if len(a) > 1 else None))
    elif cmd == "upload-done":
        d = load(); d["uploads"].append({"day": today_pt(), "stream": a[1], "id": a[2]})
        d["uploads"] = [u for u in d["uploads"] if u["day"] >= (dt.date.today() - dt.timedelta(days=10)).isoformat()]
        save(d); print("left today:", budget())
    else:
        sys.exit(__doc__)
