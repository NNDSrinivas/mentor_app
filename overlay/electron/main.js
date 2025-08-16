const { app, BrowserWindow, globalShortcut } = require('electron');
const path = require('path');
const fs = require('fs');
const os = require('os');

let win;

function createWindow() {
  win = new BrowserWindow({
    width: 400,
    height: 200,
    frame: false,
    transparent: true,
    resizable: false,
    alwaysOnTop: true,
    skipTaskbar: true,
    webPreferences: {
      nodeIntegration: true,
      contextIsolation: false
    }
  });
  win.setAlwaysOnTop(true, 'screen-saver');
  win.setVisibleOnAllWorkspaces(true, { visibleOnFullScreen: true });
  win.setIgnoreMouseEvents(true, { forward: true });
  win.loadFile(path.join(__dirname, 'index.html'));
}

function watchOverlay() {
  const dir = process.env.MENTOR_TEMP_DIR || path.join(os.tmpdir(), 'mentor_app');
  fs.mkdirSync(dir, { recursive: true });
  fs.watch(dir, (event, filename) => {
    if (!filename) return;
    if (filename.startsWith('ai_overlay_') && filename.endsWith('.json')) {
      const filePath = path.join(dir, filename);
      fs.readFile(filePath, 'utf8', (err, data) => {
        if (err) return;
        try {
          const json = JSON.parse(data);
          if (win) {
            win.webContents.send('overlay-data', json);
          }
        } catch (e) {
          console.error('Invalid overlay json', e);
        }
        fs.unlink(filePath, () => {});
      });
    }
  });
}

app.whenReady().then(() => {
  createWindow();
  globalShortcut.register('CommandOrControl+Shift+O', () => {
    if (win.isVisible()) {
      win.hide();
    } else {
      win.show();
    }
  });
  watchOverlay();
});

app.on('window-all-closed', (e) => {
  e.preventDefault();
});
