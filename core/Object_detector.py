#Import the necessary libraries
import cv2
import numpy as np
from ultralytics import YOLO
import sys
import os
import time

# Add parent folder to path
sys.path.append(os.path.abspath(os.path.join(os.getcwd(), '..')))
from calibration_files.Coord_converter import pixel_to_shelf

#Object detecting class with optimizations for live detection
class ObjectDetector3D:
    def __init__(self, model_path, camera_calibration_path=None, camera_index=0):
        """
        Initialize the object detector with YOLOv8 model and camera calibration

        Args:
            model_path: Path to trained YOLOv8 model (.pt file)
            camera_calibration_path: Path to camera calibration files (optional)
            camera_index: Camera device index (default 0)
        """
        self.model = YOLO(model_path)
        
        # Optimize model for inference speed
        try:
            self.model.to('cuda')  # Use GPU if available
        except:
            pass  # Fall back to CPU
        
        try:
            self.model.half()  # Use half precision (FP16) for faster inference
        except:
            pass  # If half precision not available, continue with FP32
        
        self.camera_index = camera_index
        self.cap = None

        # Load camera calibration if available
        self.camera_matrix = None
        self.dist_coeffs = None
        self.map1 = None
        self.map2 = None
        
        if camera_calibration_path:
            try:
                self.camera_matrix = np.load("calibration_files/camera_matrix.npy")
                self.dist_coeffs =  np.load("calibration_files/dist_coeffs.npy")
                print("Camera calibration loaded")
            except:
                print("Could not load camera calibration, using uncalibrated mode")

        self.frame_width = None
        self.frame_height = None

        # Grid configuration
        self.GRID_ROWS = 3
        self.GRID_COLS = 2

        # Performance settings
        self.INFERENCE_INTERVAL = 3  # Run detection every N frames
        self.CONFIDENCE_THRESHOLD = 0.5  # Minimum confidence for detections

    def init_undistort(self, frame_width, frame_height):
        """Initialize undistortion maps if calibration data available"""
        if self.camera_matrix is not None and self.dist_coeffs is not None:
            new_cam_matrix, roi = cv2.getOptimalNewCameraMatrix(
                self.camera_matrix, self.dist_coeffs, (frame_width, frame_height), 1
            )
            self.map1, self.map2 = cv2.initUndistortRectifyMap(
                self.camera_matrix, self.dist_coeffs, None, new_cam_matrix,
                (frame_width, frame_height), cv2.CV_16SC2
            )
            print("Undistortion maps initialized")

    def open_camera(self):
        """
        Open the camera and initialize parameters

        Returns:
            bool: True if camera opened successfully
        """
        self.cap = cv2.VideoCapture(self.camera_index)

        if not self.cap.isOpened():
            print(f"Error: Could not open camera {self.camera_index}")
            return False

        # Optimize camera settings
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # Minimize buffer for real-time capture
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        self.cap.set(cv2.CAP_PROP_FPS, 30)

        # Get actual frame dimensions
        self.frame_width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.frame_height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        
        # Initialize undistortion if calibration available
        self.init_undistort(self.frame_width, self.frame_height)

        print(f"Camera opened successfully: {self.frame_width}x{self.frame_height}")
        return True

    def close_camera(self):
        """Release the camera resource"""
        if self.cap is not None:
            self.cap.release()
            print("Camera closed")
        cv2.destroyAllWindows()

    def draw_virtual_grid(self, frame):
        """Draws a virtual grid on the frame"""
        h, w = frame.shape[:2]
        cell_w = w // self.GRID_COLS
        cell_h = h // self.GRID_ROWS

        for r in range(self.GRID_ROWS):
            for c in range(self.GRID_COLS):
                x1 = c * cell_w
                y1 = r * cell_h
                x2 = x1 + cell_w
                y2 = y1 + cell_h

                cv2.rectangle(frame, (x1, y1), (x2, y2), (255, 255, 255), 1)
                text = f"({r}, {c})"
                cv2.putText(frame, text, (x1 + 10, y1 + 25),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (200, 200, 200), 2)

    def detect_animals(self, frame):
        """Run YOLO detection and return detections"""
        results = self.model(frame, conf=self.CONFIDENCE_THRESHOLD, verbose=False)[0]
        detections = []

        for box in results.boxes:
            cls = int(box.cls[0])
            label = self.model.names[cls]
            confidence = float(box.conf[0])

            x1, y1, x2, y2 = box.xyxy[0].tolist()
            cx = int((x1 + x2) / 2)
            cy = int((y1 + y2) / 2)

            detections.append((label, cx, cy, x1, y1, x2, y2, confidence))

        return detections

    def get_grid_cell(self, cx, cy):
        """Return (row, col) of grid cell"""
        cell_w = self.frame_width // self.GRID_COLS
        cell_h = self.frame_height // self.GRID_ROWS

        col = cx // cell_w
        row = cy // cell_h

        row = min(max(row, 0), self.GRID_ROWS - 1)
        col = min(max(col, 0), self.GRID_COLS - 1)

        return int(row), int(col)

    def get_real_world_coords(self, cx, cy, bbox_height, label):
        """Convert pixel coordinates to real-world coordinates"""
        try:
            X, Y, Z = pixel_to_shelf(cx, cy, bbox_height_pixels=bbox_height, label=label, shelf_z=0)
            return X, Y, Z
        except:
            return None, None, None

    def run_live_detection(self, show_grid=True):
        """
        Main loop for real-time live detection with performance optimization

        Args:
            show_grid: Whether to display grid overlay
        """
        if not self.open_camera():
            return

        print("Live detection with optimized performance!")
        print(f"Press SPACE for detailed analysis, ESC to exit")
        print(f"Frame size: {self.frame_width}x{self.frame_height} | Inference every {self.INFERENCE_INTERVAL} frame(s)")

        frame_count = 0
        detections = []
        inference_time = 0

        try:
            while True:
                ret, frame = self.cap.read()
                if not ret:
                    continue

                frame_count += 1

                # Apply undistortion if available
                if self.map1 is not None and self.map2 is not None:
                    frame = cv2.remap(frame, self.map1, self.map2, cv2.INTER_LINEAR)

                display = frame.copy()

                # Draw grid if enabled
                if show_grid:
                    self.draw_virtual_grid(display)

                # Run inference every N frames
                if frame_count % self.INFERENCE_INTERVAL == 0:
                    start_time = time.time()
                    detections = self.detect_animals(frame)
                    inference_time = (time.time() - start_time) * 1000

                # Draw detections from previous inference
                for label, cx, cy, x1, y1, x2, y2, conf in detections:
                    cv2.rectangle(display, (int(x1), int(y1)), (int(x2), int(y2)), (0, 255, 0), 2)
                    cv2.circle(display, (cx, cy), 5, (0, 255, 0), -1)
                    row, col = self.get_grid_cell(cx, cy)
                    cv2.putText(display, f"{label} {conf:.2f}", (int(x1), int(y1) - 10),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)

                # Display performance info
                cv2.putText(display, f"Inference: {inference_time:.1f}ms | Detections: {len(detections)}", 
                            (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

                cv2.imshow("Live Detection", display)

                key = cv2.waitKey(1) & 0xFF
                if key == 27:  # ESC to quit
                    break
                elif key == 32:  # SPACE for detailed analysis
                    print("\n" + "="*60)
                    print(f"Frame #{frame_count} - Detailed Detection Results")
                    print("="*60)
                    detections = self.detect_animals(frame)
                    snapshot = display.copy()

                    for label, cx, cy, x1, y1, x2, y2, conf in detections:
                        bbox_height_pixels = y2 - y1
                        X, Y, Z = self.get_real_world_coords(cx, cy, bbox_height_pixels, label)
                        
                        if X is not None:
                            print(f"  {label} (conf: {conf:.2f}): X={X:.2f}mm, Y={Y:.2f}mm, Z={Z:.2f}mm")
                        else:
                            print(f"  {label} (conf: {conf:.2f}): Could not compute real-world coords")

                        cv2.circle(snapshot, (cx, cy), 7, (0, 255, 0), -1)
                        row, col = self.get_grid_cell(cx, cy)
                        cv2.putText(snapshot, f"{label} ({row},{col})", (int(x1), int(y1) - 30),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)

                    cv2.imshow("Detailed Detection", snapshot)
                    print("="*60 + "\n")
                    cv2.waitKey(2000)
                    cv2.destroyWindow("Detailed Detection")

        finally:
            self.close_camera()

    def run_snapshot_detection(self):
        """
        Single frame capture and detection mode
        """
        if not self.open_camera():
            return

        print("Capturing image and running detection...")

        ret, frame = self.cap.read()
        if not ret:
            print("Failed to capture frame")
            self.close_camera()
            return

        # Apply undistortion if available
        if self.map1 is not None and self.map2 is not None:
            frame = cv2.remap(frame, self.map1, self.map2, cv2.INTER_LINEAR)

        display = frame.copy()
        self.draw_virtual_grid(display)

        print("Running YOLO detection...")
        detections = self.detect_animals(frame)
        snapshot = display.copy()

        print("\n" + "="*60)
        print("Detection Results")
        print("="*60)

        for label, cx, cy, x1, y1, x2, y2, conf in detections:
            bbox_height_pixels = y2 - y1
            X, Y, Z = self.get_real_world_coords(cx, cy, bbox_height_pixels, label)
            
            if X is not None:
                print(f"  {label} (conf: {conf:.2f}): X={X:.2f}mm, Y={Y:.2f}mm, Z={Z:.2f}mm")
            else:
                print(f"  {label} (conf: {conf:.2f}): Could not compute real-world coords")

            cv2.circle(snapshot, (cx, cy), 7, (0, 255, 0), -1)
            row, col = self.get_grid_cell(cx, cy)
            cv2.putText(snapshot, f"{label} ({row},{col})", (int(x1), int(y1) - 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)

        cv2.imshow("Detection Result", snapshot)
        print(f"Total detections: {len(detections)}")
        print("="*60 + "\n")
        cv2.waitKey(2000)

        self.close_camera()