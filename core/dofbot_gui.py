"""
Unified Robot Server + GUI with Camera & Object Detection
Combines Flask web interface with robot control and YOLO vision
Runs on Raspberry Pi (or localhost for testing)

Directory Structure:
project_root/
├── core/
│   └── dofbot_gui.py  ← THIS FILE
├── Gui/
│   ├── templates/
│   │   └── Index.html
│   └── static/
└── ... other files
"""

import sys
import os
import threading
import time
from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO

# Safe import for OpenCV (cv2)
try:
    import cv2
    CV2_AVAILABLE = True
    print("✅ OpenCV (cv2) loaded")
except ImportError as e:
    cv2 = None
    CV2_AVAILABLE = False
    print(f"⚠️  Warning: OpenCV (cv2) not available: {e}")

# ============= IMPORT SETUP =============
def setup_imports():
    """Setup all imports with proper path handling"""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.abspath(os.path.join(current_dir, '..'))
    
    for path in [current_dir, parent_dir]:
        if path not in sys.path:
            sys.path.insert(0, path)

setup_imports()

# Safe import handling for robot controller
def safe_import_robot_controller():
    """Safely import RobotController with fallback"""
    try:
        from robot_controller import RobotController
        print("✅ RobotController loaded")
        return RobotController
    except ImportError as e:
        print(f"⚠️  Warning: Could not import RobotController: {e}")
        print("⚠️  Running in MOCK mode - no actual robot control")
        return None

# Safe import handling for calibration
def safe_import_calibration():
    """Safely import calibration functions"""
    try:
        from calibration_files.Coord_converter import pixel_to_shelf
        print("✅ Calibration module loaded")
        return pixel_to_shelf
    except ImportError as e:
        print(f"⚠️  Warning: Could not import calibration: {e}")
        print("⚠️  Using mock coordinate conversion")
        def mock_pixel_to_shelf(x, y, bbox_height_pixels=None, label=None, shelf_z=0):
            """Mock conversion for testing"""
            return 150.0, 0.0, 100.0
        return mock_pixel_to_shelf

# Safe import handling for object detector
def safe_import_detector():
    """Safely import ObjectDetector3D with fallback"""
    try:
        from Object_detector import ObjectDetector3D
        print("✅ Object detector loaded")
        return ObjectDetector3D
    except ImportError as e:
        print(f"⚠️  Warning: Could not import ObjectDetector3D: {e}")
        print("⚠️  Vision features will be disabled")
        return None

RobotController = safe_import_robot_controller()
pixel_to_shelf = safe_import_calibration()
ObjectDetector3D = safe_import_detector()

# ============= CONFIGURATION =============
GUI_HOST = '0.0.0.0'  # Allow connections from any IP
GUI_PORT = 5000       # Web interface port

# YOLO Model path - UPDATE THIS TO YOUR MODEL
MODEL_PATH = 'model/runs/train/toy_animals_full/weights/best.pt'  # or 'yolov8n.pt' or your trained model path

# ============= FALLBACK ANIMAL POSITIONS =============
FALLBACK_POSITIONS = {
    'lion': {'x': 180, 'y': 50, 'z': 100},
    'tiger': {'x': 180, 'y': -50, 'z': 100},
    'elephant': {'x': 150, 'y': 100, 'z': 100},
    'zebra': {'x': 150, 'y': -100, 'z': 100},
    'giraffe': {'x': 120, 'y': 80, 'z': 100},
    'leopard': {'x': 120, 'y': -80, 'z': 100},
}

DROP_ZONE = {'x': 100, 'y': -150, 'z': 150}


