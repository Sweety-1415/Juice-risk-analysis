from __future__ import annotations

from collections import Counter, defaultdict
from datetime import date, timedelta
from statistics import mean
from typing import Any

from app.data import DEFAULT_DAILY_LIMITS


def scan_insights(scan_records: list[Any]) -> dict[str, Any]:
    total = len(scan_records)
    successful = [record for record in scan_records if record.detection_status == "detected"]
    failed = total - len(successful)
    brand_counts = Counter(record.detected_name for record in successful if record.detected_name)
    avg_confidence = round(mean(record.confidence for record in successful if record.confidence is not None), 2) if successful else 0

    brand_confidence_sums = defaultdict(float)
    for record in successful:
        if record.detected_name and record.confidence is not None:
            brand_confidence_sums[record.detected_name] += record.confidence
    
    ml_evaluation = []
    for brand, count in brand_counts.items():
        ml_evaluation.append({
            "label": brand,
            "count": count,
            "avg_conf": round(brand_confidence_sums[brand] / count, 2)
        })
    ml_evaluation.sort(key=lambda x: (x["count"], x["avg_conf"]), reverse=True)

    by_day = defaultdict(int)
    risk_counter = Counter()
    for record in scan_records:
        by_day[record.created_at.date().isoformat()] += 1
        status = (record.analysis_summary or {}).get("status", "unknown")
        risk_counter[status] += 1

    recent_days = []
    start = date.today() - timedelta(days=6)
    for offset in range(7):
        current = start + timedelta(days=offset)
        recent_days.append({"label": current.strftime("%d %b"), "value": by_day.get(current.isoformat(), 0)})

    source_counter = Counter(record.source_type for record in scan_records if record.source_type)
    source_distribution = [{"label": s.title(), "value": c} for s, c in source_counter.items()]

    return {
        "total": total,
        "successful": len(successful),
        "failed": failed,
        "avg_confidence": avg_confidence,
        "top_brand": brand_counts.most_common(1)[0][0] if brand_counts else "No scans yet",
        "brand_counts": [{"label": label, "value": count} for label, count in brand_counts.most_common(6)],
        "recent_days": recent_days,
        "risk_breakdown": [
            {"label": "Safer", "value": risk_counter.get("safer", 0)},
            {"label": "Caution", "value": risk_counter.get("caution", 0)},
            {"label": "Avoid", "value": risk_counter.get("avoid", 0)},
        ],
        "ml_evaluation": ml_evaluation,
        "source_distribution": source_distribution,
    }


def tracker_insights(entries: list[Any], sugar_limit: float | None = None) -> dict[str, Any]:
    sugar_limit = sugar_limit or DEFAULT_DAILY_LIMITS["sugar_g"]
    today = date.today()
    start = today - timedelta(days=6)
    day_buckets: dict[str, dict[str, float]] = defaultdict(lambda: {"sugar": 0.0, "caffeine": 0.0, "count": 0.0, "score": 100.0})
    alerts: list[str] = []

    for entry in entries:
        day_key = entry.entry_date.isoformat()
        bucket = day_buckets[day_key]
        bucket["sugar"] += float(entry.sugar_g or 0)
        bucket["caffeine"] += float(entry.caffeine_mg or 0)
        bucket["count"] += 1
        if (entry.analysis_summary or {}).get("status") == "avoid":
            bucket["score"] -= 20
        elif (entry.analysis_summary or {}).get("status") == "caution":
            bucket["score"] -= 10

    sugar_chart = []
    health_scores = []
    risky_days = 0
    for offset in range(7):
        current = start + timedelta(days=offset)
        bucket = day_buckets.get(current.isoformat(), {"sugar": 0.0, "caffeine": 0.0, "count": 0.0, "score": 100.0})
        if bucket["sugar"] > sugar_limit:
            risky_days += 1
        sugar_chart.append({"label": current.strftime("%d %b"), "value": round(bucket["sugar"], 2)})
        health_scores.append({"label": current.strftime("%d %b"), "value": max(10, round(bucket["score"], 2))})

    total_sugar = round(sum(float(entry.sugar_g or 0) for entry in entries), 2)
    total_caffeine = round(sum(float(entry.caffeine_mg or 0) for entry in entries), 2)

    tracked_counter = Counter(entry.beverage_name for entry in entries if entry.beverage_name)
    top_tracked = [{"label": label, "value": count} for label, count in tracked_counter.most_common(4)]

    if risky_days >= 3:
        alerts.append("Your sugar intake exceeded the daily limit on several recent days. Take a break from sweet drinks.")
    if total_caffeine > 400:
        alerts.append("Caffeine intake is building up. Reduce cola or diet soda for the next few days.")
    if entries and mean(float(entry.sugar_g or 0) for entry in entries) > sugar_limit * 0.75:
        alerts.append("Average sugar per logged drink is high. Try lower-sugar options or smaller quantities.")

    if day_buckets[today.isoformat()]["count"] > 2:
        alerts.append("CRITICAL: You have consumed more than 2 beverages today. This significantly increases your sugar levels and health risks!")

    if day_buckets[today.isoformat()]["sugar"] > sugar_limit:
        alerts.append(f"CRITICAL: You have exceeded your daily sugar limit of {sugar_limit}g today! Stop consuming sugary beverages immediately.")

    return {
        "entries": len(entries),
        "total_sugar": total_sugar,
        "total_caffeine": total_caffeine,
        "risky_days": risky_days,
        "sugar_limit": sugar_limit,
        "sugar_chart": sugar_chart,
        "health_scores": health_scores,
        "top_tracked": top_tracked,
        "alerts": alerts,
    }


def build_dashboard_payload(scan_records: list[Any], tracker_entries: list[Any], sugar_limit: float | None = None) -> dict[str, Any]:
    scan_data = scan_insights(scan_records)
    tracker_data = tracker_insights(tracker_entries, sugar_limit)
    combined_alerts = tracker_data["alerts"][:]

    if scan_data["failed"] >= 3:
        combined_alerts.append("Several scans were not detected. Add brighter images or use the webcam close to the bottle label.")
    if any(item["value"] >= 3 for item in scan_data["risk_breakdown"][1:]):
        combined_alerts.append("Multiple risky beverages were scanned recently. Review the scan history before the next purchase.")

    return {
        "scan": scan_data,
        "tracker": tracker_data,
        "alerts": combined_alerts,
    }
