# Coordinate Integration Guide: Detection → Robot Control

## Overview
The system converts from **camera pixel coordinates** → **real-world coordinates** → **robot servo angles** for autonomous picking.

## Data Flow

```
┌─────────────────────────────────────────────────────────────┐
│                      CAMERA CAPTURE                         │
│                    (640x480 pixels)                         │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ↓
┌─────────────────────────────────────────────────────────────┐
│                   YOLO DETECTION                            │
│    Returns: (cx, cy, x1, y1, x2, y2, label, confidence)   │
│             cx, cy = pixel center                           │
│             x1-y2 = bounding box                            │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ↓
┌─────────────────────────────────────────────────────────────┐
│              PIXEL → REAL-WORLD CONVERSION                  │
│         coord_converter.pixel_to_shelf()                    │
│                                                              │
│  Inputs:  cx, cy (pixels)                                  │
│           bbox_height_pixels (object size)                 │
│           label (object class)                             │
│                                                              │
│  Uses:    - Camera calibration matrix                      │
│           - Camera distortion coefficients                 │
│           - Rotation/Translation to shelf frame (R_shelf)  │
│           - Object height lookup table                     │
│                                                              │
│  Outputs: X, Y, Z (mm, in robot base frame)               │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ↓
┌─────────────────────────────────────────────────────────────┐
│              ROBOT CONTROLLER                               │
│    RobotController.pick_detected_object()                  │
│                                                              │
│  - Validates coordinates (safety checks)                   │
│  - Plans pick sequence (approach → grasp → lift → drop)    │
│  - TODO: Convert X,Y,Z → servo angles (inverse kinematics)│
│  - Executes movements on Arm_Device                        │
└─────────────────────────────────────────────────────────────┘
```

## Key Coordinate Systems

### 1. **Camera Frame** (pixels)
- Origin: top-left of image
- X: horizontal (0-640)
- Y: vertical (0-480)
- Uses: YOLO bounding box coordinates

### 2. **Shelf Frame** (mm)
- Origin: fixed point on shelf
- Defined by: `R_shelf` (rotation matrix) and `T_shelf` (translation vector)
- Accounts for: camera tilt, distance from shelf
- Uses: real-world picking coordinates

### 3. **Robot Base Frame** (mm)
- Origin: robot base
- X: forward/backward (50-300mm)
- Y: left/right (-200 to +200mm)
- Z: up/down (50-350mm)

## Implementation Example

### Basic Usage

```python
# 1. Initialize detector and robot
detector = ObjectDetector3D("model/best.pt", camera_calibration_path="..")
robot = RobotController(use_real_hardware=True)
robot.connect()

# 2. Detect object from camera frame
ret, frame = detector.cap.read()
detections = detector.detect_animals(frame)

# 3. Get first detection
label, cx, cy, x1, y1, x2, y2, conf = detections[0]

# 4. Convert pixel coordinates to real-world coordinates
bbox_height_pixels = y2 - y1
X, Y, Z = detector.get_real_world_coords(cx, cy, bbox_height_pixels, label)
print(f"Object at: X={X:.2f}mm, Y={Y:.2f}mm, Z={Z:.2f}mm")

# 5. Command robot to pick
detection_data = {
    'label': label,
    'x': X,
    'y': Y,
    'z': Z,
    'confidence': conf
}
robot.pick_detected_object(detection_data)
```

### Coordinate Conversion Details

The `pixel_to_shelf()` function (in `coord_converter.ipynb`):

1. **Undistort pixel coordinates**
   - Removes lens distortion using `camera_matrix` and `dist_coeffs`
   - Converts to normalized camera coordinates

2. **Create camera ray**
   - Ray from camera origin through undistorted pixel
   - In homogeneous coordinates: `[Xn, Yn, 1.0]`

3. **Transform to shelf frame**
   - Uses `R_shelf` (rotation) and `T_shelf` (translation)
   - Calculates camera origin in shelf coordinates

4. **Estimate object depth (Z)**
   - Uses object height lookup table
   - Formula: `Z = (focal_length × real_height) / bbox_height_pixels`
   - Falls back to fixed plane intersection if object not in table

5. **Compute 3D position**
   - Ray-plane intersection at computed Z
   - Returns (X, Y, Z) in shelf frame

## Configuration Files

Located in workspace root:
- `camera_matrix.npy` - 3x3 camera intrinsic matrix
- `dist_coeffs.npy` - Distortion coefficients
- `R_shelf.npy` - Rotation matrix (camera to shelf)
- `T_shelf.npy` - Translation vector (camera to shelf)

## Object Height Lookup

Defined in `coord_converter.ipynb`:
```python
object_height_lookup = {
    "lion": 0.06,        # 60mm
    "elephant": 0.06,
    "zebra": 0.072,      # 72mm
    "giraffe": 0.09,     # 90mm
    "tiger": 0.04,       # 40mm
    "cheetah": 0.058,
}
```

**To add new objects:**
1. Measure actual height in real world (in meters)
2. Add to `object_height_lookup` in `coord_converter.ipynb`
3. Run detection again

## Safety Limits

Configured in `robot_controller.ipynb`:
```python
ROBOT_X_LIMITS = (50, 300)       # Forward/backward
ROBOT_Y_LIMITS = (-200, 200)     # Left/right
ROBOT_Z_LIMITS = (50, 350)       # Up/down
```

All coordinates are validated before robot movement. Out-of-bounds picks are rejected.

## Troubleshooting

### Issue: Coordinates seem incorrect
**Check:**
1. Camera calibration files loaded correctly
2. Object in `object_height_lookup`
3. Camera tilt/position hasn't changed since calibration

### Issue: Robot misses objects
**Check:**
1. Calibration accuracy
2. Object height measurements
3. Servo angle limits not interfering

### Issue: "Could not compute real-world coords"
**Causes:**
1. Object not in height lookup table
2. Invalid bounding box (very small object)
3. Camera ray parallel to shelf plane

## Next Steps

1. **Implement Inverse Kinematics**
   - Convert (X, Y, Z) → 6 servo angles
   - Account for DofBot arm geometry
   - Check servo limits

2. **Add Calibration Mode**
   - Helper functions to capture calibration images
   - Auto-compute camera matrix and distortion

3. **Optimize Speed**
   - Current: ~100ms per detection
   - Goal: <50ms for real-time picking

4. **Add Error Handling**
   - Retry logic if pick fails
   - Graceful recovery from collisions
