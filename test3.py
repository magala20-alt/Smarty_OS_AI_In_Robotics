import time
from Arm_Lib import Arm_Device

# Hardcoded servo angles
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

# Home position (adjust as needed)
HOME_POSITION = [90, 90, 90, 90, 90, 90]

class HardcodedRobotController:
    def __init__(self, use_real_hardware=True):
        self.use_real_hardware = use_real_hardware
        self.holding_object = False
        self.current_object = None

        if use_real_hardware:
            try:
                print("🤖 Initializing robot arm...")
                self.arm = Arm_Device()
                time.sleep(0.2)
                print("✓ Arm initialized")
                
                # Move to home position on startup
                print("🏠 Moving to home position...")
                self.move_servos(HOME_POSITION)
                print("✓ Home position reached")

            except Exception as e:
                print(f"⚠ Could not initialize Arm_Device: {e}")
                print("⚠ Running in simulation mode")
                self.use_real_hardware = False
                self.arm = None
        else:
            print("[SIM] Running in simulation mode")
            self.arm = None
            print("[SIM] Moving to home position...")
            self.move_servos(HOME_POSITION)
            print("[SIM] Home position reached")

    def move_servos(self, angles, duration=500):
        """Move all 6 servos to the given angles."""
        if not angles or len(angles) != 6:
            print("⚠ Invalid angles provided:", angles)
            return
        if self.use_real_hardware and self.arm:
            self.arm.Arm_serial_servo_write6(*angles, duration)
            time.sleep(duration / 1000)
        else:
            print(f"[SIM] Moving servos to: {angles} (duration {duration}ms)")
            time.sleep(duration / 1000)

    def grab_sequence(self, class_label):
        """Execute approach → lift → grasp sequence for a given class."""
        if class_label not in CLASS_SERVO_ANGLES:
            print(f"❌ Unknown class label: {class_label}")
            return {'status': 'error', 'message': f'Unknown class label {class_label}'}

        angles_set = CLASS_SERVO_ANGLES[class_label]

        # Approach
        print(f"🎯 {class_label}: Approaching")
        self.move_servos(angles_set.get('approach'))

        # Lift (optional)
        if angles_set.get('lift'):
            print(f"⬆ {class_label}: Lifting")
            self.move_servos(angles_set.get('lift'))

        # Grasp
        print(f"🤗 {class_label}: Grasping")
        self.move_servos(angles_set.get('grasp'))

        self.holding_object = True
        self.current_object = class_label
        return {'status': 'grab', 'message': f'Grabbed {class_label} successfully!'}


# ============================
# Example usage
# ============================

if __name__ == "__main__":
    robot = HardcodedRobotController(use_real_hardware=True)
    
    # Execute grab for lion
    result = robot.grab_sequence("lion")
    print(result)
