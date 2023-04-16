from flask import Flask

from research_environment.identity_management.web import identity_management_bp

app = Flask(__name__)

app.register_blueprint(identity_management_bp)

app.logger
