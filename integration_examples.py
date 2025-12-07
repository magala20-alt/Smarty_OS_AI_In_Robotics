"""
INTEGRATION EXAMPLE
Demonstrates how to connect GUI, Robot Controller, and Object Detection

This example shows the complete flow from voice command to physical movement.
"""

# ============================================================================
# SIMPLIFIED EXAMPLE 1: Basic Command Processing
# ============================================================================

def example_basic_command_processing():
    """
    Show how a voice command flows through the system
    """
    print("\n" + "="*70)
    print("EXAMPLE 1: Basic Command Processing")
    print("="*70)
    
    # Step 1: User gives voice command (captured by GUI)
    voice_command = "Find the lion"
    print(f"\n1. User says: '{voice_command}'")
    
    # Step 2: GUI sends to robot_server.py
    print(f"\n2. GUI sends to robot_server on port 9001")
    print(f"   >>> send_command_to_pi('{voice_command}')")
    
    # Step 3: Robot server parses command
    print(f"\n3. Robot server parses command:")
    command = voice_command.lower()
    animals = ['lion', 'tiger', 'elephant', 'zebra', 'giraffe', 'leopard']
    found_animal = next((a for a in animals if a in command), None)
    action = 'find' if 'find' in command else 'search' if 'search' in command else 'unknown'
    print(f"   Action: {action}")
    print(f"   Animal: {found_animal}")
    
    # Step 4: Get position for animal
    print(f"\n4. Look up position for {found_animal}:")
    ANIMAL_POSITIONS = {
        'lion': {'x': 180, 'y': 50, 'z': 100},
        'tiger': {'x': 180, 'y': -50, 'z': 100},
    }
    pos = ANIMAL_POSITIONS.get(found_animal)
    print(f"   Position: X={pos['x']}mm, Y={pos['y']}mm, Z={pos['z']}mm")
    
    # Step 5: Call RobotController
    print(f"\n5. Call RobotController:")
    print(f"   robot.move_to({pos['x']}, {pos['y']}, {pos['z']}, gripper_open=True)")
    
    # Step 6: Return response to GUI
    print(f"\n6. Robot server sends response back:")
    response = {
        'status': 'happy',
        'message': 'Dora found the lion! 🐾'
    }
    print(f"   {response}")
    
    # Step 7: GUI updates browser
    print(f"\n7. Flask app emits to browser via Socket.IO:")
    print(f"   socketio.emit('status', {response})")
    print(f"   Browser shows happy Dora with message")


# ============================================================================
# SIMPLIFIED EXAMPLE 2: Pick and Place
# ============================================================================

def example_pick_and_place():
    """
    Show the complete pick sequence
    """
    print("\n" + "="*70)
    print("EXAMPLE 2: Pick and Place Sequence")
    print("="*70)
    
    animal = "tiger"
    x, y, z = 180, -50, 100
    
    print(f"\nCommand: 'Grab the {animal}'")
    print(f"Target position: ({x}, {y}, {z})")
    
    print(f"\nPick sequence:")
    print(f"  [1] move_to({x}, {y}, {z + 80}) - Approach above object")
    print(f"      Servos move to hover over tiger")
    print(f"      ✓ Time: 800ms")
    
    print(f"\n  [2] move_to({x}, {y}, {z + 10}) - Lower to grasp height")
    print(f"      Arm descends to grab position")
    print(f"      ✓ Time: 800ms")
    
    print(f"\n  [3] set_gripper(False) - Close gripper")
    print(f"      Servo 6 closes (angle: 50°)")
    print(f"      ✓ Time: 500ms")
    
    print(f"\n  [4] move_to({x}, {y}, {z + 80}) - Lift object")
    print(f"      Arm lifts tiger up")
    print(f"      ✓ Time: 800ms")
    
    print(f"\n  [5] move_to(100, -150, 150) - Move to drop zone")
    print(f"      Arm moves to drop location")
    print(f"      ✓ Time: 1500ms")
    
    print(f"\n  [6] set_gripper(True) - Release object")
    print(f"      Servo 6 opens (angle: 0°)")
    print(f"      ✓ Time: 500ms")
    
    print(f"\n  [7] home() - Return to safe position")
    print(f"      Arm moves to neutral position")
    print(f"      ✓ Time: 1000ms")
    
    print(f"\nTotal time: ~6.9 seconds")
    print(f"Response sent: {{'status': 'grab', 'message': 'Dora grabbed the tiger! 🤗'}}")


