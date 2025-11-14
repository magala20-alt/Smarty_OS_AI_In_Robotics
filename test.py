from ultralytics import YOLO
import cv2

# Load your trained model
model = YOLO("runs/train/toy_animals_full/weights/best.pt")

# Open camera (0 = default webcam)
cap = cv2.VideoCapture(0)

while True:
    ret, frame = cap.read()
    if not ret:
        break

    # Run prediction
    results = model(frame)

    # Draw predictions on frame
    annotated_frame = results[0].plot()

    # Show window
    cv2.imshow("YOLOv8 Live", annotated_frame)

    # Quit when pressing 'q'
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
