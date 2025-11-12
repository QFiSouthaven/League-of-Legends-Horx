/**
 * LOL-HORX Dashboard JavaScript
 * Handles real-time updates via Socket.IO
 */

// Socket.IO connection
const socket = io();

// State
let engineRunning = false;
let csHistory = [];
let csChart = null;

// DOM Elements
const elements = {
    connectionStatus: document.getElementById('connectionStatus'),
    engineToggle: document.getElementById('engineToggle'),
    gameTime: document.getElementById('gameTime'),
    currentGameTime: document.getElementById('currentGameTime'),
    currentCS: document.getElementById('currentCS'),
    csPerMin: document.getElementById('csPerMin'),
    csRating: document.getElementById('csRating'),
    currentGold: document.getElementById('currentGold'),
    objectiveTimers: document.getElementById('objectiveTimers'),
    eventLog: document.getElementById('eventLog'),
    minimapAlerts: document.getElementById('minimapAlerts'),
    purchaseSuggestions: document.getElementById('purchaseSuggestions'),
    activeAlerts: document.getElementById('activeAlerts'),
    frameCount: document.getElementById('frameCount'),
    analysisFPS: document.getElementById('analysisFPS'),
    engineStatus: document.getElementById('engineStatus'),
    captureStatus: document.getElementById('captureStatus'),
    lastUpdate: document.getElementById('lastUpdate'),
    modeSelector: document.getElementById('modeSelector'),
    saveConfig: document.getElementById('saveConfig')
};

// Feature checkboxes
const featureCheckboxes = {
    objective_timers: document.getElementById('feature_objective_timers'),
    cs_tracker: document.getElementById('feature_cs_tracker'),
    purchase_suggestions: document.getElementById('feature_purchase_suggestions'),
    map_awareness: document.getElementById('feature_map_awareness')
};

/**
 * Initialize dashboard
 */
function init() {
    console.log('Dashboard initializing...');

    // Set up event listeners
    elements.engineToggle.addEventListener('click', toggleEngine);
    elements.saveConfig.addEventListener('click', saveConfiguration);

    // Initialize CS chart
    initializeCSChart();

    // Load initial configuration
    loadConfiguration();

    console.log('Dashboard initialized');
}

/**
 * Initialize CS per minute chart
 */
function initializeCSChart() {
    const ctx = document.getElementById('csChart').getContext('2d');

    csChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: [],
            datasets: [{
                label: 'CS/min',
                data: [],
                borderColor: '#0a84ff',
                backgroundColor: 'rgba(10, 132, 255, 0.1)',
                borderWidth: 2,
                tension: 0.4,
                fill: true
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: false
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        color: '#8e8e93'
                    },
                    grid: {
                        color: '#38383a'
                    }
                },
                x: {
                    ticks: {
                        color: '#8e8e93'
                    },
                    grid: {
                        color: '#38383a'
                    }
                }
            }
        }
    });
}

/**
 * Load configuration from server
 */
async function loadConfiguration() {
    try {
        const response = await fetch('/api/config');
        const config = await response.json();

        // Update UI
        elements.modeSelector.value = config.mode;

        for (const [feature, enabled] of Object.entries(config.features)) {
            if (featureCheckboxes[feature]) {
                featureCheckboxes[feature].checked = enabled;
            }
        }

    } catch (error) {
        console.error('Error loading configuration:', error);
        showToast('Failed to load configuration', 'danger');
    }
}

/**
 * Save configuration to server
 */
async function saveConfiguration() {
    try {
        const features = {};
        for (const [feature, checkbox] of Object.entries(featureCheckboxes)) {
            features[feature] = checkbox.checked;
        }

        const config = {
            mode: elements.modeSelector.value,
            features: features
        };

        const response = await fetch('/api/config', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(config)
        });

        if (response.ok) {
            showToast('Configuration saved successfully', 'success');
            addLogEntry('Configuration updated', 'info');
        } else {
            showToast('Failed to save configuration', 'danger');
        }

    } catch (error) {
        console.error('Error saving configuration:', error);
        showToast('Error saving configuration', 'danger');
    }
}

/**
 * Toggle analysis engine
 */
async function toggleEngine() {
    if (engineRunning) {
        await stopEngine();
    } else {
        await startEngine();
    }
}

/**
 * Start analysis engine
 */
