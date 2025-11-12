"""
Flask Web Application for LOL-HORX Dashboard

Web-based interface for monitoring game analysis in real-time.
Replaces Electron overlay with browser-accessible dashboard.
"""

from flask import Flask, render_template, jsonify, request
from flask_socketio import SocketIO, emit
from flask_cors import CORS
import asyncio
import threading
import json
from datetime import datetime

# Import analysis components
from src.config.config_loader import ConfigLoader
from src.analysis.engine import AnalysisEngine

app = Flask(__name__,
            static_folder='src/web/static',
            template_folder='src/web/templates')
app.config['SECRET_KEY'] = 'lol-horx-secret-key-change-in-production'

# Enable CORS for development
CORS(app)

# Initialize SocketIO for real-time updates
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# Global state
config_loader = None
config = None
analysis_engine = None
engine_thread = None
game_state = {
    'connected': False,
    'game_time': '0:00',
    'objective_timers': [],
    'cs_stats': None,
    'minimap_alerts': [],
    'last_update': None
}


def initialize_application():
    """Initialize configuration and analysis engine"""
    global config_loader, config, analysis_engine

    config_loader = ConfigLoader()
    config = config_loader.load_config()

    print("Web application initialized")
    print(f"  Mode: {config.mode}")
    print(f"  Features: {[k for k, v in config.features.items() if v]}")


@app.route('/')
def index():
    """Main dashboard page"""
    return render_template('dashboard.html')


@app.route('/api/status')
def get_status():
    """Get current application status"""
    return jsonify({
        'status': 'running',
        'engine_active': analysis_engine is not None and analysis_engine.running,
        'config': {
            'mode': config.mode,
            'features': config.features,
            'capture_fps': config.capture_fps
        }
    })


@app.route('/api/config', methods=['GET', 'POST'])
def handle_config():
    """Get or update configuration"""
    global config

    if request.method == 'GET':
        return jsonify({
            'mode': config.mode,
            'features': config.features,
            'capture_fps': config.capture_fps,
            'jitter_ranges': config.jitter_ranges
        })

    elif request.method == 'POST':
        data = request.json

        # Update features
        if 'features' in data:
            for feature, enabled in data['features'].items():
                if feature in config.features:
                    config.features[feature] = enabled

        # Update mode
        if 'mode' in data:
            config_loader.set_operational_mode(data['mode'])

        # Save configuration
        config_loader.save_config()

        # Notify clients
        socketio.emit('config_updated', {
            'features': config.features,
            'mode': config.mode
        })

        return jsonify({'success': True})


@app.route('/api/game-state')
def get_game_state():
    """Get current game state"""
    return jsonify(game_state)


@app.route('/api/engine/start', methods=['POST'])
def start_engine():
    """Start the analysis engine"""
    global analysis_engine, engine_thread

    if analysis_engine and analysis_engine.running:
        return jsonify({'error': 'Engine already running'}), 400

    try:
        # Create new analysis engine
        analysis_engine = WebAnalysisEngine(config_loader)

        # Start in separate thread
        engine_thread = threading.Thread(target=run_engine, daemon=True)
        engine_thread.start()

        return jsonify({'success': True, 'message': 'Analysis engine started'})

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/engine/stop', methods=['POST'])
def stop_engine():
    """Stop the analysis engine"""
    global analysis_engine

    if not analysis_engine or not analysis_engine.running:
        return jsonify({'error': 'Engine not running'}), 400

    analysis_engine.running = False

    return jsonify({'success': True, 'message': 'Analysis engine stopped'})


def run_engine():
    """Run the analysis engine (called in separate thread)"""
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(analysis_engine.run())
    except Exception as e:
        print(f"Engine error: {e}")
        import traceback
        traceback.print_exc()


