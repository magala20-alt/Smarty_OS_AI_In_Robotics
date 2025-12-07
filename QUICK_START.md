# Quick Start: Connecting GUI to Robot

## What You Have

✅ **GUI** (`Gui/app.ipynb`) - Web interface for giving voice commands  
✅ **Robot Controller** (`core/robot_controller.ipynb`) - Class for controlling the arm  
✅ **Mock Server** (`Gui/mock_pi_server.py`) - Example of server communication  
❌ **Missing** - A bridge server that connects them together

---

## Solution: 3 Simple Steps

### **Step 1: Create `robot_server.py`**

I've created `Gui/robot_server.py` - this acts as the "Pi server" that:

- Listens for commands from your GUI
- Controls the robot arm
- Sends responses back to the GUI

**First, convert the Jupyter notebook to Python:**

Since `robot_controller.ipynb` is a Jupyter notebook, you need to extract it as a Python module.

Go to `core/` directory and create `robot_controller.py` by copying the code from `robot_controller.ipynb`:

```python
# core/robot_controller.py
# (Copy all the Python cells from robot_controller.ipynb into this file)
```

Or use nbconvert:

```bash
cd core
jupyter nbconvert --to python robot_controller.ipynb --output robot_controller.py
```

---

### **Step 2: Start the Robot Server**

```bash
cd Gui
python robot_server.py
# Or with real hardware:
# python robot_server.py --hardware
```

You should see:

```
============================================================
🤖 ROBOT SERVER STARTED
============================================================
📍 Listening on 0.0.0.0:9001
🔧 Hardware mode: False
✅ Ready for GUI commands!
============================================================
```

---

### **Step 3: Start Your GUI App**

In your Jupyter notebook (`Gui/app.ipynb`), run the Flask app cells. It will start on port 5000.

The data flow:

```
Browser (localhost:5000)
    ↓ "Find the lion!"
Flask App (app.ipynb)
    ↓ TCP Socket
Robot Server (robot_server.py:9001)
    ↓ Parses command
RobotController (robot_controller.py)
    ↓ Servo commands
DofBot Arm
```

---

## What Each Part Does

| File                       | Purpose                           | What It Needs               |
| -------------------------- | --------------------------------- | --------------------------- |
| `Gui/app.ipynb`            | Web server & voice interface      | Running `robot_server.py`   |
| `Gui/robot_server.py`      | Command parser & robot controller | `core/robot_controller.py`  |
| `core/robot_controller.py` | Arm movement logic                | Hardware library `Arm_Lib`  |
| `Gui/pi_client.py`         | Sends commands to server          | Server running on port 9001 |

---

## Commands Your GUI Can Send

The robot server understands these natural language commands:

```
"Find the lion"        → Moves to lion position
"Grab the tiger"       → Picks up tiger
"Put it back"          → Puts object back in drop zone
"Help"                 → Lists available animals
"Home"                 → Returns to safe position
```

---

## Testing Without Hardware

The `robot_server.py` works in **simulation mode** by default:

```bash
python robot_server.py
```

This will:

- Pretend to move the robot
- Print commands instead of executing them
- Still respond with proper status messages to the GUI

Perfect for testing your GUI logic before running on real hardware!

---

## When You Have Real Hardware (Raspberry Pi)

1. Install on your Pi: Python, dependencies, and `Arm_Lib`
2. Update `Gui/pi_client.py`:
   ```python
   PI_HOST = '192.168.X.X'  # Your Pi's IP address
   PI_PORT = 9001
   ```
3. Run robot server on the Pi:
   ```bash
   python Gui/robot_server.py --hardware
   ```
4. The GUI can run anywhere and connect to it

---

## Troubleshooting

| Problem                                       | Solution                                                        |
| --------------------------------------------- | --------------------------------------------------------------- |
| "ModuleNotFoundError: No module named 'core'" | The import path is wrong - check you're in the `Gui/` directory |
| "Connection refused"                          | Robot server not running on port 9001                           |
| "Cannot import Arm_Device"                    | Hardware library not installed (OK for simulation mode)         |
| GUI shows "Comm error"                        | Check `PI_HOST` in `pi_client.py` matches your server           |

---

## Next: Add Object Detection

Once the GUI-Robot connection works, you can add object detection:

```python
# In robot_server.py - add this to parse_command()

if 'search for' in cmd:
    # Run object detection
    detected = run_object_detector(camera_frame)
    if detected:
        animal = detected['label']
        pos = convert_pixel_to_world_coords(detected['bbox'])
        return self.grab_object(animal, pos)
```

This would make it fully autonomous! 🤖
