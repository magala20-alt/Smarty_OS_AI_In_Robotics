# GUI to Robot Controls - Connection Guide

## Current Architecture Overview

Your system has three main components:

### 1. **GUI Layer** (`Gui/app.ipynb` & `Gui/pi_client.py`)

- Flask web server with Socket.IO for real-time updates
- Frontend: `templates/Index.html` (child-friendly interface for Dora)
- Communicates with robot via `send_command_to_pi()` function
- Currently uses socket communication on port 9001

### 2. **Robot Controller** (`core/robot_controller.ipynb`)

- `RobotController` class that manages DofBot arm
- Provides methods for movement, gripper control, and autonomous picking
- Supports both real hardware and simulation mode
- Uses inverse kinematics and coordinate conversion

### 3. **Server Communication** (`Gui/mock_pi_server.py`)

- Mock Pi server for testing (runs on port 9000)
- Receives commands as JSON strings
- Returns status and messages

---

## How to Connect Them

### **Step 1: Create a Robot Server Bridge** (Recommended)

Create a new file `Gui/robot_server.py` that acts as the Raspberry Pi server:

```python
import socket
import json
import threading
import time
import sys
import os

# Add parent folder to path
sys.path.append(os.path.abspath(os.path.join(os.getcwd(), '..')))
from core.robot_controller import RobotController

HOST = '127.0.0.1'  # Change to '0.0.0.0' for network access
PORT = 9001

class RobotServer:
    def __init__(self, use_real_hardware=False):
        """Initialize server with robot controller"""
        self.robot = RobotController(use_real_hardware=use_real_hardware)
        self.robot.connect()

    def parse_command(self, command_text):
        """Parse text commands from GUI"""
        cmd = command_text.lower().strip()

        # Extract animal names and actions
        animals = ['lion', 'tiger', 'elephant', 'zebra', 'giraffe', 'leopard']
        found_animal = next((animal for animal in animals if animal in cmd), None)

        if 'grab' in cmd and found_animal:
            # Example: Move to position and pick
            return self.grab_object(found_animal)

        elif 'put' in cmd and 'back' in cmd:
            return self.put_back_object()

        elif 'home' in cmd:
            self.robot.home()
            return {'status': 'happy', 'message': 'Dora is ready!'}

        elif found_animal:
            return self.search_object(found_animal)

        else:
            return {'status': 'sad', 'message': 'I did not understand that command 😢'}

    def grab_object(self, animal):
        """Execute pick sequence for detected object"""
        try:
            # These coordinates should come from object detection
            # For now, using example positions
            x, y, z = 150, 0, 150  # Example position (mm)

            success = self.robot.pick_object(x, y, z, obj_label=animal)

            if success:
                return {
                    'status': 'happy',
                    'message': f'Dora grabbed the {animal}! 🤗'
                }
            else:
                return {
                    'status': 'sad',
                    'message': f'Failed to pick the {animal} 😢'
                }
        except Exception as e:
            return {'status': 'sad', 'message': f'Error: {str(e)}'}

    def put_back_object(self):
        """Put object back and return home"""
        try:
            self.robot.home()
            return {
                'status': 'happy',
                'message': 'Yay! We did it! 🎉'
            }
        except Exception as e:
            return {'status': 'sad', 'message': f'Error: {str(e)}'}

    def search_object(self, animal):
        """Move around searching for object"""
        try:
            # Example: Move to search position
            self.robot.move_to(200, 0, 200, gripper_open=True)
            return {
                'status': 'happy',
                'message': f'Dora found the {animal}! 🐾'
            }
        except Exception as e:
            return {'status': 'sad', 'message': f'Error: {str(e)}'}

def handle_connection(conn, addr, server):
    """Handle incoming client connection"""
    print(f'Connected by {addr}')
    try:
        with conn:
            data = conn.recv(2048)
            if not data:
                return

            command = data.decode()
            print(f'Received: {command}')

            # Parse and execute command
            response = server.parse_command(command)

            # Send response back to GUI
            conn.send(json.dumps(response).encode())
    except Exception as e:
        print(f'Error handling connection: {e}')

def start_server(use_real_hardware=False):
    """Start the robot server"""
    server = RobotServer(use_real_hardware=use_real_hardware)
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind((HOST, PORT))
    s.listen(5)
    print(f'Robot server listening on {HOST}:{PORT}')
    print(f'Hardware mode: {use_real_hardware}')

    try:
        while True:
            conn, addr = s.accept()
            threading.Thread(target=handle_connection, args=(conn, addr, server)).start()
    except KeyboardInterrupt:
        print('Server shutting down...')
        server.robot.disconnect()
        s.close()

if __name__ == '__main__':
    # Set to True when running on actual Raspberry Pi
    USE_HARDWARE = False
    start_server(use_real_hardware=USE_HARDWARE)
```

