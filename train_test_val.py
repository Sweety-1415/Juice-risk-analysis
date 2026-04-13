import os
import shutil
import random

IMG_ROOT = "Bottle_img_label/bottle_img"
LBL_ROOT = "Bottle_img_label/bottle_label"
OUTPUT_DIR = "dataset"

SPLIT_RATIO = (0.7, 0.2, 0.1)

IMG_EXTS = [".jpg", ".jpeg", ".png"]

data = []

# 🔍 Collect all (image, label) pairs
for cls in os.listdir(IMG_ROOT):
    img_cls_path = os.path.join(IMG_ROOT, cls)
    lbl_cls_path = os.path.join(LBL_ROOT, cls)

    if not os.path.isdir(img_cls_path):
        continue

    for img_name in os.listdir(img_cls_path):
        ext = os.path.splitext(img_name)[1].lower()
        if ext not in IMG_EXTS:
            continue

        img_path = os.path.join(img_cls_path, img_name)
        label_name = os.path.splitext(img_name)[0] + ".txt"
        label_path = os.path.join(lbl_cls_path, label_name)

        data.append((img_path, label_path))

# 🔀 Shuffle
random.shuffle(data)

# ✂️ Split
train_end = int(len(data) * SPLIT_RATIO[0])
val_end = train_end + int(len(data) * SPLIT_RATIO[1])

splits = {
    "train": data[:train_end],
    "val": data[train_end:val_end],
    "test": data[val_end:]
}

# 📁 Create folders
for split in splits:
    os.makedirs(os.path.join(OUTPUT_DIR, "images", split), exist_ok=True)
    os.makedirs(os.path.join(OUTPUT_DIR, "labels", split), exist_ok=True)

# 📦 Copy files
for split, items in splits.items():
    for img_path, label_path in items:
        img_name = os.path.basename(img_path)
        label_name = os.path.basename(label_path)

        img_dst = os.path.join(OUTPUT_DIR, "images", split, img_name)
        label_dst = os.path.join(OUTPUT_DIR, "labels", split, label_name)

        shutil.copy(img_path, img_dst)

        if os.path.exists(label_path):
            shutil.copy(label_path, label_dst)
        else:
            # create empty label file (important for YOLO)
            open(label_dst, "w").close()
            print(f"⚠️ Missing label → created empty: {label_name}")

print("✅ Dataset split completed!")