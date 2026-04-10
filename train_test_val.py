import os
import shutil
import random

SOURCE_DIR = "Bottle_image"
DEST_DIR = "dataset"

SPLIT_RATIO = (0.7, 0.2, 0.1)  # train, val, test

for cls in os.listdir(SOURCE_DIR):
    cls_path = os.path.join(SOURCE_DIR, cls)
    images = os.listdir(cls_path)
    random.shuffle(images)

    train_end = int(len(images) * SPLIT_RATIO[0])
    val_end = train_end + int(len(images) * SPLIT_RATIO[1])

    splits = {
        "train": images[:train_end],
        "val": images[train_end:val_end],
        "test": images[val_end:]
    }

    for split, imgs in splits.items():
        split_dir = os.path.join(DEST_DIR, split, cls)
        os.makedirs(split_dir, exist_ok=True)

        for img in imgs:
            src = os.path.join(cls_path, img)
            dst = os.path.join(split_dir, img)
            shutil.copy(src, dst)

print("✅ Dataset split completed")