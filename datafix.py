import os

LABEL_ROOT = "Bottle_img_label/bottle_label"

# 📂 Get folder names in sorted order (IMPORTANT)
class_names = sorted([
    d for d in os.listdir(LABEL_ROOT)
    if os.path.isdir(os.path.join(LABEL_ROOT, d))
])

# 🔢 Create mapping: folder → class_id
class_map = {name: idx for idx, name in enumerate(class_names)}

print("Class Mapping:")
for k, v in class_map.items():
    print(f"{k} → {v}")

# 🔧 Update all label files
for class_name in class_names:
    folder_path = os.path.join(LABEL_ROOT, class_name)
    class_id = class_map[class_name]

    for file in os.listdir(folder_path):
        if not file.endswith(".txt"):
            continue

        file_path = os.path.join(folder_path, file)

        with open(file_path, "r") as f:
            lines = f.readlines()

        new_lines = []

        for line in lines:
            parts = line.strip().split()

            if len(parts) == 0:
                continue

            # 🔥 Replace class_id
            parts[0] = str(class_id)

            new_lines.append(" ".join(parts))

        with open(file_path, "w") as f:
            f.write("\n".join(new_lines))

print("✅ All labels updated based on folder names!")