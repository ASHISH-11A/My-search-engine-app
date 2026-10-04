# My-search-engine-app
My Search is a self-hosted, Google-like search engine powered by SearXNG and Meilisearch. It combines local indexing with web search and provides dedicated All, Images, News, and Videos tabs, running locally on Windows with Docker.
It combines a **local search index powered by Meilisearch** with **SearXNG web search** to provide broader search results while maintaining your own searchable index.

## ✨ Features

- 🔎 **All Search**
  - Search your local indexed content
  - Search the broader web through SearXNG
  - Merge and remove duplicate results

- 🖼️ **Image Search**
  - Dedicated image search tab
  - Image thumbnails
  - Image titles and source information
  - Open the original image/page

- 📰 **News Search**
  - Dedicated news tab
  - News headlines
  - Source information
  - Publication information
  - Open the original article

- 🎥 **Video Search**
  - Dedicated video search tab
  - Video thumbnails
  - Video titles
  - Source information
  - Open the original video/page

## 🗂️ Search Tabs

The Windows application provides:

**All | Images | News | Videos**

Each category uses the appropriate SearXNG search category while the **All** tab can combine results from the local index and web search.

## 🏗️ Architecture

```text
                    My Search
                        │
              ┌─────────┴─────────┐
              │                   │
        Local Search          Web Search
              │                   │
        Meilisearch            SearXNG
              │                   │
              └─────────┬─────────┘
                        │
                 My Search API
                        │
                        ▼
                 Search Interface
