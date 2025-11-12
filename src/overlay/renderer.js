/**
 * Renderer Process for Strategic Overlay
 *
 * Handles UI rendering and event processing for the overlay.
 * Receives game events from Python backend and updates the display.
 */

const { ipcRenderer } = require('electron');

// DOM Elements
let connectionStatus;
let objectiveTimers;
let timerList;
let csTracker;
let csValue;
let csPerMin;
let csRating;
let minimapAlert;
let purchaseSuggestion;
let purchaseText;
let infoHud;
let gameTime;
let gameStatus;

// State
let activeTimers = new Map();
let currentCS = 0;
let currentCSPerMin = 0;
let currentRating = '';
let isConnected = false;

/**
 * Initialize the renderer
 */
function init() {
    console.log('Renderer initializing...');

    // Get DOM elements
    connectionStatus = document.getElementById('connection-status');
    objectiveTimers = document.getElementById('objective-timers');
    timerList = document.getElementById('timer-list');
    csTracker = document.getElementById('cs-tracker');
    csValue = document.getElementById('cs-value');
    csPerMin = document.getElementById('cs-per-min');
    csRating = document.getElementById('cs-rating');
    minimapAlert = document.getElementById('minimap-alert');
    purchaseSuggestion = document.getElementById('purchase-suggestion');
    purchaseText = document.getElementById('purchase-text');
    infoHud = document.getElementById('info-hud');
    gameTime = document.getElementById('game-time');
    gameStatus = document.getElementById('game-status');

    // Set up IPC listeners
    setupIPC();

    // Start update loop
    setInterval(updateTimers, 1000);

    // Request backend status
    ipcRenderer.send('request-backend-status');

    console.log('Renderer initialized');
}

/**
 * Set up IPC communication with main process
 */
function setupIPC() {
    // Backend connection status
    ipcRenderer.on('backend-status', (event, data) => {
        isConnected = data.connected;
        updateConnectionStatus();
    });

    // Game events from backend
    ipcRenderer.on('game-event', (event, message) => {
        handleGameEvent(message);
    });

    // Pong response
    ipcRenderer.on('pong', () => {
        console.log('Pong received');
    });
}

/**
 * Update connection status display
 */
function updateConnectionStatus() {
    if (isConnected) {
        connectionStatus.textContent = 'Connected';
        connectionStatus.className = 'connected';
        gameStatus.textContent = 'Active';
    } else {
        connectionStatus.textContent = 'Disconnected';
        connectionStatus.className = 'disconnected';
        gameStatus.textContent = 'Waiting...';
    }
}

/**
 * Handle incoming game events from backend
 */
function handleGameEvent(message) {
    const { type, category, event_type, data } = message;

    console.log('Game event received:', type, category, event_type);

    switch (type) {
        case 'game_event':
            handleSpecificEvent(category, event_type, data);
            break;

        case 'state_update':
            handleStateUpdate(message.state);
            break;

        default:
            console.log('Unknown message type:', type);
    }
}

/**
 * Handle specific game event types
 */
function handleSpecificEvent(category, eventType, data) {
    switch (category) {
        case 'objective_timers':
            handleObjectiveTimer(data);
            break;

        case 'minimap_alerts':
            handleMinimapAlert(data);
            break;

        case 'purchase_suggestions':
            handlePurchaseSuggestion(data);
            break;

        case 'informational':
            handleInformational(eventType, data);
            break;

        default:
            console.log('Unknown event category:', category);
    }
}

/**
 * Handle objective timer events
 */
function handleObjectiveTimer(data) {
    const { objective, respawn_time } = data;

    console.log(`Objective timer: ${objective} respawns at ${respawn_time}`);

    // Add or update timer
    activeTimers.set(objective, {
        objective: objective,
        respawnTime: respawn_time,
        added: Date.now()
    });

    // Show timers panel
    objectiveTimers.classList.remove('hidden');

    // Show notification
    showNotification(`${capitalizeFirst(objective)} will respawn in 5-6 minutes`, 'info');
}

/**
 * Handle minimap alert events
 */
function handleMinimapAlert(data) {
    const { location, champion, confidence } = data;

    console.log(`Minimap alert at ${location}, confidence: ${confidence}`);

    // Trigger border pulse
    minimapAlert.classList.remove('active');
    void minimapAlert.offsetWidth; // Force reflow
    minimapAlert.classList.add('active');

    // Remove active class after animation
    setTimeout(() => {
        minimapAlert.classList.remove('active');
    }, 3000);

    // Show notification
    const championText = champion ? ` (${champion})` : '';
    showNotification(`Enemy spotted${championText}!`, 'warning');
}

/**
 * Handle purchase suggestion events
 */
function handlePurchaseSuggestion(data) {
    const { item, cost } = data;

    console.log(`Purchase suggestion: ${item} (${cost}g)`);

    // Update text
    purchaseText.textContent = `${item} - ${cost}g`;

    // Show suggestion
    purchaseSuggestion.classList.add('show');

    // Hide after 5 seconds
    setTimeout(() => {
        purchaseSuggestion.classList.remove('show');
    }, 5000);
}

