import os

from flask import Blueprint, current_app, jsonify, request
from flask_jwt_extended import create_access_token, get_jwt_identity, jwt_required
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from api.extensions import db
from api.models import Tenant, User
from api.services.email import send_email

RESET_TOKEN_MAX_AGE = 3600  # seconds

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/register", methods=["POST"])
def register():
    data = request.get_json(silent=True) or {}
    company_name = (data.get("company_name") or "").strip()
    full_name = (data.get("full_name") or "").strip()
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    if not company_name or not full_name or not email or not password:
        return jsonify({"message": "company_name, full_name, email and password are required"}), 400
    if len(password) < 8:
        return jsonify({"message": "Password must be at least 8 characters"}), 400
    if db.session.scalar(db.select(User).filter_by(email=email)):
        return jsonify({"message": "Email already registered"}), 409

    tenant = Tenant(name=company_name)
    user = User(tenant=tenant, email=email, full_name=full_name, role="owner")
    user.set_password(password)
    db.session.add(user)
    db.session.commit()

    token = create_access_token(identity=str(user.id))
    return jsonify({"user": user.serialize(), "token": token}), 201


@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    user = db.session.scalar(db.select(User).filter_by(email=email))
    if user is None or not user.is_active or not user.check_password(password):
        return jsonify({"message": "Invalid email or password"}), 401

    token = create_access_token(identity=str(user.id))
    return jsonify({"user": user.serialize(), "token": token}), 200


@auth_bp.route("/me", methods=["GET"])
@jwt_required()
def me():
    user = db.session.get(User, int(get_jwt_identity()))
    return jsonify(user.serialize()), 200


def _reset_serializer():
    return URLSafeTimedSerializer(current_app.config["SECRET_KEY"], salt="password-reset")


@auth_bp.route("/forgot-password", methods=["POST"])
def forgot_password():
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()

    user = db.session.scalar(db.select(User).filter_by(email=email))
    if user is not None:
        token = _reset_serializer().dumps(user.id)
        frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000")
        link = f"{frontend_url}/reset-password?token={token}"
        send_email(
            to=user.email,
            subject="Reset your InvoiceOps password",
            html=f"<p>Hi {user.full_name},</p><p>Click to reset your password (valid for 1 hour):</p><p><a href='{link}'>{link}</a></p>",
        )

    return jsonify({"message": "If that email exists, a reset link has been sent"}), 200


@auth_bp.route("/reset-password", methods=["POST"])
def reset_password():
    data = request.get_json(silent=True) or {}
    token = data.get("token") or ""
    password = data.get("password") or ""

    if len(password) < 8:
        return jsonify({"message": "Password must be at least 8 characters"}), 400
    try:
        user_id = _reset_serializer().loads(token, max_age=RESET_TOKEN_MAX_AGE)
    except (BadSignature, SignatureExpired):
        return jsonify({"message": "Invalid or expired token"}), 400

    user = db.session.get(User, user_id)
    if user is None:
        return jsonify({"message": "Invalid or expired token"}), 400

    user.set_password(password)
    db.session.commit()
    return jsonify({"message": "Password updated"}), 200