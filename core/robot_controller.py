"""
Robot Controller - Integrates with ObjectDetector for autonomous picking.
Uses real-world coordinates from the camera for precise arm positioning.
"""
try:
    import smbus
except ModuleNotFoundError:
    import smbus2 as smbus
    print("⚠️ smbus not found, using smbus2 as a replacement")
try:
    from Arm_Lib import Arm_Device
except ImportError:
    print("⚠️ Arm_Device not found - using simulation mode")
    Arm_Device = None
    
import time
import numpy as np
import sys
import os


# Add parent folder to path to import coord_converter
sys.path.append(os.path.abspath(os.path.join(os.getcwd(), '..')))
from coord_converter import pixel_to_shelf

# ============= ROBOT CONFIGURATION =============
# DofBot workspace limits (in mm, relative to robot base)
ROBOT_X_LIMITS = (50, 300)       # Forward/backward
ROBOT_Y_LIMITS = (-200, 200)     # Left/right
ROBOT_Z_LIMITS = (50, 350)       # Up/down

# Approach and grasp offsets (mm)
APPROACH_HEIGHT_OFFSET = 80      # How high above object to approach
GRASP_HEIGHT_OFFSET = 10         # How low to go for grasping

# Home/safe positions
HOME_POSITION = (150, 0, 250)
DROP_ZONE = (100, -150, 150)    # Where to drop picked objects

# Servo angle limits
SERVO_ANGLES_MIN = [0, 40, 10, 0, 0, 0]      # Min angles for each servo
SERVO_ANGLES_MAX = [180, 170, 170, 180, 180, 180]  # Max angles for each servo
MOVE_TIME_MS = 800               # Default movement time in ms

#servo hard coded angles    ---- to do some more changes here
CLASS_SERVO_ANGLES = {
    "lion": {
        "approach": [82,88,72,53,80,160],
        "lift": [],
        "grasp": [82,88,42,88,80,171]
    },
    "tiger": {
        "approach": [109,93,42,88,89,162],
        "lift": [],
        "grasp": [109,93,15,57,89,174]
    },
    "elephant": {
        "approach": [86,127,3,61,89,174],
        "lift": [],
        "grasp": [86,98,40,13,89,152]
    },
    "cheetah": {
        "approach": [97,117,15,57,89,174],
        "lift": [],
        "grasp": [97,98,40,13,89,152]
    },
    "zebra": {
        "approach": [88,104,40,8,89,168],  
        "lift": [],
        "grasp": [88,98,40,13,89,152]
    },
    "giraffe": {
        "approach": [102, 98,40,13,89,152],
        "lift": [],
        "grasp": [102, 98,40,13,89,152]
    }
}

