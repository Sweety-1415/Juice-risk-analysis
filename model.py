from ultralytics import YOLO

def main():
    model = YOLO("yolov8n.pt")  # detection model

    model.train(
        data="data.yaml",
        epochs=50,
        imgsz=640,
        batch=8,        # safe for RTX 3050 4GB
        device=0,
        workers=2,
        amp=True,

        # 🔥 AUGMENTATION SETTINGS
        hsv_h=0.015,   # color variation
        hsv_s=0.7,     # saturation
        hsv_v=0.4,     # brightness

        degrees=10,    # rotation
        translate=0.1, # shift
        scale=0.2,     # zoom in/out

        fliplr=0.5     # horizontal flip
    )

if __name__ == "__main__":
    main()