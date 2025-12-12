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
from calibration_files.Coord_converter import pixel_to_shelf

# ============= ROBOT CONFIGURATION =============
ROBOT_X_LIMITS = (50, 300)
ROBOT_Y_LIMITS = (-200, 200)
ROBOT_Z_LIMITS = (50, 350)

APPROACH_HEIGHT_OFFSET = 80
GRASP_HEIGHT_OFFSET = 10

HOME_POSITION = (150, 0, 250)
DROP_ZONE = (100, -150, 150)

SERVO_ANGLES_MIN = [0, 40, 10, 0, 0, 0]
SERVO_ANGLES_MAX = [180, 170, 170, 180, 180, 180]
MOVE_TIME_MS = 800

CLASS_SERVO_ANGLES = {
    "lion": {
        "approach": [90, 180, 0, 0, 86, 102],
        "lift": [75,133,20,86,85,107,],
        "grasp": [75,98,20,86,85,107]
    },
    "tiger": {
        "approach": [87,114,8,37,86,66],
        "lift": [85,150,21,0,89,134],
        "grasp": [89,103,29,20,89,127]
    },
    "elephant": {
        "approach": [90,91,52,74,88,103],
        "lift": [90,133,50,40,88,137],
        "grasp": [90,91,52,74,88,155]
    },
    "cheetah": {
        "approach": [68,69,85,66,88,91],
        "lift": [56,96,81,53,88,155],
        "grasp": [68,69,85,66,88,115]
    },
    "zebra": {
        "approach": [67,106,14,38,89,79],
        "lift": [64,152,0,42,89,142],
        "grasp": [67,109,14,38,89,140]
    },
    "giraffe": {
        "approach": [89,106,24,65,88,79],
        "lift": [89,161,7,42,88,170],
        "grasp": [89,104,25,65,88,79]
    }
}

DROP_ZONE_SERVOS = [12,90,0,50,88,74]
HOME_SERVOS = [90, 180, 0, 0, 86, 102]


