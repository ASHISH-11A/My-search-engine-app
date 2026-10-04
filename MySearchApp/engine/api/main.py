import os
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urlsplit, urlunsplit

import requests
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware

MEILI_URL = os.getenv("MEILI_URL", "http://meilisearch:7700")
MEILI_KEY = os.getenv("MEILI_KEY", "")
SEARXNG_URL = os.getenv("SEARXNG_URL", "http://searxng:8080")
HEADERS = {"Authorization": f"Bearer {MEILI_KEY}"}

app = FastAPI(title="My Search - Local + Web Search")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


def clean_html(value: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", value or "")).strip()


def snippet(text: str, q: str, limit: int = 280) -> str:
    clean = clean_html(text)
    words = [w for w in q.strip().split() if w]
    low = clean.lower()
    pos = -1
    for word in words:
        p = low.find(word.lower())
        if p >= 0:
            pos = p
            break
    if pos < 0:
        return clean[:limit] + ("..." if len(clean) > limit else "")
    start = max(0, pos - 110)
    end = min(len(clean), pos + 230)
    return ("..." if start else "") + clean[start:end] + ("..." if end < len(clean) else "")


def canonical_url(url: str) -> str:
    try:
        p = urlsplit(url.strip())
        if not p.scheme or not p.netloc:
            return url.strip().lower()
        path = p.path.rstrip("/") or "/"
        return urlunsplit((p.scheme.lower(), p.netloc.lower(), path, "", ""))
    except Exception:
        return url.strip().lower()


def local_search(q: str, page: int, per_page: int):
    r = requests.post(
        MEILI_URL + "/indexes/pages/search",
        headers={**HEADERS, "Content-Type": "application/json"},
        json={"q": q, "page": page, "hitsPerPage": per_page,
              "attributesToHighlight": ["title", "content"],
              "highlightPreTag": "<mark>", "highlightPostTag": "</mark>"},
        timeout=12,
    )
    r.raise_for_status()
    d = r.json()
    hits = []
    for h in d.get("hits", []):
        url = h.get("url", "")
        if not url:
            continue
        hits.append({"title": h.get("title") or url, "url": url,
                     "description": h.get("description", ""), "image": h.get("image", ""),
                     "snippet": snippet(h.get("content", ""), q), "source": "local",
                     "engine": "My local index"})
    return hits, int(d.get("estimatedTotalHits", 0) or 0)


def searx_search(q: str, category: str = "general", pageno: int = 1):
    r = requests.get(
        SEARXNG_URL + "/search",
        params={"q": q, "format": "json", "pageno": pageno, "safesearch": 0,
                "categories": category},
        headers={"Accept": "application/json"}, timeout=25,
    )
    r.raise_for_status()
    return r.json()


def normalize_media(item: dict, category: str, q: str):
    url = item.get("url") or item.get("link") or item.get("source") or ""
    if not url:
        return None
    thumb = item.get("thumbnail") or item.get("img_src") or item.get("image") or item.get("thumbnail_src") or ""
    title = clean_html(item.get("title") or item.get("name") or url)
    content = clean_html(item.get("content") or item.get("description") or "")
    result = {"title": title, "url": url, "description": content,
              "snippet": snippet(content, q), "image": thumb, "source": "web",
              "engine": item.get("engine") or "SearXNG", "type": category}
    for key in ("publishedDate", "published_date", "author", "length", "duration", "resolution", "iframe_src", "metadata"):
        if item.get(key) is not None:
            result[key] = item.get(key)
    if category == "videos" and item.get("iframe_src"):
        result["video"] = item.get("iframe_src")
    return result


def web_search(q: str, pageno: int = 1):
    d = searx_search(q, "general", pageno)
    hits = []
    for item in d.get("results", []):
        normalized = normalize_media(item, "general", q)
        if normalized:
            hits.append(normalized)
    return hits, d


def merge_unique(items, limit):
    out, seen = [], set()
    for item in items:
        key = canonical_url(item.get("url", ""))
        if not key or key in seen:
            continue
        seen.add(key); out.append(item)
        if len(out) >= limit:
            break
    return out


@app.get("/health")
def health():
    return {"ok": True}


@app.get("/search")
def search(q: str = Query(..., min_length=1), page: int = 1, per_page: int = 10):
    page = max(1, page); per_page = min(max(per_page, 1), 20)
    local_hits, local_total, web_hits, web_error = [], 0, [], None
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = {pool.submit(local_search, q, page, min(per_page, 10)): "local",
                   pool.submit(web_search, q, page): "web"}
        for future in as_completed(futures):
            kind = futures[future]
            try:
                if kind == "local": local_hits, local_total = future.result()
                else: web_hits, _ = future.result()
            except Exception as exc:
                if kind == "web": web_error = str(exc)
    merged = merge_unique(local_hits + web_hits, per_page)
    if len(merged) < per_page and page == 1:
        try: merged = merge_unique(merged + web_search(q, 2)[0], per_page)
        except Exception: pass
    return {"query": q, "page": page, "perPage": per_page,
            "total": max(local_total + len(web_hits), len(merged)),
            "localTotal": local_total, "webCount": len(web_hits),
            "totalPages": max(1, (max(local_total, len(merged)) + per_page - 1) // per_page),
            "hits": merged, "webAvailable": web_error is None,
            "webError": web_error if web_error else None}


@app.get("/media")
def media(q: str = Query(..., min_length=1), category: str = Query("images"), page: int = 1, per_page: int = 24):
    category = category.lower().strip()
    if category not in {"images", "news", "videos"}:
        return {"query": q, "category": category, "hits": [], "total": 0,
                "error": "category must be images, news, or videos"}
    page = max(1, page); per_page = min(max(per_page, 1), 50)
    try:
        d = searx_search(q, category, page)
        hits = [x for item in d.get("results", []) if (x := normalize_media(item, category, q))]
        hits = merge_unique(hits, per_page)
        return {"query": q, "category": category, "page": page,
                "perPage": per_page, "total": len(hits), "hits": hits,
                "webAvailable": True}
    except Exception as exc:
        return {"query": q, "category": category, "page": page,
                "perPage": per_page, "total": 0, "hits": [],
                "webAvailable": False, "error": str(exc)}


@app.get("/suggest")
def suggest(q: str = Query("", max_length=100)):
    if not q.strip(): return {"suggestions": []}
    try:
        r = requests.post(MEILI_URL + "/indexes/pages/search",
                          headers={**HEADERS, "Content-Type": "application/json"},
                          json={"q": q, "limit": 8, "attributesToRetrieve": ["title", "url"]}, timeout=8)
        r.raise_for_status(); out, seen = [], set()
        for h in r.json().get("hits", []):
            t = (h.get("title") or h.get("url", "")).strip()
            if t and t.lower() not in seen: seen.add(t.lower()); out.append(t[:120])
        return {"suggestions": out}
    except Exception:
        return {"suggestions": []}