/**
 * Handle informational events
 */
function handleInformational(eventType, data) {
    console.log(`Informational event: ${eventType}`, data);

    // Handle different informational event types
    switch (eventType) {
        case 'game_start':
            showNotification('Game started - Good luck!', 'info');
            break;

        case 'game_end':
            showNotification('Game ended', 'info');
            break;

        default:
            // Generic handling
            break;
    }
}

/**
 * Handle state updates from backend
 */
function handleStateUpdate(state) {
    console.log('State update received:', state);

    const { features } = state;

    // Update objective timers
    if (features.objective_timers) {
        updateObjectiveTimersFromState(features.objective_timers);
    }

    // Update CS tracker
    if (features.cs_tracker) {
        updateCSTracker(features.cs_tracker);
    }
}

/**
 * Update objective timers from state
 */
function updateObjectiveTimersFromState(timers) {
    // Sync with current timers
    for (const timer of timers) {
        const { objective, time_remaining } = timer;

        if (!activeTimers.has(objective)) {
            const respawnTime = Date.now() / 1000 + time_remaining;
            activeTimers.set(objective, {
                objective: objective,
                respawnTime: respawnTime,
                added: Date.now()
            });
        }
    }
}

/**
 * Update CS tracker display
 */
function updateCSTracker(data) {
    const { cs, cs_per_min, rating } = data;

    currentCS = cs;
    currentCSPerMin = cs_per_min;
    currentRating = rating;

    // Update display
    csValue.textContent = cs;
    csPerMin.textContent = `${cs_per_min.toFixed(1)} CS/min`;

    csRating.textContent = rating;
    csRating.className = `cs-rating ${rating.replace('_', '-')}`;

    // Show CS tracker
    csTracker.classList.remove('hidden');
}

/**
 * Update timers display (called every second)
 */
function updateTimers() {
    if (activeTimers.size === 0) {
        return;
    }

    const now = Date.now() / 1000;
    const timersToRemove = [];

    // Clear timer list
    timerList.innerHTML = '';

    // Update each timer
    for (const [objective, timer] of activeTimers) {
        const timeRemaining = timer.respawnTime - now;

        if (timeRemaining <= 0) {
            // Timer expired
            timersToRemove.push(objective);
            showNotification(`${capitalizeFirst(objective)} has respawned!`, 'success');
            continue;
        }

        // Create timer element
        const timerElement = createTimerElement(objective, timeRemaining);
        timerList.appendChild(timerElement);
    }

    // Remove expired timers
    for (const objective of timersToRemove) {
        activeTimers.delete(objective);
    }

    // Hide panel if no timers
    if (activeTimers.size === 0) {
        objectiveTimers.classList.add('hidden');
    }
}

/**
 * Create timer element
 */
function createTimerElement(objective, timeRemaining) {
    const div = document.createElement('div');
    div.className = 'timer-item';

    const objectiveSpan = document.createElement('span');
    objectiveSpan.className = 'timer-objective';
    objectiveSpan.textContent = capitalizeFirst(objective);

    const timeSpan = document.createElement('span');
    timeSpan.className = 'timer-time';

    // Format time
    const minutes = Math.floor(timeRemaining / 60);
    const seconds = Math.floor(timeRemaining % 60);
    timeSpan.textContent = `${minutes}:${seconds.toString().padStart(2, '0')}`;

    // Apply color based on time remaining
    if (timeRemaining <= 30) {
        timeSpan.classList.add('urgent');
    } else if (timeRemaining <= 60) {
        timeSpan.classList.add('warning');
    }

    div.appendChild(objectiveSpan);
    div.appendChild(timeSpan);

    return div;
}

/**
 * Show notification
 */
function showNotification(message, type = 'info') {
    const notification = document.createElement('div');
    notification.className = 'notification';
    notification.textContent = message;

    // Set border color based on type
    const colors = {
        info: '#2196f3',
        warning: '#ff9800',
        error: '#f44336',
        success: '#4caf50'
    };

    notification.style.borderLeftColor = colors[type] || colors.info;

    document.body.appendChild(notification);

    // Show notification
    setTimeout(() => {
        notification.classList.add('show');
    }, 10);

    // Hide and remove after 4 seconds
    setTimeout(() => {
        notification.classList.remove('show');
        setTimeout(() => {
            notification.remove();
        }, 300);
    }, 4000);
}

/**
 * Capitalize first letter
 */
function capitalizeFirst(str) {
    return str.charAt(0).toUpperCase() + str.slice(1);
}

/**
 * Send message to backend
 */
function sendToBackend(message) {
    ipcRenderer.send('send-to-backend', message);
}

/**
 * Send ping to test connection
 */
function sendPing() {
    ipcRenderer.send('ping');
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', init);

// Export functions for debugging
window.overlay = {
    sendPing,
    sendToBackend,
    showNotification
};

console.log('Renderer script loaded');
