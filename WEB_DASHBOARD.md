# LOL-HORX Web Dashboard

## Overview

The LOL-HORX Web Dashboard provides a browser-based interface for real-time game analysis monitoring. This is the **recommended** way to use LOL-HORX as it provides better accessibility, easier debugging, and works on any platform with a web browser.

## Features

### 📊 Real-Time Analytics Dashboard
- Live game state monitoring
- Objective timers with visual countdowns
- CS/min tracker with performance ratings
- Gold and game time display
- Interactive charts and graphs

### ⚙️ Dynamic Configuration
- Toggle features on/off in real-time
- Switch between Standard and Passive modes
- Save configuration changes
- No restart required for most settings

### 🎮 Game Analysis
- **Objective Timers**: Dragon, Baron, Herald respawn tracking
- **CS Tracker**: Per-minute CS with performance rating (Poor to Excellent)
- **Map Awareness**: Minimap threat detection and alerts
- **Purchase Suggestions**: Smart item recommendation system
- **Event Log**: Comprehensive history of all game events

### 🔄 Real-Time Updates
- WebSocket-based instant updates
- No page refresh needed
- Live connection status indicator
- Automatic reconnection on disconnect

## Quick Start

### Installation

1. **Install Python dependencies:**
```bash
pip install -r requirements.txt
```

2. **Start the web dashboard:**
```bash
python main.py --web
```

3. **Open your browser:**
Navigate to: `http://localhost:5000`

That's it! The dashboard will be ready to use.

## Usage

### Starting the Application

**Web Dashboard (Recommended):**
```bash
python main.py --web
```

**With specific mode:**
```bash
python main.py --web --mode passive
```

**Development mode (with debug logging):**
```bash
python main.py --web --dev
```

### Dashboard Interface

#### Header Section
- **Connection Status**: Shows if connected to analysis engine
- **Start/Stop Engine**: Control the analysis engine
- **Real-time indicators**: Live connection and status updates

#### Left Sidebar - Controls
- **Operational Mode**: Switch between Standard and Passive
- **Feature Toggles**: Enable/disable individual features
- **Save Configuration**: Persist changes to config file
- **System Statistics**: FPS, frame count, timestamps

#### Main Panel
- **Game State Overview**: Current CS, gold, time, performance rating
- **Objective Timers**: Visual cards showing respawn times
- **CS/min Chart**: Historical performance graph
- **Event Log**: Real-time event feed with timestamps

#### Right Sidebar
- **Map Awareness**: Minimap threat visualization
- **Purchase Suggestions**: Recommended items based on gold
- **Active Alerts**: Current warnings and notifications

### Controls

#### Starting Analysis
1. Click **"Start Engine"** button in the header
2. Analysis engine begins capturing and processing
3. Watch the dashboard populate with real-time data

#### Stopping Analysis
1. Click **"Stop Engine"** button
2. Engine stops gracefully
3. Dashboard shows last known state

#### Changing Features
1. Check/uncheck feature boxes in left sidebar
2. Click **"Save Configuration"**
3. Changes apply immediately (no restart needed)

#### Changing Mode
1. Select mode from dropdown (Standard/Passive)
2. Click **"Save Configuration"**
3. **Passive Mode** disables proactive alerts (map awareness, purchase suggestions)

## API Endpoints

The web server exposes REST API endpoints for external integration:

### Status Endpoints

**GET `/api/status`**
- Returns: Current engine status and configuration
```json
{
  "status": "running",
  "engine_active": true,
  "config": {
    "mode": "standard",
    "features": {...},
    "capture_fps": 10
  }
}
```

**GET `/api/game-state`**
- Returns: Current game state
```json
{
  "connected": true,
  "game_time": "15:30",
  "objective_timers": [...],
  "cs_stats": {...},
  "last_update": "2025-01-15T12:00:00"
}
```

### Control Endpoints

**POST `/api/engine/start`**
- Starts the analysis engine
- Returns: `{"success": true, "message": "..."}`

**POST `/api/engine/stop`**
- Stops the analysis engine
- Returns: `{"success": true, "message": "..."}`

### Configuration Endpoints

**GET `/api/config`**
- Returns: Current configuration

**POST `/api/config`**
- Body: Configuration JSON
- Returns: Success/failure status
```json
{
  "mode": "standard",
  "features": {
    "objective_timers": true,
    "cs_tracker": true,
    "purchase_suggestions": false,
    "map_awareness": true
  }
}
```

## WebSocket Events

Real-time updates are delivered via Socket.IO:

### Client → Server Events

| Event | Description |
|-------|-------------|
| `connect` | Initial connection to server |
| `request_state` | Request current game state |
| `ping` | Connection health check |

### Server → Client Events

| Event | Data | Description |
|-------|------|-------------|
| `connection_status` | `{connected: bool}` | Connection established |
| `engine_status` | `{status: string, connected: bool}` | Engine status changed |
| `game_state` | `{...}` | Complete game state |
| `state_update` | `{features: {...}}` | Partial state update |
| `game_events` | `{events: [...]}` | Real-time game events |
| `config_updated` | `{...}` | Configuration changed |
| `engine_error` | `{error: string}` | Engine error occurred |
| `pong` | `{timestamp: string}` | Ping response |

## Architecture

