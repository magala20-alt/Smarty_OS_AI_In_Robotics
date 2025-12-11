import time
from Arm_Lib import Arm_Device
import time

Arm = Arm_Device()
time.sleep(0.1)

# --- Move 1 ---
Arm.Arm_serial_servo_write6(90, 180, 0, 0, 86, 102, 2000)  # 1 second
time.sleep(3.1)  # wait a little longer than the move duration

# --- Move 2 ---
Arm.Arm_serial_servo_write6(75,98,20,86,85,102, 2000)  # 1 second
time.sleep(3.1)

# --- Move 3 ---
Arm.Arm_serial_servo_write6(77,103,11,98,85,107, 2000)  # 1 second
time.sleep(3.1)

# --- Move 4 ---
Arm.Arm_serial_servo_write6(70,120,28,56,88,108, 2000)  # 1 second
time.sleep(4.1)

# --- Move 5 ---
Arm.Arm_serial_servo_write6(12,90,0,50,88,74, 2000)  # 1 second
time.sleep(3.1)

# --- Move 1 ---
Arm.Arm_serial_servo_write6(90, 180, 0, 0, 86, 102, 2000)  # 1 second
time.sleep(3.1)  # wait a little longer than the move duration
