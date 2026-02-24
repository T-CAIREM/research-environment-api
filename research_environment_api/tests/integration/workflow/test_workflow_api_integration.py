"""Integration tests for Workflow API endpoints.

Scope
-----
These tests exercise the HTTP endpoints under /workflow/* using:
- a real Flask app (test client)
- a real Postgres DB (container + Alembic migrations)
- no Celery needed: we manipulate DB rows directly and call read endpoints

What we validate
----------------
- GET /workflow/<workflow_id>      returns 200, correct shape and field values
- GET /workflow/list/<user_email>  returns 200, only IN_PROGRESS rows for that user
- Completed/failed rows are NOT returned by the list endpoint
- Multiple users workflows are isolated from each other
- Error cases for unknown workflow ids
"""

import uuid

import pytest


class TestWorkflowAPIIntegration:
    """Read-only workflow status endpoints."""

    # ------------------------------------------------------------------
    # helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _seed_activity(
        db_session,
        *,
        invoker_email,
        build_type,
        build_status,
        workspace_id="ws-proj-test",
        workbench_id=None,
    ):
        """Insert a WorkbenchActivity row directly and return its id."""
        from research_environment_api.modules.monitoring_management import models

        activity_id = str(uuid.uuid4())
        with db_session() as session:
            with session.begin():
                activity = models.WorkbenchActivity(
                    id=activity_id,
                    invoker_email=invoker_email,
                    build_type=build_type,
                    build_status=build_status,
                    workspace_id=workspace_id,
                    workbench_id=workbench_id,
                )
                session.add(activity)
        return activity_id

    # ------------------------------------------------------------------
    # GET /workflow/<workflow_id>
    # ------------------------------------------------------------------

    def test_get_workflow_returns_200_with_correct_shape(self, client, db_session):
        """GET /workflow/<id> returns 200 and a Workflow-schema-compatible body."""
        from research_environment_api.background import enums

        wid = self._seed_activity(
            db_session,
            invoker_email="alice@example.com",
            build_type=enums.BuildType.WORKBENCH_CREATION,
            build_status=enums.WorkflowStatus.IN_PROGRESS,
            workspace_id="ws-alice-001",
        )

        response = client.get(f"/workflow/{wid}")

        assert response.status_code == 200
        data = response.json
        assert data["id"] == wid
        assert data["workspace_id"] == "ws-alice-001"
        assert "build_type" in data
        assert "status" in data

    def test_get_workflow_returns_correct_build_type_and_status(
        self, client, db_session
    ):
        """GET /workflow/<id> reflects the exact build_type and status stored."""
        from research_environment_api.background import enums

        wid = self._seed_activity(
            db_session,
            invoker_email="bob@example.com",
            build_type=enums.BuildType.WORKSPACE_CREATION,
            build_status=enums.WorkflowStatus.SUCCESS,
            workspace_id="ws-bob-002",
        )

        response = client.get(f"/workflow/{wid}")

        assert response.status_code == 200
        data = response.json
        assert data["build_type"] == "workspace_creation"
        assert data["status"] == "success"

    def test_get_workflow_failure_status_reflected(self, client, db_session):
        """A FAILURE workflow is returned with status='failure'."""
        from research_environment_api.background import enums

        wid = self._seed_activity(
            db_session,
            invoker_email="charlie@example.com",
            build_type=enums.BuildType.WORKBENCH_DESTROY,
            build_status=enums.WorkflowStatus.FAILURE,
            workspace_id="ws-charlie-003",
        )

        response = client.get(f"/workflow/{wid}")

        assert response.status_code == 200
        assert response.json["status"] == "failure"

    def test_get_workflow_unknown_id_raises(self, client):
        """GET with a non-existent workflow id raises an exception (no row found)."""
        fake_id = str(uuid.uuid4())

        with pytest.raises(Exception):
            client.get(f"/workflow/{fake_id}")

    # ------------------------------------------------------------------
    # GET /workflow/list/<user_email>
    # ------------------------------------------------------------------

    def test_list_workflows_returns_only_in_progress_for_user(self, client, db_session):
        """GET /workflow/list/<email> returns only IN_PROGRESS rows for that user."""
        from research_environment_api.background import enums

        email = "listuser@example.com"

        in_progress_id = self._seed_activity(
            db_session,
            invoker_email=email,
            build_type=enums.BuildType.WORKBENCH_CREATION,
            build_status=enums.WorkflowStatus.IN_PROGRESS,
        )
        # SUCCESS row -- should NOT appear in the list
        self._seed_activity(
            db_session,
            invoker_email=email,
            build_type=enums.BuildType.WORKBENCH_STOP,
            build_status=enums.WorkflowStatus.SUCCESS,
        )

        response = client.get(f"/workflow/list/{email}")

        assert response.status_code == 200
        data = response.json
        assert isinstance(data, list)
        ids = [w["id"] for w in data]
        assert in_progress_id in ids
        for w in data:
            assert w["status"] == "in_progress"

    def test_list_workflows_returns_empty_for_user_without_active_workflows(
        self, client, db_session
    ):
        """A user with only SUCCESS/FAILURE rows gets an empty list."""
        from research_environment_api.background import enums

        email = "idleuser@example.com"

        self._seed_activity(
            db_session,
            invoker_email=email,
            build_type=enums.BuildType.WORKSPACE_DELETION,
            build_status=enums.WorkflowStatus.SUCCESS,
        )

        response = client.get(f"/workflow/list/{email}")

        assert response.status_code == 200
        assert response.json == []

    def test_list_workflows_isolates_users(self, client, db_session):
        """Workflows for user A are not returned when listing user B's workflows."""
        from research_environment_api.background import enums

        email_a = "usera-isolated@example.com"
        email_b = "userb-isolated@example.com"

        wid_a = self._seed_activity(
            db_session,
            invoker_email=email_a,
            build_type=enums.BuildType.WORKBENCH_CREATION,
            build_status=enums.WorkflowStatus.IN_PROGRESS,
        )

        response = client.get(f"/workflow/list/{email_b}")

        assert response.status_code == 200
        ids = [w["id"] for w in response.json]
        assert wid_a not in ids

    def test_list_workflows_multiple_in_progress_all_returned(self, client, db_session):
        """All IN_PROGRESS rows for a user are included in the list response."""
        from research_environment_api.background import enums

        email = "multiactive@example.com"

        seeded_ids = [
            self._seed_activity(
                db_session,
                invoker_email=email,
                build_type=enums.BuildType.WORKBENCH_CREATION,
                build_status=enums.WorkflowStatus.IN_PROGRESS,
                workspace_id=f"ws-multi-{i}",
            )
            for i in range(3)
        ]

        response = client.get(f"/workflow/list/{email}")

        assert response.status_code == 200
        returned_ids = [w["id"] for w in response.json]
        for wid in seeded_ids:
            assert wid in returned_ids

    def test_list_workflows_never_returns_other_users_workflows(
        self, client, db_session
    ):
        """Even when many users have IN_PROGRESS rows, list returns only the requested one."""
        from research_environment_api.background import enums

        target_email = "target@example.com"
        other_email = "other@example.com"

        target_wid = self._seed_activity(
            db_session,
            invoker_email=target_email,
            build_type=enums.BuildType.WORKBENCH_CREATION,
            build_status=enums.WorkflowStatus.IN_PROGRESS,
        )
        other_wid = self._seed_activity(
            db_session,
            invoker_email=other_email,
            build_type=enums.BuildType.WORKBENCH_CREATION,
            build_status=enums.WorkflowStatus.IN_PROGRESS,
        )

        response = client.get(f"/workflow/list/{target_email}")

        assert response.status_code == 200
        returned_ids = [w["id"] for w in response.json]
        assert target_wid in returned_ids
        assert other_wid not in returned_ids