# ============= ROBOT CONTROLLER WITH VISION =============
class RobotController_Manager:
    """
    Manages robot hardware, camera, and vision-based object detection.
    Integrates YOLO detection with robot arm control.
    """
    
    def __init__(self, use_real_hardware=False, use_vision=True):
        """
        Initialize robot controller with optional vision.
        
        Args:
            use_real_hardware: If True, initialize real arm. If False, simulate.
            use_vision: If True, use camera and YOLO detection. If False, use fallback positions.
        """
        self.use_real_hardware = use_real_hardware
        self.use_vision = use_vision
        self.robot = None
        self.detector = None
        self.holding_object = False
        self.current_object = None
        
        # Initialize robot hardware
        if RobotController is None:
            print("⚠️  RobotController not available - using mock mode only")
        else:
            try:
                print("🤖 Initializing robot...")
                self.robot = RobotController(use_real_hardware=use_real_hardware)
                self.robot.connect()
                self.robot.home()
                print("✅ Robot initialized and homed")
            except Exception as e:
                print(f"⚠️  Error initializing robot: {e}")
                print("⚠️  Continuing in mock mode")
                self.robot = None
        
        # Initialize vision system
        if use_vision and ObjectDetector3D is not None:
            try:
                print("📷 Initializing camera and YOLO detector...")
                self.detector = ObjectDetector3D(
                    model_path=MODEL_PATH,
                    camera_calibration_path='calibration_files/',
                    camera_index=0
                )
                print("✅ Vision system initialized")
            except Exception as e:
                print(f"⚠️  Error initializing vision: {e}")
                print("⚠️  Falling back to predefined positions")
                self.detector = None
                self.use_vision = False
        else:
            print("⚠️  Vision system not available - using fallback positions")
            self.use_vision = False
    
    def detect_object_position(self, animal_name):
        """
        Use camera and YOLO to detect object position in real-time.
        
        Args:
            animal_name: Name of animal to detect
            
        Returns:
            dict: {'x': float, 'y': float, 'z': float} or None if not found
        """
        if not self.use_vision or not self.detector:
            print("⚠️  Vision not available, using fallback position")
            return FALLBACK_POSITIONS.get(animal_name)
        
        try:
            print(f"📷 Capturing frame to detect {animal_name}...")
            
            # Open camera
            if not self.detector.open_camera():
                print("❌ Failed to open camera")
                return FALLBACK_POSITIONS.get(animal_name)
            
            # Capture frame
            ret, frame = self.detector.cap.read()
            if not ret:
                print("❌ Failed to capture frame")
                self.detector.close_camera()
                return FALLBACK_POSITIONS.get(animal_name)
            
            # Apply undistortion if available
            if (self.detector.map1 is not None and 
                self.detector.map2 is not None and 
                CV2_AVAILABLE):
                try:
                    frame = cv2.remap(frame, self.detector.map1,
                                    self.detector.map2, cv2.INTER_LINEAR)
                except Exception as e:
                    print(f"⚠️  Warning: Undistortion failed: {e}")
            
            # Run YOLO detection
            print(f"🔍 Running detection for {animal_name}...")
            detections = self.detector.detect_animals(frame)
            
            # Find target animal
            target_detection = None
            for label, cx, cy, x1, y1, x2, y2, conf in detections:
                if label.lower() == animal_name.lower():
                    target_detection = (label, cx, cy, x1, y1, x2, y2, conf)
                    break
            
            self.detector.close_camera()
            
            if not target_detection:
                print(f"❌ {animal_name} not detected in frame")
                return FALLBACK_POSITIONS.get(animal_name)
            
            # Extract detection info
            label, cx, cy, x1, y1, x2, y2, conf = target_detection
            bbox_height = y2 - y1
            
            print(f"✅ Detected {label} at pixel ({cx}, {cy}) with confidence {conf:.2f}")
            
            # Convert to robot coordinates
            X, Y, Z = pixel_to_shelf(cx, cy, bbox_height_pixels=bbox_height, 
                                    label=label, shelf_z=0)
            
            if X is None or Y is None or Z is None:
                print("❌ Failed to convert coordinates")
                return FALLBACK_POSITIONS.get(animal_name)
            
            print(f"📍 Robot coordinates: X={X:.2f}mm, Y={Y:.2f}mm, Z={Z:.2f}mm")
            
            return {'x': float(X), 'y': float(Y), 'z': float(Z)}
        
        except Exception as e:
            print(f"❌ Error in vision detection: {e}")
            import traceback
            traceback.print_exc()
            return FALLBACK_POSITIONS.get(animal_name)
    
    def parse_command(self, command_text):
        """Parse natural language commands."""
        cmd = command_text.lower().strip()
        print(f"📨 Parsing command: '{cmd}'")
        
        animals = list(FALLBACK_POSITIONS.keys())
        found_animal = next((animal for animal in animals if animal in cmd), None)
        
        # --- VISION CONTROL ---
        if 'vision' in cmd:
            if 'on' in cmd:
                if ObjectDetector3D is not None:
                    self.use_vision = True
                    return {'status': 'happy', 'message': 'Vision system enabled! 📷'}
                else:
                    return {'status': 'sad', 'message': 'Vision system not available! 😢'}
            elif 'off' in cmd:
                self.use_vision = False
                return {'status': 'happy', 'message': 'Vision system disabled. Using fallback positions! 📍'}
        
        # --- HELP COMMAND ---
        if 'help' in cmd:
            animal_list = ', '.join(animals)
            vision_status = "ON 📷" if self.use_vision else "OFF 📍"
            return {'status': 'happy', 'message': f'I can find: {animal_list} 🐾\nVision: {vision_status}'}
        
        # --- GRAB/PICK COMMAND ---
        if any(word in cmd for word in ['grab', 'pick', 'take']):
            if found_animal:
                return self.grab_object(found_animal)
            else:
                return {'status': 'confused', 'message': 'Which animal do you want me to grab? 🤔'}
        
        # --- PUT BACK COMMAND ---
        if 'put' in cmd and 'back' in cmd:
            if self.holding_object:
                return self.put_back_object()
            else:
                return {'status': 'sad', 'message': 'I am not holding anything! 😢'}
        
        # --- FIND/SEARCH COMMAND ---
        if any(word in cmd for word in ['find', 'search', 'look']):
            if found_animal:
                return self.search_object(found_animal)
            else:
                return {'status': 'confused', 'message': 'What animal are we looking for? 🔍'}
        
        # --- HOME COMMAND ---
        if 'home' in cmd:
            return self.go_home()
        
        # --- DEFAULT ---
        return {'status': 'sad', 'message': "I didn't understand that! Say 'help' for commands. 😢"}
    
    def grab_object(self, animal):
        """Detect and grab an object using vision or fallback positions."""
        if not self.robot:
            vision_status = " (VISION)" if self.use_vision else " (FALLBACK)"
            return {'status': 'grab', 'message': f'[MOCK{vision_status}] Dora grabbed the {animal}! 🤗'}
        
        try:
            if self.holding_object:
                return {'status': 'sad', 'message': f'I am already holding the {self.current_object}! 😢'}
            
            pos = self.detect_object_position(animal)
            
            if not pos:
                return {'status': 'sad', 'message': f'I do not know where the {animal} is! 😢'}
            
            source = "📷 Vision detected" if self.use_vision else "📍 Using saved position"
            print(f"🎯 {source}: Grabbing {animal} at {pos}")
            
            success = self.robot.pick_object(pos['x'], pos['y'], pos['z'], obj_label=animal)
            
            if success:
                self.holding_object = True
                self.current_object = animal
                vision_emoji = "📷" if self.use_vision else "📍"
                return {'status': 'grab', 'message': f'Dora grabbed the {animal}! {vision_emoji}🤗'}
            else:
                return {'status': 'sad', 'message': f'I could not grab the {animal}! 😢'}
        
        except Exception as e:
            print(f"❌ Error grabbing object: {e}")
            return {'status': 'sad', 'message': f'Oops! Something went wrong: {str(e)}'}
    
    def search_object(self, animal):
        """Search for an object using vision or move to fallback position."""
        if not self.robot:
            vision_status = " (VISION)" if self.use_vision else " (FALLBACK)"
            return {'status': 'happy', 'message': f'[MOCK{vision_status}] Dora found the {animal}! 🐾'}
        
        try:
            pos = self.detect_object_position(animal)
            
            if not pos:
                return {'status': 'sad', 'message': f'I have not seen the {animal}! 😢'}
            
            source = "📷 Vision detected" if self.use_vision else "📍 Using saved position"
            print(f"🔍 {source}: Searching for {animal} at {pos}")
            
            self.robot.move_to(pos['x'], pos['y'], pos['z'] + 100, gripper_open=True)
            
            vision_emoji = "📷" if self.use_vision else "📍"
            return {'status': 'happy', 'message': f'Dora found the {animal}! {vision_emoji}🐾'}
        
        except Exception as e:
            print(f"❌ Error searching: {e}")
            return {'status': 'sad', 'message': f'I could not search: {str(e)}'}
    
    def put_back_object(self):
        """Put object back in drop zone and return home."""
        if not self.robot:
            return {'status': 'putback', 'message': '[MOCK] We did it! 🎉'}
        
        try:
            if not self.holding_object:
                return {'status': 'sad', 'message': 'I am not holding anything! 😢'}
            
            print(f"🏠 Putting back {self.current_object}")
            
            drop = DROP_ZONE
            self.robot.move_to(drop['x'], drop['y'], drop['z'], gripper_open=False)
            self.robot.set_gripper(True)
            time.sleep(0.5)
            self.robot.home()
            
            self.holding_object = False
            object_name = self.current_object
            self.current_object = None
            
            return {'status': 'putback', 'message': f'We put the {object_name} back! Yay! 🎉'}
        
        except Exception as e:
            print(f"❌ Error putting back object: {e}")
            return {'status': 'sad', 'message': f'Oops! Could not put it back: {str(e)}'}
    
    def go_home(self):
        """Return robot to home position."""
        if not self.robot:
            return {'status': 'happy', 'message': '[MOCK] Dora is home! 🏠'}
        
        try:
            print("🏠 Moving home")
            self.robot.home()
            return {'status': 'happy', 'message': 'Dora is ready! 🏠'}
        except Exception as e:
            print(f"❌ Error going home: {e}")
            return {'status': 'sad', 'message': f'Could not go home: {str(e)}'}
    
    def shutdown(self):
        """Safely shutdown robot and camera connections."""
        if self.robot:
            try:
                print("👋 Disconnecting robot...")
                self.robot.disconnect()
            except Exception as e:
                print(f"⚠️  Error disconnecting robot: {e}")
        
        if self.detector:
            try:
                print("📷 Closing camera...")
                self.detector.close_camera()
            except Exception as e:
                print(f"⚠️  Error closing camera: {e}")


