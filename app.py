"""
JuiceScan AI - Full Web Application
====================================
Features:
- Login / Register / Forgot Password
- Dashboard with Profile
- Product name search → Risk Analysis
- Image upload (bottle/label) → YOLO inference → Risk Analysis
- Camera scan → Risk Analysis
- AI Chatbot with voice over
- Multi-language translation (text + voice)
- History saving
"""

import os
import uuid
import json
import hashlib
import sqlite3
from datetime import datetime
from functools import wraps
from pathlib import Path

from flask import (
    Flask, render_template, request, jsonify,
    redirect, url_for, session, flash, g
)
from werkzeug.utils import secure_filename

# YOLO
try:
    from ultralytics import YOLO
    YOLO_AVAILABLE = True
except ImportError:
    YOLO_AVAILABLE = False

# Translation
try:
    from deep_translator import GoogleTranslator
    TRANSLATOR_AVAILABLE = True
except ImportError:
    TRANSLATOR_AVAILABLE = False

app = Flask(__name__)
app.secret_key = "juicescan_ai_secret_key_2026_super_secure"

# ─── Config ──────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent
UPLOAD_FOLDER = BASE_DIR / "uploads"
UPLOAD_FOLDER.mkdir(exist_ok=True)
DB_PATH = BASE_DIR / "juicescan.db"
MODEL_PATH = BASE_DIR / "runs" / "beverage_model" / "weights" / "best.pt"
IMG_SIZE = 224

app.config["UPLOAD_FOLDER"] = str(UPLOAD_FOLDER)
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}

# ─── YOLO Model ──────────────────────────────────────────────────────────────
model = None
if YOLO_AVAILABLE and MODEL_PATH.exists():
    try:
        model = YOLO(str(MODEL_PATH))
        print(f"[OK] YOLOv8 model loaded from {MODEL_PATH}")
    except Exception as e:
        print(f"[ERR] Failed to load model: {e}")
else:
    print("[WARN] YOLO model not available — running in mock mode")

