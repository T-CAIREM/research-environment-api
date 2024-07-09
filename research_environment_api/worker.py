from dotenv import load_dotenv

# Loading the env variables to be used while loading the app
load_dotenv()

from research_environment_api.background.app import create_celery
from research_environment_api.modules.app import app as research_environment_backend_app

research_environment_backend_app.initialize()

app = create_celery(
    research_environment_backend_app.config.celery_broker_url,
    research_environment_backend_app.config.celery_result_backend,
)
