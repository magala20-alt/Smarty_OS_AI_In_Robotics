from ultralytics import YOLO
import cv2
import numpy as np

# Load trained model
model = YOLO("runs/train/toy_animals_full/weights/best.pt")

def get_dominant_color(image):
    # reshape image for clustering
    pixels = image.reshape((-1, 3))
    pixels = np.float32(pixels)
    # k-means clustering to find dominant color
    _, labels, palette = cv2.kmeans(
        pixels,
        2,  # number of colors to find
        None,
        (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 50, 0.2),
        10,
        cv2.KMEANS_RANDOM_CENTERS
    )

    # most common cluster
    _, counts = np.unique(labels, return_counts=True)
    dominant = palette[np.argmax(counts)]
    return dominant.astype(int)

def color_name(rgb):
    r, g, b = rgb

    # Convert RGB → HSV
    color = np.uint8([[rgb]])
    hsv = cv2.cvtColor(color, cv2.COLOR_BGR2HSV)[0][0]
    h, s, v = hsv

    # ---- Zebra special detection (black + white stripes) ----
    if (s < 40 and v > 160):  # white
        return "white/black (zebra)"

    # ---- Grey detection ----
    if s < 50 and 50 < v < 200:
        return "grey"

    # ---- Yellow (cheetah, lion, giraffe) ----
    if 20 < h < 35 and s > 80:
        return "yellow"

    # ---- Orange/Red (tiger) ----
    if (5 < h < 20 and s > 100) or (h <= 5 and s > 100):
        return "orange/red"

    return "unknown color"


# Open camera (0 = default webcam)
cap = cv2.VideoCapture(0)

while True:
    ret, frame = cap.read()
    if not ret:
        break

    # Run prediction
    results = model(frame)

    # Annotated frame from YOLO
    annotated_frame = results[0].plot()

    # Loop through detections
    for box in results[0].boxes:
        x1, y1, x2, y2 = map(int, box.xyxy[0])
        cls = int(box.cls[0])
        label = model.names[cls]

        # Crop detected object
        crop = frame[y1:y2, x1:x2]

        if crop.size > 0:
            rgb = get_dominant_color(crop)
            col = color_name(rgb)

            # Display text on the frame
            text = f"{label}: {col}"
            cv2.putText(
                annotated_frame,
                text,
                (x1, y1 - 10),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (0, 255, 255),
                2
            )

    # Show window
    cv2.imshow("YOLOv8 + Color Detection", annotated_frame)

    # Quit when pressing 'q'
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