# ─── Health Risk Database ────────────────────────────────────────────────────
HEALTH_RISK_DB = {
    "7up": {
        "display_name": "7UP",
        "type": "Carbonated Soft Drink",
        "sugar_level": "High",
        "risk": "HIGH",
        "calories_per_100ml": 42,
        "sugar_per_100ml": 11.0,
        "caffeine": False,
        "artificial_colors": False,
        "warnings": ["Diabetes", "Obesity", "Dental decay", "Kidney stones"],
        "safe_for": [],
        "not_safe_for": ["Diabetics", "Obese individuals", "Children under 5", "Kidney patients"],
        "can_consume": ["Healthy adults (occasionally)", "Athletes (post-workout hydration alternative)"],
        "advice": "High sugar lemon-lime carbonated drink. Contains 11g sugar per 100ml. Not recommended for diabetics, obese individuals, or children. Occasional consumption for healthy adults is acceptable.",
        "ingredients": "Carbonated Water, Sugar, Citric Acid, Natural Flavoring, Sodium Citrate"
    },
    "Campa": {
        "display_name": "Campa Cola",
        "type": "Carbonated Soft Drink",
        "sugar_level": "High",
        "risk": "HIGH",
        "calories_per_100ml": 44,
        "sugar_per_100ml": 11.0,
        "caffeine": True,
        "artificial_colors": True,
        "warnings": ["Diabetes", "Obesity", "Dental decay", "Caffeine sensitivity"],
        "safe_for": [],
        "not_safe_for": ["Diabetics", "Pregnant women", "Children under 5", "Hypertension patients"],
        "can_consume": ["Healthy adults (occasionally)"],
        "advice": "High sugar carbonated drink with caffeine and artificial colors. Avoid if managing blood sugar or blood pressure levels.",
        "ingredients": "Carbonated Water, Sugar, Caramel Color, Phosphoric Acid, Caffeine, Natural Flavors"
    },
    "CocaCola": {
        "display_name": "Coca-Cola",
        "type": "Carbonated Soft Drink",
        "sugar_level": "High",
        "risk": "HIGH",
        "calories_per_100ml": 42,
        "sugar_per_100ml": 10.6,
        "caffeine": True,
        "artificial_colors": True,
        "warnings": ["Diabetes", "Obesity", "Dental decay", "Heart disease", "Caffeine addiction"],
        "safe_for": [],
        "not_safe_for": ["Diabetics", "Heart patients", "Hypertension patients", "Pregnant women", "Children under 5"],
        "can_consume": ["Healthy adults (in moderation, max 1 can/day)"],
        "advice": "Contains high sugar (10.6g/100ml) and caffeine (32mg/330ml). Regular consumption linked to Type 2 diabetes, obesity, and cardiovascular issues. Not suitable for diabetics, heart or hypertension patients.",
        "ingredients": "Carbonated Water, Sugar, Caramel Color (E150d), Phosphoric Acid, Natural Flavors, Caffeine"
    },
    "Fanta": {
        "display_name": "Fanta Orange",
        "type": "Carbonated Soft Drink",
        "sugar_level": "High",
        "risk": "HIGH",
        "calories_per_100ml": 48,
        "sugar_per_100ml": 11.5,
        "caffeine": False,
        "artificial_colors": True,
        "warnings": ["Diabetes", "Obesity", "Dental decay", "Artificial colors (ADHD risk)", "Hyperactivity in children"],
        "safe_for": [],
        "not_safe_for": ["Diabetics", "Children with ADHD", "Obese individuals", "People with color sensitivity"],
        "can_consume": ["Healthy adults (occasionally)"],
        "advice": "High sugar orange-flavored drink with artificial colors (Sunset Yellow). May cause hyperactivity in children. Avoid for diabetics and children with attention disorders.",
        "ingredients": "Carbonated Water, Sugar, Orange Juice (5%), Citric Acid, Sodium Citrate, Sunset Yellow (E110), Beta-Carotene"
    },
    "Fizz": {
        "display_name": "Fizz",
        "type": "Carbonated Soft Drink",
        "sugar_level": "High",
        "risk": "HIGH",
        "calories_per_100ml": 40,
        "sugar_per_100ml": 10.0,
        "caffeine": False,
        "artificial_colors": False,
        "warnings": ["Diabetes", "Obesity", "Dental decay"],
        "safe_for": [],
        "not_safe_for": ["Diabetics", "Obese individuals", "Children under 5"],
        "can_consume": ["Healthy adults (occasionally)"],
        "advice": "Carbonated sugary drink. Not recommended for health-conscious consumers or people managing chronic conditions.",
        "ingredients": "Carbonated Water, Sugar, Citric Acid, Natural Flavoring"
    },
    "Frooti": {
        "display_name": "Frooti Mango",
        "type": "Fruit Drink",
        "sugar_level": "Medium-High",
        "risk": "MODERATE",
        "calories_per_100ml": 60,
        "sugar_per_100ml": 13.0,
        "caffeine": False,
        "artificial_colors": False,
        "warnings": ["Diabetes", "Obesity", "High fructose", "High calorie"],
        "safe_for": ["Occasional consumption for healthy adults"],
        "not_safe_for": ["Diabetics", "Obese individuals", "People on low-sugar diets"],
        "can_consume": ["Healthy adults", "Children over 5 (in moderation)", "Athletes (energy source)"],
        "advice": "Mango fruit drink with added sugar. Despite being marketed as 'fruity', it contains 13g sugar per 100ml. Moderate consumption advisable. Not suitable for diabetics.",
        "ingredients": "Water, Sugar, Mango Pulp (15%), Citric Acid, Mango Flavoring, Preservatives (E211)"
    },
    "Limca": {
        "display_name": "Limca",
        "type": "Carbonated Soft Drink",
        "sugar_level": "High",
        "risk": "HIGH",
        "calories_per_100ml": 40,
        "sugar_per_100ml": 10.0,
        "caffeine": False,
        "artificial_colors": False,
        "warnings": ["Diabetes", "Obesity", "Dental decay"],
        "safe_for": [],
        "not_safe_for": ["Diabetics", "Obese individuals", "Kidney patients"],
        "can_consume": ["Healthy adults (occasionally)"],
        "advice": "Lime-flavored carbonated drink with high sugar content. While caffeine-free, the sugar level makes it unsuitable for diabetics.",
        "ingredients": "Carbonated Water, Sugar, Citric Acid, Lime Flavoring, Sodium Citrate"
    },
    "Maaza": {
        "display_name": "Maaza Mango",
        "type": "Fruit Drink",
        "sugar_level": "Medium-High",
        "risk": "MODERATE",
        "calories_per_100ml": 58,
        "sugar_per_100ml": 13.5,
        "caffeine": False,
        "artificial_colors": False,
        "warnings": ["Diabetes", "Obesity", "High fructose", "High calorie"],
        "safe_for": ["Occasional consumption for healthy adults"],
        "not_safe_for": ["Diabetics", "Obese individuals", "People on calorie-restricted diets"],
        "can_consume": ["Healthy adults", "Children over 5 (in moderation)"],
        "advice": "Mango fruit drink with added sugar. Contains higher sugar than some sodas. Limit intake for weight management.",
        "ingredients": "Water, Sugar, Mango Pulp (14%), Citric Acid, Preservatives, Mango Flavoring"
    },
    "MD_Diet": {
        "display_name": "Mountain Dew Diet",
        "type": "Diet Carbonated Drink",
        "sugar_level": "Zero/Low",
        "risk": "LOW",
        "calories_per_100ml": 1,
        "sugar_per_100ml": 0.0,
        "caffeine": True,
        "artificial_colors": True,
        "warnings": ["Artificial sweeteners (Aspartame)", "Caffeine sensitivity", "Not for Phenylketonuria (PKU) patients"],
        "safe_for": ["Diabetics (in moderation)", "Weight management", "Calorie-conscious individuals"],
        "not_safe_for": ["People with PKU", "Caffeine-sensitive individuals", "Pregnant women (due to caffeine)", "Children under 5"],
        "can_consume": ["Diabetics (in moderation)", "People on weight-loss diets", "Healthy adults"],
        "advice": "Zero sugar diet soda. Contains artificial sweeteners (Aspartame) instead of sugar. Generally safer for diabetics but should be consumed in moderation due to caffeine content.",
        "ingredients": "Carbonated Water, Citric Acid, Aspartame, Sodium Benzoate, Caffeine, Yellow 5, Acesulfame K"
    },
    "MD_Original": {
        "display_name": "Mountain Dew Original",
        "type": "Carbonated Soft Drink",
        "sugar_level": "High",
        "risk": "HIGH",
        "calories_per_100ml": 46,
        "sugar_per_100ml": 12.0,
        "caffeine": True,
        "artificial_colors": True,
        "warnings": ["Diabetes", "Obesity", "High caffeine", "Dental decay", "Anxiety", "Insomnia"],
        "safe_for": [],
        "not_safe_for": ["Diabetics", "Heart patients", "People with anxiety", "Insomnia sufferers", "Children", "Pregnant women"],
        "can_consume": ["Healthy adults (occasionally, max 1 can/day)"],
        "advice": "High sugar (12g/100ml) and high caffeine (54mg/330ml). One of the highest caffeine sodas. Avoid for diabetics, anxiety sufferers, and people with sleep issues.",
        "ingredients": "Carbonated Water, Sugar, Concentrated Orange Juice, Citric Acid, Sodium Benzoate, Caffeine, Yellow 5, Gum Arabic"
    },
    "Mirinda": {
        "display_name": "Mirinda Orange",
        "type": "Carbonated Soft Drink",
        "sugar_level": "High",
        "risk": "HIGH",
        "calories_per_100ml": 46,
        "sugar_per_100ml": 11.3,
        "caffeine": False,
        "artificial_colors": True,
        "warnings": ["Diabetes", "Obesity", "Dental decay", "Artificial colors", "Hyperactivity risk"],
        "safe_for": [],
        "not_safe_for": ["Diabetics", "Children with ADHD", "Obese individuals"],
        "can_consume": ["Healthy adults (occasionally)"],
        "advice": "Orange-flavored with high sugar and artificial colors. Contains Sunset Yellow which is linked to hyperactivity in children. Avoid for diabetics.",
        "ingredients": "Carbonated Water, Sugar, Citric Acid, Sunset Yellow (E110), Sodium Benzoate, Orange Flavoring"
    },
    "Pepsi_Cherry": {
        "display_name": "Pepsi Cherry",
        "type": "Carbonated Soft Drink",
        "sugar_level": "High",
        "risk": "HIGH",
        "calories_per_100ml": 44,
        "sugar_per_100ml": 11.0,
        "caffeine": True,
        "artificial_colors": True,
        "warnings": ["Diabetes", "Obesity", "Caffeine", "Dental decay", "Artificial flavoring"],
        "safe_for": [],
        "not_safe_for": ["Diabetics", "Heart patients", "Caffeine-sensitive individuals", "Children under 5"],
        "can_consume": ["Healthy adults (occasionally)"],
        "advice": "Cherry-flavored cola with high sugar, caffeine, and artificial flavoring. Not recommended for diabetics or heart patients.",
        "ingredients": "Carbonated Water, Sugar, Caramel Color, Phosphoric Acid, Caffeine, Natural and Artificial Cherry Flavor, Citric Acid"
    },
    "Pepsi_Diet": {
        "display_name": "Pepsi Diet",
        "type": "Diet Carbonated Drink",
        "sugar_level": "Zero/Low",
        "risk": "LOW",
        "calories_per_100ml": 1,
        "sugar_per_100ml": 0.0,
        "caffeine": True,
        "artificial_colors": True,
        "warnings": ["Artificial sweeteners (Aspartame)", "Caffeine sensitivity"],
        "safe_for": ["Diabetics (in moderation)", "Weight management"],
        "not_safe_for": ["People with PKU", "Caffeine-sensitive individuals", "Pregnant women"],
        "can_consume": ["Diabetics (in moderation)", "People on diets", "Healthy adults"],
        "advice": "Zero sugar with artificial sweeteners. Safer option for diabetics in moderation. Watch for caffeine content if sensitive.",
        "ingredients": "Carbonated Water, Caramel Color, Phosphoric Acid, Aspartame, Potassium Benzoate, Caffeine, Citric Acid, Acesulfame K"
    },
    "Pepsi_Original": {
        "display_name": "Pepsi Original",
        "type": "Carbonated Soft Drink",
        "sugar_level": "High",
        "risk": "HIGH",
        "calories_per_100ml": 44,
        "sugar_per_100ml": 11.0,
        "caffeine": True,
        "artificial_colors": True,
        "warnings": ["Diabetes", "Obesity", "Caffeine", "Dental decay", "Heart disease"],
        "safe_for": [],
        "not_safe_for": ["Diabetics", "Heart patients", "Hypertension patients", "Children under 5"],
        "can_consume": ["Healthy adults (in moderation)"],
        "advice": "Contains high sugar and caffeine. Regular consumption increases risk of Type 2 diabetes and cardiovascular disease. Avoid if diabetic or have hypertension.",
        "ingredients": "Carbonated Water, Sugar, Caramel Color (E150d), Phosphoric Acid, Caffeine, Natural Flavors"
    },
    "Pepsi_ReducedSugar": {
        "display_name": "Pepsi Reduced Sugar",
        "type": "Reduced Sugar Drink",
        "sugar_level": "Medium",
        "risk": "MODERATE",
        "calories_per_100ml": 28,
        "sugar_per_100ml": 6.5,
        "caffeine": True,
        "artificial_colors": True,
        "warnings": ["Moderate diabetes risk", "Caffeine", "Artificial sweeteners"],
        "safe_for": ["Health-conscious individuals (with moderation)"],
        "not_safe_for": ["Diabetics (use with caution)", "Caffeine-sensitive individuals"],
        "can_consume": ["Healthy adults", "People transitioning to lower sugar intake"],
        "advice": "Reduced sugar variant with ~40% less sugar than original. Better option but still has sugar. Use with caution for diabetics. Good transitional drink.",
        "ingredients": "Carbonated Water, Sugar, Caramel Color, Phosphoric Acid, Aspartame, Caffeine, Acesulfame K, Citric Acid"
    },
    "Pepsi_Zero": {
        "display_name": "Pepsi Zero Sugar",
        "type": "Zero Sugar Drink",
        "sugar_level": "Zero",
        "risk": "LOW",
        "calories_per_100ml": 0,
        "sugar_per_100ml": 0.0,
        "caffeine": True,
        "artificial_colors": True,
        "warnings": ["Artificial sweeteners", "Caffeine sensitivity", "Ginseng extract"],
        "safe_for": ["Diabetics (in moderation)", "Weight management", "Calorie restriction"],
        "not_safe_for": ["People with PKU", "Caffeine-sensitive individuals"],
        "can_consume": ["Diabetics", "People on weight-loss diets", "Calorie-conscious individuals", "Healthy adults"],
        "advice": "Zero sugar and zero calories. Safest Pepsi option for diabetics and weight watchers. Contains artificial sweeteners and caffeine.",
        "ingredients": "Carbonated Water, Caramel Color, Phosphoric Acid, Aspartame, Potassium Benzoate, Caffeine, Acesulfame K, Ginseng Extract"
    },
    "Pulpy": {
        "display_name": "Minute Maid Pulpy Orange",
        "type": "Fruit Drink",
        "sugar_level": "Medium-High",
        "risk": "MODERATE",
        "calories_per_100ml": 48,
        "sugar_per_100ml": 11.0,
        "caffeine": False,
        "artificial_colors": False,
        "warnings": ["Diabetes", "High sugar", "Processed fruit (not fresh)", "Preservatives"],
        "safe_for": ["Occasional consumption for healthy adults"],
        "not_safe_for": ["Diabetics", "Obese individuals"],
        "can_consume": ["Healthy adults", "Children over 5 (in moderation)"],
        "advice": "Orange drink with pulp. Despite fruit content, still contains significant added sugar. Not a substitute for actual fruit or fresh juice.",
        "ingredients": "Water, Sugar, Orange Juice (10%), Orange Pulp, Citric Acid, Sodium Citrate, Beta-Carotene, Vitamin C"
    },
    "Slice": {
        "display_name": "Slice Mango",
        "type": "Fruit Drink",
        "sugar_level": "Medium-High",
        "risk": "MODERATE",
        "calories_per_100ml": 56,
        "sugar_per_100ml": 13.0,
        "caffeine": False,
        "artificial_colors": False,
        "warnings": ["Diabetes", "Obesity", "High fructose", "High calorie"],
        "safe_for": ["Occasional consumption for healthy adults"],
        "not_safe_for": ["Diabetics", "Obese individuals", "Calorie-restricted diets"],
        "can_consume": ["Healthy adults", "Children over 5 (small amounts)"],
        "advice": "Mango drink with added sugar and high calorie content. One of the highest calorie fruit drinks available.",
        "ingredients": "Water, Sugar, Mango Pulp (15%), Citric Acid, Preservatives (E211), Mango Flavoring"
    },
    "Sprite": {
        "display_name": "Sprite",
        "type": "Carbonated Soft Drink",
        "sugar_level": "High",
        "risk": "HIGH",
        "calories_per_100ml": 40,
        "sugar_per_100ml": 10.0,
        "caffeine": False,
        "artificial_colors": False,
        "warnings": ["Diabetes", "Obesity", "Dental decay"],
        "safe_for": [],
        "not_safe_for": ["Diabetics", "Obese individuals", "Children under 5"],
        "can_consume": ["Healthy adults (occasionally)"],
        "advice": "High sugar lemon-lime drink. Caffeine-free but still carries high sugar risks. Not suitable for diabetics.",
        "ingredients": "Carbonated Water, Sugar, Citric Acid, Natural Lime Flavoring, Sodium Citrate"
    },
    "ThumbsUp": {
        "display_name": "Thums Up",
        "type": "Carbonated Soft Drink",
        "sugar_level": "High",
        "risk": "HIGH",
        "calories_per_100ml": 42,
        "sugar_per_100ml": 10.5,
        "caffeine": True,
        "artificial_colors": True,
        "warnings": ["Diabetes", "Obesity", "Caffeine", "Dental decay", "Heart disease risk"],
        "safe_for": [],
        "not_safe_for": ["Diabetics", "Heart patients", "Hypertension patients", "Children", "Pregnant women"],
        "can_consume": ["Healthy adults (in moderation)"],
        "advice": "Indian cola with high sugar and caffeine. Known for strong carbonation that can aggravate acid reflux. Avoid if diabetic or have heart conditions.",
        "ingredients": "Carbonated Water, Sugar, Caramel Color (E150d), Phosphoric Acid, Caffeine, Natural Flavoring"
    },
}

