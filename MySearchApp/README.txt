MY SEARCH - DESKTOP APPLICATION

This package turns the existing My Search Docker stack into a Windows desktop application.

The desktop app:
- starts Docker Desktop when needed
- starts the local My Search stack
- chooses a free local port automatically
- opens the search UI inside the application window
- keeps the existing Meilisearch/crawler/SearXNG architecture
- stops the Docker stack when the application exits

REQUIREMENTS
- Windows 10/11
- Docker Desktop using WSL2
- Internet access on first run so Docker can pull/build images

BUILD A WINDOWS EXE
1. Double-click BUILD_WINDOWS_APP.bat
2. It installs Node.js LTS if needed.
3. It runs npm install and builds the Electron application.
4. The dist folder will contain a portable EXE and an installer.

RUN WITHOUT BUILDING
- Double-click RUN_APP_DEV.bat after Node.js is installed.

IMPORTANT
Docker Desktop is still required because the search backend runs in Docker.
The app itself is the desktop front end/orchestrator; it does not replace Docker.
