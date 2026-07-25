const { app, BrowserWindow, Menu } = require('electron');
const path = require('path');
const fs = require('fs');
const http = require('http');
const { spawn } = require('child_process');

const BACKEND_PORT = 8002;
const BACKEND_URL = `http://127.0.0.1:${BACKEND_PORT}`;
const isDev = !app.isPackaged;

let mainWindow;
let backendProcess;

function backendEnv() {
  // Route the backend's DB/PGN output and Stockfish lookup at files that
  // live outside the (read-only once installed, or ephemeral if bundled by
  // PyInstaller) app directory. See database.py / pgnhandler.py / engine.py
  // for the env vars they respect.
  const userData = app.getPath('userData');
  const env = {
    ...process.env,
    JARVIS_DB_PATH: path.join(userData, 'games_db.sqlite'),
    JARVIS_GAMES_DIR: path.join(userData, 'games'),
  };

  if (!isDev) {
    const stockfishPath = path.join(process.resourcesPath, 'backend', 'stockfish', 'stockfish.exe');
    if (fs.existsSync(stockfishPath)) {
      env.STOCKFISH_PATH = stockfishPath;
    }
  }

  return env;
}

function startBackend() {
  if (isDev) {
    // Dev: run straight from source with the same interpreter/checkout the
    // rest of the project uses, so `npm run electron-dev` needs no separate
    // "start the backend" step.
    const repoRoot = path.join(__dirname, '..', '..');
    backendProcess = spawn('python', ['main.py', 'serve', '--port', String(BACKEND_PORT)], {
      cwd: repoRoot,
      env: backendEnv(),
    });
  } else {
    // Prod: the PyInstaller-built onefile exe, copied in by electron-builder
    // (see package.json "build.extraResources").
    const backendExe = path.join(process.resourcesPath, 'backend', 'jarvis-backend.exe');
    backendProcess = spawn(backendExe, ['serve', '--port', String(BACKEND_PORT)], {
      cwd: app.getPath('userData'),
      env: backendEnv(),
    });
  }

  backendProcess.stdout.on('data', (d) => process.stdout.write(`[backend] ${d}`));
  backendProcess.stderr.on('data', (d) => process.stderr.write(`[backend] ${d}`));
  backendProcess.on('error', (err) => console.error('Failed to start backend:', err));
}

function waitForBackend(timeoutMs = 15000) {
  const start = Date.now();
  return new Promise((resolve) => {
    const poll = () => {
      const req = http.get(BACKEND_URL, (res) => {
        res.resume();
        resolve(true);
      });
      req.on('error', () => {
        if (Date.now() - start > timeoutMs) {
          resolve(false);
        } else {
          setTimeout(poll, 300);
        }
      });
    };
    poll();
  });
}

async function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1400,
    height: 900,
    icon: path.join(__dirname, 'icon.png'),
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      preload: path.join(__dirname, 'preload.js'),
    },
  });

  await waitForBackend();

  if (isDev) {
    mainWindow.loadURL('http://localhost:3000');
  } else {
    mainWindow.loadFile(path.join(__dirname, '..', 'build', 'index.html'));
  }

  mainWindow.on('closed', () => {
    mainWindow = null;
  });

  createMenu();
}

function createMenu() {
  const template = [
    {
      label: 'JARVIS Chess',
      submenu: [
        { label: 'About', role: 'about' },
        { type: 'separator' },
        { label: 'Quit', accelerator: 'CmdOrCtrl+Q', click: () => app.quit() },
      ],
    },
    {
      label: 'View',
      submenu: [
        { label: 'Reload', accelerator: 'CmdOrCtrl+R', role: 'reload' },
        { label: 'Dev Tools', accelerator: 'F12', role: 'toggleDevTools' },
      ],
    },
  ];
  Menu.setApplicationMenu(Menu.buildFromTemplate(template));
}

app.on('ready', () => {
  startBackend();
  createWindow();
});

app.on('window-all-closed', () => {
  if (backendProcess) backendProcess.kill();
  if (process.platform !== 'darwin') app.quit();
});

app.on('before-quit', () => {
  if (backendProcess) backendProcess.kill();
});
