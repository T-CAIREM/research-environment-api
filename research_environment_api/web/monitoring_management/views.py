from research_environment_api.modules.monitoring_management import services
from research_environment_api.web.decorators import validate_token
from research_environment_api.web.monitoring_management import (
    monitoring_management_bp,
    schemas,
)
from research_environment_api.modules.app import app
from flask import Response, stream_with_context


@monitoring_management_bp.get("/datasets")
@validate_token
def list_workbench_monitoring_data_entries():
    """Lists monitoring data, for example total usage time, for datasets.
    ---
    get:
      tags:
        - monitoring_management
      description: Lists monitoring data for datasets.
      responses:
        200:
          description: Returns monitoring data list
          content:
            application/json:
              schema: WorkbenchMonitoringDataEntry
    """

    workbenches_monitoring_data_entries = (
        services.list_workbench_monitoring_data_entries()
    )
    serialized_workbenches_monitoring_data = schemas.WorkbenchMonitoringDataEntry(
        many=True
    ).dump(workbenches_monitoring_data_entries)

    return serialized_workbenches_monitoring_data, 200


@monitoring_management_bp.get("/active_users")
@validate_token
def list_active_users_per_dataset():
    """Lists active users per dataset.
    ---
    get:
      tags:
        - monitoring_management
      description: Lists active users per datasets
      responses:
        200:
          description: Returns list of active users per datasets
          content:
            application/json:
              schema: UsersPerDatasetEntry
    """

    active_users_per_dataset = services.get_active_users_per_dataset()
    serialized_users_per_dataset_entries = schemas.UsersPerDatasetEntry(many=True).dump(
        active_users_per_dataset
    )

    return serialized_users_per_dataset_entries, 200


@monitoring_management_bp.route("/events")
def server_side_event():
    def generate():
        pubsub = app.config.redis_client.pubsub()
        pubsub.subscribe("workflow_events")
        try:
            while True:
                message = pubsub.get_message(timeout=30)
                if message and message["type"] == "message":
                    yield f"event: workflow_update\ndata: {message['data'].decode()}\n\n"
                else:
                    yield ": keepalive\n\n"
        finally:
            pubsub.close()

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