# Product name aliases for text search
PRODUCT_ALIASES = {}
for key, val in HEALTH_RISK_DB.items():
    # Add the key itself
    PRODUCT_ALIASES[key.lower()] = key
    PRODUCT_ALIASES[val["display_name"].lower()] = key
    # Add without spaces/special chars
    clean = val["display_name"].lower().replace(" ", "").replace("-", "").replace("_", "")
    PRODUCT_ALIASES[clean] = key

# Extra aliases
EXTRA_ALIASES = {
    "coca cola": "CocaCola", "coke": "CocaCola", "cola": "CocaCola",
    "pepsi": "Pepsi_Original", "pepsi original": "Pepsi_Original",
    "pepsi diet": "Pepsi_Diet", "diet pepsi": "Pepsi_Diet",
    "pepsi zero": "Pepsi_Zero", "zero pepsi": "Pepsi_Zero",
    "pepsi cherry": "Pepsi_Cherry", "cherry pepsi": "Pepsi_Cherry",
    "pepsi reduced sugar": "Pepsi_ReducedSugar",
    "mountain dew": "MD_Original", "dew": "MD_Original", "mt dew": "MD_Original",
    "mountain dew diet": "MD_Diet", "diet dew": "MD_Diet", "diet mountain dew": "MD_Diet",
    "thumbs up": "ThumbsUp", "thums up": "ThumbsUp", "thumsup": "ThumbsUp",
    "7 up": "7up", "seven up": "7up", "sevenup": "7up",
    "minute maid": "Pulpy", "minute maid pulpy": "Pulpy",
    "campa cola": "Campa", "campa": "Campa",
    "frooti": "Frooti", "mango frooti": "Frooti",
    "maaza": "Maaza", "mango maaza": "Maaza",
    "mirinda": "Mirinda", "miranda": "Mirinda",
    "slice": "Slice", "mango slice": "Slice",
    "sprite": "Sprite", "limca": "Limca", "fizz": "Fizz",
    "pulpy orange": "Pulpy", "pulpy": "Pulpy",
    "fanta": "Fanta", "fanta orange": "Fanta",
}
PRODUCT_ALIASES.update(EXTRA_ALIASES)

