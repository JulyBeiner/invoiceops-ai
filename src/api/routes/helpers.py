from flask_jwt_extended import get_jwt_identity

from api.extensions import db
from api.models import User


def current_user():
    """Return the User behind the JWT of the current request.

    Only call this inside a route protected with @jwt_required().
    """
    return db.session.get(User, int(get_jwt_identity()))


def current_tenant_id():
    """Return the tenant id of the logged-in user."""
    return current_user().tenant_id
