"""
train_yolov8.py
===============
Fine-tunes a YOLOv8 nano classification model on the prepared beverage dataset.

Prerequisites:
    1. Run prepare_dataset.py first to create the dataset/ folder
    2. pip install ultralytics

Usage:
    python train_yolov8.py
"""

from pathlib import Path
from ultralytics import YOLO

# ─── Configuration ───────────────────────────────────────────────────────────
DATASET_DIR = Path(r"c:\Users\sweet\OneDrive\Documents\Juice\dataset")
PROJECT_DIR = Path(r"c:\Users\sweet\OneDrive\Documents\Juice\runs")
MODEL_NAME = "yolov8n-cls.pt"      # Nano classification - fast, lightweight
EXPERIMENT_NAME = "beverage_model"

# Training hyperparameters
EPOCHS = 50
IMG_SIZE = 224                      # Standard classification input size
BATCH_SIZE = 16                     # Reduce to 8 if you run out of memory
PATIENCE = 10                       # Early stopping patience
OPTIMIZER = "AdamW"
LR0 = 0.001                        # Initial learning rate
LRF = 0.01                         # Final learning rate (fraction of lr0)
WORKERS = 4                        # Data loader workers


def main():
    print("=" * 60)
    print("  YOLOv8 Beverage Classification - Training")
    print("=" * 60)
    
    # Verify dataset exists
    train_dir = DATASET_DIR / "train"
    val_dir = DATASET_DIR / "val"
    
    if not train_dir.exists() or not val_dir.exists():
        print("\n[ERROR] Dataset not found!")
        print(f"  Expected: {train_dir}")
        print(f"  Expected: {val_dir}")
        print("\n  Please run prepare_dataset.py first.")
        return
    
    # Count classes
    classes = sorted([d.name for d in train_dir.iterdir() if d.is_dir()])
    print(f"\n[INFO] Found {len(classes)} classes:")
    for i, cls in enumerate(classes):
        train_count = len(list((train_dir / cls).glob("*")))
        val_count = len(list((val_dir / cls).glob("*")))
        print(f"  {i:>2}. {cls:<25} train={train_count:>4}  val={val_count:>4}")
    
    # Load pretrained model
    print(f"\n[Step 1] Loading pretrained model: {MODEL_NAME}")
    model = YOLO(MODEL_NAME)
    
    # Start training
    print(f"\n[Step 2] Starting training...")
    print(f"  Epochs:     {EPOCHS}")
    print(f"  Image size: {IMG_SIZE}")
    print(f"  Batch size: {BATCH_SIZE}")
    print(f"  Optimizer:  {OPTIMIZER}")
    print(f"  Patience:   {PATIENCE} (early stopping)")
    print(f"  Project:    {PROJECT_DIR}")
    print(f"  Name:       {EXPERIMENT_NAME}")
    print()
    
    results = model.train(
        data=str(DATASET_DIR),
        epochs=EPOCHS,
        imgsz=IMG_SIZE,
        batch=BATCH_SIZE,
        patience=PATIENCE,
        optimizer=OPTIMIZER,
        lr0=LR0,
        lrf=LRF,
        workers=WORKERS,
        project=str(PROJECT_DIR),
        name=EXPERIMENT_NAME,
        exist_ok=True,
        pretrained=True,
        # Augmentation settings (helpful for small/imbalanced classes)
        hsv_h=0.015,          # HSV-Hue augmentation
        hsv_s=0.7,            # HSV-Saturation augmentation
        hsv_v=0.4,            # HSV-Value augmentation
        degrees=10.0,         # Rotation augmentation
        translate=0.1,        # Translation augmentation
        scale=0.5,            # Scale augmentation
        fliplr=0.5,           # Horizontal flip probability
        flipud=0.0,           # No vertical flip (bottles are upright)
        mosaic=0.0,           # Disable mosaic for classification
        erasing=0.1,          # Random erasing augmentation
        verbose=True,
    )
    
    # Training complete
    print("\n" + "=" * 60)
    print("  TRAINING COMPLETE!")
    print("=" * 60)
    
    best_model_path = PROJECT_DIR / EXPERIMENT_NAME / "weights" / "best.pt"
    last_model_path = PROJECT_DIR / EXPERIMENT_NAME / "weights" / "last.pt"
    
    print(f"\n  Best model: {best_model_path}")
    print(f"  Last model: {last_model_path}")
    print(f"  Results:    {PROJECT_DIR / EXPERIMENT_NAME}")
    
    # Quick validation
    print(f"\n[Step 3] Running validation on best model...")
    best_model = YOLO(str(best_model_path))
    metrics = best_model.val(
        data=str(DATASET_DIR),
        imgsz=IMG_SIZE,
        batch=BATCH_SIZE,
        project=str(PROJECT_DIR),
        name=f"{EXPERIMENT_NAME}_val",
        exist_ok=True,
    )
    
    print(f"\n  Top-1 Accuracy: {metrics.top1:.4f}")
    print(f"  Top-5 Accuracy: {metrics.top5:.4f}")
    
    print(f"\n[DONE] Training pipeline complete!")
    print(f"  Next step: Run evaluate_model.py for detailed analysis")


if __name__ == "__main__":
    main()
