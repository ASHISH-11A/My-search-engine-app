const { contextBridge, ipcRenderer } = require('electron');
contextBridge.exposeInMainWorld('mySearch', {
  start: () => ipcRenderer.invoke('start'),
  stop: () => ipcRenderer.invoke('stop'),
  openSearch: () => ipcRenderer.invoke('open-search'),
  installDocker: () => ipcRenderer.invoke('install-docker'),
  onStatus: cb => ipcRenderer.on('status', (_, v) => cb(v)),
  onLog: cb => ipcRenderer.on('log', (_, v) => cb(v))
});
