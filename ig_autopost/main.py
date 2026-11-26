"""Daily Instagram autopost for Super Deals India.

Stages (run by GitHub Actions, see .github/workflows/daily_post.yml):
  python -m ig_autopost.main prepare   -> picks today's calendar row, writes copy (Gemini), renders slides
  (workflow commits + pushes posts/<date>/ so the images get public URLs)
  python -m ig_autopost.main publish   -> posts the carousel to Instagram, records it in posts/posted.json
  python -m ig_autopost.main preview --date 2026-12-01  -> local test: write + render only, never posts
"""
import argparse
import csv
import json
import os
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests

from .facebook import post_to_page
from .instagram import publish_carousel
from .render import render_post
from .writer import build_caption, write_post

BASE = Path(__file__).resolve().parent.parent
CALENDAR = BASE / "content" / "calendar.csv"
POSTS = BASE / "posts"
POSTED = POSTS / "posted.json"
IST = timezone(timedelta(hours=5, minutes=30))


def today_ist():
    return datetime.now(IST).strftime("%Y-%m-%d")


def load_row(date):
    with open(CALENDAR, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row["date"].strip() == date:
                return row
    return None


def load_posted():
    return json.loads(POSTED.read_text()) if POSTED.exists() else {}


def set_output(name, value):
    out = os.environ.get("GITHUB_OUTPUT")
    if out:
        with open(out, "a") as f:
            f.write(f"{name}={value}\n")


def prepare(date):
    posted = load_posted()
    if date in posted:
        set_output("ready", "false")
        if fb_enabled() and "facebook" not in posted[date] and (POSTS / date / "content.json").exists():
            print(f"{date} already on Instagram; Facebook post still missing.")
            set_output("fb_ready", "true")
        else:
            print(f"{date} already posted, nothing to do.")
        return
    row = load_row(date)
    if not row:
        print(f"No calendar row for {date}. Add one to content/calendar.csv.")
        set_output("ready", "false")
        return
    content = write_post(row)
    out_dir = POSTS / date
    paths = render_post(content, out_dir)
    content["slide_files"] = [p.name for p in paths]
    content["caption_full"] = build_caption(content)
    (out_dir / "content.json").write_text(json.dumps(content, ensure_ascii=False, indent=2))
    print(f"Prepared {len(paths)} slides for {date}: {row['topic']}")
    set_output("ready", "true")


def public_url(date, name):
    repo = os.environ["GITHUB_REPOSITORY"]          # owner/repo, set by GitHub Actions
    branch = os.environ.get("IMAGE_BRANCH") or os.environ.get("GITHUB_REF_NAME") or "main"
    return f"https://raw.githubusercontent.com/{repo}/{branch}/posts/{date}/{name}"


def wait_public(urls, timeout=180):
    start = time.time()
    for u in urls:
        while True:
            r = requests.head(u, timeout=20)
            if r.status_code == 200 and "image" in r.headers.get("content-type", ""):
                break
            if time.time() - start > timeout:
                raise TimeoutError(f"Image not publicly reachable: {u} ({r.status_code}). Is the repo public?")
            time.sleep(5)


def publish(date):
    posted = load_posted()
    if date in posted:
        print(f"{date} already posted: {posted[date].get('permalink')}")
        return
    content = json.loads((POSTS / date / "content.json").read_text())
    urls = [public_url(date, n) for n in content["slide_files"]]
    wait_public(urls)
    media_id, link = publish_carousel(urls, content["caption_full"])
    posted[date] = {"topic": content["topic"], "media_id": media_id, "permalink": link,
                    "posted_at": datetime.now(IST).isoformat(timespec="seconds")}
    POSTED.write_text(json.dumps(posted, ensure_ascii=False, indent=2))
    print(f"Posted {date}: {link}")
    if fb_enabled():
        facebook(date)


def fb_enabled():
    return (os.environ.get("POST_TO_FACEBOOK") or "true").lower() != "false"


def facebook(date):
    """Post the same slides to the Facebook Page. Never undoes or blocks the Instagram post."""
    posted = load_posted()
    entry = posted.get(date)
    if not entry:
        print(f"{date} is not on Instagram yet; skipping Facebook.")
        return
    if "facebook" in entry:
        print(f"{date} already on Facebook: {entry['facebook']}")
        return
    content = json.loads((POSTS / date / "content.json").read_text())
    urls = [public_url(date, n) for n in content["slide_files"]]
    try:
        wait_public(urls)
        post_id, link = post_to_page(urls, content["caption_full"])
        entry["facebook"] = link
        entry.pop("facebook_error", None)
        print(f"Posted {date} to Facebook: {link}")
    except Exception as e:  # Instagram post stays; error is recorded and shown as a warning
        entry["facebook_error"] = str(e)[:500]
        print(f"::warning::Facebook post failed for {date}: {e}")
    posted[date] = entry
    POSTED.write_text(json.dumps(posted, ensure_ascii=False, indent=2))


def preview(date):
    row = load_row(date)
    if not row:
        sys.exit(f"No calendar row for {date}")
    content = write_post(row)
    out_dir = BASE / "preview" / date
    render_post(content, out_dir)
    (out_dir / "caption.txt").write_text(build_caption(content))
    print(f"Preview written to {out_dir}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("stage", choices=["prepare", "publish", "facebook", "preview"])
    ap.add_argument("--date", default=None, help="YYYY-MM-DD (default: today in IST)")
    a = ap.parse_args()
    d = a.date or today_ist()
    {"prepare": prepare, "publish": publish, "facebook": facebook, "preview": preview}[a.stage](d)