# ============================================================================
# SIMPLIFIED EXAMPLE 3: With Object Detection
# ============================================================================

def example_with_detection():
    """
    Show integration with object detection
    """
    print("\n" + "="*70)
    print("EXAMPLE 3: With Object Detection (Future Enhancement)")
    print("="*70)
    
    print("""
Advanced integration would add:

1. CAMERA CAPTURE
   └─ Capture frame from Raspberry Pi camera

2. OBJECT DETECTION
   frame = capture_frame()
   detections = yolo_detector(frame)
   # Returns: [{'label': 'lion', 'bbox': (x1,y1,x2,y2), 'conf': 0.95}]

3. COORDINATE CONVERSION
   pixel_coords = detections[0]['bbox']
   world_coords = pixel_to_shelf(pixel_coords, camera_matrix, distortion)
   # Returns: {'x': 150, 'y': 20, 'z': 100}  (real-world coordinates)

4. ROBOT PICKING
   robot.pick_detected_object({
       'label': 'lion',
       'x': 150,
       'y': 20,
       'z': 100,
       'confidence': 0.95
   })

5. RESPONSE
   Returns: {'status': 'happy', 'message': 'Found and picked the lion! 🎉'}

This makes it fully AUTONOMOUS! 🤖
    """)


# ============================================================================
# EXAMPLE 4: Code Integration Points
# ============================================================================

def example_code_integration():
    """
    Show actual code at each integration point
    """
    print("\n" + "="*70)
    print("EXAMPLE 4: Actual Code at Integration Points")
    print("="*70)
    
    code = """
# POINT 1: GUI (Gui/app.ipynb)
@app.route('/send', methods=['POST'])
def send():
    data = request.json
    command = data.get('command')
    response = send_command_to_pi(command)  # ← Calls pi_client
    socketio.emit('status', response)
    return jsonify({'ok': True})


# POINT 2: Client (Gui/pi_client.py)
def send_command_to_pi(command_text, timeout=8):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((PI_HOST, PI_PORT))  # Connect to robot_server.py
    s.send(command_text.encode())
    data = s.recv(4096)
    return json.loads(data.decode())


# POINT 3: Server (Gui/robot_server.py)
class RobotServer:
    def parse_command(self, command_text):
        # Parse "find the lion" → animal='lion', action='find'
        response = self.search_object('lion')
        return response
    
    def search_object(self, animal):
        pos = ANIMAL_POSITIONS[animal]
        self.robot.move_to(pos['x'], pos['y'], pos['z'], gripper_open=True)
        return {'status': 'happy', 'message': f'Dora found the {animal}! 🐾'}


# POINT 4: Controller (core/robot_controller.py)
class RobotController:
    def move_to(self, x, y, z, gripper_open=True):
        # Calculate servo angles from (x,y,z)
        angles = [90, 90, 90, 0, 90, 0 if gripper_open else 50]
        self._execute_move(angles, move_time=800)
        return True
    
    def _execute_move(self, angles, move_time=800):
        # Send to hardware via Arm_Device
        self.arm.Arm_serial_servo_write6(*angles, move_time)
        return True


# POINT 5: Hardware (Arm_Device)
arm.Arm_serial_servo_write6(90, 90, 90, 0, 90, 0)
# Servos move to specified angles
    """
    print(code)


# ============================================================================
# EXAMPLE 5: Testing Guide
# ============================================================================

