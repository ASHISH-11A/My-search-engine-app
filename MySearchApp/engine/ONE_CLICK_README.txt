MY SEARCH - ONE CLICK V4
========================

Double-click:
    START_SEARCH_ENGINE.bat

V4 adds SearXNG web search to the previous local search engine.

WHAT IT DOES
------------
- Keeps your own crawler + Meilisearch local index.
- Adds SearXNG as a web/metasearch layer.
- Runs local and web search at the same time.
- Merges results and removes duplicate URLs.
- Labels each result as LOCAL INDEX or WEB.
- Shows the SearXNG engine that supplied web results when available.
- Keeps the automatic free-port selection and Docker conflict cleanup.

WHY SEARXNG
-----------
SearXNG is a metasearch engine: it queries multiple search services and
combines their results. It does not contain Google's complete index itself.
That is why this setup keeps Meilisearch/crawler as your permanent local index
and uses SearXNG to make the search much broader.

IMPORTANT
---------
This is still your own local search UI. It is not Google and does not pretend
to be Google. Web results are obtained through your local SearXNG container.

SearXNG's JSON API is enabled in searxng/settings.yml so the API container can
request /search?q=...&format=json internally over the Docker network.

The SearXNG limiter is disabled because this instance is intended for local
Docker-to-Docker use. Do NOT expose the SearXNG container directly to the
public internet without adding appropriate protection.

CRAWLER
-------
The crawler still starts from SEEDS in docker-compose.yml. Change SEEDS to
sites you want in your own permanent index. SearXNG provides broad web search
without requiring those pages to be crawled first.

TROUBLESHOOTING
---------------
If the first search says services are starting, wait 10-30 seconds and retry.
Use VIEW_CRAWLER_LOGS.bat to inspect crawler output.
Use docker compose logs searxng to inspect SearXNG.

The launcher removes old fixed-name containers from previous versions and
selects a free web port between 3000 and 3099.
