"""Post the same carousel to the Super Deals India Facebook Page as a multi-photo post.

Uses the same system-user token (needs pages_show_list, pages_read_engagement, pages_manage_posts).
The Page is found automatically: the Page linked to IG_USER_ID, or FB_PAGE_ID if set.
"""
import os

import requests

API_VERSION = os.environ.get("IG_API_VERSION") or "v24.0"
BASE = f"https://graph.facebook.com/{API_VERSION}"


def _check(r):
    if r.status_code >= 400:
        raise RuntimeError(f"Facebook API error {r.status_code}: {r.text}")
    return r.json()


def _page():
    """Return (page_id, page_access_token)."""
    token = os.environ["IG_ACCESS_TOKEN"]
    want_page = os.environ.get("FB_PAGE_ID")
    ig_id = os.environ.get("IG_USER_ID")
    data = _check(requests.get(f"{BASE}/me/accounts", params={
        "fields": "id,name,access_token,instagram_business_account", "limit": 50,
        "access_token": token}, timeout=30)).get("data", [])
    for p in data:
        linked = (p.get("instagram_business_account") or {}).get("id")
        if (want_page and p["id"] == want_page) or (not want_page and linked == ig_id):
            return p["id"], p["access_token"]
    if len(data) == 1 and not want_page:
        return data[0]["id"], data[0]["access_token"]
    raise RuntimeError("Facebook Page not found for this token. Set FB_PAGE_ID or check the system user's Page access.")


def post_to_page(image_urls, caption):
    page_id, page_token = _page()
    media = []
    for url in image_urls:
        res = _check(requests.post(f"{BASE}/{page_id}/photos", data={
            "url": url, "published": "false", "access_token": page_token}, timeout=90))
        media.append(res["id"])
    data = {"message": caption, "access_token": page_token}
    for i, mid in enumerate(media):
        data[f"attached_media[{i}]"] = f'{{"media_fbid":"{mid}"}}'
    post = _check(requests.post(f"{BASE}/{page_id}/feed", data=data, timeout=90))
    post_id = post["id"]
    link = f"https://www.facebook.com/{post_id}"
    return post_id, link
