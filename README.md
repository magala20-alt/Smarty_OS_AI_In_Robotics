# Smarty_OS_AI_In_Robotics

## Description

Smarty OS is an educational AI-powered DoFBOT robot designed to help children explore robotics through interactive play. Using a child-friendly graphical interface, kids can type simple commands such as “grab zebra”, or they can select an animal directly through picture-based buttons. Smarty OS then uses computer vision and robotics control to locate the correct toy animal on the shelf and attempt to pick it up.

After retrieving the requested animal, the GUI updates to confirm that the item has been successfully found. This project provides a fun hands-on introduction to AI and robotics concepts.

## Getting Started

1. Clone the repository to your local machine.
2. Open a terminal, navigate to the project folder, and install dependencies by running: pip install -r requirements.txt
   The requirements.txt file includes all the necessary libraries for running the project.
3. In the same terminal, navigate to the core directory: cd Smarty_OS_AI_In_Robotics/core
4. Launch the GUI by running: python dofbot_gui.py
5. After running the command, a JupyterLab link will appear in the terminal.
   Copy the link and paste it into your web browser.
6. Once JupyterLab opens, run dofbot_gui.py to start the Smarty OS graphical interface.

### Usage

Once the GUI loads, you can interact with the robot in two ways:

1. Text or Pictures

Type simple instructions such as:

“Grab lion”

Smarty OS will identify the correct toy animal on the shelf and attempt to pick it up.

2. Visual Selection Mode

You can also click the “Picture” button in the GUI.
This will display images of all available toy animals.
Simply click on the animal you want, and the robot will move to pick it up automatically.

After the task is completed, the GUI will display a message confirming that the animal has been successfully found and retrieved.

### Prerequisites

All required Python libraries are included in requirements.txt.  
Make sure you have Python 3.8+ installed.

### Troubleshooting Camera Issues

Use the steps below to verify that your camera is properly detected and working.

1. Test the camera feed

Open a terminal and run:

ffplay /dev/video0

If the camera opens successfully, the device is working

2. Check if OpenCV can access the camera

If you get an error, test the camera index with OpenCV:
python3 -c "import cv2; cap = cv2.VideoCapture(0); print('Opened:', cap.isOpened()); ret, frame = cap.read(); print('Read:', ret)"

Opened: True means the camera device was found

Read: True means frames are being successfully captured

If either value is False, the camera index may be incorrect.

3. Find available camera indices

To list all connected video devices, run:
v4l2-ctl --list-devices 2>&1

Under "USB 2.0 Camera", you will see the available camera indices (e.g., /dev/video0, /dev/video1, etc.).

4. Update your code

Use one of the camera indices listed above in your Python code:
cap = cv2.VideoCapture(<camera_index>)
Replace <camera_index> with the correct number (0, 1, 2, ...).

## Contributors

Angel Magala - Robotic Movement
Sebabatso Maloi -AI model development
Mehtaab Andoo - GUI
