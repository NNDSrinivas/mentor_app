const { app, BrowserWindow, globalShortcut } = require('electron');

let win;

function createWindow() {
  win = new BrowserWindow({
    width: 520,
    height: 380,
    transparent: true,
    frame: false,
    alwaysOnTop: true,
    focusable: false,
    hasShadow: false,
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
    }
  });

  win.setIgnoreMouseEvents(true, { forward: true });
  win.setVisibleOnAllWorkspaces(true, { visibleOnFullScreen: true });
  win.loadURL('http://localhost:8084/overlay.html');
}

app.whenReady().then(() => {
  createWindow();
  const shortcut = 'CmdOrCtrl+Shift+O';
  globalShortcut.register(shortcut, () => {
    if (!win) return;
    if (win.isVisible()) {
      win.hide();
    } else {
      win.show();
    }
  });
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

app.on('will-quit', () => {
  globalShortcut.unregisterAll();
});
