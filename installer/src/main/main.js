const { app, BrowserWindow, ipcMain } = require('electron');
const path = require('path');
const { Installer } = require('./installer');

let mainWindow;
let installer;

function createWindow() {
    mainWindow = new BrowserWindow({
        width: 500,
        height: 400,
        frame: false,
        resizable: false,
        transparent: false,
        backgroundColor: '#1a1925',
        icon: path.join(__dirname, '../../resources/icon.ico'),
        webPreferences: {
            nodeIntegration: true,
            contextIsolation: false
        }
    });

    mainWindow.loadFile(path.join(__dirname, '../renderer/index.html'));

    // Uncomment for dev tools
    // mainWindow.webContents.openDevTools();

    mainWindow.on('closed', () => {
        mainWindow = null;
    });
}

app.whenReady().then(() => {
    if (process.platform === 'win32') {
        app.setAppUserModelId('Flux.Platform.Installer');
    }

    installer = new Installer();
    createWindow();
});

app.on('window-all-closed', () => {
    app.quit();
});

// IPC Handlers
ipcMain.handle('get-default-path', () => {
    // Default to Program Files
    return path.join(process.env.ProgramFiles || 'C:\\Program Files', 'Flux Platform');
});

ipcMain.handle('start-install', async (event, installPath) => {
    return await installer.install(installPath, (progress) => {
        mainWindow.webContents.send('install-progress', progress);
    });
});

ipcMain.handle('create-shortcuts', async (event, { installPath, desktop, startMenu }) => {
    return await installer.createShortcuts(installPath, desktop, startMenu);
});

ipcMain.handle('launch-app', async (event, installPath) => {
    return await installer.launchApp(installPath);
});

ipcMain.on('window-close', () => {
    app.quit();
});

ipcMain.on('window-minimize', () => {
    mainWindow.minimize();
});