async function startEngine() {
    try {
        elements.engineToggle.disabled = true;
        elements.engineToggle.textContent = 'Starting...';

        const response = await fetch('/api/engine/start', {
            method: 'POST'
        });

        if (response.ok) {
            engineRunning = true;
            elements.engineToggle.textContent = 'Stop Engine';
            elements.engineStatus.textContent = 'Running';
            addLogEntry('Analysis engine started', 'success');
        } else {
            showToast('Failed to start engine', 'danger');
        }

    } catch (error) {
        console.error('Error starting engine:', error);
        showToast('Error starting engine', 'danger');
    } finally {
        elements.engineToggle.disabled = false;
    }
}

/**
 * Stop analysis engine
 */
async function stopEngine() {
    try {
        elements.engineToggle.disabled = true;
        elements.engineToggle.textContent = 'Stopping...';

        const response = await fetch('/api/engine/stop', {
            method: 'POST'
        });

        if (response.ok) {
            engineRunning = false;
            elements.engineToggle.textContent = 'Start Engine';
            elements.engineStatus.textContent = 'Stopped';
            addLogEntry('Analysis engine stopped', 'info');
        } else {
            showToast('Failed to stop engine', 'danger');
        }

    } catch (error) {
        console.error('Error stopping engine:', error);
        showToast('Error stopping engine', 'danger');
    } finally {
        elements.engineToggle.disabled = false;
    }
}

/**
 * Update connection status
 */
function updateConnectionStatus(connected) {
    const statusDot = elements.connectionStatus.querySelector('.status-dot');
    const statusText = elements.connectionStatus.querySelector('.status-text');

    if (connected) {
        statusDot.classList.add('connected');
        statusText.textContent = 'Connected';
    } else {
        statusDot.classList.remove('connected');
        statusText.textContent = 'Disconnected';
    }
}

/**
 * Update objective timers display
 */
function updateObjectiveTimers(timers) {
    if (!timers || timers.length === 0) {
        elements.objectiveTimers.innerHTML = '<div class="empty-state"><p>No active timers</p></div>';
        return;
    }

    elements.objectiveTimers.innerHTML = '';

    timers.forEach(timer => {
        const card = document.createElement('div');
        card.className = 'timer-card';

        const objective = document.createElement('div');
        objective.className = 'timer-objective';
        objective.textContent = timer.objective.charAt(0).toUpperCase() + timer.objective.slice(1);

        const timeRemaining = timer.time_remaining;
        const minutes = Math.floor(timeRemaining / 60);
        const seconds = Math.floor(timeRemaining % 60);

        const time = document.createElement('div');
        time.className = 'timer-time';
        time.textContent = `${minutes}:${seconds.toString().padStart(2, '0')}`;

        // Apply urgency classes
        if (timeRemaining <= 30) {
            time.classList.add('urgent');
        } else if (timeRemaining <= 60) {
            time.classList.add('warning');
        }

        card.appendChild(objective);
        card.appendChild(time);
        elements.objectiveTimers.appendChild(card);
    });
}

/**
 * Update CS tracker display
 */
function updateCSTracker(csData) {
    if (!csData) return;

    elements.currentCS.textContent = csData.cs || 0;
    elements.csPerMin.textContent = `${(csData.cs_per_min || 0).toFixed(1)} CS/min`;

    // Update rating badge
    const rating = csData.rating || 'N/A';
    elements.csRating.textContent = rating;
    elements.csRating.className = 'rating-badge';

    if (rating !== 'N/A') {
        elements.csRating.classList.add(rating.replace('_', '-'));
    }

    // Update chart
    updateCSChart(csData.cs_per_min || 0);
}

/**
 * Update CS chart
 */
function updateCSChart(csPerMin) {
    const now = new Date();
    const timeLabel = `${now.getHours()}:${now.getMinutes().toString().padStart(2, '0')}`;

    csHistory.push({ time: timeLabel, value: csPerMin });

    // Keep only last 20 data points
    if (csHistory.length > 20) {
        csHistory.shift();
    }

    csChart.data.labels = csHistory.map(d => d.time);
    csChart.data.datasets[0].data = csHistory.map(d => d.value);
    csChart.update('none'); // Update without animation
}

/**
 * Add entry to event log
 */
function addLogEntry(message, type = 'info') {
    const entry = document.createElement('div');
    entry.className = `log-entry log-${type}`;

    const time = document.createElement('span');
    time.className = 'log-time';
    const now = new Date();
    time.textContent = `${now.getHours().toString().padStart(2, '0')}:${now.getMinutes().toString().padStart(2, '0')}:${now.getSeconds().toString().padStart(2, '0')}`;

    const msg = document.createElement('span');
    msg.className = 'log-message';
    msg.textContent = message;

    entry.appendChild(time);
    entry.appendChild(msg);

    // Add to top of log
    elements.eventLog.insertBefore(entry, elements.eventLog.firstChild);

    // Keep only last 50 entries
    while (elements.eventLog.children.length > 50) {
        elements.eventLog.removeChild(elements.eventLog.lastChild);
    }
}

