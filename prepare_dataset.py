"""
prepare_dataset.py
==================
Organizes the Bottle_image and Label datasets into YOLOv8 classification format.
"""

import os
import shutil
import random
from pathlib import Path
from collections import defaultdict

# ─── Configuration ───────────────────────────────────────────────────────────
SOURCE_DIR_1 = Path(r"c:\Users\sweet\OneDrive\Documents\Juice\Bottle_image")
SOURCE_DIR_2 = Path(r"c:\Users\sweet\OneDrive\Documents\Juice\Label")
OUTPUT_DIR = Path(r"c:\Users\sweet\OneDrive\Documents\Juice\dataset")
VAL_SPLIT = 0.2          # 20% for validation
RANDOM_SEED = 42
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}

# ─── Standardized class names ────────────────────────────────────────────────
CLASS_NAME_MAP = {
    # Bottle_image maps
    "7up": "7up",
    "campa_dataset": "Campa",
    "CocaCola": "CocaCola",
    "Fanta": "Fanta",
    "fizz_dataset": "Fizz",
    "Frooti": "Frooti",
    "Limca": "Limca",
    "Maaza": "Maaza",
    "MD.Diet": "MD_Diet",
    "MD.Orig": "MD_Original",
    "mirinda_dataset": "Mirinda",
    "P.Cherry": "Pepsi_Cherry",
    "P.diet": "Pepsi_Diet",
    "P.Orig": "Pepsi_Original",
    "P.Rsugar": "Pepsi_ReducedSugar",
    "P.Zero": "Pepsi_Zero",
    "pulpy_dataset": "Pulpy",
    "Slice": "Slice",
    "Sprite": "Sprite",
    "ThumbsUp": "ThumbsUp",
    
    # Label maps
    "7up_label": "7up",
    "Campa": "Campa",
    # CocaCola is same
    # Fanta is same
    "Fizz": "Fizz",
    # Frooti is same
    # Limca is same
    "MD.diet": "MD_Diet",
    "MD.orig": "MD_Original",
    # Maaza is same
    "Mirinda": "Mirinda",
    "P.cherry": "Pepsi_Cherry",
    "P.deit": "Pepsi_Diet",
    "P.orig": "Pepsi_Original",
    # P.Rsugar is same
    # P.Zero is same
    "Pulpy": "Pulpy",
    # Slice is same
    # Sprite is same
    "Thumbsup": "ThumbsUp"
}

def collect_images_from_source(source_dir: Path, class_images: dict, source_name: str) -> dict:
    """Collect all image paths grouped by class, appending to existing dictionary."""
    if not source_dir.exists():
        print(f"  [ERROR] {source_dir} not found!")
        return class_images
        
    for folder in sorted(source_dir.iterdir()):
        if not folder.is_dir():
            continue
        
        class_name = CLASS_NAME_MAP.get(folder.name, folder.name)
        
        images = [
            f for f in folder.iterdir()
            if f.is_file() and f.suffix.lower() in IMAGE_EXTENSIONS
        ]
        
        if len(images) == 0:
            print(f"  [{source_name}] [SKIP] {folder.name} -> 0 images found")
            continue
        
        class_images[class_name].extend(images)
        print(f"  [{source_name}] [OK]   {folder.name} -> {class_name}: {len(images)} images")
    
    return class_images


def split_dataset(class_images: dict, val_split: float, seed: int) -> tuple:
    """Split images into train and val sets (stratified by class)."""
    random.seed(seed)
    train_data = {}
    val_data = {}
    
    for class_name, images in class_images.items():
        shuffled = images.copy()
        random.shuffle(shuffled)
        
        n_val = max(1, int(len(shuffled) * val_split))  # At least 1 val image
        
        val_data[class_name] = shuffled[:n_val]
        train_data[class_name] = shuffled[n_val:]
    
    return train_data, val_data


def copy_images(data: dict, output_dir: Path, split_name: str):
    """Copy images to the output directory under the correct class folder."""
    for class_name, images in data.items():
        dest_dir = output_dir / split_name / class_name
        dest_dir.mkdir(parents=True, exist_ok=True)
        
        for img_path in images:
            dest_path = dest_dir / img_path.name
            if dest_path.exists():
                stem = img_path.stem
                suffix = img_path.suffix
                counter = 1
                while dest_path.exists():
                    dest_path = dest_dir / f"{stem}_{counter}{suffix}"
                    counter += 1
            
            shutil.copy2(str(img_path), str(dest_path))


def print_summary(train_data: dict, val_data: dict):
    print("\n" + "=" * 60)
    print(f"{'Class':<25} {'Train':>8} {'Val':>8} {'Total':>8}")
    print("-" * 60)
    
    total_train = total_val = 0
    for class_name in sorted(train_data.keys()):
        t = len(train_data[class_name])
        v = len(val_data[class_name])
        total_train += t
        total_val += v
        print(f"{class_name:<25} {t:>8} {v:>8} {t+v:>8}")
    
    print("-" * 60)
    print(f"{'TOTAL':<25} {total_train:>8} {total_val:>8} {total_train+total_val:>8}")
    print("=" * 60)


def main():
    print("=" * 60)
    print("  YOLOv8 Unified Dataset Preparation")
    print("=" * 60)
    
    if OUTPUT_DIR.exists():
        print(f"\n[INFO] Removing existing dataset at: {OUTPUT_DIR}")
        shutil.rmtree(OUTPUT_DIR)
    
    # Step 1: Collect images
    class_images = defaultdict(list)
    print(f"\n[Step 1] Scanning Bottle Images...\n")
    class_images = collect_images_from_source(SOURCE_DIR_1, class_images, "BOTTLES")
    
    print(f"\n[Step 1] Scanning Label Images...\n")
    class_images = collect_images_from_source(SOURCE_DIR_2, class_images, "LABELS")
    
    print(f"\n  Found {len(class_images)} final combined classes, "
          f"{sum(len(v) for v in class_images.values())} total images")
    
    # Step 2: Split into train/val
    print(f"\n[Step 2] Splitting dataset (train: {1-VAL_SPLIT:.0%}, val: {VAL_SPLIT:.0%})")
    train_data, val_data = split_dataset(class_images, VAL_SPLIT, RANDOM_SEED)
    
    # Step 3: Copy to output structure
    print(f"\n[Step 3] Copying unified images to: {OUTPUT_DIR}")
    copy_images(train_data, OUTPUT_DIR, "train")
    copy_images(val_data, OUTPUT_DIR, "val")
    
    # Step 4: Summary
    print_summary(train_data, val_data)
    print(f"\n[DONE] Unified Dataset ready at: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
