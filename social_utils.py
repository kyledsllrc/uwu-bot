import re
import json
import os
import time
import asyncio
from html import unescape
import urllib.request
import urllib.parse
import urllib.error

# Simple in-memory cache to avoid repeated fetches
_SIMPLE_CACHE = {}
_CACHE_TTL = 300  # seconds
_DISK_CACHE_FILE = "social_cache.json"
_DISK_CACHE = {}

DEFAULT_APIFY_TOKEN = "apify_api_i0BKd3PhiRGpbsxhl0szT0fBuj8wSW2CziLN"


def _load_disk_cache():
    try:
        if _DISK_CACHE:
            return
        if not os.path.exists(_DISK_CACHE_FILE):
            return
        with open(_DISK_CACHE_FILE, "r", encoding="utf-8") as f:
            raw = json.load(f)
            _DISK_CACHE.update(raw)
    except Exception:
        return


def _save_disk_cache():
    try:
        with open(_DISK_CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(_DISK_CACHE, f)
    except Exception:
        return

def _sync_fetch_html(url, headers=None, timeout=10):
    req = urllib.request.Request(url, headers=headers or {})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            text = resp.read().decode('utf-8', errors='ignore')
            return text, resp.status
    except urllib.error.HTTPError as e:
        return None, e.code
    except Exception:
        return None, None


async def fetch_html(url, headers=None, timeout=10, retries=3):
    """Fetch HTML with in-memory + disk caching and simple retries/backoff.

    Returns (text, status) or (None, status/None) on failure.
    """
    _load_disk_cache()
    now = time.time()
    # Disk cache lookup
    try:
        entry = _DISK_CACHE.get(url)
        if entry and now - entry.get("ts", 0) < _CACHE_TTL:
            return entry.get("text"), 200
    except Exception:
        pass

    # In-memory cache
    cached = _SIMPLE_CACHE.get(url)
    if cached and now - cached[0] < _CACHE_TTL:
        return cached[1], 200

    default_headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/125.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://www.google.com/",
        "Connection": "keep-alive",
    }
    if headers:
        default_headers.update(headers)

    loop = asyncio.get_running_loop()
    attempt = 0
    backoff = 0.5
    while attempt < retries:
        attempt += 1
        try:
            text, status = await loop.run_in_executor(None, _sync_fetch_html, url, default_headers, timeout)
            if status == 200 and text:
                _SIMPLE_CACHE[url] = (now, text)
                try:
                    _DISK_CACHE[url] = {"ts": now, "text": text}
                    _save_disk_cache()
                except Exception:
                    pass
                return text, status
            if status and 400 <= status < 500:
                return None, status
        except Exception:
            pass
        await asyncio.sleep(backoff)
        backoff *= 1.5
    return None, None


def extract_og_meta(html, prop):
    m = re.search(rf'<meta[^>]+property=["\']{re.escape(prop)}["\'][^>]+content=["\']([^"\']+)["\']', html, re.I)
    if m:
        return unescape(m.group(1)).strip()
    m = re.search(rf'<meta[^>]+name=["\']{re.escape(prop)}["\'][^>]+content=["\']([^"\']+)["\']', html, re.I)
    if m:
        return unescape(m.group(1)).strip()
    return None