class RobotController:
    """
    Controls the DofBot robot arm with coordinate conversion and safety checks.
    
    Accepts real-world coordinates from object detection and converts them
    to robot servo angles for precise picking operations.
    """

    def __init__(self, use_real_hardware=True):
        """
        Initialize robot controller.
        
        Args:
            use_real_hardware: If True, initialize actual Arm_Device. 
                             If False, simulate commands (for testing).
        """
        print("🤖 Initializing robot controller...")
        self.is_connected = False
        self.arm = None
        self.use_real_hardware = use_real_hardware
        
        if use_real_hardware:
            try:

                self.arm = Arm_Device()
                time.sleep(0.2)
                print("✓ Arm_Device initialized")

            # Automatically attempt connection
                self.connect()
                
            except Exception as e:
                print(f"⚠ Could not initialize Arm_Device: {e}")
                print("  Running in simulation mode")
                self.use_real_hardware = False
                self.arm = None  # simulation mode
        def beep(self, duration_ms=300):
            if self.use_real_hardware and self.arm:
                try:
                    self.arm.Arm_Buzzer_On(duration_ms)
                    time.sleep(duration_ms / 1000)
                    self.arm.Arm_Buzzer_On(0)
                except Exception as e:
                    print(f"⚠ Beep failed: {e}")
            else:
                print(f"[SIM] Beep ({duration_ms}ms)")

        
        def connect(self):
            """Connect to robot and beep on success."""
            if not self.use_real_hardware:
                print("🔧 Simulation mode - no hardware to connect")
                self.is_connected = False
                return False
            
            print("🔌 Connecting to robot...")
            try:
                # Beep to show successful hardware connection
                self.beep(300)
                self.is_connected = True
                print("✓ Robot connected")
                return True
    
            except Exception as e:
                print(f"❌ Robot connection failed: {e}")
                self.is_connected = False
                return False


    def disconnect(self):
        """Safely disconnect from robot."""
        self.beep()  # Beep before disconnect
        if self.arm is not None:
            self.arm = None
        print("Robot disconnected")
        self.is_connected = False

    def _execute_move(self, detected_class, position_type="approach", gripper_open=True, move_time=MOVE_TIME_MS):
        """
        Execute servo movement for a detected class with angle validation.
        
        Args:
            detected_class: The object/animal label as key to CLASS_SERVO_ANGLES
            position_type: "approach", "grasp", or "lift"
            gripper_open: True for open, False for closed
            move_time: Movement duration in milliseconds
            
        Returns:
            bool: True if successful
        """
        # Get angles from CLASS_SERVO_ANGLES
        if detected_class not in CLASS_SERVO_ANGLES:
            print(f"⚠ Unknown class: {detected_class}")
            return False
        
        angles = CLASS_SERVO_ANGLES[detected_class][position_type].copy()
        
        # Set gripper angle
        angles[-1] = 0 if gripper_open else 50
        
        # Validate angles
        for i, angle in enumerate(angles):
            if not (SERVO_ANGLES_MIN[i] <= angle <= SERVO_ANGLES_MAX[i]):
                print(f"⚠ Servo {i} angle {angle}° outside limits [{SERVO_ANGLES_MIN[i]}, {SERVO_ANGLES_MAX[i]}]")
                return False
        
        # Beep before move
        self.beep(200)
        
        if self.use_real_hardware and self.arm is not None:
            try:
                self.arm.Arm_serial_servo_write6(*angles, move_time)
                time.sleep(move_time / 1000.0)  # Wait for motion to complete
                self.beep(200)  # Beep after move
                return True
            except Exception as e:
                print(f"❌ Movement failed: {e}")
                return False
        else:
            # Simulation mode
            print(f"  [SIM] Move: angles={angles}, time={move_time}ms")
            time.sleep(0.5)
            self.beep(200)
            return True

    def _adjust_angles_for_height(self, base_angles, z_mm, obj_label):
        """
        Adjust servo angles for Dofbot Pi based on detected object height.
        
        Dofbot Pi servo layout:
        - servo[0]: Base rotation (horizontal)
        - servo[1]: Shoulder joint (main vertical movement) ← HEIGHT ADJUSTMENT
        - servo[2]: Elbow joint (extends/retracts)
        - servo[3]: Wrist rotation
        - servo[4]: Wrist pitch
        - servo[5]: Gripper
        
        Args:
            base_angles: Hardcoded servo angles for the object
            z_mm: Detected height in mm
            obj_label: Object label (for logging)
            
        Returns:
            Adjusted servo angles
        """
        adjusted = base_angles.copy()
        
        # Your reference height (height your hardcoded angles were calibrated at)
        # Adjust this value to match YOUR calibration point
        REFERENCE_HEIGHT = 200  # mm
        
        # Height difference
        height_delta = z_mm - REFERENCE_HEIGHT
        
        # For Dofbot Pi, servo[1] (shoulder) primarily controls vertical reach
        SHOULDER_SERVO = 1
        
        # Sensitivity: approximately how many degrees per mm of height change
        # For Dofbot Pi with 15kg servos and ~150mm link lengths:
        # ~0.15-0.25 degrees per mm is typical
        # Start conservative and adjust based on testing
        ANGLE_PER_MM = 0.2  # degrees/mm - CALIBRATE THIS VALUE
        
        # Apply adjustment
        adjusted[SHOULDER_SERVO] += (height_delta * ANGLE_PER_MM)
        
        # Clamp to valid servo range (Dofbot servos typically 0-240°, but limit to safer range)
        adjusted[SHOULDER_SERVO] = max(30, min(150, adjusted[SHOULDER_SERVO]))
        
        print(f"   Height adjustment: z={z_mm}mm (delta={height_delta:+.0f}mm) " +
            f"→ shoulder angle={adjusted[SHOULDER_SERVO]:.1f}° (was {base_angles[SHOULDER_SERVO]:.1f}°)")
        
        return adjusted

    def move_to_label_position(self, obj_label, position_type="approach", gripper_open=True, move_time=MOVE_TIME_MS):
        """
        Move robot to hardcoded position for detected object label.
        
        Args:
            obj_label: Object label (e.g., "cup", "bottle")
            position_type: "approach", "grasp", or "lift"
            gripper_open: True for open, False for closed
            move_time: Movement duration in ms
            
        Returns:
            bool: Success
        """
        if obj_label not in CLASS_SERVO_ANGLES:
            print(f"⚠ Unknown label: {obj_label}")
            return False
        
        angles = CLASS_SERVO_ANGLES[obj_label][position_type].copy()
        angles[-1] = 0 if gripper_open else 50  # Set gripper
        
        print(f"📍 Moving to {position_type} position for {obj_label}")
        return self._execute_move(angles, move_time)

    def set_gripper(self, open_state, move_time=500):
        """
        Open or close gripper.
        
        Args:
            open_state: True for open, False for closed
            move_time: Movement duration in ms
        """
        gripper_angle = 0 if open_state else 50
        print(f"🔧 Gripper: {'OPEN' if open_state else 'CLOSE'}")
        
        # Servo 6 is the gripper
        if self.use_real_hardware and self.arm is not None:
            try:
                self.arm.Arm_serial_servo_write(6, gripper_angle, move_time)
                time.sleep(move_time / 1000.0)
            except Exception as e:
                print(f"❌ Gripper control failed: {e}")
        else:
            print(f"  [SIM] Gripper angle={gripper_angle}°")
            time.sleep(move_time / 1000.0)

    def home(self, move_time=1000):
       self.arm.Arm_serial_servo_write6(HOME_POSITION, move_time)

    def pick_object(self, obj_label="object", z_mm=None):
        """
        Execute complete autonomous pick sequence using hardcoded servo positions.
        
        Args:
            obj_label: Label of detected object
            z_mm: Detected object height in mm (optional, for dynamic adjustment)
            
        Returns:
            bool: True if pick successful
        """
        print(f"\n{'='*60}")
        print(f"🤖 PICK SEQUENCE: {obj_label.upper()}")
        if z_mm:
            print(f"   Detected height: z={z_mm:.1f}mm")
        print(f"{'='*60}")

        if obj_label not in LABEL_SERVO_POSITIONS:
            print(f"❌ Unknown object label: {obj_label}")
            return False

        # 1. Approach above object
        print(f"[1/6] Approaching above object...")
        if not self.move_to_label_position(obj_label, "approach", gripper_open=True, z_mm=z_mm):
            print("❌ Approach failed")
            return False
        print("     ✓ Approached")

        # 2. Lower to grasp height
        print(f"[2/6] Lowering to grasp height...")
        if not self.move_to_label_position(obj_label, "grasp", gripper_open=True, z_mm=z_mm):
            print("❌ Lower failed")
            return False
        print("     ✓ Positioned")

        # 3. Close gripper
        print(f"[3/6] Closing gripper...")
        self.set_gripper(False)
        time.sleep(0.5)  # Wait for gripper to close
        print("     ✓ Gripped")

        # 4. Lift object
        print(f"[4/6] Lifting object...")
        if not self.move_to_label_position(obj_label, "lift", gripper_open=False, z_mm=z_mm):
            print("❌ Lift failed")
            return False
        print("     ✓ Lifted")

        # 5. Move to drop zone
        print(f"[5/6] Moving to drop zone...")
        if not self._execute_move(DROP_ZONE_SERVOS, MOVE_TIME_MS):
            print("❌ Drop zone move failed")
            return False
        print("     ✓ At drop zone")

        # 6. Release object
        print(f"[6/6] Releasing object...")
        self.set_gripper(True)
        time.sleep(0.5)
        print("     ✓ Released")

        # Return to home
        print(f"Returning to home...")
        self._execute_move(HOME_SERVOS, MOVE_TIME_MS)
        
        print(f"{'='*60}")
        print(f"✅ PICK COMPLETE - {obj_label.upper()} picked successfully!")
        print(f"{'='*60}\n")

        return True

    def pick_detected_object(self, detection_data):
        """
        Pick an object using detection data from ObjectDetector.
        
        Args:
            detection_data: Dict with keys:
                - 'label': object class name
                - 'x': real-world X coordinate (mm)
                - 'y': real-world Y coordinate (mm)
                - 'z': real-world Z coordinate (mm)
                - 'confidence': detection confidence (optional)
        """
        label = detection_data.get('label', 'unknown')
        x = detection_data.get('x')
        y = detection_data.get('y')
        z = detection_data.get('z')
        conf = detection_data.get('confidence', 0.0)

        if x is None or y is None or z is None:
            print("❌ Invalid detection data - missing coordinates")
            return False

        print(f"📦 Detected: {label} (confidence: {conf:.2f})")
        return self.pick_object(x, y, z, obj_label=label)