# ============= FLASK WEB APPLICATION =============

# Initialize robot controller (global instance)
robot_manager = None

# Flask setup - Paths for core/dofbot_gui.py structure
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))  # core/
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)               # project_root/

TEMPLATE_DIR = os.path.join(SCRIPT_DIR, 'Gui', 'templates')
STATIC_DIR = os.path.join(SCRIPT_DIR, 'Gui', 'static')

print(f"\n{'='*70}")
print(f"📁 FLASK PATH CONFIGURATION")
print(f"{'='*70}")
print(f"Script location:  {SCRIPT_DIR}")
print(f"Project root:     {PROJECT_ROOT}")
print(f"Template dir:     {TEMPLATE_DIR}")
print(f"Static dir:       {STATIC_DIR}")

# Verify directories exist
template_exists = os.path.exists(TEMPLATE_DIR)
static_exists = os.path.exists(STATIC_DIR)

print(f"Template exists:  {'✅' if template_exists else '❌'}")
print(f"Static exists:    {'✅' if static_exists else '❌'}")

# List files in template directory
if template_exists:
    try:
        files = [f for f in os.listdir(TEMPLATE_DIR) if os.path.isfile(os.path.join(TEMPLATE_DIR, f))]
        print(f"Template files:   {', '.join(files) if files else 'EMPTY'}")
        
        # Check for Index.html specifically
        index_variations = ['Index.html', 'index.html', 'INDEX.html']
        for var in index_variations:
            if var in files:
                print(f"✅ Found: {var}")
    except Exception as e:
        print(f"⚠️  Could not list template files: {e}")