def extract_json_ld(html):
    # extract first <script type="application/ld+json">...</script>
    m = re.search(r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>', html, re.S | re.I)
    if not m:
        return None
    try:
        return json.loads(m.group(1))
    except Exception:
        return None


def extract_window_shared_data(html):
    # Look for window._sharedData = { ... }; using brace matching to be robust
    idx = html.find('window._sharedData')
    if idx == -1:
        return None
    # find the first '{' after the assignment
    brace_idx = html.find('{', idx)
    if brace_idx == -1:
        return None
    depth = 0
    end_idx = None
    for i in range(brace_idx, len(html)):
        ch = html[i]
        if ch == '{':
            depth += 1
        elif ch == '}':
            depth -= 1
            if depth == 0:
                end_idx = i
                break
    if end_idx is None:
        return None
    s = html[brace_idx:end_idx+1]
    try:
        return json.loads(s)
    except Exception:
        return None


def parse_counts_from_description(desc):
    if not desc:
        return {}
    counts = {}
    m = re.search(r'([\d,\.]+)\s+Followers', desc, re.I)
    if m:
        counts['followers'] = m.group(1)
    m = re.search(r'([\d,\.]+)\s+Following', desc, re.I)
    if m:
        counts['following'] = m.group(1)
    m = re.search(r'([\d,\.]+)\s+Posts', desc, re.I)
    if m:
        counts['posts'] = m.group(1)
    return counts


def get_instagram_counts_from_shared_data(shared):
    try:
        user = shared['entry_data']['ProfilePage'][0]['graphql']['user']
        followers = user.get('edge_followed_by', {}).get('count')
        following = user.get('edge_follow', {}).get('count')
        posts = user.get('edge_owner_to_timeline_media', {}).get('count')
        return {
            'followers': str(followers) if followers is not None else None,
            'following': str(following) if following is not None else None,
            'posts': str(posts) if posts is not None else None,
        }
    except Exception:
        return {}


def get_instagram_counts_from_html(html):
    # Regex-based best-effort extraction from the page HTML (handles sharedData JSON without full parse)
    counts = {}
    m = re.search(r'"edge_followed_by"\s*:\s*\{[^}]*"count"\s*:\s*([\d,\.]+)', html)
    if m:
        counts['followers'] = m.group(1)
    m = re.search(r'"edge_follow"\s*:\s*\{[^}]*"count"\s*:\s*([\d,\.]+)', html)
    if m:
        counts['following'] = m.group(1)
    m = re.search(r'"edge_owner_to_timeline_media"\s*:\s*\{[^}]*"count"\s*:\s*([\d,\.]+)', html)
    if m:
        counts['posts'] = m.group(1)
    return counts


def get_instagram_profile_from_shared_data(shared):
    try:
        user = shared['entry_data']['ProfilePage'][0]['graphql']['user']
        profile = {
            'name': user.get('full_name'),
            'biography': user.get('biography'),
            'is_private': bool(user.get('is_private')),
            'is_verified': bool(user.get('is_verified')),
            'profile_pic_url': user.get('profile_pic_url_hd') or user.get('profile_pic_url'),
            'external_url': user.get('external_url'),
            'category_name': user.get('category_name'),
            'username': user.get('username'),
        }
        if isinstance(user.get('edge_followed_by'), dict):
            profile['followers'] = str(user['edge_followed_by'].get('count'))
        if isinstance(user.get('edge_follow'), dict):
            profile['following'] = str(user['edge_follow'].get('count'))
        if isinstance(user.get('edge_owner_to_timeline_media'), dict):
            profile['posts'] = str(user['edge_owner_to_timeline_media'].get('count'))
        return profile
    except Exception:
        return {}


def get_instagram_profile_from_html(html):
    profile = {
        'profile_pic_url': extract_og_meta(html, 'og:image'),
        'name': extract_og_meta(html, 'og:title'),
        'biography': extract_og_meta(html, 'og:description'),
    }
    counts = {}
    if profile['biography']:
        counts, _ = _parse_counts_from_description(profile['biography'])
    profile.update(counts)
    return profile


def get_tiktok_profile_from_html(html):
    profile = {
        'profile_pic_url': extract_og_meta(html, 'og:image'),
        'name': extract_og_meta(html, 'og:title'),
        'biography': extract_og_meta(html, 'og:description'),
        'url': extract_og_meta(html, 'og:url'),
    }
    counts = get_tiktok_counts_from_sig_state(html) or {}
    if not counts and profile['biography']:
        followers = re.search(r'([\d,\.]+)\s+Followers', profile['biography'], re.I)
        if followers:
            counts['followers'] = followers.group(1)
        posts = re.search(r'([\d,\.]+)\s+Videos', profile['biography'], re.I)
        if posts:
            counts['posts'] = posts.group(1)
    profile.update(counts)
    profile['is_verified'] = 'verified' in (profile.get('name') or '').lower()
    return profile


def get_facebook_profile_from_html(html):
    profile = {
        'profile_pic_url': extract_og_meta(html, 'og:image'),
        'name': extract_og_meta(html, 'og:title'),
        'biography': extract_og_meta(html, 'og:description'),
        'url': extract_og_meta(html, 'og:url'),
    }
    if profile['biography']:
        followers = re.search(r'([\d,\.]+)\s+Followers', profile['biography'], re.I)
        if followers:
            profile['followers'] = followers.group(1)
        likes = re.search(r'([\d,\.]+)\s+Likes', profile['biography'], re.I)
        if likes:
            profile['likes'] = likes.group(1)
    return profile


def get_tiktok_counts_from_sig_state(html):
    # Best-effort: look for JSON objects containing 'followers' or 'fans'
    m = re.search(r'(?:window\.__INIT_PROPS__|window\.__INIT_DATA__|<script[^>]+id="SIGI_STATE"[^>]*>)(.*?)</script>', html, re.S | re.I)
    text = None
    if m:
        text = m.group(1)
    else:
        # Search for JSON-like blocks
        m = re.search(r'{\s*"UserModule".*?}', html, re.S)
        if m:
            text = m.group(0)
    if not text:
        # fallback: return empty
        return {}
    # find numeric follower fields
    try:
        # Extract numbers by key names
        m = re.search(r'"fans"\s*:\s*([\d,\.]+)', text)
        if m:
            return {'followers': m.group(1)}
        m = re.search(r'"followers"\s*:\s*([\d,\.]+)', text)
        if m:
            return {'followers': m.group(1)}
    except Exception:
        pass
    return {}


# expose a helper to get profile info for instagram
_dummy = get_instagram_counts_from_shared_data  # keep linter quiet


def _sync_post_json(url, payload, timeout=45):
    data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
        },
        method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            if 200 <= resp.status < 300:
                body = resp.read().decode('utf-8', errors='ignore')
                return json.loads(body)
    except Exception as exc:
        print(f"Apify request failed: {exc}")
    return None


