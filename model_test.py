import cv2
from ultralytics import YOLO

model = YOLO(r"runs\classify\train3\weights\best.pt")

THRESHOLD = 0.7  # 🔥 tune this (0.6–0.8 ideal)

cap = cv2.VideoCapture(0)

while True:
    ret, frame = cap.read()
    results = model(frame)

    probs = results[0].probs
    top1 = probs.top1
    confidence = probs.top1conf.item()

    if confidence > THRESHOLD:
        label = results[0].names[top1]
        text = f"{label} ({confidence:.2f})"
    else:
        text = f"Unknown ({confidence:.2f})"

    cv2.putText(frame, text, (20, 50),
                cv2.FONT_HERSHEY_SIMPLEX, 1, (0,255,0), 2)

    cv2.imshow("Prediction", frame)

    if cv2.waitKey(1) & 0xFF == 27:
        break

cap.release()
cv2.destroyAllWindows()