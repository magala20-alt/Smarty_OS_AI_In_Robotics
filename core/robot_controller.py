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
        "approach": [82, 88, 72, 53, 80, 160],
        "lift": [],
        "grasp": [82, 88, 42, 88, 80, 171]
    },
    "tiger": {
        "approach": [109, 93, 42, 88, 89, 162],
        "lift": [],
        "grasp": [109, 93, 15, 57, 89, 174]
    },
    "elephant": {
        "approach": [86, 127, 3, 61, 89, 174],
        "lift": [],
        "grasp": [86, 98, 40, 13, 89, 152]
    },
    "cheetah": {
        "approach": [97, 117, 15, 57, 89, 174],
        "lift": [],
        "grasp": [97, 98, 40, 13, 89, 152]
    },
    "zebra": {
        "approach": [88, 104, 40, 8, 89, 168],
        "lift": [],
        "grasp": [88, 98, 40, 13, 89, 152]
    },
    "giraffe": {
        "approach": [102, 98, 40, 13, 89, 152],
        "lift": [],
        "grasp": [102, 98, 40, 13, 89, 152]
    }
}

DROP_ZONE_SERVOS = [150, 90, 90, 90, 90, 0]
HOME_SERVOS = [90, 90, 90, 90, 90, 0]


class Robot_Controller:
    """
    Controls the DofBot robot arm with coordinate conversion and safety checks.
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
                self.arm.Arm_Buzzer_On(0)
            except Exception as e:
                print(f"⚠ Beep failed: {e}")
        else:
            print(f"[SIM] Beep ({duration_ms}ms)")

    def connect(self):
        """
        Establish connection to the robot hardware.
        Sets self.is_connected = True if successful.
        """
        if not self.use_real_hardware:
            print("🔧 Simulation mode - skipping hardware connection")
            self.is_connected = False
            return False

        if self.arm is None:
            print("❌ Arm_Device object is None, cannot connect")
            self.is_connected = False
            return False

        try:
            # Optional: move servos to default positions as a connection test
            print("🔗 Connecting to hardware...")
            self.arm.Arm_serial_servo_write6(90, 90, 90, 90, 90, 90, 500)
            time.sleep(0.5)
            
            self.is_connected = True
            print("✅ Hardware connection established")
            self.beep()
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

    def _execute_move(self, servo_angles, move_time=MOVE_TIME_MS):
        """
        Low-level servo movement executor.
        """
        # Validate angles
        for i, angle in enumerate(servo_angles):
            if not (SERVO_ANGLES_MIN[i] <= angle <= SERVO_ANGLES_MAX[i]):
                print(f"⚠ Servo {i} angle {angle}° outside limits")
                return False

        self.beep(200)

        if self.use_real_hardware and self.arm:
            try:
                self.arm.Arm_serial_servo_write6(*servo_angles, move_time)
                time.sleep(move_time / 1000.0)
                self.beep(200)
                return True
            except Exception as e:
                print(f"❌ Movement failed: {e}")
                return False

        else:
            print(f"[SIM] Move → {servo_angles} ({move_time}ms)")
            time.sleep(0.5)
            self.beep(200)
            return True

    def _adjust_angles_for_height(self, base_angles, z_mm, obj_label):
        adjusted = base_angles.copy()
        REFERENCE_HEIGHT = 200
        height_delta = z_mm - REFERENCE_HEIGHT
        SHOULDER = 1
        ANGLE_PER_MM = 0.2

        adjusted[SHOULDER] += height_delta * ANGLE_PER_MM
        adjusted[SHOULDER] = max(30, min(150, adjusted[SHOULDER]))

        print(
            f"   Height adjustment: z={z_mm}mm "
            f"(delta={height_delta:+.0f}) → shoulder={adjusted[SHOULDER]:.1f}°"
        )
        return adjusted

    def move_to_label_position(self, obj_label, position_type="approach", gripper_open=True, z_mm=None):
        if obj_label not in CLASS_SERVO_ANGLES:
            print(f"⚠ Unknown label: {obj_label}")
            return False

        angles = CLASS_SERVO_ANGLES[obj_label][position_type].copy()
        angles[-1] = 0 if gripper_open else 50

        if z_mm is not None:
            angles = self._adjust_angles_for_height(angles, z_mm, obj_label)

        print(f"📍 Moving to {position_type} position for {obj_label}")
        return self._execute_move(angles)

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
        print("\n" + "=" * 60)
        print(f"🤖 PICK SEQUENCE: {obj_label.upper()}")
        if z_mm:
            print(f"   Detected height: z={z_mm:.1f}mm")
        print("=" * 60)

        if obj_label not in CLASS_SERVO_ANGLES:
            print(f"❌ Unknown object label: {obj_label}")
            return False

        # 1. Approach
        print("[1/6] Approaching...")
        if not self.move_to_label_position(obj_label, "approach", True, z_mm):
            return False

        # 2. Lower
        print("[2/6] Lowering...")
        if not self.move_to_label_position(obj_label, "grasp", True, z_mm):
            return False

        # 3. Grip
        print("[3/6] Gripping...")
        self.set_gripper(False)
        time.sleep(0.5)

        # 4. Lift
        print("[4/6] Lifting...")
        if not self.move_to_label_position(obj_label, "lift", False, z_mm):
            return False

        # 5. Drop zone
        print("[5/6] Moving to drop zone...")
        if not self._execute_move(DROP_ZONE_SERVOS):
            return False

        # 6. Release
        print("[6/6] Releasing...")
        self.set_gripper(True)
        time.sleep(0.5)

        self.home()

        print("=" * 60)
        print(f"✅ PICK COMPLETE - {obj_label.upper()} picked successfully!")
        print("=" * 60)
        return True

    def pick_detected_object(self, detection_data):
        label = detection_data.get('label', 'unknown')
        x = detection_data.get('x')
        y = detection_data.get('y')
        z = detection_data.get('z')
        conf = detection_data.get('confidence', 0.0)

        if x is None or y is None or z is None:
            print("❌ Invalid detection data - missing coordinates")
            return False

        print(f"📦 Detected: {label} (confidence: {conf:.2f})")
        return self.pick_object(label, z_mm=z)