print(f"{'='*70}\n")

app = Flask(__name__, 
            template_folder=TEMPLATE_DIR,
            static_folder=STATIC_DIR)

socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')


def find_index_template():
    """Find the correct index template (case-insensitive)"""
    try:
        files = os.listdir(TEMPLATE_DIR)
        for filename in files:
            if filename.lower() == 'index.html':
                return filename
    except:
        pass
    return 'Index.html'  # Default fallback


@app.route('/')
def index():
    """Home page"""
    template_name = find_index_template()
    try:
        return render_template(template_name)
    except Exception as e:
        # If template not found, show helpful error page
        try:
            files = os.listdir(TEMPLATE_DIR)
            file_list = '<br>'.join(f'• {f}' for f in files)
        except:
            file_list = 'Could not list files'
        
        return f"""
        <html>
        <head><title>Template Not Found</title></head>
        <body style="font-family: Arial; padding: 20px;">
            <h1>❌ Template Not Found</h1>
            <p><strong>Error:</strong> {str(e)}</p>
            <p><strong>Looking for:</strong> {template_name}</p>
            <p><strong>In directory:</strong> {TEMPLATE_DIR}</p>
            <hr>
            <h2>Files found:</h2>
            <p>{file_list}</p>
            <hr>
            <h3>💡 Solutions:</h3>
            <ol>
                <li>Make sure Index.html exists in: <code>{TEMPLATE_DIR}</code></li>
                <li>Check the filename case matches exactly</li>
                <li>Verify the Gui/templates directory structure</li>
            </ol>
        </body>
        </html>
        """, 404


