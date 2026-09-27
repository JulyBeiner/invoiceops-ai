from api.routes.auth import auth_bp
from api.routes.clients import clients_bp
from api.routes.health import api
from api.routes.services import services_bp

__all__ = ["api", "auth_bp", "clients_bp", "services_bp"]
