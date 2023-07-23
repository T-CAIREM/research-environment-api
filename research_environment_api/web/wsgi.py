from dotenv import load_dotenv

from research_environment_api.modules.app import app as research_environment_backend_app
from research_environment_api.modules.celery import create_celery
from research_environment_api.web.app import create_app

load_dotenv()

research_environment_backend_app.initialize()

app = create_app()
celery_app = create_celery(
    research_environment_backend_app.config.celery_broker_url,
    research_environment_backend_app.config.celery_result_backend,
)
