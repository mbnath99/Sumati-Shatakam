#!/usr/bin/env python3
"""
Builds today's post:  picks the padyam for today's date, renders video + image + captions,
and writes the WhatsApp/Facebook share page into ./site (published by GitHub Pages).

  python daily.py                    # today's padyam (India time)
  python daily.py --date 2026-11-01  # padyam for a given date
  python daily.py --verse 49         # force a specific padyam
  python daily.py --schedule 10      # just print the next 10 days' schedule
"""
import argparse, datetime as dt, json, os, shutil, sys
from zoneinfo import ZoneInfo
import render

HERE = os.path.dirname(os.path.abspath(__file__))
IST = ZoneInfo("Asia/Kolkata")

def playlist(cfg, book):
    skip = set(cfg.get("extra_skip", []))
    out = []
    for v in book["verses"]:
        if v.get("skip") or v["n"] in skip:
            continue
        if cfg.get("skip_flagged") and v.get("review"):
            continue
        out.append(v)
    return out

def verse_for(date, cfg, book):
    plist = playlist(cfg, book)
    start = dt.date.fromisoformat(cfg["start_date"])
    idx = (date - start).days
    if idx < 0:
        return None, f"start_date {start} is in the future"
    if idx >= len(plist):
        if cfg.get("after_last", "repeat") == "stop":
            return None, "all padyams have been posted (after_last = stop)"
        idx %= len(plist)
    return plist[idx], None

def write_output(name, value):
    gh = os.environ.get("GITHUB_OUTPUT")
    if gh:
        with open(gh, "a", encoding="utf-8") as f:
            f.write(f"{name}={value}\n")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date")
    ap.add_argument("--verse", type=int)
    ap.add_argument("--schedule", type=int, help="print the schedule for the next N days and exit")
    ap.add_argument("--site", default=os.path.join(HERE, "site"))
    a = ap.parse_args()
    cfg, book = render.load_config(), render.load_book()
    today = dt.date.fromisoformat(a.date) if a.date else dt.datetime.now(IST).date()

    if a.schedule:
        for i in range(a.schedule):
            d = today + dt.timedelta(days=i)
            v, why = verse_for(d, cfg, book)
            print(d, "->", f"padyam {v['n']}: {v['padyam'][0]}" if v else why)
        return

    if a.verse:
        verse = next(v for v in book["verses"] if v["n"] == a.verse)
    else:
        verse, why = verse_for(today, cfg, book)
        if verse is None:
            print("Nothing to post:", why); write_output("post", "false"); return

    site = a.site
    if os.path.exists(site): shutil.rmtree(site)
    os.makedirs(os.path.join(site, "media"))
    stem = f"{today.isoformat()}-padyam-{verse['n']:03d}"
    video = os.path.join(site, "media", stem + ".mp4")
    image = os.path.join(site, "media", stem + ".jpg")
    print(f"{today}: padyam {verse['n']} — {verse['padyam'][0]}")
    render.render_card(verse, cfg, image)
    dur = render.render_video(verse, cfg, video, cfg.get("sound", {}))
    caps = render.captions(verse, cfg, book)
    today_json = dict(date=today.isoformat(), n=verse["n"], padyam=verse["padyam"], bhavam=verse["bhavam"],
                      video=f"media/{stem}.mp4", image=f"media/{stem}.jpg", duration=round(dur, 1),
                      title=book["title"], handle=cfg.get("handle", ""), **caps)
    with open(os.path.join(site, "today.json"), "w", encoding="utf-8") as f:
        json.dump(today_json, f, ensure_ascii=False, indent=1)
    shutil.copy(os.path.join(HERE, "site_template", "index.html"), os.path.join(site, "index.html"))
    os.makedirs(os.path.join(site, "fonts"))
    for fn in ("NotoSansTelugu.ttf", "Suravaram.ttf"):
        shutil.copy(os.path.join(HERE, "fonts", fn), os.path.join(site, "fonts", fn))
    open(os.path.join(site, ".nojekyll"), "w").close()
    print(f"built site/ ({dur:.1f}s video)")
    write_output("post", "true")
    write_output("n", verse["n"])
    write_output("date", today.isoformat())
    write_output("video_path", video)
    write_output("video_rel", f"media/{stem}.mp4")
    write_output("image_rel", f"media/{stem}.jpg")

if __name__ == "__main__":
    main()