```
┌─────────────────────────┐
│   Web Browser           │
│   (Dashboard UI)        │
└───────────┬─────────────┘
            │ HTTP/WebSocket
            │
┌───────────▼─────────────┐
│   Flask Web Server      │
│   (app.py)              │
│   - REST API            │
│   - Socket.IO           │
└───────────┬─────────────┘
            │ Function Calls
            │
┌───────────▼─────────────┐
│  Analysis Engine        │
│  (WebAnalysisEngine)    │
│  - Capture Manager      │
│  - OCR Reader           │
│  - Minimap Analyzer     │
│  - Strategic Features   │
└─────────────────────────┘
```

## Advantages vs Electron Overlay

| Feature | Web Dashboard | Electron Overlay |
|---------|---------------|------------------|
| **Accessibility** | Any device on network | Same machine only |
| **Multiple Viewers** | ✅ Yes | ❌ No |
| **Easy Debugging** | Browser DevTools | Limited |
| **Resource Usage** | Lower | Higher |
| **Click-through** | N/A (separate window) | ✅ Yes |
| **Remote Access** | ✅ Yes | ❌ No |
| **Mobile Friendly** | ✅ Responsive | ❌ No |
| **Configuration UI** | ✅ Built-in | ❌ No |

## Customization

### Changing Port

Edit `app.py`:
```python
socketio.run(app, host='0.0.0.0', port=8080)  # Change from 5000
```

### Allowing Remote Access

By default, the server binds to `0.0.0.0`, allowing network access.

**Security Warning**: Only allow remote access on trusted networks!

To restrict to localhost only:
```python
socketio.run(app, host='127.0.0.1', port=5000)
```

### Custom Styling

Modify `src/web/static/css/dashboard.css` to customize colors, layout, and styling.

CSS variables are defined at the top:
```css
:root {
    --primary-color: #0a84ff;
    --secondary-color: #30d158;
    /* ... customize as needed */
}
```

## Troubleshooting

### Dashboard Won't Load

**Check if server is running:**
```bash
curl http://localhost:5000/api/status
```

**Check for port conflicts:**
```bash
# Linux/Mac
lsof -i :5000

# Windows
netstat -ano | findstr :5000
```

**Solution**: Change port in `app.py` or kill conflicting process

### WebSocket Connection Fails

**Check browser console** (F12) for errors.

Common issues:
- **CORS errors**: Make sure Flask-CORS is installed
- **Mixed content**: Use `http://` not `https://` for localhost
- **Firewall**: Allow port 5000 through firewall

### No Data Showing

1. **Check engine status** in dashboard
2. **Start the engine** using "Start Engine" button
3. **Check console** for error messages
4. **Verify game is running** (if not using mock mode)

### High CPU Usage

**Reduce capture FPS** in configuration:
```json
{
  "capture_fps": 5
}
```

Lower FPS = lower CPU usage

## Development

### Running in Debug Mode

```bash
python main.py --web --dev
```

This enables:
- Flask debug mode
- Detailed logging
- Auto-reload on code changes

### Testing Without Game

The dashboard works with mock data by default. To test:

1. Start dashboard: `python main.py --web`
2. Click "Start Engine"
3. Watch simulated data populate

### Adding New Features

1. **Backend**: Add analysis in `src/analysis/` or `src/features/`
2. **API**: Add endpoint in `app.py`
3. **Frontend**: Update `dashboard.html` and `dashboard.js`
4. **Styling**: Add CSS to `dashboard.css`

## Performance

### Typical Resource Usage

- **CPU**: 5-15% (depending on capture FPS)
- **RAM**: 100-200 MB
- **Network**: <1 KB/s (WebSocket updates)
- **Disk**: None (all in-memory)

### Optimization Tips

1. **Lower capture FPS** for less CPU usage
2. **Disable unused features** to reduce processing
3. **Use Passive Mode** for minimal overhead
4. **Close unused browser tabs**

## Security Considerations

### Safe Practices

✅ **DO:**
- Run on localhost for personal use
- Use on trusted home networks only
- Keep dependencies updated
- Review code before running

❌ **DON'T:**
- Expose to public internet without authentication
- Run on public/untrusted networks
- Share dashboard access with unknown parties
- Modify core security features

### Network Security

The dashboard binds to `0.0.0.0` by default, allowing LAN access.

**For maximum security**, bind to localhost only:
```python
# app.py
socketio.run(app, host='127.0.0.1', port=5000)
```

## FAQ

**Q: Can I access the dashboard from my phone?**
A: Yes! Find your computer's IP address and navigate to `http://YOUR_IP:5000` on your phone's browser (must be on same network).

**Q: Does this work without the game running?**
A: Yes, it uses mock data for testing. Real game requires League of Legends running.

**Q: Can multiple people view the dashboard simultaneously?**
A: Yes! Multiple browsers can connect and view the same data.

**Q: Is this detectable by anti-cheat?**
A: This is a **read-only analysis tool** that doesn't interact with the game. However, use at your own risk and review Riot's ToS.

**Q: How do I stop the server?**
A: Press `Ctrl+C` in the terminal where the server is running.

**Q: Can I run this on Linux/Mac?**
A: Yes! The web dashboard works on all platforms. Some screen capture features may require Windows.

## Support

For issues, questions, or contributions:
- Check the main README.md
- Review test cases
- Check browser console for errors
- Ensure all dependencies are installed

## Conclusion

The Web Dashboard provides a modern, flexible interface for LOL-HORX with real-time monitoring, easy configuration, and cross-platform support. It's the recommended way to use LOL-HORX for most users.

**Ready to start?**
```bash
python main.py --web
```

Open `http://localhost:5000` and enjoy! 🎮📊
