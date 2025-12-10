import time
from Arm_Lib import Arm_Device
#Create a robotic arm object
Arm = Arm_Device()
time.sleep(.1)

Arm.Arm_serial_servo_write() #define the servos angles