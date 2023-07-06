from dotenv import load_dotenv

from research_environment_api.web.app import create_app

# FIXME: Move to a more sensible place one a production config is created.
load_dotenv()

app = create_app("research_environment_api.web.config.Config")
celery_app = app.extensions["celery"]
