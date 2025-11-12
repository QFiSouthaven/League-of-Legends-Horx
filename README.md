# LOL-HORX - League of Legends Strategic Overlay

A hybrid application with a Python backend and Electron frontend that provides strategic information overlay for League of Legends. Built with a "Safety First" design principle, featuring sandboxed processes, secure IPC, and adaptive jitter control.

## Architecture Overview

### Three-Part Modular Design

```
┌─────────────────────┐
│   Electron Overlay  │  ← Transparent, Click-through UI
│    (Frontend)       │
└──────────┬──────────┘
           │ WebSocket IPC
           │ (Adaptive Jitter)
┌──────────▼──────────┐
│  Python Backend     │  ← Analysis Engine
│  (Sandboxed)        │
└──────────┬──────────┘
           │
    ┌──────┴──────┐
    │             │
┌───▼────┐  ┌────▼─────┐
│Capture │  │ Analysis │
│Manager │  │ Modules  │
└────────┘  └──────────┘
```

### Components

1. **Capture Module** (`src/capture/`)
   - Window-specific screen capture
   - ROI-based frame extraction
   - In-memory processing (no disk writes)

2. **Analysis Engine** (`src/analysis/`)
   - OCR text extraction (game clock, CS, gold)
   - Minimap threat detection
   - Objective event parsing

3. **Strategic Features** (`src/features/`)
   - Objective timers (Dragon, Baron, Herald)
   - CS/min tracker with performance rating
   - Purchase suggestions
   - Map awareness alerts

4. **IPC Handler** (`src/ipc/`)
   - WebSocket communication
   - Adaptive jitter control (30-400ms based on event type)
   - Event prioritization

5. **Overlay** (`src/overlay/`)
   - Transparent Electron window
   - Click-through interface
   - Real-time event visualization

## Installation

### Prerequisites

- Python 3.8+
- Node.js 16+
- npm or yarn
- Windows OS (for full functionality)

### Python Dependencies

```bash
pip install -r requirements.txt
```

**Optional dependencies:**
- Tesseract OCR (for text extraction): https://github.com/tesseract-ocr/tesseract
- Windows: `pywin32` is automatically installed on Windows

### Node Dependencies

```bash
npm install
```

## Configuration

### ROI Configuration

Edit `src/config/rois.json` to adjust Region of Interest coordinates for different screen resolutions:

```json
{
  "resolution": "1920x1080",
  "rois": {
    "minimap": {
      "x": 0,
      "y": 780,
      "width": 260,
      "height": 260
    }
  }
}
```

### Application Configuration

Create `src/config/app_config.json` to customize settings:

```json
{
  "mode": "standard",
  "ipc_host": "127.0.0.1",
  "ipc_port": 8765,
  "capture_fps": 10,
  "features": {
    "objective_timers": true,
    "cs_tracker": true,
    "purchase_suggestions": true,
    "map_awareness": true
  },
  "jitter_ranges": {
    "informational": [100, 300],
    "objective_timers": [50, 200],
    "minimap_alerts": [30, 80],
    "purchase_suggestions": [150, 400]
  }
}
```

### Operational Modes

- **Standard Mode**: All features enabled with visual notifications
- **Passive Mode**: Information-only, disables proactive alerts

## Running the Application

### Full Application

```bash
python main.py
```

**Options:**
```bash
python main.py --dev              # Enable development mode
python main.py --mode passive     # Run in passive mode
python main.py --config /path     # Use custom config directory
```

### Test Analysis Engine Only

```bash
python main.py --test-engine
```

Or directly:
```bash
python src/analysis/engine.py
```

### Test Individual Components

```bash
# Test configuration loader
python src/config/config_loader.py

# Test capture manager
python src/capture/capture_manager.py

# Test OCR reader
python src/analysis/ocr_reader.py

# Test minimap analyzer
python src/analysis/minimap_analyzer.py

# Test strategic features
python src/features/strategic_features.py
```

## Test Cases

### 1. Window Capture Isolation
**Test**: Verify the application only captures the League of Legends game window.

**Steps**:
1. Start the application
2. Open multiple windows (browser, file explorer, etc.)
3. Check capture manager logs to confirm only LoL window is captured

**Expected Result**: No other windows or desktop captured

### 2. Click-Through Overlay
**Test**: Confirm overlay is fully transparent and inputs pass through.

**Steps**:
1. Start the application with overlay
2. Try clicking on game elements through the overlay
3. Press keyboard shortcuts

**Expected Result**: All inputs reach the game client

### 3. OCR Accuracy - Kill Feed
**Test**: Test OCR accuracy for kill feed events in a bot game.

**Steps**:
1. Start a bot game
2. Kill Dragon or Baron
3. Check logs for detected objective event

**Expected Result**: Event detected within 1-2 seconds

### 4. CS/Min Tracker Validation
**Test**: Validate CS/min calculation against in-game score.

**Steps**:
1. Play a game for 10 minutes
2. Compare overlay CS/min with in-game stats (Tab key)
3. Record at 5, 10, and 20 minute marks

**Expected Result**: CS/min within ±0.5 of actual

### 5. Minimap Alert
**Test**: Trigger minimap alert by enemy appearance.

**Steps**:
1. Start a game
2. Walk an enemy bot into vision on minimap
3. Observe border pulse on overlay

**Expected Result**: Red border pulse appears on minimap area

### 6. Passive Information Mode
**Test**: Ensure disabling features stops notifications.

**Steps**:
1. Set `map_awareness: false` in config
2. Restart application
3. Trigger minimap event

**Expected Result**: No minimap alert displayed

