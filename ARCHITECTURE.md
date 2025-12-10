
# System Architecture Diagram

## Current System Layout

```
┌─────────────────────────────────────────────────────────────────────┐
│                          WEB BROWSER                                 │
│  http://localhost:5000  (Child-friendly voice interface)            │
│  - Test or Image input                                              │
│  - Displays Dora animations                                         │
│  - Shows status messages                                            │
└──────────────────────────┬──────────────────────────────────────────┘
                           │
                    Socket.IO (Bidirectional)
                           │
┌──────────────────────────▼──────────────────────────────────────────┐
│                    FLASK WEB SERVER                                  │
│            (Gui/app.ipynb - Running in Jupyter)                     │
│                                                                      │
│  Routes:                                                            │
│  - GET  / → Serve Index.html                                       │
│  - POST /send → Receive voice command                              │
│  - Emit status via Socket.IO → Update browser                      │
│                                                                      │
│  Calls:                                                             │
│  - send_command_to_pi(command)  ← Imported from pi_client.py       │
└──────────────────────────┬──────────────────────────────────────────┘
                           │
                   TCP Socket (JSON)
                   Port: 9001
                           │
┌──────────────────────────▼──────────────────────────────────────────┐
│                   ROBOT SERVER                                       │
│           (Gui/robot_server.py - Your bridge!)                      │
│                                                                      │
│  Responsibilities:                                                  │
│  1. Accept commands from GUI client                                │    │
│  2. Call RobotController methods                                   │
│  3. Send JSON response back to GUI                                 │
│                                                                      │
│  Key Methods:                                                       │
│  - parse_command(text)   → Route command to handler                │
│  - grab_object(animal)   → Pick sequence                           │
│  - put_back_object()     → Drop sequence                           │
│  - search_object(animal) → Move to location                        │
└──────────────────────────┬──────────────────────────────────────────┘
                           │
           Calls RobotController methods
                           │
┌──────────────────────────▼──────────────────────────────────────────┐
│                 ROBOT CONTROLLER                                     │
│        (core/robot_controller.py - Converted from .ipynb)           │
│                                                                      │
│  Class: RobotController                                            │
│  ├─ __init__()          → Initialize Arm_Device                    │
│  ├─ connect()           → Connect to robot                         │
│  ├─ move_to(x, y, z)    → Move to coordinates (mm)                 │
│  ├─ set_gripper(open)   → Open/close gripper                       │
│  ├─ pick_object(x,y,z)  → Complete pick sequence                   │
│  ├─ home()              → Return to safe position                  │
│  └─ _execute_move()     → Low-level servo control                  │
│                                                                      │
│  Safety Features:                                                   │
│  - Angle validation (servo limits)                                 │
│  - Position bounds checking (workspace limits)                     │
│  - Approach/grasp sequencing                                       │
└──────────────────────────┬──────────────────────────────────────────┘
                           │
          Serial Communication (UART)
                           │
┌──────────────────────────▼──────────────────────────────────────────┐
│                    Arm_Device Library                                │
│  (External hardware library for DofBot)                             │
│  ├─ Arm_serial_servo_write6()  → Move all 6 servos                 │
│  ├─ Arm_serial_servo_write()   → Move single servo                 │
│  └─ Arm_Buzzer_On()            → Beep buzzer                       │
└──────────────────────────┬──────────────────────────────────────────┘
                           │
                    Hardware SPI/I2C
                           │
┌──────────────────────────▼──────────────────────────────────────────┐
│                   DofBot Robot Arm                                   │
│  ├─ 6 Servo motors (base, shoulder, elbow, wrist, rotate, gripper) │
│  ├─ Gripper actuator                                               │
│  └─ Buzzer                                                         │
└──────────────────────────────────────────────────────────────────────┘
```

---

## Data Flow Examples

### Example 1: User says "Find the lion"

