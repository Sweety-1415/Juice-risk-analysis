from __future__ import annotations

from copy import deepcopy
from typing import Any

from app.data import BEVERAGE_LIBRARY, DEFAULT_DAILY_LIMITS


def get_beverage(key: str | None) -> dict[str, Any] | None:
    if not key:
        return None
    return deepcopy(BEVERAGE_LIBRARY.get(key))


def _profile_conditions(profile: Any) -> tuple[set[str], set[str], float]:
    if not profile:
        return set(), set(), DEFAULT_DAILY_LIMITS["sugar_g"]
    conditions = {item.lower() for item in (profile.conditions or [])}
    sensitivities = {item.lower() for item in (profile.sensitivities or [])}
    sugar_limit = float(profile.daily_sugar_limit_g or DEFAULT_DAILY_LIMITS["sugar_g"])
    return conditions, sensitivities, sugar_limit


def _scale_nutrients(base_nutrients: dict[str, float], serving_ml: float, quantity_ml: float) -> dict[str, float]:
    scale = 1 if serving_ml <= 0 else quantity_ml / serving_ml
    return {key: round(float(value) * scale, 2) for key, value in base_nutrients.items()}


def _portion_guidance(sugar: float, caffeine: float, quantity_ml: float) -> str:
    if sugar >= 25 or caffeine >= 30:
        return f"Keep it under {min(150, int(quantity_ml))} ml and avoid a second serving today."
    if sugar >= 12:
        return f"Limit to about {min(200, int(quantity_ml))} ml and pair it with a meal, not on an empty stomach."
    return f"A single serving of around {int(quantity_ml)} ml is acceptable only if the rest of the day stays balanced."


def _better_alternatives(tags: set[str], conditions: set[str]) -> list[str]:
    alternatives = [
        "Plain water",
        "Unsweetened coconut water",
        "Buttermilk",
        "Homemade lemon water without sugar",
    ]
    if "diabetes" in conditions or "pcos" in conditions or "fatty liver" in conditions:
        alternatives = [
            "Plain water",
            "Unsweetened buttermilk",
            "Infused water with cucumber or mint",
            "Vegetable juice without added sugar",
        ]
    elif "acidity / gerd" in conditions or "gastritis" in conditions:
        alternatives = [
            "Plain water",
            "Tender coconut water",
            "Buttermilk",
            "Diluted non-citrus homemade juice without added sugar",
        ]
    elif "caffeinated" in tags:
        alternatives.append("Fresh fruit pieces instead of cola for an energy craving")
    return alternatives


def _compensation_plan(status: str, sugar: float, caffeine: float, acidity: float) -> list[str]:
    plan = []
    if status in {"caution", "avoid"}:
        plan.append("Pause packaged sweet drinks for the next 2 to 3 days.")
    if sugar >= 20:
        plan.append("Keep the rest of today free from dessert, sweet tea, and extra sweet beverages.")
    if caffeine >= 25:
        plan.append("Avoid more caffeinated drinks for the rest of the day.")
    if acidity >= 6:
        plan.append("Choose bland, low-acid foods and avoid taking another fizzy drink today.")
    if not plan:
        plan.append("No compensation needed beyond normal hydration and moderation.")
    return plan


