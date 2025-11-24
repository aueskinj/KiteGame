# Must import and patch eventlet before anything else
import eventlet
eventlet.monkey_patch()

# Now we can safely import other modules
import time
from flask import Flask, render_template
from flask_socketio import SocketIO, emit
from flask_cors import CORS
from game.core.game_state import GameState

# Create Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'  # Required for Flask-SocketIO
app.config['CORS_HEADERS'] = 'Content-Type'

# Enable CORS
CORS(app, resources={r"/*": {"origins": "*"}})

# Configure SocketIO with CORS settings
socketio = SocketIO(
    app,
    async_mode='eventlet',
    cors_allowed_origins="*",
    logger=False,
    engineio_logger=False
)

# Frame rate management
FRAME_RATE = 60
FRAME_TIME = 1.0 / FRAME_RATE
last_update = time.time()

# Create game state
game_state = GameState()

@app.route('/')
def index():
    """Render game interface."""
    return render_template('index.html')
    
@socketio.on('connect')
def handle_connect():
    """Handle new client connection."""
    with app.app_context():
        emit('game_state', game_state.get_client_data())
    
@socketio.on('input')
def handle_input(data):
    """Handle client input events."""
    with app.app_context():
        game_state.handle_event(data)

@socketio.on('new_game')
def handle_new_game():
    """Handle new game request."""
    global game_state
    with app.app_context():
        game_state = GameState()  # Create a fresh game state
        emit('game_state', game_state.get_client_data())
    
def game_loop():
    """Main game loop."""
    global last_update
    
    while True:
        try:
            current_time = time.time()
            dt = current_time - last_update
            last_update = current_time
            
            # Update game state within app context
            with app.app_context():
                game_state.update(dt)
                state_data = game_state.get_client_data()
            
            # Broadcast state to all clients
            socketio.emit('game_state', state_data, namespace='/')
            
            # Maintain frame rate
            elapsed = time.time() - current_time
            sleep_time = max(0, FRAME_TIME - elapsed)
            eventlet.sleep(sleep_time)
            
        except Exception as e:
            print(f"Error in game loop: {e}")
            eventlet.sleep(1)  # Sleep for a second before retrying
        
def create_app():
    """Create and configure the application."""
    return app

if __name__ == '__main__':
    try:
        # Start game loop in background
        eventlet.spawn(game_loop)
        
        # Start Flask-SocketIO server
        socketio.run(app,
                    host='0.0.0.0',  # Allow external connections
                    port=5000,
                    debug=True,
                    use_reloader=False)  # Disable reloader to avoid duplicate game loops
    except KeyboardInterrupt:
        print("\nShutting down gracefully...")
    except Exception as e:
        print(f"Error starting server: {e}")