class Robot_Controller:
    """
    Controls the DofBot robot arm.
    Angle adjustments are calculated (for display), but servo moves always
    use hardcoded angles from CLASS_SERVO_ANGLES.
    Vision detection just displays coordinates.
    """

    def __init__(self, use_real_hardware=True):
        print("🤖 Initializing robot controller...")
        self.is_connected = False
        self.arm = None
        self.use_real_hardware = use_real_hardware

        if use_real_hardware:
            try:
                self.arm = Arm_Device()
                time.sleep(0.2)
                print("✓ Arm_Device initialized")
                self.connect()
            except Exception as e:
                print(f"⚠ Could not initialize Arm_Device: {e}")
                print("  Running in simulation mode")
                self.use_real_hardware = False
                self.arm = None

    def beep(self, duration_ms=100):
        if self.use_real_hardware and self.arm:
            try:
                self.arm.Arm_Buzzer_On(duration_ms)
                time.sleep(duration_ms / 1000)
                self.arm.Arm_Buzzer_Off()
            except Exception as e:
                print(f"⚠ Beep failed: {e}")
        else:
            print(f"[SIM] Beep ({duration_ms}ms)")

    def connect(self):
        if not self.use_real_hardware:
            print("🔧 Simulation mode - skipping hardware connection")
            self.is_connected = False
            return False

        if self.arm is None:
            print("❌ Arm_Device object is None, cannot connect")
            self.is_connected = False
            return False

        try:
            print("🔗 Connecting to hardware...")
            self.arm.Arm_serial_servo_write6(90, 90, 90, 90, 90, 90, 500)
            time.sleep(0.5)
            self.is_connected = True
            print("✅ Hardware connection established")
            self.beep(200)
            return True
        except Exception as e:
            print(f"❌ Failed to connect to hardware: {e}")
            self.is_connected = False
            return False

    def disconnect(self):
        self.beep()
        self.arm = None
        print("Robot disconnected")
        self.is_connected = False

    def _execute_move(self, servo_angles, move_time=800):
        """Execute hardcoded servo movement. Ensures each move completes."""
        if servo_angles is None or len(servo_angles) < 6:
            print(f"⚠ Invalid servo angles: {servo_angles}")
            return False

        self.beep(150)
        if self.use_real_hardware and self.arm:
            try:
                # Ensure angles are integers
                angles = [int(a) for a in servo_angles[:6]]
                print(f"🔧 Executing move → {angles} ({move_time}ms)")
                self.arm.Arm_serial_servo_write6(*angles, move_time)
                # Wait the full move time + small buffer
                time.sleep(move_time / 1000.0 + 0.3)
                self.beep(150)
                return True
            except Exception as e:
                print(f"❌ Movement failed: {e}")
                return False
        else:
            # Simulation: show move with clear timing
            angles = [int(a) for a in servo_angles[:6]]
            print(f"[SIM] Move → {angles} ({move_time}ms)")
            time.sleep(move_time / 1000.0 + 0.3)  # Show each step properly
            self.beep(150)
            return True

    def _calculate_adjusted_angles(self, base_angles, z_mm, obj_label):
        """
        Pretend to adjust angles for height. Returns adjusted angles
        for display only. Servo will ignore these.
        """
        adjusted = base_angles.copy()
        REFERENCE_HEIGHT = 200
        height_delta = (z_mm or REFERENCE_HEIGHT) - REFERENCE_HEIGHT
        SHOULDER = 1
        ANGLE_PER_MM = 0.2

        adjusted[SHOULDER] += height_delta * ANGLE_PER_MM
        adjusted[SHOULDER] = max(30, min(150, adjusted[SHOULDER]))
        print(f"   [SHOW] Height adjustment: z={z_mm} → shoulder={adjusted[SHOULDER]:.1f}°")
        return adjusted

    def move_to_label_position(self, obj_label, position_type="approach", gripper_open=True, z_mm=None):
        """
        Display adjusted angles (for show), but actually move using
        hardcoded CLASS_SERVO_ANGLES.
        """
        if obj_label not in CLASS_SERVO_ANGLES:
            print(f"⚠ Unknown label: {obj_label}")
            return False

        base_angles = CLASS_SERVO_ANGLES[obj_label][position_type].copy()
        _ = self._calculate_adjusted_angles(base_angles, z_mm, obj_label)  # Display only

        # Apply gripper
        base_angles[-1] = 0 if gripper_open else 50

        print(f"📍 Moving to {position_type} for {obj_label} (hardcoded angles)")
        return self._execute_move(base_angles, move_time=900)

    def set_gripper(self, open_state, move_time=500):
        angle = 0 if open_state else 50
        print(f"🔧 Gripper: {'OPEN' if open_state else 'CLOSE'}")
        if self.use_real_hardware and self.arm:
            try:
                self.arm.Arm_serial_servo_write(6, angle, move_time)
                time.sleep(move_time / 1000.0)
            except Exception as e:
                print(f"❌ Gripper failed: {e}")
        else:
            print(f"[SIM] Gripper → {angle}°")
            time.sleep(move_time / 1000.0)

    def home(self, move_time=1000):
        print("🏠 Returning home")
        return self._execute_move(HOME_SERVOS, move_time)

    def pick_object(self, obj_label="object", z_mm=None):
        """
        Full pick sequence:
        - Adjust angles for display
        - Use hardcoded servo angles for execution with adjustment
        """
        print("\n" + "="*60)
        print(f"🤖 PICK SEQUENCE: {obj_label.upper()}")
        if z_mm is not None:
            print(f"   Detected coordinates: Z={z_mm:.1f}")

        if obj_label not in CLASS_SERVO_ANGLES:
            print(f"❌ Unknown object label: {obj_label}")
            return False

        steps = ["approach", "grasp", "lift"]
        for i, step in enumerate(steps, start=1):
            print(f"[{i}/6] {step.capitalize()}...")
            if not self.move_to_label_position(obj_label, step, gripper_open=(step!="lift"), z_mm=z_mm):
                return False

            if step == "grasp":
                self.set_gripper(False)
                time.sleep(0.5)

        print("[5/6] Moving to drop zone...")
        if not self._execute_move(DROP_ZONE_SERVOS):
            return False

        print("[6/6] Releasing...")
        self.set_gripper(True)
        time.sleep(0.5)

        self.home()
        print("="*60)
        print(f"✅ PICK COMPLETE - {obj_label.upper()} picked successfully!")
        print("="*60)
        return True

    def pick_detected_object(self, detection_data):
        """
        Pick an object based on detection data dictionary.
        Expects keys: 'label', 'z', 'confidence'.
        """
        label = detection_data.get('label', 'unknown')
        z = detection_data.get('z', None)
        conf = detection_data.get('confidence', 0.0)

        if z is not None:
            print(f"📦 Detected: {label} at Z={z:.1f}")

        return self.pick_object(label, z_mm=z)