def analyze_beverage(
    beverage: dict[str, Any],
    profile: Any = None,
    *,
    quantity_ml: float | None = None,
    custom_name: str | None = None,
    custom_ingredients: list[str] | None = None,
) -> dict[str, Any]:
    beverage = deepcopy(beverage)
    conditions, sensitivities, sugar_limit = _profile_conditions(profile)
    serving_ml = float(beverage.get("serving_ml") or 250)
    quantity_ml = float(quantity_ml or serving_ml)
    nutrients = _scale_nutrients(beverage.get("nutrients", {}), serving_ml, quantity_ml)
    tags = set(beverage.get("risk_tags", []))

    caution_reasons: list[str] = []
    avoid_reasons: list[str] = []
    allergy_alerts: list[str] = []
    suggestions: list[str] = []
    strengths: list[str] = []
    health_flags: list[str] = []
    penalties = 0

    sugar = nutrients.get("sugar_g", 0.0)
    sodium = nutrients.get("sodium_mg", 0.0)
    caffeine = nutrients.get("caffeine_mg", 0.0)
    calories = nutrients.get("calories", 0.0)
    acidity = nutrients.get("acidity", 0.0)

    if sugar > sugar_limit:
        avoid_reasons.append(f"Sugar load is {sugar} g, above the profile limit of {sugar_limit} g.")
        health_flags.append("Exceeds sugar limit")
        penalties += 26
    elif sugar > max(12, sugar_limit * 0.6):
        caution_reasons.append(f"Sugar load is {sugar} g, so portion control is important.")
        health_flags.append("High sugar load")
        penalties += 14

    if caffeine >= 30:
        caution_reasons.append(f"Caffeine is {caffeine} mg, which may disturb blood pressure or acidity.")
        health_flags.append("High caffeine")
        penalties += 10

    if acidity >= 8:
        caution_reasons.append("This drink is highly acidic and can worsen reflux or gastritis.")
        health_flags.append("High acidity")
        penalties += 10
    elif acidity >= 6:
        caution_reasons.append("Mild acidity means it should not be taken too frequently on an empty stomach.")
        penalties += 5

    if sodium >= 60:
        caution_reasons.append(f"Sodium is {sodium} mg, which is not ideal for frequent intake.")
        health_flags.append("High sodium")
        penalties += 7

    if "carbonated" in tags:
        caution_reasons.append("Carbonation can cause bloating and reflux in sensitive users.")
        health_flags.append("Carbonated")
        penalties += 5

    if "preservative" in tags:
        caution_reasons.append("Processed preservatives make this a poor choice for daily hydration.")
        health_flags.append("Ultra-processed")
        penalties += 5

    if "diabetes" in conditions and sugar >= 10:
        avoid_reasons.append("Diabetes profile detected: this beverage has enough sugar to cause a blood glucose spike.")
        penalties += 30
    if "high bp" in conditions and (caffeine >= 20 or sodium >= 45):
        caution_reasons.append("High BP profile detected: caffeine or sodium may push blood pressure upward.")
        penalties += 12
    if "low bp" in conditions and sugar == 0 and "diet_soft_drink" in beverage.get("category", ""):
        caution_reasons.append("Low BP profile detected: sugar-free soda does not help support energy or hydration quality.")
        penalties += 6
    if "thyroid" in conditions and ("artificial_sweetener" in tags or caffeine >= 25):
        caution_reasons.append("Thyroid profile detected: use caution with processed stimulants and artificial sweeteners.")
        penalties += 10
    if "pcos" in conditions and sugar >= 12:
        avoid_reasons.append("PCOS profile detected: high sugar drinks can worsen insulin resistance.")
        penalties += 20
    if "obesity" in conditions and (sugar >= 15 or calories >= 120):
        avoid_reasons.append("Obesity management profile detected: this drink is too calorie-dense for regular intake.")
        penalties += 18
    if "kidney disease" in conditions and ("preservative" in tags or sodium >= 40):
        caution_reasons.append("Kidney disease profile detected: sodium and additives should stay limited.")
        penalties += 15
    if "fatty liver" in conditions and sugar >= 12:
        avoid_reasons.append("Fatty liver profile detected: added sugar and fructose are not recommended.")
        penalties += 20
    if "high cholesterol" in conditions and sugar >= 18:
        caution_reasons.append("High cholesterol profile detected: frequent sugary beverages can worsen metabolic risk.")
        penalties += 12
    if "heart disease" in conditions and (sugar >= 18 or caffeine >= 25):
        caution_reasons.append("Heart disease profile detected: stimulants and sugary soft drinks should stay minimal.")
        penalties += 16
    if ("acidity / gerd" in conditions or "gastritis" in conditions) and ("carbonated" in tags or acidity >= 6 or caffeine >= 1):
        avoid_reasons.append("Acidity / gastritis profile detected: carbonation, acids, or caffeine can trigger symptoms.")
        penalties += 24
    if "ibs" in conditions and ("carbonated" in tags or acidity >= 6):
        caution_reasons.append("IBS profile detected: fizzy or acidic drinks may cause bloating or discomfort.")
        penalties += 10
    if "pregnancy" in conditions and (caffeine >= 25 or "artificial_sweetener" in tags):
        caution_reasons.append("Pregnancy profile detected: caffeine and artificial sweeteners should be limited.")
        penalties += 14

    if "mango allergy" in sensitivities and "mango" in tags:
        allergy_alerts.append("Mango sensitivity detected: this product contains mango ingredients.")
        health_flags.append("Allergy trigger")
        penalties += 35
    if "citrus allergy" in sensitivities and "citrus" in tags:
        allergy_alerts.append("Citrus sensitivity detected: this product includes lemon, lime, or orange flavour.")
        health_flags.append("Allergy trigger")
        penalties += 35
    if "caffeine sensitivity" in sensitivities and caffeine >= 1:
        allergy_alerts.append("Caffeine sensitivity detected: this beverage contains caffeine.")
        health_flags.append("Sensitivity trigger")
        penalties += 28
    if "artificial sweetener sensitivity" in sensitivities and "artificial_sweetener" in tags:
        allergy_alerts.append("Artificial sweetener sensitivity detected: choose a natural alternative.")
        health_flags.append("Sensitivity trigger")
        penalties += 28
    if "preservative sensitivity" in sensitivities and "preservative" in tags:
        allergy_alerts.append("Preservative sensitivity detected: this beverage is processed and additive-heavy.")
        health_flags.append("Sensitivity trigger")
        penalties += 20

    if sugar <= 6:
        strengths.append("Lower sugar than regular soft drinks.")
    if caffeine == 0:
        strengths.append("No caffeine in this serving.")
    if beverage.get("category") == "fruit_drink":
        strengths.append("Fruit-based flavour may feel more acceptable than cola, but sugar still matters.")
    if sugar <= 5 and "artificial_sweetener" not in tags and "preservative" not in tags:
        strengths.append("Relatively lighter metabolic load than most packaged soft drinks.")

    score = max(5, 100 - penalties)
    if allergy_alerts or len(avoid_reasons) >= 2 or penalties >= 60:
        status = "avoid"
    elif avoid_reasons or penalties >= 35:
        status = "caution"
    else:
        status = "safer"

    traffic_light = {"safer": "green", "caution": "amber", "avoid": "red"}[status]
    frequency_limit = "1 to 2 times per week at most"
    if status == "avoid":
        frequency_limit = "best avoided"
    elif sugar <= 6 and caffeine == 0 and "preservative" not in tags:
        frequency_limit = "occasionally, while staying inside the daily sugar limit"

    if status == "avoid":
        suggestions.append("Avoid this drink for now and replace it with water, buttermilk, unsweetened coconut water, or homemade low-sugar juice.")
    elif status == "caution":
        suggestions.append("Limit to a small serving and avoid taking it on consecutive days.")
    else:
        suggestions.append("If you still choose this drink, keep the rest of the day low in added sugar.")

    if sugar > 20:
        suggestions.append("Drink extra water and avoid another sweetened beverage today.")
    if "carbonated" in tags:
        suggestions.append("Do not take it on an empty stomach if you have bloating or reflux.")
    if "artificial_sweetener" in tags:
        suggestions.append("Sugar-free does not mean healthy for unlimited use; treat it as an occasional option.")

    can_consume = beverage.get("good_for", []).copy()
    should_avoid = beverage.get("avoid_for", []).copy()
    if status == "safer":
        can_consume.append("Users without the selected health risks, when keeping portions moderate.")
    else:
        should_avoid.append("Anyone already near their daily sugar or acidity limit today.")

    analysis = {
        "beverage_name": custom_name or beverage.get("display_name"),
        "category": beverage.get("category"),
        "quantity_ml": quantity_ml,
        "ingredients": custom_ingredients or beverage.get("ingredients", []),
        "nutrients": nutrients,
        "status": status,
        "score": score,
        "traffic_light": traffic_light,
        "health_flags": list(dict.fromkeys(health_flags)),
        "strengths": list(dict.fromkeys(strengths)),
        "caution_reasons": list(dict.fromkeys(caution_reasons)),
        "avoid_reasons": list(dict.fromkeys(avoid_reasons)),
        "allergy_alerts": list(dict.fromkeys(allergy_alerts)),
        "suggestions": list(dict.fromkeys(suggestions)),
        "can_consume": list(dict.fromkeys(can_consume)),
        "should_avoid": list(dict.fromkeys(should_avoid)),
        "portion_guidance": _portion_guidance(sugar, caffeine, quantity_ml),
        "frequency_limit": frequency_limit,
        "better_alternatives": _better_alternatives(tags, conditions),
        "compensation_plan": _compensation_plan(status, sugar, caffeine, acidity),
    }
    return analysis


