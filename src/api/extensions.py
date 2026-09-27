from flask import jsonify
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt

db = SQLAlchemy()
migrate = Migrate()
jwt = JWTManager()
cors = CORS()
bcrypt = Bcrypt()


@jwt.unauthorized_loader
def _missing_token(reason):
    return jsonify({"message": "Missing or invalid Authorization header"}), 401


@jwt.invalid_token_loader
def _invalid_token(reason):
    return jsonify({"message": "Invalid token"}), 401


@jwt.expired_token_loader
def _expired_token(jwt_header, jwt_payload):
    return jsonify({"message": "Token has expired"}), 401