```
User speaks into microphone
        ↓
Browser captures audio: "find the lion"
        ↓
POST /send with {"command": "find the lion"}
        ↓
Flask app.py receives request
        ↓
Calls: send_command_to_pi("find the lion")
        ↓
pi_client opens TCP socket to localhost:9001
        ↓
Robot server receives: "find the lion"
        ↓
parse_command() identifies:
  - Action: "find"
  - Animal: "lion"
  - Calls: search_object("lion")
        ↓
RobotController.move_to(180, 50, 200)  [lion position]
        ↓
_execute_move() calculates servo angles
        ↓
Arm_Device.Arm_serial_servo_write6() sends to hardware
        ↓
Servos move to point at lion
        ↓
Response sent back: {"status": "happy", "message": "Dora found the lion! 🐾"}
        ↓
Flask emits via Socket.IO to browser
        ↓
Browser shows happy Dora and message
```

### Example 2: User says "Grab the tiger"

```
POST /send {"command": "grab the tiger"}
        ↓
parse_command() identifies action: "grab", animal: "tiger"
        ↓
grab_object("tiger") called
        ↓
Looks up tiger position: {'x': 180, 'y': -50, 'z': 100}
        ↓
RobotController.pick_object(180, -50, 100):
  [1] move_to(180, -50, 200) - approach from above
  [2] move_to(180, -50, 110) - lower to object
  [3] set_gripper(False)     - close gripper
  [4] move_to(180, -50, 200) - lift object
  [5] move_to(100, -150, 150) - move to drop zone
  [6] set_gripper(True)      - open gripper
  [7] home()                 - return home
        ↓
Response: {"status": "grab", "message": "Dora grabbed the tiger! 🤗"}
        ↓
Browser shows Dora happy with tiger
```

---

## File Structure

```
Smarty_OS_AI_In_Robotics/
├── Gui/
│   ├── app.ipynb                 ← Flask web server (RUNNING)
│   ├── pi_client.py              ← Client that sends to server
│   ├── robot_server.py           ← ⭐ NEW: Bridge server
│   ├── templates/
│   │   └── Index.html            ← Web interface
│   └── static/
│       └── (images, sounds, etc)
│
├── core/
│   ├── robot_controller.ipynb    ← Original Jupyter version
│   ├── robot_controller.py       ← ⭐ CONVERT TO THIS
│   └── object_detector.ipynb     ← Detection pipeline
│
└── (calibration files, models, etc)
```

---

## Connection Checklist

```
□ Step 1: Convert robot_controller.ipynb to .py
  Command: jupyter nbconvert --to python core/robot_controller.ipynb

□ Step 2: Start robot server in Terminal 1
  Command: cd Gui && python robot_server.py

□ Step 3: Start Flask app in Jupyter (Terminal 2 or Jupyter cell)
  Command: python -m flask run --host 0.0.0.0 --port 5000

□ Step 4: Open browser
  URL: http://localhost:5000

□ Step 5: Give voice command
  Say: "Find the lion"

Expected result:
  ✓ Microphone captures voice
  ✓ Flask receives command
  ✓ Server parses "find lion"
  ✓ RobotController moves arm
  ✓ Browser shows status message
```

---

## Key Connection Points

| Component A     | Calls     | Component B     | Method        | Purpose           |
| --------------- | --------- | --------------- | ------------- | ----------------- |
| Flask App       | TCP       | Robot Server    | socket.send() | Send command text |
| Robot Server    | Imports   | RobotController | move_to()     | Move arm          |
| RobotController | Uses      | Arm_Device      | write6()      | Control servos    |
| GUI Client      | Socket.IO | Flask           | emit()        | Return status     |

---

## Testing & Debugging

### Check server is listening:

```bash
netstat -ano | findstr :9001   # Windows
# or
lsof -i :9001                   # Mac/Linux
```

### Test connection:

```python
import socket, json

s = socket.socket()
s.connect(('localhost', 9001))
s.send(b'find the lion')
print(json.loads(s.recv(4096)))
s.close()
```

### Check Flask:

```
http://localhost:5000  # Should show Dora interface
```

### Verbose logging:

```bash
python robot_server.py  # Already has print() debugging
```

---

## When Ready for Real Hardware

Switch from `localhost` to Raspberry Pi:

**On the Pi:**

```bash
git clone <your-repo>
cd Smarty_OS_AI_In_Robotics
python Gui/robot_server.py --hardware
```

**On your computer:**
Update `Gui/pi_client.py`:

```python
PI_HOST = '192.168.1.100'  # Your Pi's IP
```

**Open browser:**

```
http://192.168.1.100:5000
```

Everything else stays the same! 🚀