def analyze_custom_entry(payload: dict[str, Any], profile: Any = None) -> dict[str, Any]:
    beverage = {
        "display_name": payload["beverage_name"],
        "category": "custom_entry",
        "serving_ml": float(payload.get("quantity_ml") or 250),
        "nutrients": {
            "calories": float(payload.get("calories") or 0),
            "sugar_g": float(payload.get("sugar_g") or 0),
            "sodium_mg": float(payload.get("sodium_mg") or 0),
            "caffeine_mg": float(payload.get("caffeine_mg") or 0),
            "acidity": float(payload.get("acidity") or 0),
        },
        "ingredients": [item.strip() for item in (payload.get("ingredients_text") or "").split(",") if item.strip()],
        "risk_tags": [],
        "good_for": ["Custom drink entries with low sugar and no trigger ingredients may fit moderate use."],
        "avoid_for": [],
    }
    ingredients_lower = " ".join(beverage["ingredients"]).lower()
    if "mango" in ingredients_lower:
        beverage["risk_tags"].append("mango")
    if any(item in ingredients_lower for item in ["orange", "lime", "lemon", "citrus"]):
        beverage["risk_tags"].append("citrus")
    if any(item in ingredients_lower for item in ["sweetener", "aspartame", "sucralose", "acesulfame"]):
        beverage["risk_tags"].append("artificial_sweetener")
    if any(item in ingredients_lower for item in ["benzoate", "sulfite", "preservative"]):
        beverage["risk_tags"].append("preservative")
    if float(payload.get("caffeine_mg") or 0) > 0:
        beverage["risk_tags"].append("caffeinated")
    if float(payload.get("sugar_g") or 0) > 12:
        beverage["risk_tags"].append("high_sugar")
    if float(payload.get("acidity") or 0) > 5:
        beverage["risk_tags"].append("carbonated")

    return analyze_beverage(
        beverage,
        profile,
        quantity_ml=float(payload.get("quantity_ml") or 250),
        custom_name=payload["beverage_name"],
        custom_ingredients=beverage["ingredients"],
    )
