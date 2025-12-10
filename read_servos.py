import time
from Arm_Lib import Arm_Device
#Create a robotic arm object
Arm = Arm_Device()
time.sleep(.1)

def main():
        for i in range(6):
            aa = Arm.Arm_serial_servo_read(i+1)
            print(aa)
            time.sleep(.01)
            time.sleep(.5)
            print("END OF LINE! ")



main()
