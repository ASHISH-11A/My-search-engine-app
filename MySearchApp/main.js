const { app, BrowserWindow, ipcMain, shell } = require('electron');
const path = require('path');
const fs = require('fs');
const net = require('net');
const { spawn, execFile } = require('child_process');

let mainWindow;
let engineProcess = null;
let webPort = null;

function engineRoot() {
  return app.isPackaged
    ? path.join(process.resourcesPath, 'engine')
    : path.join(__dirname, 'engine');
}

function isFree(port) {
  return new Promise(resolve => {
    const s = net.createServer();
    s.once('error', () => resolve(false));
    s.once('listening', () => s.close(() => resolve(true)));
    s.listen(port, '127.0.0.1');
  });
}

async function findPort() {
  for (let p = 3000; p <= 3099; p++) if (await isFree(p)) return p;
  throw new Error('No free port found between 3000 and 3099.');
}

function run(command, args, options = {}) {
  return new Promise((resolve, reject) => {
    execFile(command, args, { windowsHide: true, ...options }, (error, stdout, stderr) => {
      if (error) reject(Object.assign(error, { stdout, stderr }));
      else resolve({ stdout, stderr });
    });
  });
}

async function dockerReady() {
  try { await run('docker', ['info']); return true; } catch { return false; }
}

async function startDockerDesktop() {
  const candidates = [
    path.join(process.env.ProgramFiles || 'C:\\Program Files', 'Docker', 'Docker', 'Docker Desktop.exe'),
    path.join(process.env.LOCALAPPDATA || '', 'Docker', 'Docker Desktop.exe')
  ];
  for (const p of candidates) {
    if (fs.existsSync(p)) { spawn(p, [], { detached: true, stdio: 'ignore' }).unref(); return; }
  }
  try { spawn('Docker Desktop', [], { detached: true, stdio: 'ignore', shell: true }).unref(); } catch {}
}

async function waitDocker(ms = 180000) {
  const started = Date.now();
  while (Date.now() - started < ms) {
    if (await dockerReady()) return true;
    await new Promise(r => setTimeout(r, 2000));
  }
  return false;
}

function runCompose(args, env) {
  return new Promise((resolve, reject) => {
    const child = spawn('docker', ['compose', ...args], {
      cwd: engineRoot(),
      env: { ...process.env, ...env, COMPOSE_PROJECT_NAME: 'mysearch' },
      windowsHide: true
    });
    let output = '';
    child.stdout.on('data', d => { output += d.toString(); mainWindow?.webContents.send('log', d.toString()); });
    child.stderr.on('data', d => { output += d.toString(); mainWindow?.webContents.send('log', d.toString()); });
    child.on('error', reject);
    child.on('close', code => code === 0 ? resolve(output) : reject(new Error(output || `docker compose exited ${code}`)));
  });
}

async function waitForWeb(port) {
  const started = Date.now();
  while (Date.now() - started < 120000) {
    try {
      const r = await fetch(`http://127.0.0.1:${port}`);
      if (r.ok) return true;
    } catch {}
    await new Promise(r => setTimeout(r, 1500));
  }
  return false;
}

async function startEngine() {
  if (engineProcess) return { port: webPort };
  mainWindow.webContents.send('status', 'Checking Docker Desktop…');
  if (!(await dockerReady())) {
    mainWindow.webContents.send('status', 'Starting Docker Desktop…');
    await startDockerDesktop();
    if (!(await waitDocker())) throw new Error('Docker Desktop did not become ready. Install/start Docker Desktop and try again.');
  }
  webPort = await findPort();
  mainWindow.webContents.send('status', `Starting search engine on port ${webPort}…`);
  const env = { WEB_PORT: String(webPort) };
  try { await runCompose(['down', '--remove-orphans'], env); } catch {}
  engineProcess = true;
  try {
    await runCompose(['up', '--build', '-d'], env);
    const ok = await waitForWeb(webPort);
    if (!ok) throw new Error('The search web service did not become ready.');
    mainWindow.webContents.send('status', 'Search engine is ready.');
    await mainWindow.loadURL(`http://127.0.0.1:${webPort}`);
    return { port: webPort };
  } catch (e) {
    engineProcess = null;
    throw e;
  }
}

async function stopEngine() {
  if (!engineProcess) return;
  try { await runCompose(['down', '--remove-orphans'], { WEB_PORT: String(webPort || 3000) }); } catch {}
  engineProcess = null;
  webPort = null;
  mainWindow.webContents.send('status', 'Search engine stopped.');
}

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1050,
    height: 760,
    minWidth: 850,
    minHeight: 600,
    backgroundColor: '#111827',
    webPreferences: { preload: path.join(__dirname, 'preload.js'), contextIsolation: true, nodeIntegration: false }
  });
  mainWindow.loadFile(path.join(__dirname, 'launcher.html'));
}

ipcMain.handle('start', async () => {
  try { return { ok: true, ...(await startEngine()) }; }
  catch (e) { mainWindow.webContents.send('status', 'Startup failed.'); return { ok: false, error: e.message }; }
});
ipcMain.handle('stop', async () => { await stopEngine(); return { ok: true }; });
ipcMain.handle('open-search', async () => {
  if (webPort) await shell.openExternal(`http://127.0.0.1:${webPort}`);
});
ipcMain.handle('install-docker', async () => {
  const url = 'https://www.docker.com/products/docker-desktop/';
  await shell.openExternal(url);
  return { ok: true };
});

app.whenReady().then(async () => {
  createWindow();
  app.on('activate', () => { if (BrowserWindow.getAllWindows().length === 0) createWindow(); });
});
app.on('before-quit', async e => {
  if (engineProcess) { e.preventDefault(); await stopEngine(); app.exit(0); }
});
app.on('window-all-closed', () => { if (process.platform !== 'darwin') app.quit(); });
