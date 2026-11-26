"""Publish a carousel to Instagram via the Graph API (Facebook login / system-user token).

The system-user token from Meta Business Suite never expires, so no refresh is needed.
"""
import os
import time

import requests

API_VERSION = os.environ.get("IG_API_VERSION") or "v24.0"
HOST = os.environ.get("IG_API_HOST") or "graph.facebook.com"
BASE = f"https://{HOST}/{API_VERSION}"


def _token():
    return os.environ["IG_ACCESS_TOKEN"]


def _check(r):
    if r.status_code >= 400:
        raise RuntimeError(f"Instagram API error {r.status_code}: {r.text}")
    return r.json()


def _wait_ready(container_id, timeout=300):
    start = time.time()
    while time.time() - start < timeout:
        info = _check(requests.get(f"{BASE}/{container_id}",
                                   params={"fields": "status_code", "access_token": _token()}, timeout=30))
        status = info.get("status_code")
        if status == "FINISHED":
            return
        if status in ("ERROR", "EXPIRED"):
            raise RuntimeError(f"Container {container_id} failed: {info}")
        time.sleep(5)
    raise TimeoutError(f"Container {container_id} not ready after {timeout}s")


def publishing_quota(ig_id):
    return _check(requests.get(f"{BASE}/{ig_id}/content_publishing_limit",
                               params={"fields": "quota_usage,config", "access_token": _token()}, timeout=30))


def publish_carousel(image_urls, caption):
    ig_id = os.environ["IG_USER_ID"]
    if not 2 <= len(image_urls) <= 10:
        raise ValueError("Carousel needs 2-10 images")
    children = []
    for url in image_urls:
        res = _check(requests.post(f"{BASE}/{ig_id}/media", data={
            "image_url": url, "is_carousel_item": "true", "access_token": _token()}, timeout=60))
        children.append(res["id"])
    for cid in children:
        _wait_ready(cid)
    parent = _check(requests.post(f"{BASE}/{ig_id}/media", data={
        "media_type": "CAROUSEL", "children": ",".join(children),
        "caption": caption, "access_token": _token()}, timeout=60))
    _wait_ready(parent["id"])
    published = _check(requests.post(f"{BASE}/{ig_id}/media_publish", data={
        "creation_id": parent["id"], "access_token": _token()}, timeout=60))
    media_id = published["id"]
    link = _check(requests.get(f"{BASE}/{media_id}", params={
        "fields": "permalink", "access_token": _token()}, timeout=30)).get("permalink")
    return media_id, link