/**
 * Show toast notification
 */
function showToast(message, type = 'info') {
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.textContent = message;

    const container = document.getElementById('toastContainer');
    container.appendChild(toast);

    // Remove after 4 seconds
    setTimeout(() => {
        toast.style.opacity = '0';
        setTimeout(() => toast.remove(), 300);
    }, 4000);
}

/**
 * Add minimap alert
 */
function addMinimapAlert(position) {
    const marker = document.createElement('div');
    marker.className = 'minimap-alert-marker';
    marker.style.left = `${position[0]}px`;
    marker.style.top = `${position[1]}px`;

    elements.minimapAlerts.appendChild(marker);

    // Remove after 3 seconds
    setTimeout(() => marker.remove(), 3000);

    // Add to active alerts
    addActiveAlert('Enemy spotted on minimap', 'danger');
}

/**
 * Add active alert
 */
function addActiveAlert(message, type = 'info') {
    const alert = document.createElement('div');
    alert.className = `alert-item ${type}`;
    alert.textContent = message;

    elements.activeAlerts.insertBefore(alert, elements.activeAlerts.firstChild);

    // Remove after 10 seconds
    setTimeout(() => alert.remove(), 10000);

    // Keep only last 5 alerts
    while (elements.activeAlerts.children.length > 5) {
        elements.activeAlerts.removeChild(elements.activeAlerts.lastChild);
    }
}

// Socket.IO Event Handlers
socket.on('connect', () => {
    console.log('Connected to server');
    updateConnectionStatus(true);
    showToast('Connected to server', 'success');
});

socket.on('disconnect', () => {
    console.log('Disconnected from server');
    updateConnectionStatus(false);
    showToast('Disconnected from server', 'warning');
});

socket.on('engine_status', (data) => {
    console.log('Engine status:', data);
    updateConnectionStatus(data.connected);
    elements.captureStatus.textContent = data.status === 'running' ? 'Active' : 'Idle';
});

socket.on('game_state', (state) => {
    console.log('Game state update:', state);

    // Update game time
    if (state.game_time) {
        elements.gameTime.textContent = state.game_time;
        elements.currentGameTime.textContent = state.game_time;
    }

    // Update objective timers
    if (state.objective_timers) {
        updateObjectiveTimers(state.objective_timers);
    }

    // Update CS stats
    if (state.cs_stats) {
        updateCSTracker(state.cs_stats);
    }

    // Update last update time
    if (state.last_update) {
        const updateTime = new Date(state.last_update);
        elements.lastUpdate.textContent = updateTime.toLocaleTimeString();
    }
});

socket.on('state_update', (state) => {
    console.log('State update:', state);

    if (state.features) {
        if (state.features.objective_timers) {
            updateObjectiveTimers(state.features.objective_timers);
        }

        if (state.features.cs_tracker) {
            updateCSTracker(state.features.cs_tracker);
        }
    }
});

socket.on('game_events', (data) => {
    console.log('Game events:', data);

    data.events.forEach(event => {
        if (event.type === 'objective_timer') {
            const message = `${event.objective.charAt(0).toUpperCase() + event.objective.slice(1)} killed - respawns in ${Math.floor(event.time_remaining / 60)}m`;
            addLogEntry(message, 'info');
            showToast(message, 'info');
        }

        if (event.type === 'minimap_alert') {
            addLogEntry('Enemy spotted on minimap', 'warning');
            addMinimapAlert(event.position);
            showToast('Enemy spotted!', 'warning');
        }
    });
});

socket.on('config_updated', (data) => {
    console.log('Config updated:', data);
    showToast('Configuration updated', 'info');
});

socket.on('engine_error', (data) => {
    console.error('Engine error:', data);
    showToast(`Engine error: ${data.error}`, 'danger');
    addLogEntry(`Error: ${data.error}`, 'danger');
});

socket.on('pong', (data) => {
    console.log('Pong:', data);
});

// Initialize on page load
document.addEventListener('DOMContentLoaded', init);

// Export for debugging
window.dashboard = {
    socket,
    showToast,
    addLogEntry,
    startEngine,
    stopEngine
};

console.log('Dashboard script loaded');
