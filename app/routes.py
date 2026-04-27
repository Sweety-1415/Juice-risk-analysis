from __future__ import annotations

import csv
from io import StringIO
from datetime import date, datetime

from flask import Response, abort, current_app, flash, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user
from werkzeug.security import check_password_hash, generate_password_hash

from app.data import BEVERAGE_LIBRARY, HEALTH_CONDITIONS, SENSITIVITY_OPTIONS, beverage_choices
from app.extensions import db
from app.models import HealthProfile, PasswordResetAudit, ScanRecord, TrackerEntry, User
from app.services.analysis_service import analyze_beverage, analyze_custom_entry, get_beverage
from app.services.analytics_service import build_dashboard_payload, scan_insights, tracker_insights
from app.services.detection_service import detect_upload, detect_webcam, training_metrics


def register_routes(app):
    def _scan_record_or_404(record_id: int) -> ScanRecord:
        record = ScanRecord.query.filter_by(id=record_id, user_id=current_user.id).first()
        if not record:
            abort(404)
        return record

    def _tracker_entry_or_404(entry_id: int) -> TrackerEntry:
        entry = TrackerEntry.query.filter_by(id=entry_id, user_id=current_user.id).first()
        if not entry:
            abort(404)
        return entry

    def _csv_response(filename: str, rows: list[dict[str, str | int | float]]) -> Response:
        stream = StringIO()
        if rows:
            writer = csv.DictWriter(stream, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)
        else:
            stream.write("no_data\n")
        return Response(
            stream.getvalue(),
            mimetype="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )

    @app.context_processor
    def inject_globals():
        return {
            "beverage_catalog": BEVERAGE_LIBRARY,
            "catalog_choices": beverage_choices(),
        }

    # Public endpoints that do NOT require authentication
    _PUBLIC_ENDPOINTS = {"login", "register", "forgot_password", "database_error", "static", "index"}

    @app.before_request
    def require_database_and_profile():
        # Always allow static file requests
        if request.endpoint == "static":
            return None

        # If DB is not ready, only allow the database-error page
        if not current_app.config.get("DATABASE_READY", False):
            if request.endpoint not in {"database_error"}:
                return redirect(url_for("database_error"))
            return None

        # If user is NOT logged in, only allow public endpoints
        if not current_user.is_authenticated:
            if request.endpoint not in _PUBLIC_ENDPOINTS:
                flash("Please log in to access this page.", "warning")
                return redirect(url_for("login"))
            return None

        # User IS logged in — enforce health profile completion
        # Allow dashboard and other pages even without a completed profile (Skip is valid)
        exempt = {"logout", "health_profile", "settings", "api_scan", "dashboard", "scan", "scan_history",
                  "export_scan_history", "personal_tracker", "daily_tracker", "ml_evaluation",
                  "export_tracker_history", "delete_scan_history", "delete_tracker_entry",
                  "edit_tracker_entry"}
        if request.endpoint in exempt or (request.endpoint or "").startswith("static"):
            return None
        return None

    @app.route("/database-error")
    def database_error():
        return render_template("database_error.html", error=current_app.config.get("DATABASE_ERROR", "Unknown MySQL error."))

    @app.route("/")
    def index():
        if current_user.is_authenticated:
            return redirect(url_for("dashboard"))
        return redirect(url_for("login"))

    @app.route("/register", methods=["GET", "POST"])
    def register():
        if current_user.is_authenticated:
            return redirect(url_for("dashboard"))
        if request.method == "POST":
            username = request.form.get("username", "").strip()
            password = request.form.get("password", "")
            confirm_password = request.form.get("confirm_password", "")
            recovery_answer = request.form.get("recovery_answer", "").strip()

            if not username or len(username) < 3:
                flash("Username must be at least 3 characters long.", "danger")
            elif len(password) < 8:
                flash("Password must be at least 8 characters long.", "danger")
            elif password != confirm_password:
                flash("Password confirmation does not match.", "danger")
            elif not recovery_answer:
                flash("Recovery keyword is required for the forgot-password flow.", "danger")
            elif User.query.filter_by(username=username).first():
                flash("That username already exists. Try another one.", "danger")
            else:
                user = User(
                    username=username,
                    password_hash=generate_password_hash(password),
                    recovery_hash=generate_password_hash(recovery_answer.lower()),
                )
                profile = HealthProfile(profile_completed=False)
                user.profile = profile
                db.session.add(user)
                db.session.commit()
                # Auto-login and redirect to health profile setup
                login_user(user)
                flash("Account created! Set up your health profile for personalised scan results.", "success")
                return redirect(url_for("health_profile"))

        return render_template("auth/register.html")

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if current_user.is_authenticated:
            return redirect(url_for("dashboard"))
        if request.method == "POST":
            username = request.form.get("username", "").strip()
            password = request.form.get("password", "")

            # Reject blank fields immediately
            if not username or not password:
                flash("Please enter both username and password.", "danger")
                return render_template("auth/login.html")

            # Look up user strictly by username in MySQL
            user = User.query.filter_by(username=username).first()

            # User not found — reject clearly
            if user is None:
                flash("No account found with that username. Please register first.", "danger")
                return render_template("auth/login.html")

            # Password does not match stored hash — reject
            if not check_password_hash(user.password_hash, password):
                flash("Incorrect password. Please try again.", "danger")
                return render_template("auth/login.html")

            # Both match — log the user in
            user.last_login_at = datetime.utcnow()
            db.session.commit()
            login_user(user, remember=False)
            flash(f"Welcome back, {user.username}!", "success")
            if not user.profile or not user.profile.profile_completed:
                return redirect(url_for("health_profile"))
            return redirect(url_for("dashboard"))

        return render_template("auth/login.html")

    @app.route("/forgot-password", methods=["GET", "POST"])
    def forgot_password():
        if current_user.is_authenticated:
            return redirect(url_for("dashboard"))
        if request.method == "POST":
            username = request.form.get("username", "").strip()
            recovery_answer = request.form.get("recovery_answer", "").strip().lower()
            new_password = request.form.get("new_password", "")
            confirm_password = request.form.get("confirm_password", "")
            user = User.query.filter_by(username=username).first()

            if not user:
                flash("No user found with that username.", "danger")
            elif not check_password_hash(user.recovery_hash, recovery_answer):
                flash("Recovery keyword does not match.", "danger")
            elif len(new_password) < 8:
                flash("New password must be at least 8 characters long.", "danger")
            elif new_password != confirm_password:
                flash("Password confirmation does not match.", "danger")
            else:
                user.password_hash = generate_password_hash(new_password)
                db.session.add(PasswordResetAudit(user=user))
                db.session.commit()
                flash("Password reset completed. Please log in again.", "success")
                return redirect(url_for("login"))

        return render_template("auth/forgot_password.html")

    @app.route("/logout")
    @login_required
    def logout():
        logout_user()
        flash("You have been logged out.", "info")
        return redirect(url_for("login"))

    @app.route("/health-profile", methods=["GET", "POST"])
    @login_required
    def health_profile():
        profile = current_user.profile or HealthProfile(user=current_user)
        if request.method == "POST":
            profile.conditions = request.form.getlist("conditions")
            profile.sensitivities = request.form.getlist("sensitivities")
            profile.notes = request.form.get("notes", "").strip()
            try:
                profile.daily_sugar_limit_g = float(request.form.get("daily_sugar_limit_g") or 25)
            except ValueError:
                profile.daily_sugar_limit_g = 25
            profile.profile_completed = True
            db.session.add(profile)
            db.session.commit()
            flash("Health profile saved for future scan analysis.", "success")
            return redirect(url_for("dashboard"))

        return render_template(
            "health_profile.html",
            conditions=HEALTH_CONDITIONS,
            sensitivities=SENSITIVITY_OPTIONS,
            profile=profile,
        )

    @app.route("/dashboard")
    @login_required
    def dashboard():
        scan_records = ScanRecord.query.filter_by(user_id=current_user.id).order_by(ScanRecord.created_at.desc()).all()
        tracker_entries = TrackerEntry.query.filter_by(user_id=current_user.id).order_by(TrackerEntry.entry_date.desc()).all()
        payload = build_dashboard_payload(scan_records, tracker_entries, current_user.profile.daily_sugar_limit_g if current_user.profile else None)
        recent_scans = scan_records[:5]
        recent_tracker = tracker_entries[:5]
        return render_template("dashboard.html", payload=payload, recent_scans=recent_scans, recent_tracker=recent_tracker)

    @app.route("/scan")
    @login_required
    def scan():
        recent_scans = ScanRecord.query.filter_by(user_id=current_user.id).order_by(ScanRecord.created_at.desc()).limit(6).all()
        return render_template("scan.html", recent_scans=recent_scans)

    @app.route("/api/scan", methods=["POST"])
    @login_required
    def api_scan():
        try:
            if "image" in request.files and request.files["image"].filename:
                detection = detect_upload(request.files["image"])
                source_type = "upload"
            else:
                payload = request.get_json(silent=True) or {}
                if not payload.get("image"):
                    return jsonify({"ok": False, "message": "Please upload an image or capture one from the webcam."}), 400
                detection = detect_webcam(payload["image"])
                source_type = "webcam"
        except Exception as exc:
            return jsonify({"ok": False, "message": f"Scan failed: {exc}"}), 400

        beverage = get_beverage(detection.get("label"))
        if detection["status"] == "detected" and beverage:
            analysis = analyze_beverage(beverage, current_user.profile)
            detected_name = beverage["display_name"]
        else:
            analysis = {
                "beverage_name": "Unknown",
                "status": "avoid",
                "score": 0,
                "strengths": [],
                "caution_reasons": [],
                "avoid_reasons": ["No product was detected. Use a clearer image with the full bottle visible."],
                "allergy_alerts": [],
                "suggestions": ["Try scanning again under better lighting and keep the label fully in frame."],
                "can_consume": [],
                "should_avoid": ["Unverified product intake should not be trusted for health analysis."],
                "ingredients": [],
                "nutrients": {},
                "quantity_ml": 0,
            }
            detected_name = None

        record = ScanRecord(
            user_id=current_user.id,
            source_type=source_type,
            image_path=detection.get("image_path"),
            annotated_path=detection.get("annotated_path"),
            detected_label=detection.get("label"),
            detected_name=detected_name,
            confidence=detection.get("confidence"),
            detection_status=detection["status"],
            nutrition_snapshot=analysis.get("nutrients", {}),
            analysis_summary=analysis,
        )
        db.session.add(record)
        db.session.commit()

        image_url = url_for("static", filename=record.image_path) if record.image_path else None
        annotated_url = url_for("static", filename=record.annotated_path) if record.annotated_path else None
        return jsonify(
            {
                "ok": True,
                "record_id": record.id,
                "detected_name": record.detected_name,
                "confidence": record.confidence,
                "status": record.detection_status,
                "image_url": image_url,
                "annotated_url": annotated_url,
                "analysis": analysis,
            }
        )

    @app.route("/scan-history")
    @login_required
    def scan_history():
        scan_records = ScanRecord.query.filter_by(user_id=current_user.id).order_by(ScanRecord.created_at.desc()).all()
        return render_template("scan_history.html", scan_records=scan_records)

    @app.route("/scan-history/export")
    @login_required
    def export_scan_history():
        scan_records = ScanRecord.query.filter_by(user_id=current_user.id).order_by(ScanRecord.created_at.desc()).all()
        rows = []
        for record in scan_records:
            analysis = record.analysis_summary or {}
            nutrients = analysis.get("nutrients", {})
            rows.append(
                {
                    "record_id": record.id,
                    "created_at": record.created_at.isoformat(sep=" ", timespec="seconds"),
                    "source_type": record.source_type,
                    "detected_name": record.detected_name or "Not detected",
                    "confidence": record.confidence or 0,
                    "status": analysis.get("status", record.detection_status),
                    "score": analysis.get("score", 0),
                    "sugar_g": nutrients.get("sugar_g", 0),
                    "sodium_mg": nutrients.get("sodium_mg", 0),
                    "caffeine_mg": nutrients.get("caffeine_mg", 0),
                    "top_reason": "; ".join((analysis.get("avoid_reasons") or analysis.get("caution_reasons") or [])[:2]),
                    "suggestions": "; ".join((analysis.get("suggestions") or [])[:3]),
                }
            )
        return _csv_response("nutrilens_scan_history.csv", rows)

    @app.route("/scan-history/<int:record_id>/delete", methods=["POST"])
    @login_required
    def delete_scan_history(record_id: int):
        record = _scan_record_or_404(record_id)
        db.session.delete(record)
        db.session.commit()
        flash("Scan history item deleted.", "success")
        return redirect(url_for("scan_history"))

    @app.route("/personal-tracker", methods=["GET", "POST"])
    @login_required
    def personal_tracker():
        if request.method == "POST":
            entry_date = request.form.get("entry_date") or date.today().isoformat()
            beverage_key = request.form.get("beverage_key") or None
            quantity_ml = float(request.form.get("quantity_ml") or 250)
            notes = request.form.get("notes", "").strip()

            if beverage_key and beverage_key in BEVERAGE_LIBRARY:
                beverage = get_beverage(beverage_key)
                analysis = analyze_beverage(beverage, current_user.profile, quantity_ml=quantity_ml)
                nutrients = analysis["nutrients"]
                beverage_name = beverage["display_name"]
                ingredients_text = ", ".join(beverage.get("ingredients", []))
            else:
                payload = {
                    "beverage_name": request.form.get("custom_name", "").strip(),
                    "ingredients_text": request.form.get("ingredients_text", "").strip(),
                    "sugar_g": request.form.get("sugar_g") or 0,
                    "sodium_mg": request.form.get("sodium_mg") or 0,
                    "caffeine_mg": request.form.get("caffeine_mg") or 0,
                    "calories": request.form.get("calories") or 0,
                    "acidity": request.form.get("acidity") or 0,
                    "quantity_ml": quantity_ml,
                }
                if not payload["beverage_name"]:
                    flash("Select a known beverage or enter a custom beverage name.", "danger")
                    return redirect(url_for("personal_tracker"))
                analysis = analyze_custom_entry(payload, current_user.profile)
                nutrients = analysis["nutrients"]
                beverage_name = payload["beverage_name"]
                ingredients_text = payload["ingredients_text"]

            entry = TrackerEntry(
                user_id=current_user.id,
                entry_date=date.fromisoformat(entry_date),
                beverage_key=beverage_key,
                beverage_name=beverage_name,
                ingredients_text=ingredients_text,
                sugar_g=nutrients.get("sugar_g", 0),
                sodium_mg=nutrients.get("sodium_mg", 0),
                caffeine_mg=nutrients.get("caffeine_mg", 0),
                calories=nutrients.get("calories", 0),
                acidity=nutrients.get("acidity", 0),
                quantity_ml=quantity_ml,
                notes=notes,
                analysis_summary=analysis,
            )
            db.session.add(entry)
            db.session.commit()
            flash("Tracker entry saved to MySQL.", "success")
            return redirect(url_for("personal_tracker"))

        entries = TrackerEntry.query.filter_by(user_id=current_user.id).order_by(TrackerEntry.entry_date.desc(), TrackerEntry.id.desc()).limit(20).all()
        return render_template("personal_tracker.html", entries=entries, today=date.today().isoformat())

    @app.route("/personal-tracker/export")
    @login_required
    def export_tracker_history():
        entries = TrackerEntry.query.filter_by(user_id=current_user.id).order_by(TrackerEntry.entry_date.desc(), TrackerEntry.id.desc()).all()
        rows = []
        for entry in entries:
            analysis = entry.analysis_summary or {}
            rows.append(
                {
                    "entry_id": entry.id,
                    "entry_date": entry.entry_date.isoformat(),
                    "beverage_name": entry.beverage_name,
                    "quantity_ml": entry.quantity_ml,
                    "sugar_g": entry.sugar_g,
                    "sodium_mg": entry.sodium_mg,
                    "caffeine_mg": entry.caffeine_mg,
                    "calories": entry.calories,
                    "status": analysis.get("status", ""),
                    "score": analysis.get("score", 0),
                    "portion_guidance": analysis.get("portion_guidance", ""),
                    "frequency_limit": analysis.get("frequency_limit", ""),
                    "notes": entry.notes or "",
                }
            )
        return _csv_response("nutrilens_tracker_history.csv", rows)

    @app.route("/personal-tracker/<int:entry_id>/edit", methods=["GET", "POST"])
    @login_required
    def edit_tracker_entry(entry_id: int):
        entry = _tracker_entry_or_404(entry_id)
        if request.method == "POST":
            entry_date = request.form.get("entry_date") or entry.entry_date.isoformat()
            beverage_key = request.form.get("beverage_key") or None
            quantity_ml = float(request.form.get("quantity_ml") or 250)
            notes = request.form.get("notes", "").strip()

            if beverage_key and beverage_key in BEVERAGE_LIBRARY:
                beverage = get_beverage(beverage_key)
                analysis = analyze_beverage(beverage, current_user.profile, quantity_ml=quantity_ml)
                nutrients = analysis["nutrients"]
                beverage_name = beverage["display_name"]
                ingredients_text = ", ".join(beverage.get("ingredients", []))
            else:
                payload = {
                    "beverage_name": request.form.get("custom_name", "").strip() or entry.beverage_name,
                    "ingredients_text": request.form.get("ingredients_text", "").strip(),
                    "sugar_g": request.form.get("sugar_g") or 0,
                    "sodium_mg": request.form.get("sodium_mg") or 0,
                    "caffeine_mg": request.form.get("caffeine_mg") or 0,
                    "calories": request.form.get("calories") or 0,
                    "acidity": request.form.get("acidity") or 0,
                    "quantity_ml": quantity_ml,
                }
                analysis = analyze_custom_entry(payload, current_user.profile)
                nutrients = analysis["nutrients"]
                beverage_name = payload["beverage_name"]
                ingredients_text = payload["ingredients_text"]

            entry.entry_date = date.fromisoformat(entry_date)
            entry.beverage_key = beverage_key
            entry.beverage_name = beverage_name
            entry.ingredients_text = ingredients_text
            entry.sugar_g = nutrients.get("sugar_g", 0)
            entry.sodium_mg = nutrients.get("sodium_mg", 0)
            entry.caffeine_mg = nutrients.get("caffeine_mg", 0)
            entry.calories = nutrients.get("calories", 0)
            entry.acidity = nutrients.get("acidity", 0)
            entry.quantity_ml = quantity_ml
            entry.notes = notes
            entry.analysis_summary = analysis
            db.session.commit()
            flash("Tracker entry updated.", "success")
            return redirect(url_for("personal_tracker"))

        custom_mode = not (entry.beverage_key and entry.beverage_key in BEVERAGE_LIBRARY)
        return render_template("edit_tracker_entry.html", entry=entry, custom_mode=custom_mode)

    @app.route("/personal-tracker/<int:entry_id>/delete", methods=["POST"])
    @login_required
    def delete_tracker_entry(entry_id: int):
        entry = _tracker_entry_or_404(entry_id)
        db.session.delete(entry)
        db.session.commit()
        flash("Tracker entry deleted.", "success")
        return redirect(url_for("personal_tracker"))

    @app.route("/daily-tracker")
    @login_required
    def daily_tracker():
        entries = TrackerEntry.query.filter_by(user_id=current_user.id).order_by(TrackerEntry.entry_date.desc()).all()
        insights = tracker_insights(entries, current_user.profile.daily_sugar_limit_g if current_user.profile else None)
        return render_template("daily_tracker.html", entries=entries[:15], insights=insights)

    @app.route("/ml-evaluation")
    @login_required
    def ml_evaluation():
        training = training_metrics()
        scans = ScanRecord.query.filter_by(user_id=current_user.id).order_by(ScanRecord.created_at.desc()).all()
        insights = scan_insights(scans)
        return render_template("ml_evaluation.html", training=training, insights=insights)

    @app.route("/settings", methods=["GET", "POST"])
    @login_required
    def settings():
        if request.method == "POST":
            action = request.form.get("action")
            if action == "profile":
                new_username = request.form.get("username", "").strip()
                if not new_username:
                    flash("Username cannot be empty.", "danger")
                elif new_username != current_user.username and User.query.filter_by(username=new_username).first():
                    flash("That username is already in use.", "danger")
                else:
                    current_user.username = new_username
                    db.session.commit()
                    flash("Profile settings updated.", "success")
            elif action == "password":
                current_password = request.form.get("current_password", "")
                new_password = request.form.get("new_password", "")
                recovery_answer = request.form.get("recovery_answer", "").strip()
                if not check_password_hash(current_user.password_hash, current_password):
                    flash("Current password is incorrect.", "danger")
                elif len(new_password) < 8:
                    flash("New password must be at least 8 characters long.", "danger")
                else:
                    current_user.password_hash = generate_password_hash(new_password)
                    if recovery_answer:
                        current_user.recovery_hash = generate_password_hash(recovery_answer.lower())
                    db.session.commit()
                    flash("Password and recovery keyword updated.", "success")
            return redirect(url_for("settings"))

        return render_template("settings.html")
