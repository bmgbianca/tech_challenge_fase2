import os

from flask import Flask
from flask_cors import CORS

from .routes import routes


def create_app():
    app = Flask(__name__)
    # CORS_ORIGINS: domínios do frontend separados por vírgula (vazio libera todos)
    origins = [o.strip() for o in os.getenv("CORS_ORIGINS", "").split(",") if o.strip()]
    CORS(app, origins=origins or "*")

    app.register_blueprint(routes)
    return app
