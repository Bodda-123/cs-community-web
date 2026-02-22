import os
from datetime import timedelta  # for time durations


class BaseConfig:  # development / production

    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-change-me")  # for protection (sessions / forms ....)

    SQLALCHEMY_TRACK_MODIFICATIONS = False  # saving memory

    WTF_CSRF_ENABLED = True

    SESSION_PERMANENT = False
    REMEMBER_COOKIE_DURATION = timedelta(seconds=0)
    REMEMBER_COOKIE_REFRESH_EACH_REQUEST = False


class DevConfig(BaseConfig):  # coding / testing

    SQLALCHEMY_DATABASE_URI = "sqlite:///aviation.db"
    DEBUG = True  # show error details


class ProdConfig(BaseConfig):  # running

    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL", "sqlite:///aviation.db")
    DEBUG = False  # hide error details from user
