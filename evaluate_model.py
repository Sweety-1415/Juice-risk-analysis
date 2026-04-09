"""
evaluate_model.py
=================
Evaluates the trained YOLOv8 beverage classification model.
- Runs validation metrics
- Per-class accuracy breakdown
- Sample predictions
- Exports model to ONNX

Prerequisites:
    1. Run prepare_dataset.py first
    2. Run train_yolov8.py first

Usage:
    python evaluate_model.py
    python evaluate_model.py --image path/to/test_image.jpg
"""

import argparse
import sys
from pathlib import Path
from ultralytics import YOLO

# ─── Configuration ───────────────────────────────────────────────────────────
DATASET_DIR = Path(r"c:\Users\sweet\OneDrive\Documents\Juice\dataset")
MODEL_PATH = Path(r"c:\Users\sweet\OneDrive\Documents\Juice\runs\beverage_model\weights\best.pt")
PROJECT_DIR = Path(r"c:\Users\sweet\OneDrive\Documents\Juice\runs")
IMG_SIZE = 224

# ─── Health Risk Database ────────────────────────────────────────────────────
# This will be used in the next phase for risk analysis
HEALTH_RISK_DB = {
    "7up": {
        "sugar_level": "High",
        "risk": "HIGH",
        "calories_per_100ml": 42,
        "sugar_per_100ml": 11.0,
        "warnings": ["Diabetes", "Obesity", "Dental decay"],
        "safe_for": [],
        "advice": "High sugar carbonated drink. Not recommended for diabetics or weight-conscious individuals."
    },
    "Campa": {
        "sugar_level": "High",
        "risk": "HIGH",
        "calories_per_100ml": 44,
        "sugar_per_100ml": 11.0,
        "warnings": ["Diabetes", "Obesity", "Dental decay"],
        "safe_for": [],
        "advice": "High sugar carbonated drink. Avoid if managing blood sugar levels."
    },
    "CocaCola": {
        "sugar_level": "High",
        "risk": "HIGH",
        "calories_per_100ml": 42,
        "sugar_per_100ml": 10.6,
        "warnings": ["Diabetes", "Obesity", "Dental decay", "Heart disease risk"],
        "safe_for": [],
        "advice": "Contains high sugar and caffeine. Not suitable for diabetics or hypertension patients."
    },
    "Fanta": {
        "sugar_level": "High",
        "risk": "HIGH",
        "calories_per_100ml": 48,
        "sugar_per_100ml": 11.5,
        "warnings": ["Diabetes", "Obesity", "Dental decay", "Artificial colors"],
        "safe_for": [],
        "advice": "High sugar with artificial colors. Avoid for children with ADHD and diabetics."
    },
    "Fizz": {
        "sugar_level": "High",
        "risk": "HIGH",
        "calories_per_100ml": 40,
        "sugar_per_100ml": 10.0,
        "warnings": ["Diabetes", "Obesity", "Dental decay"],
        "safe_for": [],
        "advice": "Carbonated sugary drink. Not recommended for health-conscious consumers."
    },
    "Frooti": {
        "sugar_level": "Medium-High",
        "risk": "MODERATE",
        "calories_per_100ml": 60,
        "sugar_per_100ml": 13.0,
        "warnings": ["Diabetes", "Obesity", "High fructose"],
        "safe_for": ["Occasional consumption for healthy adults"],
        "advice": "Mango fruit drink with added sugar. Moderate consumption advisable."
    },
    "Limca": {
        "sugar_level": "High",
        "risk": "HIGH",
        "calories_per_100ml": 40,
        "sugar_per_100ml": 10.0,
        "warnings": ["Diabetes", "Obesity", "Dental decay"],
        "safe_for": [],
        "advice": "Lime-flavored carbonated drink with high sugar content."
    },
    "Maaza": {
        "sugar_level": "Medium-High",
        "risk": "MODERATE",
        "calories_per_100ml": 58,
        "sugar_per_100ml": 13.5,
        "warnings": ["Diabetes", "Obesity", "High fructose"],
        "safe_for": ["Occasional consumption for healthy adults"],
        "advice": "Mango fruit drink. Contains added sugar. Limit intake."
    },
    "MD_Diet": {
        "sugar_level": "Zero/Low",
        "risk": "LOW",
        "calories_per_100ml": 1,
        "sugar_per_100ml": 0.0,
        "warnings": ["Artificial sweeteners", "Caffeine sensitivity"],
        "safe_for": ["Diabetics (in moderation)", "Weight management"],
        "advice": "Diet version with zero sugar. Contains artificial sweeteners. Generally safer for diabetics."
    },
    "MD_Original": {
        "sugar_level": "High",
        "risk": "HIGH",
        "calories_per_100ml": 46,
        "sugar_per_100ml": 12.0,
        "warnings": ["Diabetes", "Obesity", "Caffeine", "Dental decay"],
        "safe_for": [],
        "advice": "High sugar and caffeine content. Not recommended for diabetics or those with anxiety."
    },
    "Mirinda": {
        "sugar_level": "High",
        "risk": "HIGH",
        "calories_per_100ml": 46,
        "sugar_per_100ml": 11.3,
        "warnings": ["Diabetes", "Obesity", "Dental decay", "Artificial colors"],
        "safe_for": [],
        "advice": "Orange flavored with high sugar and artificial colors. Avoid for diabetics."
    },
    "Pepsi_Cherry": {
        "sugar_level": "High",
        "risk": "HIGH",
        "calories_per_100ml": 44,
        "sugar_per_100ml": 11.0,
        "warnings": ["Diabetes", "Obesity", "Caffeine", "Dental decay"],
        "safe_for": [],
        "advice": "High sugar with caffeine and cherry flavoring. Not for diabetics."
    },
    "Pepsi_Diet": {
        "sugar_level": "Zero/Low",
        "risk": "LOW",
        "calories_per_100ml": 1,
        "sugar_per_100ml": 0.0,
        "warnings": ["Artificial sweeteners", "Caffeine sensitivity"],
        "safe_for": ["Diabetics (in moderation)", "Weight management"],
        "advice": "Zero sugar with artificial sweeteners. Safer option for diabetics in moderation."
    },
    "Pepsi_Original": {
        "sugar_level": "High",
        "risk": "HIGH",
        "calories_per_100ml": 44,
        "sugar_per_100ml": 11.0,
        "warnings": ["Diabetes", "Obesity", "Caffeine", "Dental decay"],
        "safe_for": [],
        "advice": "Contains high sugar and caffeine. Avoid for diabetics and hypertension."
    },
    "Pepsi_ReducedSugar": {
        "sugar_level": "Medium",
        "risk": "MODERATE",
        "calories_per_100ml": 28,
        "sugar_per_100ml": 6.5,
        "warnings": ["Diabetes (moderate risk)", "Caffeine"],
        "safe_for": ["Health-conscious with moderation"],
        "advice": "Reduced sugar variant. Better option but still contains sugar. Use with caution for diabetics."
    },
    "Pepsi_Zero": {
        "sugar_level": "Zero",
        "risk": "LOW",
        "calories_per_100ml": 0,
        "sugar_per_100ml": 0.0,
        "warnings": ["Artificial sweeteners", "Caffeine sensitivity"],
        "safe_for": ["Diabetics (in moderation)", "Weight management", "Calorie restriction"],
        "advice": "Zero sugar and zero calories. Contains artificial sweeteners. Safest Pepsi option for diabetics."
    },
    "Pulpy": {
        "sugar_level": "Medium-High",
        "risk": "MODERATE",
        "calories_per_100ml": 48,
        "sugar_per_100ml": 11.0,
        "warnings": ["Diabetes", "High sugar", "Processed fruit"],
        "safe_for": ["Occasional consumption for healthy adults"],
        "advice": "Orange drink with pulp. Contains added sugar despite fruit content."
    },
    "Slice": {
        "sugar_level": "Medium-High",
        "risk": "MODERATE",
        "calories_per_100ml": 56,
        "sugar_per_100ml": 13.0,
        "warnings": ["Diabetes", "Obesity", "High fructose"],
        "safe_for": ["Occasional consumption for healthy adults"],
        "advice": "Mango drink with added sugar. High calorie content."
    },
    "Sprite": {
        "sugar_level": "High",
        "risk": "HIGH",
        "calories_per_100ml": 40,
        "sugar_per_100ml": 10.0,
        "warnings": ["Diabetes", "Obesity", "Dental decay"],
        "safe_for": [],
        "advice": "High sugar carbonated drink. Not suitable for diabetics."
    },
    "ThumbsUp": {
        "sugar_level": "High",
        "risk": "HIGH",
        "calories_per_100ml": 42,
        "sugar_per_100ml": 10.5,
        "warnings": ["Diabetes", "Obesity", "Caffeine", "Dental decay"],
        "safe_for": [],
        "advice": "High sugar cola with caffeine. Avoid for diabetics and hypertension."
    },
}


