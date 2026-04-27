from __future__ import annotations

from datetime import datetime

from flask_login import UserMixin

from app.extensions import db


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    recovery_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    last_login_at = db.Column(db.DateTime)

    profile = db.relationship("HealthProfile", back_populates="user", uselist=False, cascade="all, delete-orphan")
    scans = db.relationship("ScanRecord", back_populates="user", cascade="all, delete-orphan")
    tracker_entries = db.relationship("TrackerEntry", back_populates="user", cascade="all, delete-orphan")
    reset_audits = db.relationship("PasswordResetAudit", back_populates="user", cascade="all, delete-orphan")


class HealthProfile(db.Model):
    __tablename__ = "health_profiles"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, unique=True)
    conditions = db.Column(db.JSON, nullable=False, default=list)
    sensitivities = db.Column(db.JSON, nullable=False, default=list)
    notes = db.Column(db.Text)
    daily_sugar_limit_g = db.Column(db.Float, nullable=False, default=25.0)
    profile_completed = db.Column(db.Boolean, nullable=False, default=False)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = db.relationship("User", back_populates="profile")


class ScanRecord(db.Model):
    __tablename__ = "scan_records"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    source_type = db.Column(db.String(20), nullable=False)
    image_path = db.Column(db.String(255))
    annotated_path = db.Column(db.String(255))
    detected_label = db.Column(db.String(80))
    detected_name = db.Column(db.String(120))
    confidence = db.Column(db.Float)
    detection_status = db.Column(db.String(20), nullable=False, default="not_detected")
    nutrition_snapshot = db.Column(db.JSON, nullable=False, default=dict)
    analysis_summary = db.Column(db.JSON, nullable=False, default=dict)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, index=True)

    user = db.relationship("User", back_populates="scans")


class TrackerEntry(db.Model):
    __tablename__ = "tracker_entries"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    entry_date = db.Column(db.Date, nullable=False, index=True)
    beverage_key = db.Column(db.String(80))
    beverage_name = db.Column(db.String(120), nullable=False)
    ingredients_text = db.Column(db.Text)
    sugar_g = db.Column(db.Float, nullable=False, default=0.0)
    sodium_mg = db.Column(db.Float, nullable=False, default=0.0)
    caffeine_mg = db.Column(db.Float, nullable=False, default=0.0)
    calories = db.Column(db.Float, nullable=False, default=0.0)
    acidity = db.Column(db.Float, nullable=False, default=0.0)
    quantity_ml = db.Column(db.Float, nullable=False, default=250.0)
    notes = db.Column(db.Text)
    analysis_summary = db.Column(db.JSON, nullable=False, default=dict)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    user = db.relationship("User", back_populates="tracker_entries")


class PasswordResetAudit(db.Model):
    __tablename__ = "password_reset_audits"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    reset_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    user = db.relationship("User", back_populates="reset_audits")
