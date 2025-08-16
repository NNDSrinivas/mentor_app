const { ipcRenderer } = require('electron');

const container = document.getElementById('overlay');

ipcRenderer.on('overlay-data', (_event, data) => {
  container.textContent = data.content || '';
});