def evaluate_model(model_path: Path):
    """Run validation and print metrics."""
    print("=" * 60)
    print("  YOLOv8 Beverage Model - Evaluation")
    print("=" * 60)
    
    if not model_path.exists():
        print(f"\n[ERROR] Model not found at: {model_path}")
        print("  Please run train_yolov8.py first.")
        return None
    
    print(f"\n[Step 1] Loading model: {model_path}")
    model = YOLO(str(model_path))
    
    # Run validation
    print(f"\n[Step 2] Running validation on: {DATASET_DIR / 'val'}")
    metrics = model.val(
        data=str(DATASET_DIR),
        imgsz=IMG_SIZE,
        batch=16,
        project=str(PROJECT_DIR),
        name="beverage_eval",
        exist_ok=True,
    )
    
    print(f"\n{'='*60}")
    print(f"  VALIDATION RESULTS")
    print(f"{'='*60}")
    print(f"  Top-1 Accuracy: {metrics.top1:.4f} ({metrics.top1*100:.1f}%)")
    print(f"  Top-5 Accuracy: {metrics.top5:.4f} ({metrics.top5*100:.1f}%)")
    print(f"{'='*60}")
    
    return model


def predict_image(model, image_path: str):
    """Predict a single image and show risk analysis."""
    print(f"\n[Prediction] Analyzing: {image_path}")
    
    results = model.predict(
        source=image_path,
        imgsz=IMG_SIZE,
        verbose=False,
    )
    
    if not results or len(results) == 0:
        print("  No predictions made.")
        return
    
    result = results[0]
    probs = result.probs
    
    # Get top-5 predictions
    top5_indices = probs.top5
    top5_confs = probs.top5conf.tolist()
    class_names = result.names
    
    print(f"\n  {'Rank':<6} {'Beverage':<25} {'Confidence':>12}")
    print(f"  {'-'*45}")
    
    for i, (idx, conf) in enumerate(zip(top5_indices, top5_confs)):
        name = class_names[idx]
        bar = "█" * int(conf * 20)
        print(f"  {i+1:<6} {name:<25} {conf:>10.1%}  {bar}")
    
    # Health risk analysis for top prediction
    top_class = class_names[top5_indices[0]]
    top_conf = top5_confs[0]
    
    print(f"\n{'='*60}")
    print(f"  HEALTH RISK ANALYSIS - {top_class}")
    print(f"{'='*60}")
    
    risk_info = HEALTH_RISK_DB.get(top_class)
    if risk_info:
        risk_emoji = {"LOW": "✅", "MODERATE": "⚠️", "HIGH": "🔴"}.get(risk_info["risk"], "❓")
        
        print(f"\n  {risk_emoji} Risk Level: {risk_info['risk']}")
        print(f"  Sugar Level: {risk_info['sugar_level']}")
        print(f"  Calories: {risk_info['calories_per_100ml']} kcal/100ml")
        print(f"  Sugar: {risk_info['sugar_per_100ml']}g/100ml")
        
        if risk_info["warnings"]:
            print(f"\n  ⚠️  Health Warnings:")
            for w in risk_info["warnings"]:
                print(f"      • {w}")
        
        if risk_info["safe_for"]:
            print(f"\n  ✅ Safe For:")
            for s in risk_info["safe_for"]:
                print(f"      • {s}")
        
        print(f"\n  💡 Advice: {risk_info['advice']}")
    else:
        print(f"\n  No risk data available for {top_class}")
    
    print(f"\n{'='*60}")