@app.route('/send', methods=['POST'])
def send():
    """Endpoint to send command to robot"""
    data = request.json
    command = data.get('command', '').strip()
    
    if not command:
        return jsonify({'ok': False, 'error': 'No command provided'})
    
    socketio.emit('status', {'state': 'thinking', 'message': '🤔 Dora is thinking...'})
    threading.Thread(target=execute_command, args=(command,), daemon=True).start()
    
    return jsonify({'ok': True})


@app.route('/vision/status', methods=['GET'])
def vision_status():
    """Get current vision system status"""
    global robot_manager
    if robot_manager:
        return jsonify({
            'enabled': robot_manager.use_vision,
            'available': robot_manager.detector is not None
        })
    return jsonify({'enabled': False, 'available': False})


def execute_command(command):
    """Execute robot command and update GUI with response."""
    global robot_manager
    
    try:
        if robot_manager is None:
            socketio.emit('status', {'state': 'sad', 'message': 'Robot is not initialized! 😢'})
            return
        
        response = robot_manager.parse_command(command)
        state = response.get('status', 'sad')
        message = response.get('message', '')
        
        socketio.emit('status', {'state': state, 'message': message})
    
    except Exception as e:
        print(f"❌ Error executing command: {e}")
        socketio.emit('status', {'state': 'sad', 'message': "Uh-oh! Something went wrong. 😢"})


# ============= MAIN APPLICATION =============

def start_application(use_real_hardware=False, use_vision=True, 
                     host=None, port=None, debug=False):
    """Start the unified robot server and GUI with vision support."""
    global robot_manager
    
    if host is None:
        host = GUI_HOST
    if port is None:
        port = GUI_PORT
    
    print(f"\n{'='*60}")
    print(f"🤖 DORA ROBOT SERVER + GUI + VISION STARTING")
    print(f"{'='*60}")
    
    print("🔧 Initializing robot controller with vision...")
    robot_manager = RobotController_Manager(
        use_real_hardware=use_real_hardware,
        use_vision=use_vision
    )
    
    print(f"🎨 Starting web interface on http://{host}:{port}")
    print(f"🔧 Hardware mode: {use_real_hardware}")
    print(f"📷 Vision mode: {use_vision}")
    print(f"✅ Ready for commands!")
    print(f"{'='*60}\n")
    
    try:
        socketio.run(app, host=host, port=port, debug=debug, 
                    use_reloader=False, allow_unsafe_werkzeug=True)
    except KeyboardInterrupt:
        print("\n🛑 Shutting down...")
    finally:
        if robot_manager:
            robot_manager.shutdown()
        print("✅ Application stopped")


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Dora Robot Server + GUI + Vision')
    parser.add_argument('--hardware', action='store_true', 
                       help='Connect to real hardware (Raspberry Pi)')
    parser.add_argument('--no-vision', action='store_true',
                       help='Disable vision system (use fallback positions)')
    parser.add_argument('--host', default=GUI_HOST,
                       help=f'Server host (default: {GUI_HOST})')
    parser.add_argument('--port', type=int, default=GUI_PORT,
                       help=f'Server port (default: {GUI_PORT})')
    parser.add_argument('--debug', action='store_true',
                       help='Enable debug mode')
    parser.add_argument('--model', default=MODEL_PATH,
                       help=f'Path to YOLO model (default: {MODEL_PATH})')
    
    args = parser.parse_args()
    
    if args.model:
        MODEL_PATH = args.model
    
    try:
        start_application(
            use_real_hardware=args.hardware,
            use_vision=not args.no_vision,
            host=args.host,
            port=args.port,
            debug=args.debug
        )
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)