### 7. Adaptive Jitter Verification
**Test**: Measure latency for adaptive jitter functionality.

**Steps**:
1. Enable debug logging in IPC handler
2. Trigger multiple events
3. Measure time from event to notification

**Expected Result**:
- Objective timers: 50-200ms delay
- Minimap alerts: 30-80ms delay
- Purchase suggestions: 150-400ms delay

### 8. Memory Leak Test
**Test**: Monitor for memory leaks during extended operation.

**Steps**:
1. Start application
2. Run alongside game for 30 minutes
3. Monitor Python process memory usage

**Expected Result**: Memory usage stable, no significant growth

### 9. Process Isolation
**Test**: Verify analysis engine runs in separate process.

**Steps**:
1. Start application
2. Check process list for separate Python processes
3. Kill analysis engine process

**Expected Result**: Main process continues, overlay shows disconnected

### 10. IPC Reconnection
**Test**: Test IPC reconnection after backend restart.

**Steps**:
1. Start application
2. Stop analysis engine
3. Restart analysis engine

**Expected Result**: Overlay automatically reconnects within 3 seconds

## Features

### ✅ Implemented

- ✅ Secure screen capture (window-specific, ROI-based)
- ✅ Sandboxed analysis engine process
- ✅ WebSocket IPC with adaptive jitter
- ✅ OCR text extraction (game clock, CS, gold, kill feed)
- ✅ Minimap threat detection (color-based)
- ✅ Objective timers (Dragon, Baron, Herald)
- ✅ CS/min tracker with performance rating
- ✅ Purchase suggestions framework
- ✅ Map awareness alerts
- ✅ Transparent, click-through overlay
- ✅ Configuration management
- ✅ Operational modes (Standard/Passive)

### 🚧 Future Enhancements

- Advanced template matching for champion detection
- Machine learning-based threat prediction
- Item build path database integration
- Multi-language OCR support
- Custom alert configurations
- Performance profiling dashboard
- Replay file analysis

## Project Structure

```
League-of-Legends-Horx/
├── main.py                      # Application entry point
├── package.json                 # Node.js dependencies
├── requirements.txt             # Python dependencies
├── README.md                    # This file
│
├── src/
│   ├── capture/
│   │   └── capture_manager.py   # Screen capture module
│   │
│   ├── analysis/
│   │   ├── engine.py           # Analysis engine core
│   │   ├── ocr_reader.py       # OCR text extraction
│   │   └── minimap_analyzer.py # Minimap analysis
│   │
│   ├── features/
│   │   └── strategic_features.py # Strategic assistant features
│   │
│   ├── ipc/
│   │   └── ipc_handler.py      # IPC with adaptive jitter
│   │
│   ├── config/
│   │   ├── config_loader.py    # Configuration management
│   │   ├── rois.json           # ROI definitions
│   │   └── app_config.json     # Application settings (optional)
│   │
│   └── overlay/
│       ├── main.js             # Electron main process
│       ├── renderer.js         # Overlay rendering logic
│       └── index.html          # Overlay UI structure
```

## Safety & Security

### Design Principles

1. **Process Isolation**: Analysis engine runs in separate sandboxed process
2. **No Disk Writes**: All frame processing in-memory only
3. **Secure IPC**: Local-only WebSocket with no external network access
4. **Adaptive Jitter**: Randomized delays to minimize behavioral footprint
5. **Click-Through UI**: Overlay never intercepts game inputs
6. **Minimal Permissions**: No unnecessary system access

### Disclaimer

This tool is designed for educational and strategic assistance purposes. Users are responsible for ensuring compliance with League of Legends Terms of Service. The developers make no guarantees regarding detection or account safety.

## Troubleshooting

### Electron doesn't start
```bash
npm install
npm install electron --save-dev
```

### Tesseract not found
Install Tesseract OCR and add to PATH:
- Windows: https://github.com/UB-Mannheim/tesseract/wiki
- Add installation path to system PATH

### Game window not detected
- Ensure League of Legends is running
- Check `target_window_name` in config matches window title
- Use fallback mode for testing: `use_fallback=True` in capture manager

### WebSocket connection fails
- Check if port 8765 is available
- Verify firewall isn't blocking localhost connections
- Ensure analysis engine starts before overlay

### Poor OCR accuracy
- Adjust ROI coordinates in `rois.json`
- Increase `ocr_confidence_threshold` in config
- Ensure UI scale is 100% in game settings

## Development

### Running in Development Mode

```bash
python main.py --dev
```

This enables:
- Electron DevTools
- Verbose logging
- Hot reload for overlay (manual)

### Adding New Features

1. Create feature logic in `src/features/strategic_features.py`
2. Add event creation in IPC handler
3. Add UI rendering in `src/overlay/renderer.js`
4. Update configuration schema in `config_loader.py`

### Testing with Mock Data

All modules support mock/fallback mode for testing without game:

```python
# Use mock OCR
ocr_reader = create_ocr_reader(use_mock=True)

# Use fallback capture
capture_manager = create_capture_manager(..., use_fallback=True)

# Use mock minimap analyzer
minimap_analyzer = create_minimap_analyzer(use_mock=True)
```

## Contributing

Contributions are welcome! Please ensure:

1. Code follows existing style and structure
2. All tests pass
3. New features include test cases
4. Documentation is updated
5. Security implications are considered

## License

MIT License - See LICENSE file for details

## Acknowledgments

- Built with safety and security as primary design goals
- Inspired by community interest in strategic learning tools
- Thanks to the League of Legends community

---

**Note**: This project is not affiliated with Riot Games. League of Legends and Riot Games are trademarks or registered trademarks of Riot Games, Inc.