async def try_instagram_api(username):
    """Attempt to use Apify API (APIFY_API_TOKEN / APIFY_TOKEN) or IG_API_TOKEN if credentials are available."""
    token = (
        os.getenv("APIFY_API_TOKEN") or
        os.getenv("APIFY_TOKEN") or
        os.getenv("APIFY_KEY") or
        os.getenv("IG_API_TOKEN") or
        DEFAULT_APIFY_TOKEN
    )
    if not token:
        return None

    clean_user = username.strip().lstrip("@")
    if not clean_user:
        return None

    loop = asyncio.get_running_loop()

    # Try actor 1: apify~instagram-profile-scraper
    url1 = f"https://api.apify.com/v2/acts/apify~instagram-profile-scraper/run-sync-get-dataset-items?token={token}"
    payload1 = {"usernames": [clean_user], "resultsLimit": 1}
    try:
        items = await loop.run_in_executor(None, _sync_post_json, url1, payload1, 30)
        if isinstance(items, list) and len(items) > 0:
            data = items[0]
            if isinstance(data, dict) and (data.get("username") or data.get("followersCount") is not None or data.get("fullName")):
                return {
                    "username": data.get("username") or clean_user,
                    "name": data.get("fullName") or data.get("name"),
                    "biography": data.get("biography") or data.get("bio"),
                    "followers": str(data["followersCount"]) if data.get("followersCount") is not None else None,
                    "following": str(data["followsCount"]) if data.get("followsCount") is not None else None,
                    "posts": str(data["postsCount"]) if data.get("postsCount") is not None else None,
                    "profile_pic_url": data.get("profilePicUrlHD") or data.get("profilePicUrl"),
                    "is_verified": bool(data.get("isVerified")),
                    "is_private": bool(data.get("isPrivate")),
                    "external_url": data.get("externalUrl") or data.get("website"),
                }
    except Exception as exc:
        print(f"Apify actor 1 failed: {exc}")

    # Fallback to actor 2: apify~instagram-scraper
    url2 = f"https://api.apify.com/v2/acts/apify~instagram-scraper/run-sync-get-dataset-items?token={token}"
    payload2 = {"directUrls": [f"https://www.instagram.com/{clean_user}/"], "resultsType": "details", "resultsLimit": 1}
    try:
        items2 = await loop.run_in_executor(None, _sync_post_json, url2, payload2, 30)
        if isinstance(items2, list) and len(items2) > 0:
            data = items2[0]
            if isinstance(data, dict) and (data.get("username") or data.get("followersCount") is not None or data.get("fullName")):
                return {
                    "username": data.get("username") or clean_user,
                    "name": data.get("fullName") or data.get("name"),
                    "biography": data.get("biography") or data.get("bio"),
                    "followers": str(data["followersCount"]) if data.get("followersCount") is not None else None,
                    "following": str(data["followsCount"]) if data.get("followsCount") is not None else None,
                    "posts": str(data["postsCount"]) if data.get("postsCount") is not None else None,
                    "profile_pic_url": data.get("profilePicUrlHD") or data.get("profilePicUrl"),
                    "is_verified": bool(data.get("isVerified")),
                    "is_private": bool(data.get("isPrivate")),
                    "external_url": data.get("externalUrl") or data.get("website"),
                }
    except Exception as exc:
        print(f"Apify actor 2 failed: {exc}")

    return None


async def try_facebook_api(identifier):
    token = os.getenv("FB_API_TOKEN")
    if not token:
        return None
    # Placeholder for Graph API lookup
    return None


async def try_tiktok_api(username):
    token = os.getenv("TT_API_TOKEN")
    if not token:
        return None
    # Placeholder: TikTok API access is not public; leave as None unless configured.
    return None
