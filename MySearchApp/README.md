# My Search Desktop Application

Windows desktop wrapper for the My Search stack: Meilisearch + crawler + SearXNG + custom web UI.

## Requirements
- Windows 10/11
- Docker Desktop with WSL2 backend

The application starts Docker Compose automatically. On first use Docker may need to download images and build the services, so startup can take several minutes.

## Build the Windows app
Install Node.js 20+ then run:

    npm install
    npm run dist

The `dist` folder will contain a portable EXE and an installer.


## V5 tabs
The search interface now includes All, Images, News, and Videos tabs. Images/news/videos are powered by SearXNG category searches through the local FastAPI `/media` endpoint. SearXNG supports category-specific API searches and JSON output when JSON is enabled in settings.
