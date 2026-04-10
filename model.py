from ultralytics import YOLO

def main():
    model = YOLO("yolov8n-cls.pt")

    model.train(
        data="dataset",
        epochs=50,
        imgsz=224,
        batch=16,
        device=0,
        workers=2,
        amp=True
    )

if __name__ == "__main__":
    main()