# ─── Supported Languages ─────────────────────────────────────────────────────
LANGUAGES = {
    "en": "English", "hi": "Hindi", "ta": "Tamil", "te": "Telugu",
    "kn": "Kannada", "ml": "Malayalam", "bn": "Bengali", "mr": "Marathi",
    "gu": "Gujarati", "pa": "Punjabi", "ur": "Urdu",
    "es": "Spanish", "fr": "French", "de": "German", "zh": "Chinese",
    "ja": "Japanese", "ko": "Korean", "ar": "Arabic", "pt": "Portuguese",
    "ru": "Russian",
}

# ─── Database ────────────────────────────────────────────────────────────────
def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(str(DB_PATH))
        g.db.row_factory = sqlite3.Row
    return g.db

@app.teardown_appcontext
def close_db(exception):
    db = g.pop("db", None)
    if db is not None:
        db.close()

def init_db():
    db = sqlite3.connect(str(DB_PATH))
    db.execute("""CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        full_name TEXT DEFAULT '',
        age INTEGER DEFAULT 0,
        health_conditions TEXT DEFAULT '',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""")
    db.execute("""CREATE TABLE IF NOT EXISTS history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        product_name TEXT NOT NULL,
        risk_level TEXT NOT NULL,
        input_type TEXT DEFAULT 'text',
        result_json TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id)
    )""")
    db.commit()
    db.close()