---

### **Step 2: Update GUI Configuration**

Update `Gui/pi_client.py` to point to your server:

```python
import socket
import json

# Local testing (change to Pi IP when deploying)
PI_HOST = '127.0.0.1'  # Change to '192.168.x.x' for actual Pi
PI_PORT = 9001

def send_command_to_pi(command_text, timeout=8):
    """Send command to robot server and get response"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(timeout)
        s.connect((PI_HOST, PI_PORT))
        s.send(command_text.encode())
        data = s.recv(4096)
        s.close()
        return json.loads(data.decode())
    except Exception as e:
        return {'status': 'sad', 'message': f'Comm error: {e}'}
```

---

### **Step 3: Enhanced Integration with Object Detection**

For full autonomous picking, integrate with object detection:

```python
# In robot_server.py - add this method to RobotServer class

def handle_detected_object(self, detection_data):
    """
    Handle a detected object for picking

    Args:
        detection_data: {
            'label': 'lion',
            'x': 150,  # real-world mm coordinates
            'y': 20,
            'z': 100,
            'confidence': 0.95
        }
    """
    try:
        success = self.robot.pick_detected_object(detection_data)

        if success:
            return {
                'status': 'happy',
                'message': f"Dora picked the {detection_data['label']}! 🎉"
            }
        else:
            return {
                'status': 'sad',
                'message': f"Could not pick the {detection_data['label']}"
            }
    except Exception as e:
        return {'status': 'sad', 'message': f'Error: {str(e)}'}
```

---

## Communication Flow

```
┌─────────────────────────────────────────────────────────┐
│  Web Browser (Index.html)                               │
│  User says: "Find the lion"                             │
└──────────────────┬──────────────────────────────────────┘
                   │ Socket.IO
                   ▼
┌─────────────────────────────────────────────────────────┐
│  Flask App (app.ipynb)                                  │
│  - Receives command: "find the lion"                    │
│  - Sends to pi_client.send_command_to_pi()              │
└──────────────────┬──────────────────────────────────────┘
                   │ TCP Socket (JSON)
                   ▼
┌─────────────────────────────────────────────────────────┐
│  Robot Server (robot_server.py)                         │
│  - Parses command                                       │
│  - Calls RobotController methods                        │
└──────────────────┬──────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────────┐
│  RobotController (robot_controller.ipynb)               │
│  - Executes motion commands                             │
│  - Controls servos via Arm_Device                       │
└─────────────────────────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────────┐
│  DofBot Robot Arm                                       │
│  - Physical movement                                    │
└─────────────────────────────────────────────────────────┘
```

---

## Running the System

### **For Testing (Simulation Mode)**:

**Terminal 1 - Start Robot Server:**

```bash
cd Gui
python robot_server.py
```

**Terminal 2 - Start GUI:**

```bash
cd Gui
# Then in Jupyter, run:
# jupyter nbconvert --to notebook --execute app.ipynb
# Or directly: python -m flask run --host 0.0.0.0 --port 5000
```

**Browser:**

```
http://localhost:5000
```

---

## Key Integration Points

| Component                                  | Method                | Purpose                     |
| ------------------------------------------ | --------------------- | --------------------------- |
| **RobotController.move_to()**              | Position control      | Move to X, Y, Z coordinates |
| **RobotController.pick_object()**          | Autonomous picking    | Complete pick sequence      |
| **RobotController.pick_detected_object()** | Detection integration | Use detection data          |
| **RobotController.set_gripper()**          | Gripper control       | Open/close gripper          |
| **RobotController.home()**                 | Safe position         | Return to home              |

---

## Next Steps

1. **Convert notebooks to Python files** - The `.ipynb` files should be converted to `.py` for easier imports
2. **Add object detection integration** - Connect camera feed and detection pipeline
3. **Implement coordinate conversion** - Use `coord_converter.pixel_to_shelf()` for detection → robot coords
4. **Add error handling** - Robust fallback for connection/hardware failures
5. **Deploy to Raspberry Pi** - Update `PI_HOST` with actual Pi IP address

---

## Troubleshooting

| Issue                  | Solution                                                      |
| ---------------------- | ------------------------------------------------------------- |
| Connection refused     | Ensure robot_server.py is running on correct port (9001)      |
| Command not recognized | Check command parsing logic in `parse_command()`              |
| Servos not moving      | Verify `use_real_hardware=True` and Arm_Device is initialized |
| GUI shows "Comm error" | Check network connectivity and firewall settings              |
