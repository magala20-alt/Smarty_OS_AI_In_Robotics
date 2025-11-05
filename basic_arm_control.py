import time
from adafruit_servokit import ServoKit

kit = ServoKit(channels=16)

ELBOW = 1
WRIST = 2
GRIPPER = 3

def test_joints ():
    print("Testing elbow")
    kit.servo[ELBOW].angle = 0
    time.sleep(1)
    kit.servo[ELBOW].angle = 90
    time.sleep(1)
    kit.servo[ELBOW].angle = 180
    time.sleep(1)

    print("Testing wrist")
    kit.servo[WRIST].angle = 0
    time.sleep(1)
    kit.servo[WRIST].angle = 90
    time.sleep(1)
    kit.servo[WRIST].angle = 180
    time.sleep(1)

    print("Testing gripper")
    kit.servo[GRIPPER].angle = 0
    time.sleep(1)
    kit.servo[GRIPPER].angle = 90

test_joints()