class WebAnalysisEngine(AnalysisEngine):
    """
    Extended analysis engine that sends updates to web clients via SocketIO
    """

    def __init__(self, config_loader):
        """Initialize with web integration"""
        # Don't initialize IPC handler (we'll use SocketIO instead)
        self.config_loader = config_loader
        self.config = config_loader.config

        # Initialize components
        from src.capture.capture_manager import create_capture_manager
        from src.analysis.ocr_reader import create_ocr_reader
        from src.analysis.minimap_analyzer import create_minimap_analyzer
        from src.features.strategic_features import StrategicAssistant

        self.capture_manager = create_capture_manager(
            self.config.target_window_name,
            self.config.rois,
            use_fallback=True
        )

        self.ocr_reader = create_ocr_reader(
            confidence_threshold=self.config.ocr_confidence_threshold,
            use_mock=True
        )

        self.minimap_analyzer = create_minimap_analyzer(use_mock=True)
        self.strategic_assistant = StrategicAssistant(self.config)

        # State
        self.running = False
        self.last_capture_time = 0
        self.capture_interval = 1.0 / self.config.capture_fps
        self.frame_count = 0

        # Find game window
        self.capture_manager.find_game_window()

    async def run(self):
        """Main analysis loop with web updates"""
        self.running = True

        print("Web Analysis Engine running...")

        # Notify web clients
        socketio.emit('engine_status', {'status': 'running', 'connected': True})
        game_state['connected'] = True

        try:
            while self.running:
                current_time = asyncio.get_event_loop().time()

                if current_time - self.last_capture_time >= self.capture_interval:
                    await self._process_frame_web()
                    self.last_capture_time = current_time

                await asyncio.sleep(0.01)

        except Exception as e:
            print(f"Engine error: {e}")
            socketio.emit('engine_error', {'error': str(e)})

        finally:
            self.running = False
            socketio.emit('engine_status', {'status': 'stopped', 'connected': False})
            game_state['connected'] = False

    async def _process_frame_web(self):
        """Process frame and send updates to web clients"""
        import time

        try:
            # Get required ROIs
            rois_to_capture = self._get_required_rois()
            frames = self.capture_manager.capture_specific_rois(rois_to_capture)

            ocr_data = {}
            events = []

            # Process game clock
            if "game_clock" in frames:
                game_time = self.ocr_reader.read_game_time(frames["game_clock"].image)
                if game_time:
                    ocr_data["game_time"] = game_time
                    game_state['game_time'] = str(game_time)

            # Process CS
            if "player_cs" in frames:
                cs = self.ocr_reader.read_cs(frames["player_cs"].image)
                if cs is not None:
                    ocr_data["cs"] = cs

            # Process gold
            if "player_gold" in frames:
                gold = self.ocr_reader.read_gold(frames["player_gold"].image)
                if gold is not None:
                    ocr_data["gold"] = gold

            # Process kill feed
            if "kill_feed" in frames:
                objective_events = self.ocr_reader.parse_kill_feed(frames["kill_feed"].image)
                if objective_events:
                    ocr_data["objective_events"] = objective_events

                    for event in objective_events:
                        timer = self.strategic_assistant.objective_timers.add_objective_event(event)
                        if timer:
                            events.append({
                                'type': 'objective_timer',
                                'objective': event.objective_type.value,
                                'respawn_time': timer.respawn_time,
                                'time_remaining': timer.time_remaining(time.time())
                            })

            # Update strategic assistant
            self.strategic_assistant.process_ocr_data(ocr_data)

            # Process minimap
            if "minimap" in frames:
                threats = self.minimap_analyzer.analyze(frames["minimap"].image)
                alerts = self.strategic_assistant.process_minimap_data(threats)

                for alert in alerts:
                    events.append({
                        'type': 'minimap_alert',
                        'position': alert['position'],
                        'confidence': alert['confidence']
                    })

            # Send events to web clients
            if events:
                socketio.emit('game_events', {'events': events})

            # Send state update every 5 seconds
            if self.frame_count % (self.config.capture_fps * 5) == 0:
                state = self.strategic_assistant.get_state()

                # Update global game state
                if 'features' in state:
                    if 'objective_timers' in state['features']:
                        game_state['objective_timers'] = state['features']['objective_timers']

                    if 'cs_tracker' in state['features']:
                        game_state['cs_stats'] = state['features']['cs_tracker']

                game_state['last_update'] = datetime.now().isoformat()

                # Emit to clients
                socketio.emit('state_update', state)

            self.frame_count += 1

        except Exception as e:
            print(f"Error processing frame: {e}")


# SocketIO event handlers
@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    print(f"Client connected: {request.sid}")
    emit('connection_status', {'connected': True})
    emit('game_state', game_state)


@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection"""
    print(f"Client disconnected: {request.sid}")


@socketio.on('request_state')
def handle_state_request():
    """Client requests current game state"""
    emit('game_state', game_state)


@socketio.on('ping')
def handle_ping():
    """Respond to ping"""
    emit('pong', {'timestamp': datetime.now().isoformat()})


def main():
    """Main entry point for web application"""
    print("="*60)
    print("LOL-HORX Web Dashboard")
    print("="*60)

    # Initialize application
    initialize_application()

    # Run Flask app with SocketIO
    print("\nStarting web server...")
    print(f"Dashboard: http://localhost:5000")
    print(f"API: http://localhost:5000/api/status")
    print("\nPress Ctrl+C to stop")

    socketio.run(app, host='0.0.0.0', port=5000, debug=False)


if __name__ == "__main__":
    main()