def export_model(model, model_path: Path):
    """Export model to ONNX format."""
    print(f"\n[Export] Exporting model to ONNX...")
    
    onnx_path = model.export(format="onnx", imgsz=IMG_SIZE)
    print(f"  ONNX model saved to: {onnx_path}")
    
    return onnx_path


def main():
    parser = argparse.ArgumentParser(description="Evaluate YOLOv8 Beverage Model")
    parser.add_argument("--image", type=str, help="Path to a test image for prediction")
    parser.add_argument("--export", action="store_true", help="Export model to ONNX")
    parser.add_argument("--model", type=str, default=str(MODEL_PATH), help="Path to model weights")
    args = parser.parse_args()
    
    model_path = Path(args.model)
    
    # Evaluate
    model = evaluate_model(model_path)
    if model is None:
        sys.exit(1)
    
    # Predict on specific image if provided
    if args.image:
        predict_image(model, args.image)
    else:
        # Run sample predictions on a few val images
        print(f"\n[Step 3] Running sample predictions...")
        val_dir = DATASET_DIR / "val"
        sample_count = 0
        for class_dir in sorted(val_dir.iterdir()):
            if class_dir.is_dir():
                images = list(class_dir.glob("*.jpg")) + list(class_dir.glob("*.png"))
                if images:
                    predict_image(model, str(images[0]))
                    sample_count += 1
                    if sample_count >= 5:  # Show 5 samples
                        break
    
    # Export if requested
    if args.export:
        export_model(model, model_path)
    
    print(f"\n[DONE] Evaluation complete!")
    print(f"\nUsage examples:")
    print(f"  python evaluate_model.py --image path/to/bottle.jpg")
    print(f"  python evaluate_model.py --export")


if __name__ == "__main__":
    main()
