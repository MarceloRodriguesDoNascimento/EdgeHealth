import os


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "edgehealth-dev")
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", "sqlite:///edgehealth.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
