"""
Application factory: builds and configures the Flask app.
"""
import os

from flask import Flask, jsonify, send_from_directory

from api.admin import setup_admin
from api.commands import setup_commands
from api.config import config_by_name
from api.extensions import bcrypt, cors, db, jwt, migrate
from api.routes import api, auth_bp
from api.utils import APIException, generate_sitemap

STATIC_DIR = os.path.join(os.path.dirname(
    os.path.realpath(__file__)), "../dist/")


def _default_config_name():
    return "development" if os.getenv("FLASK_DEBUG") == "1" else "production"


def create_app(config_name=None):
    config_name = config_name or os.getenv("APP_ENV") or _default_config_name()

    app = Flask(__name__)
    app.url_map.strict_slashes = False
    app.config.from_object(config_by_name[config_name])

    if not app.config.get("SQLALCHEMY_DATABASE_URI"):
        raise RuntimeError("DATABASE_URL is not set. Check your .env file.")

    db.init_app(app)
    migrate.init_app(app, db, compare_type=True)
    jwt.init_app(app)
    bcrypt.init_app(app)
    cors.init_app(app, resources={r"/api/*": {"origins": "*"}})

    app.register_blueprint(api, url_prefix="/api")
    app.register_blueprint(auth_bp, url_prefix="/api/auth")
    setup_commands(app)
    if app.config["ADMIN_ENABLED"]:
        setup_admin(app)

    register_error_handlers(app)
    register_frontend_routes(app)
    return app


def register_error_handlers(app):
    @app.errorhandler(APIException)
    def handle_api_exception(error):
        return jsonify(error.to_dict()), error.status_code


def register_frontend_routes(app):
    @app.route("/")
    def sitemap():
        if app.config["DEBUG"]:
            return generate_sitemap(app)
        return send_from_directory(STATIC_DIR, "index.html")

    @app.route("/<path:path>", methods=["GET"])
    def serve_any_other_file(path):
        if not os.path.isfile(os.path.join(STATIC_DIR, path)):
            path = "index.html"
        response = send_from_directory(STATIC_DIR, path)
        response.cache_control.max_age = 0
        return response


app = create_app()

if __name__ == "__main__":
    PORT = int(os.environ.get("PORT", 3001))
    app.run(host="0.0.0.0", port=PORT, debug=True)
