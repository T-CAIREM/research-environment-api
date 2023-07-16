from research_environment_api.modules.app import app as research_environment_backend_app
from research_environment_api.web.app import create_app

research_environment_backend_app.initialize()

app = create_app()
