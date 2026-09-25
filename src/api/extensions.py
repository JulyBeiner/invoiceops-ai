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
