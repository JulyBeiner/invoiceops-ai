import os


def _normalize(url):
    # Render and Heroku provide "postgres://", but SQLAlchemy requires "postgresql://"
    return url.replace("postgres://", "postgresql://", 1) if url else url


class BaseConfig:
    SECRET_KEY = os.getenv("FLASK_APP_KEY", "dev-secret-change-me")
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", SECRET_KEY)
    SQLALCHEMY_DATABASE_URI = _normalize(os.getenv("DATABASE_URL"))
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    ADMIN_ENABLED = False
    TESTING = False


class DevelopmentConfig(BaseConfig):
    DEBUG = True
    ADMIN_ENABLED = True


class TestingConfig(BaseConfig):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = _normalize(
        os.getenv("TEST_DATABASE_URL",
                  "postgresql://gitpod:postgres@localhost:5432/example_test")
    )


class ProductionConfig(BaseConfig):
    pass


config_by_name = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
}
