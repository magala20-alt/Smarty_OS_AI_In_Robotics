import cv2
import numpy as np
from ultralytics import YOLO
import threading
import time
import sys
import os


# Add parent folder to path to import coord_converter
sys.path.append(os.path.abspath(os.path.join(os.getcwd(), '..')))
from core.calibration_files.Coord_converter import pixel_to_shelf

camera_matrix = np.load("./core/calibration_files/camera_matrix.npy")
dist_coeffs = np.load("./core/calibration_files/dist_coeffs.npy")

# Compute undistortion map
def init_undistort(frame_width, frame_height):
    new_cam_matrix, roi = cv2.getOptimalNewCameraMatrix(
        camera_matrix, dist_coeffs, (frame_width, frame_height), 1
    )
    map1, map2 = cv2.initUndistortRectifyMap(
        camera_matrix, dist_coeffs, None, new_cam_matrix,
        (frame_width, frame_height), cv2.CV_16SC2
    )
    return map1, map2


# Load your YOLO model with optimizations
model = YOLO("./core/model/runs/train/toy_animals_full/weights/best.pt")
try:
    model.to('cuda')  # Use GPU if available
except:
    pass  # Fall back to CPU
        
try:
    model.model.float()  # Use half precision (FP16) for faster inference
except:
    pass  # If half precision not available, continue with FP32
# Grid configuration for virtual checkerboard
GRID_ROWS = 3
GRID_COLS = 2

# Performance settings
INFERENCE_INTERVAL = 3 # Run detection every N frames (adjust for balance between speed and accuracy)
FRAME_SKIP = 2 # Skip frames to reduce processing load
CONFIDENCE_THRESHOLD = 0.5  # Only show detections above this confidence

def draw_virtual_grid(frame):
    """Draws a virtual 3x2 grid on the frame."""
    h, w = frame.shape[:2]
    cell_w = w // GRID_COLS
    cell_h = h // GRID_ROWS

    for r in range(GRID_ROWS):
        for c in range(GRID_COLS):
            x1 = c * cell_w
            y1 = r * cell_h
            x2 = x1 + cell_w
            y2 = y1 + cell_h

            # Draw box
            cv2.rectangle(frame, (x1, y1), (x2, y2), (255, 255, 255), 1)

            # Label cell coordinates
            text = f"({r}, {c})"
            cv2.putText(frame, text, (x1 + 10, y1 + 25),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (200, 200, 200), 2)

def detect_animals(frame):
    """YOLO detect animals and return list: (label, cx, cy, x1, y1, x2, y2)."""
    # Use low confidence threshold for faster detection, filter later
    results = model(frame, conf=CONFIDENCE_THRESHOLD, verbose=False)[0]
    detections = []

    for box in results.boxes:
        cls = int(box.cls[0])
        label = model.names[cls]

        x1, y1, x2, y2 = box.xyxy[0].tolist()
        cx = int((x1 + x2) / 2)
        cy = int((y1 + y2) / 2)

        detections.append((label, cx, cy, x1, y1, x2, y2))

    return detections

def get_grid_cell(cx, cy, frame_width, frame_height):
    """Return (row, col) of the grid cell where the point falls."""
    cell_w = frame_width // GRID_COLS
    cell_h = frame_height // GRID_ROWS

    col = cx // cell_w
    row = cy // cell_h

    # Clamp inside range
    row = min(max(row, 0), GRID_ROWS - 1)
    col = min(max(col, 0), GRID_COLS - 1)

    return int(row), int(col)

            
# ---------------- Main ----------------
def main():
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Failed to open camera")
        return

    # Optimize camera settings
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # Minimize buffer for real-time capture
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 320)  # Reduce frame size (default often too large)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 240)
    cap.set(cv2.CAP_PROP_FPS, 30)  # Set target FPS

    # Read one frame to initialize undistortion
    ret, frame = cap.read()
    if not ret:
        print("Failed to capture frame")
        cap.release()
        return

    h, w = frame.shape[:2]
    map1, map2 = init_undistort(w, h)

    print("Live detection with optimized performance!")
    print(f"Press SPACE to run detection on current frame, ESC to exit")
    print(f"Frame size: {w}x{h} | Inference every {INFERENCE_INTERVAL} frame(s)")

    frame_count = 0
    detections = []
    last_detection_time = 0
    inference_time = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            continue

        frame_count += 1

        # Undistort
        frame = cv2.remap(frame, map1, map2, cv2.INTER_LINEAR)
        display = frame.copy()

        # Draw grid
        draw_virtual_grid(display)

        # Run inference every N frames to reduce lag
        if frame_count % INFERENCE_INTERVAL == 0:
            start_time = time.time()
            detections = detect_animals(frame)
            inference_time = (time.time() - start_time) * 1000  # Convert to ms

        # Draw detections on display (from previous inference)
        for label, cx, cy, x1, y1, x2, y2 in detections:
            # Draw detection box and label
            cv2.rectangle(display, (int(x1), int(y1)), (int(x2), int(y2)), (0, 255, 0), 2)
            cv2.circle(display, (cx, cy), 5, (0, 255, 0), -1)
            row, col = get_grid_cell(cx, cy, w, h)
            cv2.putText(display, f"{label}", (int(x1), int(y1) - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)

        # Display FPS and inference time
        cv2.putText(display, f"Inference: {inference_time:.1f}ms | Detections: {len(detections)}", 
                    (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

        cv2.imshow("Live Detection", display)

        key = cv2.waitKey(1) & 0xFF
        if key == 27:  # ESC to quit
            break
        elif key == 32:  # SPACE to show detailed detection info
            print("\n" + "="*50)
            print(f"Frame #{frame_count} - Detailed Detection Results")
            print("="*50)
            detections = detect_animals(frame)  # Force detection on current frame
            snapshot = display.copy()

            for label, cx, cy, x1, y1, x2, y2 in detections:
                # Compute bounding box height in pixels
                bbox_height_pixels = y2 - y1

                # Convert pixels to real-world coordinates using pixel_to_shelf
                X, Y, Z = pixel_to_shelf(cx, cy, bbox_height_pixels=bbox_height_pixels, label=label, shelf_z=0)
                print(f"  {label}: X={X:.2f}mm, Y={Y:.2f}mm, Z={Z:.2f}mm (pixel: {cx}, {cy})")

                # Draw detection
                cv2.circle(snapshot, (cx, cy), 7, (0, 255, 0), -1)
                row, col = get_grid_cell(cx, cy, w, h)
                cv2.putText(snapshot, f"{label} ({row},{col})", (int(x1), int(y1) - 30),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)

            cv2.imshow("Detailed Detection", snapshot)
            print("="*50 + "\n")
            cv2.waitKey(2000)  # Show for 2 seconds
            cv2.destroyWindow("Detailed Detection")

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()