def example_testing_guide():
    """
    How to test each part
    """
    print("\n" + "="*70)
    print("EXAMPLE 5: Testing Each Component")
    print("="*70)
    
    tests = """
TEST 1: Robot Server Only
  $ cd Gui
  $ python robot_server.py
  
  In another terminal:
  $ python -c "
import socket, json
s = socket.socket()
s.connect(('localhost', 9001))
s.send(b'find the lion')
print(json.loads(s.recv(4096)))
  "
  
  Expected: {'status': 'happy', 'message': 'Dora found the lion! 🐾'}


TEST 2: Flask + Robot Server
  Terminal 1: $ python Gui/robot_server.py
  Terminal 2: $ python -m flask run --port 5000
  
  Browser: http://localhost:5000
  Try: Click microphone and say "Find the lion"
  
  Expected: Dora shows happy animation with message


TEST 3: Full Integration
  Terminal 1: $ python Gui/robot_server.py --hardware
  Terminal 2: $ cd Gui && python -m flask run --port 5000
  
  Browser: http://192.168.X.X:5000  (Pi IP)
  Say: "Grab the tiger"
  
  Expected: Robot arm picks up tiger 🤖
    """
    print(tests)


# ============================================================================
# TROUBLESHOOTING EXAMPLES
# ============================================================================

def example_troubleshooting():
    """
    Common problems and solutions
    """
    print("\n" + "="*70)
    print("EXAMPLE 6: Troubleshooting")
    print("="*70)
    
    troubleshooting = """
PROBLEM: "Connection refused" when GUI sends command

Solution:
  1. Check server is running:
     $ lsof -i :9001  (Mac/Linux)
     or
     $ netstat -ano | findstr :9001  (Windows)
  
  2. If not running, start it:
     $ cd Gui
     $ python robot_server.py
  
  3. Check no firewall blocking port 9001


PROBLEM: "Module not found: core.robot_controller"

Solution:
  1. Convert notebook to Python:
     $ cd core
     $ jupyter nbconvert --to python robot_controller.ipynb
  
  2. Check file exists:
     $ ls core/robot_controller.py  (Mac/Linux)
     or
     $ dir core\\robot_controller.py  (Windows)


PROBLEM: Robot doesn't move, but server responds

Solution:
  1. You're probably in simulation mode (correct!)
  2. To use real hardware:
     $ python robot_server.py --hardware
  
  3. Check hardware is connected:
     - USB cable to Arm_Device
     - Python can import Arm_Lib
     $ python -c "from Arm_Lib import Arm_Device; print('OK')"


PROBLEM: Voice command not recognized

Solution:
  1. Check browser has microphone permission
  2. Speak clearly and say animal name
  3. Check browser console for JavaScript errors
  4. Check server logs for parsed command
    """
    print(troubleshooting)


# ============================================================================
# MAIN
# ============================================================================

if __name__ == '__main__':
    print("\n")
    print("╔" + "═"*68 + "╗")
    print("║" + " "*15 + "SMARTY OS - INTEGRATION EXAMPLES" + " "*21 + "║")
    print("╚" + "═"*68 + "╝")
    
    examples = [
        ("1. Basic Command Processing", example_basic_command_processing),
        ("2. Pick and Place Sequence", example_pick_and_place),
        ("3. Object Detection Integration", example_with_detection),
        ("4. Code Integration Points", example_code_integration),
        ("5. Testing Guide", example_testing_guide),
        ("6. Troubleshooting", example_troubleshooting),
    ]
    
    for i, (name, func) in enumerate(examples):
        try:
            func()
        except Exception as e:
            print(f"\nError in {name}: {e}")
    
    print("\n" + "="*70)
    print("END OF EXAMPLES")
    print("="*70)
    print("""
Next steps:
1. Review the documentation files:
   - CONNECTION_SUMMARY.md
   - QUICK_START.md
   - ARCHITECTURE.md
   - GUI_ROBOT_CONNECTION_GUIDE.md

2. Convert robot_controller.ipynb to .py
3. Start robot_server.py
4. Test with Flask app
5. Give voice commands!

Good luck! 🚀
    """)