init_db()

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# ─── Auth Decorator ──────────────────────────────────────────────────────────
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated

# ─── Helper Functions ─────────────────────────────────────────────────────────
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def find_product(query):
    """Search for a product by name. Returns (key, data) or (None, None)."""
    q = query.strip().lower()
    # Exact match
    if q in PRODUCT_ALIASES:
        key = PRODUCT_ALIASES[q]
        return key, HEALTH_RISK_DB[key]
    # Partial match
    for alias, key in PRODUCT_ALIASES.items():
        if q in alias or alias in q:
            return key, HEALTH_RISK_DB[key]
    return None, None

def run_yolo_inference(filepath):
    """Run YOLO model on an image file."""
    if model is None:
        return "CocaCola", 0.95  # Mock fallback
    results = model.predict(source=filepath, imgsz=IMG_SIZE, verbose=False)
    if results and len(results) > 0:
        result = results[0]
        probs = result.probs
        top_idx = probs.top5[0]
        top_conf = float(probs.top5conf[0])
        class_name = result.names[top_idx]
        return class_name, top_conf
    return "Unknown", 0.0

def build_chatbot_response(product_key, product_data, user_question=""):
    """Generate a chatbot-style response about a product."""
    d = product_data
    risk_emoji = {"LOW": "✅", "MODERATE": "⚠️", "HIGH": "🔴"}.get(d["risk"], "❓")

    response = f"{risk_emoji} **{d['display_name']}** — Risk Level: **{d['risk']}**\n\n"
    response += f"📊 **Nutrition per 100ml:** {d['calories_per_100ml']} calories, {d['sugar_per_100ml']}g sugar\n\n"

    # Who CAN consume
    if d.get("can_consume"):
        response += "✅ **Who CAN consume this:**\n"
        for item in d["can_consume"]:
            response += f"  • {item}\n"
        response += "\n"

    # Who should NOT consume
    if d.get("not_safe_for"):
        response += "🚫 **Who should NOT consume this:**\n"
        for item in d["not_safe_for"]:
            response += f"  • {item}\n"
        response += "\n"

    # Warnings
    if d.get("warnings"):
        response += "⚠️ **Health Warnings:**\n"
        for w in d["warnings"]:
            response += f"  • {w}\n"
        response += "\n"

    response += f"💡 **Advice:** {d['advice']}\n"

    return response

