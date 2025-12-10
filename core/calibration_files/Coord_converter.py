import numpy as np
import cv2
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

camera_matrix = np.load(os.path.join(BASE_DIR, "camera_matrix.npy"))
dist_coeffs = np.load(os.path.join(BASE_DIR, "dist_coeffs.npy"))
R_shelf = np.load(os.path.join(BASE_DIR, "R_shelf.npy"))
T_shelf = np.load(os.path.join(BASE_DIR, "T_shelf.npy"))

# Dictionary of real-world heights (meters) for your objects
object_height_lookup = {
    "lion": 0.06,
    "elephant": 0.06,
    "zebra": 0.072,
    "giraffe":0.09,
    "tiger":0.04,
    "cheetah":0.058,
}

def pixel_to_shelf(cx, cy, bbox_height_pixels=None, label=None, shelf_z=0):
    """
    Convert YOLO pixel center (cx, cy) into real-world coordinates (X, Y, Z).
    
    If bbox_height_pixels and label are provided, estimate Z using object size.
    Otherwise, intersect the camera ray with Z = shelf_z plane.

    Returns floats (X, Y, Z)
    """

    # --- 1. Undistort pixel → normalized camera coordinates ---
    undistorted = cv2.undistortPoints(
        np.array([[[cx, cy]]], dtype=np.float32),
        camera_matrix,
        dist_coeffs
    )[0][0]

    Xn, Yn = float(undistorted[0]), float(undistorted[1])
    ray_cam = np.array([Xn, Yn, 1.0], dtype=float)  # homogeneous camera ray

    # --- 2. Compute the camera origin in shelf coordinates ---
    C_shelf = -(R_shelf.T @ T_shelf).reshape(3)

    # --- 3. Convert ray into shelf coordinates ---
    ray_shelf = (R_shelf.T @ ray_cam).reshape(3)

    # --- 4. Estimate Z from object size if bbox and label are provided ---
    if bbox_height_pixels is not None and label is not None:
        if label in object_height_lookup:
            H_real = object_height_lookup[label]
            focal_length = camera_matrix[1, 1]  # using fy
            Z = (focal_length * H_real) / bbox_height_pixels
        else:
            # fallback if object not in dictionary
            Z = shelf_z
    else:
        # --- Intersection with fixed plane ---
        if abs(ray_shelf[2]) < 1e-6:
            raise ZeroDivisionError("Camera ray is parallel to the shelf plane (Z).")
        t = (shelf_z - C_shelf[2]) / ray_shelf[2]
        P = C_shelf + t * ray_shelf
        return float(P[0]), float(P[1]), float(P[2])

    # --- 5. Compute X, Y using estimated Z ---
    t = (Z - C_shelf[2]) / ray_shelf[2]
    P = C_shelf + t * ray_shelf

    return float(P[0]), float(P[1]), float(P[2])


