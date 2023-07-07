from flask import Flask
from celery import Celery, Task


def celery_init_app(app: Flask) -> Celery:
    class FlaskTask(Task):
        def __call__(self, *args: object, **kwargs: object) -> object:
            with app.app_context():
                return self.run(*args, **kwargs)

    celery_app = Celery(app.name, task_cls=FlaskTask)
    celery_app.config_from_object(app.config)
    celery_app.set_default()
    celery_app.conf.accept_content = ['application/json', 'application/x-python-serialize', 'pickle']
    celery_app.conf.result_serializer = 'pickle'
    app.extensions["celery"] = celery_app
    return celery_app


def create_app(config_object: str):
    app = Flask(__name__)
    app.config.from_object(config_object)
    celery_init_app(app)

    from research_environment_api.web.identity_management import identity_management_bp
    from research_environment_api.web.billing_management import billing_management_bp
    from research_environment_api.web.workspace_management import (
        workspace_management_bp,
    )
    from research_environment_api.web.workbench_management import (
        workbench_management_bp,
    )

    app.register_blueprint(identity_management_bp, url_prefix="/identity")
    app.register_blueprint(billing_management_bp, url_prefix="/billing")
    app.register_blueprint(workspace_management_bp, url_prefix="/workspace")
    app.register_blueprint(workbench_management_bp, url_prefix="/workbench")

    return app