# ─── Routes ──────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    if "user_id" in session:
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        db = get_db()
        user = db.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
        if user and user["password_hash"] == hash_password(password):
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            session["full_name"] = user["full_name"] or user["username"]
            return redirect(url_for("dashboard"))
        flash("Invalid username or password", "error")
    return render_template("login.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        full_name = request.form.get("full_name", "").strip()
        if not username or not email or not password:
            flash("All fields are required", "error")
            return render_template("register.html")
        db = get_db()
        try:
            db.execute(
                "INSERT INTO users (username, email, password_hash, full_name) VALUES (?, ?, ?, ?)",
                (username, email, hash_password(password), full_name)
            )
            db.commit()
            flash("Registration successful! Please login.", "success")
            return redirect(url_for("login"))
        except sqlite3.IntegrityError:
            flash("Username or email already exists", "error")
    return render_template("register.html")

@app.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    if request.method == "POST":
        email = request.form.get("email", "").strip()
        new_password = request.form.get("new_password", "")
        db = get_db()
        user = db.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        if user and new_password:
            db.execute("UPDATE users SET password_hash = ? WHERE email = ?",
                       (hash_password(new_password), email))
            db.commit()
            flash("Password reset successful! Please login.", "success")
            return redirect(url_for("login"))
        elif not user:
            flash("Email not found", "error")
    return render_template("forgot_password.html")

@app.route("/dashboard")
@login_required
def dashboard():
    return render_template("dashboard.html",
                           username=session.get("username"),
                           full_name=session.get("full_name"),
                           languages=LANGUAGES)

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

# ─── API Routes ──────────────────────────────────────────────────────────────

@app.route("/api/analyze-name", methods=["POST"])
@login_required
def analyze_name():
    data = request.get_json()
    product_name = data.get("product_name", "")
    key, product_data = find_product(product_name)
    if product_data:
        # Save history
        db = get_db()
        db.execute(
            "INSERT INTO history (user_id, product_name, risk_level, input_type, result_json) VALUES (?, ?, ?, ?, ?)",
            (session["user_id"], product_data["display_name"], product_data["risk"], "text", json.dumps(product_data))
        )
        db.commit()
        chat_response = build_chatbot_response(key, product_data)
        return jsonify({"success": True, "brand": key, "confidence": 1.0,
                        "risk_info": product_data, "chat_response": chat_response})
    return jsonify({"success": False, "error": f"Product '{product_name}' not found. Try: Coca-Cola, Pepsi, Fanta, Sprite, 7UP, etc."})

@app.route("/api/analyze-image", methods=["POST"])
@login_required
def analyze_image():
    if "image" not in request.files:
        return jsonify({"error": "No image uploaded"}), 400
    file = request.files["image"]
    if file.filename == "" or not allowed_file(file.filename):
        return jsonify({"error": "Invalid file type. Use PNG, JPG, or WEBP."}), 400

    ext = file.filename.rsplit(".", 1)[1].lower()
    filename = f"{uuid.uuid4().hex}.{ext}"
    filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    file.save(filepath)

    class_name, confidence = run_yolo_inference(filepath)

    try:
        os.remove(filepath)
    except:
        pass

    product_data = HEALTH_RISK_DB.get(class_name)
    if product_data:
        db = get_db()
        input_type = request.form.get("input_type", "image")
        db.execute(
            "INSERT INTO history (user_id, product_name, risk_level, input_type, result_json) VALUES (?, ?, ?, ?, ?)",
            (session["user_id"], product_data["display_name"], product_data["risk"], input_type, json.dumps(product_data))
        )
        db.commit()
        chat_response = build_chatbot_response(class_name, product_data)
        return jsonify({"success": True, "brand": class_name, "confidence": confidence,
                        "risk_info": product_data, "chat_response": chat_response})

    return jsonify({"success": False, "error": f"Detected brand '{class_name}' not in our health database."})

@app.route("/api/chat", methods=["POST"])
@login_required
def chat():
    data = request.get_json()
    message = data.get("message", "").strip().lower()

    # Try to find a product in the message
    key, product_data = find_product(message)
    if product_data:
        response = build_chatbot_response(key, product_data, message)
        return jsonify({"success": True, "response": response})

    # General health questions
    if any(w in message for w in ["hello", "hi", "hey"]):
        return jsonify({"success": True, "response": "👋 Hello! I'm JuiceScan AI. Ask me about any beverage — I'll tell you the health risks and who can or can't consume it.\n\nTry typing a beverage name like 'Coca-Cola', 'Pepsi', or 'Frooti'!"})

    if any(w in message for w in ["diabetic", "diabetes", "sugar patient"]):
        safe = [v["display_name"] for v in HEALTH_RISK_DB.values() if v["risk"] == "LOW"]
        return jsonify({"success": True, "response": f"🩺 **For Diabetics:**\n\n✅ **Safer Options:** {', '.join(safe)}\n\n🚫 **Avoid:** All regular sugar-containing drinks (Coke, Pepsi Original, Fanta, etc.)\n\n💡 Always choose zero-sugar or diet variants and consume in moderation."})

    if any(w in message for w in ["safe", "healthy", "low risk", "best"]):
        safe = [v["display_name"] for v in HEALTH_RISK_DB.values() if v["risk"] == "LOW"]
        return jsonify({"success": True, "response": f"✅ **Lowest Risk Beverages in our database:**\n\n" + "\n".join(f"  • {s}" for s in safe) + "\n\n💡 These are zero/low sugar options. Fresh water, coconut water, or fresh fruit juice is always the healthiest choice!"})

    if any(w in message for w in ["worst", "dangerous", "avoid", "high risk"]):
        dangerous = [v["display_name"] for v in HEALTH_RISK_DB.values() if v["risk"] == "HIGH"]
        return jsonify({"success": True, "response": f"🔴 **High Risk Beverages:**\n\n" + "\n".join(f"  • {d}" for d in dangerous) + "\n\n⚠️ These beverages have high sugar content (10-13g/100ml) and should be avoided by diabetics, heart patients, and obese individuals."})

    if any(w in message for w in ["child", "children", "kids", "baby"]):
        return jsonify({"success": True, "response": "👶 **For Children:**\n\n🚫 **Avoid all carbonated drinks** for children under 5\n⚠️ **Limit fruit drinks** (Frooti, Maaza, Slice) to small amounts\n✅ **Best options:** Water, milk, fresh fruit juice, coconut water\n\n💡 Even 'fruit drinks' contain added sugar and are not a substitute for actual fruits."})

    if any(w in message for w in ["pregnant", "pregnancy"]):
        return jsonify({"success": True, "response": "🤰 **During Pregnancy:**\n\n🚫 **Avoid:** All caffeinated drinks (Coca-Cola, Pepsi, Mountain Dew, Thums Up)\n⚠️ **Limit:** Diet drinks with artificial sweeteners\n✅ **Better Options:** Water, fresh fruit juice, coconut water, milk\n\n💡 Caffeine intake should be limited to <200mg/day during pregnancy."})

    if any(w in message for w in ["heart", "bp", "blood pressure", "hypertension"]):
        return jsonify({"success": True, "response": "❤️ **For Heart / Hypertension Patients:**\n\n🚫 **Avoid:** Coca-Cola, Pepsi Original, Mountain Dew, Thums Up (high caffeine + sugar)\n⚠️ **Caution:** Diet drinks (still contain caffeine)\n✅ **Better:** Water, herbal tea, coconut water\n\n💡 High sugar drinks increase risk of cardiovascular disease."})

    if any(w in message for w in ["compare", "vs", "versus", "difference"]):
        return jsonify({"success": True, "response": "📊 **Quick Comparison:**\n\nAsk me about any specific drink like 'Pepsi vs Coke' or just type a drink name to see its full analysis!\n\n💡 You can also upload a photo of any beverage bottle for instant analysis."})

    return jsonify({"success": True, "response": "🤔 I didn't quite understand that. Here's what I can help with:\n\n• Type a **beverage name** (e.g., 'Coca-Cola', 'Pepsi Zero')\n• Ask about health conditions (e.g., 'drinks for diabetics')\n• Ask about safety (e.g., 'safe drinks for children')\n• Upload a **bottle photo** or **label image** for AI analysis\n• Use the **camera** to scan a bottle in real-time"})

@app.route("/api/translate", methods=["POST"])
@login_required
def translate():
    data = request.get_json()
    text = data.get("text", "")
    target_lang = data.get("target_lang", "en")

    if not text:
        return jsonify({"error": "No text provided"}), 400

    if target_lang == "en":
        return jsonify({"success": True, "translated_text": text})

    if TRANSLATOR_AVAILABLE:
        try:
            translated = GoogleTranslator(source="en", target=target_lang).translate(text)
            return jsonify({"success": True, "translated_text": translated})
        except Exception as e:
            return jsonify({"success": False, "error": str(e), "translated_text": text})
    else:
        return jsonify({"success": False, "error": "Translation service not available. Install: pip install deep-translator",
                        "translated_text": text})

@app.route("/api/history", methods=["GET"])
@login_required
def get_history():
    db = get_db()
    rows = db.execute(
        "SELECT * FROM history WHERE user_id = ? ORDER BY created_at DESC LIMIT 50",
        (session["user_id"],)
    ).fetchall()
    history = []
    for r in rows:
        history.append({
            "id": r["id"],
            "product_name": r["product_name"],
            "risk_level": r["risk_level"],
            "input_type": r["input_type"],
            "created_at": r["created_at"],
        })
    return jsonify({"success": True, "history": history})

@app.route("/api/profile", methods=["GET", "POST"])
@login_required
def profile():
    db = get_db()
    if request.method == "POST":
        data = request.get_json()
        full_name = data.get("full_name", "")
        age = data.get("age", 0)
        health_conditions = data.get("health_conditions", "")
        db.execute("UPDATE users SET full_name=?, age=?, health_conditions=? WHERE id=?",
                   (full_name, age, health_conditions, session["user_id"]))
        db.commit()
        session["full_name"] = full_name
        return jsonify({"success": True, "message": "Profile updated successfully!"})
    else:
        user = db.execute("SELECT * FROM users WHERE id=?", (session["user_id"],)).fetchone()
        return jsonify({
            "success": True,
            "username": user["username"],
            "email": user["email"],
            "full_name": user["full_name"],
            "age": user["age"],
            "health_conditions": user["health_conditions"],
            "created_at": user["created_at"]
        })

if __name__ == "__main__":
    print("\n" + "=" * 50)
    print("  🧃 JuiceScan AI — Starting Server")
    print("=" * 50)
    print(f"  Model: {'✅ Loaded' if model else '⚠️ Mock Mode'}")
    print(f"  Database: {DB_PATH}")
    print(f"  URL: http://localhost:5000")
    print("=" * 50 + "\n")
    app.run(debug=True, host="0.0.0.0", port=5000)
