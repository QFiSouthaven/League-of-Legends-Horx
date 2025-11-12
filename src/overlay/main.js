/**
 * Electron Main Process for Strategic Overlay
 *
 * Creates a transparent, borderless, always-on-top browser window
 * that passes all mouse and keyboard input through to the game client.
 */

const { app, BrowserWindow, ipcMain, screen } = require('electron');
const path = require('path');
const WebSocket = require('ws');

let mainWindow = null;
let pythonBackendWs = null;
let isConnectedToBackend = false;

// WebSocket configuration
const WS_HOST = '127.0.0.1';
const WS_PORT = 8765;

/**
 * Create the transparent overlay window
 */
function createWindow() {
    // Get primary display dimensions
    const primaryDisplay = screen.getPrimaryDisplay();
    const { width, height } = primaryDisplay.workAreaSize;

    mainWindow = new BrowserWindow({
        width: width,
        height: height,
        x: 0,
        y: 0,
        transparent: true,
        frame: false,
        alwaysOnTop: true,
        skipTaskbar: true,
        resizable: false,
        movable: false,
        minimizable: false,
        maximizable: false,
        closable: true,
        focusable: false,
        webPreferences: {
            nodeIntegration: true,
            contextIsolation: false,
            enableRemoteModule: false
        }
    });

    // Load the overlay HTML
    mainWindow.loadFile(path.join(__dirname, 'index.html'));

    // Make window click-through
    mainWindow.setIgnoreMouseEvents(true, { forward: true });

    // Ensure window stays on top
    mainWindow.setAlwaysOnTop(true, 'screen-saver');

    // Open DevTools in development mode
    if (process.argv.includes('--dev')) {
        mainWindow.webContents.openDevTools();
    }

    // Handle window close
    mainWindow.on('closed', () => {
        mainWindow = null;
        disconnectFromBackend();
    });

    console.log('Overlay window created');
}

/**
 * Connect to Python backend via WebSocket
 */
function connectToBackend() {
    const wsUrl = `ws://${WS_HOST}:${WS_PORT}`;

    console.log(`Connecting to Python backend at ${wsUrl}...`);

    pythonBackendWs = new WebSocket(wsUrl);

    pythonBackendWs.on('open', () => {
        console.log('Connected to Python backend');
        isConnectedToBackend = true;

        // Send connection confirmation
        pythonBackendWs.send(JSON.stringify({
            type: 'connection',
            status: 'connected'
        }));

        // Notify renderer
        if (mainWindow) {
            mainWindow.webContents.send('backend-status', { connected: true });
        }
    });

    pythonBackendWs.on('message', (data) => {
        try {
            const message = JSON.parse(data.toString());
            handleBackendMessage(message);
        } catch (error) {
            console.error('Error parsing backend message:', error);
        }
    });

    pythonBackendWs.on('error', (error) => {
        console.error('WebSocket error:', error);
        isConnectedToBackend = false;

        if (mainWindow) {
            mainWindow.webContents.send('backend-status', { connected: false });
        }
    });

    pythonBackendWs.on('close', () => {
        console.log('Disconnected from Python backend');
        isConnectedToBackend = false;

        if (mainWindow) {
            mainWindow.webContents.send('backend-status', { connected: false });
        }

        // Attempt to reconnect after 3 seconds
        setTimeout(connectToBackend, 3000);
    });
}

/**
 * Disconnect from Python backend
 */
function disconnectFromBackend() {
    if (pythonBackendWs) {
        pythonBackendWs.close();
        pythonBackendWs = null;
    }
    isConnectedToBackend = false;
}

/**
 * Handle messages from Python backend
 */
function handleBackendMessage(message) {
    // Forward message to renderer process
    if (mainWindow) {
        mainWindow.webContents.send('game-event', message);
    }
}

/**
 * Send message to Python backend
 */
function sendToBackend(message) {
    if (isConnectedToBackend && pythonBackendWs) {
        pythonBackendWs.send(JSON.stringify(message));
    } else {
        console.warn('Not connected to backend, message not sent');
    }
}

// App lifecycle events
app.whenReady().then(() => {
    createWindow();

    // Connect to Python backend after window is created
    setTimeout(connectToBackend, 1000);

    app.on('activate', () => {
        if (BrowserWindow.getAllWindows().length === 0) {
            createWindow();
        }
    });
});

app.on('window-all-closed', () => {
    disconnectFromBackend();
    if (process.platform !== 'darwin') {
        app.quit();
    }
});

// IPC handlers for renderer process
ipcMain.on('send-to-backend', (event, message) => {
    sendToBackend(message);
});

ipcMain.on('toggle-click-through', (event, enabled) => {
    if (mainWindow) {
        mainWindow.setIgnoreMouseEvents(enabled, { forward: true });
    }
});

ipcMain.on('request-backend-status', (event) => {
    event.reply('backend-status', { connected: isConnectedToBackend });
});

// Handle ping from renderer
ipcMain.on('ping', (event) => {
    event.reply('pong');
});

console.log('Electron main process started');
