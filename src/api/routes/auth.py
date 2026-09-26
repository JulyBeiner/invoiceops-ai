from flask import Blueprint, jsonify, request
from flask_jwt_extended import create_access_token

from api.extensions import db
from api.models import Tenant, User

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
