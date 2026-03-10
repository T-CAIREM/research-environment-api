"""Integration tests for the Workbench collaborators API.

Scope
-----
These tests exercise the HTTP endpoints under `/workbench/collaborators` using:
- a real Flask app (test client)
- a real Postgres DB (container + Alembic migrations)

What we validate
----------------
- request/response contract shape (schema load in a few key places)
- DB records in `WorkbenchCollaboratorData` are created/updated as expected
- status transitions: SUCCESS / REMOVED / FAILED
- filtering behavior for GET (only SUCCESS collaborators returned)
- isolation between different (workspace_project_id, service_account_name) pairs
"""

from unittest.mock import MagicMock

import pytest


class TestWorkbenchCollaboratorAPIIntegration:
    """Collaborator management endpoints: add/remove/list behaviors."""

    @pytest.fixture
    def mock_iam_client(self, mocker):
        """Patch IAM client so tests remain offline."""
        from google.cloud import iam_admin_v1

        mock_client = MagicMock(spec=iam_admin_v1.IAMClient)
        mocker.patch(
            "research_environment_api.modules.app.app.config.google_iam_client",
            mock_client,
        )
        return mock_client

    @pytest.fixture
    def mock_iam_operations(self, mocker):
        """Mock helper functions that mutate IAM bindings.

        These are the functions our service layer calls to grant/revoke access.
        Mocking them lets us simulate success/failure deterministically.
        """
        add_binding = mocker.patch(
            "research_environment_api.modules.workbench_management.services.add_iam_binding",
            autospec=True,
            return_value=True,
        )
        remove_binding = mocker.patch(
            "research_environment_api.modules.workbench_management.services.remove_iam_binding",
            autospec=True,
            return_value=True,
        )
        return {"add": add_binding, "remove": remove_binding}

    def test_add_collaborators_creates_database_records(
        self, client, db_session, mock_iam_client, mock_iam_operations
    ):
        """POST creates one DB record per collaborator and grants access via IAM."""
        from research_environment_api.modules.workbench_management import (
            models as workbench_models,
        )
        from research_environment_api.web.workbench_management import schemas

        payload = {
            "workspace_project_id": "test-workspace-123",
            "service_account_name": "test-service-account",
            "collaborators": ["user1@example.com", "user2@example.com"],
        }

        # Contract check: payload matches request schema.
        schemas.WorkbenchCollaboratorModificationRequest().load(payload)

        response = client.post("/workbench/collaborators", json=payload)
        assert response.status_code == 200
        assert response.json == {"message": "Collaborators added successfully."}

        with db_session() as session:
            records = (
                session.query(workbench_models.WorkbenchCollaboratorData)
                .filter_by(
                    workspace_project_id=payload["workspace_project_id"],
                    service_account_name=payload["service_account_name"],
                )
                .all()
            )

            assert len(records) == 2

            emails = [record.collaborator_email for record in records]
            assert "user1@example.com" in emails
            assert "user2@example.com" in emails

            for record in records:
                assert record.status == workbench_models.CollaboratorStatus.SUCCESS
                assert record.viewed is False

        # One IAM binding per collaborator.
        assert mock_iam_operations["add"].call_count == 2

    def test_add_collaborators_updates_existing_records(
        self, client, db_session, mock_iam_client, mock_iam_operations
    ):
        """POST is idempotent-ish: existing record is reused and moved back to SUCCESS."""
        from research_environment_api.modules.workbench_management import (
            models as workbench_models,
        )

        workspace_project_id = "test-workspace-456"
        service_account_name = "test-service-account-2"
        collaborator_email = "existing@example.com"

        # Seed a non-success record to validate state reset.
        with db_session() as session:
            existing_record = workbench_models.WorkbenchCollaboratorData(
                workspace_project_id=workspace_project_id,
                service_account_name=service_account_name,
                collaborator_email=collaborator_email,
                viewed=True,
                status=workbench_models.CollaboratorStatus.REMOVED,
            )
            session.add(existing_record)
            session.commit()

        payload = {
            "workspace_project_id": workspace_project_id,
            "service_account_name": service_account_name,
            "collaborators": [collaborator_email],
        }
        response = client.post("/workbench/collaborators", json=payload)
        assert response.status_code == 200

        with db_session() as session:
            records = (
                session.query(workbench_models.WorkbenchCollaboratorData)
                .filter_by(
                    workspace_project_id=workspace_project_id,
                    service_account_name=service_account_name,
                    collaborator_email=collaborator_email,
                )
                .all()
            )

            assert len(records) == 1
            assert records[0].status == workbench_models.CollaboratorStatus.SUCCESS
            assert records[0].viewed is False

    def test_add_collaborators_handles_iam_failure(
        self, client, db_session, mock_iam_client, mock_iam_operations
    ):
        """IAM failure is captured as FAILED status in DB (the endpoint should not 500)."""
        from research_environment_api.modules.workbench_management import (
            models as workbench_models,
        )

        workspace_project_id = "test-workspace-789"
        service_account_name = "test-service-account-3"

        mock_iam_operations["add"].side_effect = Exception("IAM binding failed")

        payload = {
            "workspace_project_id": workspace_project_id,
            "service_account_name": service_account_name,
            "collaborators": ["failing@example.com"],
        }

        response = client.post("/workbench/collaborators", json=payload)
        assert response.status_code == 200

        with db_session() as session:
            records = (
                session.query(workbench_models.WorkbenchCollaboratorData)
                .filter_by(
                    workspace_project_id=workspace_project_id,
                    service_account_name=service_account_name,
                )
                .all()
            )

            assert len(records) == 1
            assert records[0].status == workbench_models.CollaboratorStatus.FAILED
            assert records[0].collaborator_email == "failing@example.com"

    def test_remove_collaborators_updates_status_via_delete_endpoint(
        self, client, db_session, mock_iam_client, mock_iam_operations
    ):
        """DELETE revokes access and marks collaborator rows as REMOVED."""
        from research_environment_api.modules.workbench_management import (
            models as workbench_models,
        )

        workspace_project_id = "test-workspace-101"
        service_account_name = "test-service-account-4"
        collaborator_email = "toremove@example.com"

        with db_session() as session:
            record = workbench_models.WorkbenchCollaboratorData(
                workspace_project_id=workspace_project_id,
                service_account_name=service_account_name,
                collaborator_email=collaborator_email,
                viewed=False,
                status=workbench_models.CollaboratorStatus.SUCCESS,
            )
            session.add(record)
            session.commit()

        payload = {
            "workspace_project_id": workspace_project_id,
            "service_account_name": service_account_name,
            "collaborators": [collaborator_email],
        }
        response = client.delete("/workbench/collaborators", json=payload)
        assert response.status_code == 200
        assert response.json == {"message": "Collaborators removed successfully."}

        with db_session() as session:
            record = (
                session.query(workbench_models.WorkbenchCollaboratorData)
                .filter_by(
                    workspace_project_id=workspace_project_id,
                    service_account_name=service_account_name,
                    collaborator_email=collaborator_email,
                )
                .first()
            )

            assert record is not None
            assert record.status == workbench_models.CollaboratorStatus.REMOVED
            assert record.viewed is True

        assert mock_iam_operations["remove"].call_count == 1

    def test_get_workbench_collaborators(self, client, db_session, mock_iam_client):
        """GET returns only active (SUCCESS) collaborators."""
        from research_environment_api.modules.workbench_management import (
            models as workbench_models,
        )
        from research_environment_api.web.workbench_management import schemas

        workspace_project_id = "test-workspace-202"
        service_account_name = "test-service-account-5"

        # Seed a realistic mix of statuses.
        with db_session() as session:
            session.add_all(
                [
                    workbench_models.WorkbenchCollaboratorData(
                        workspace_project_id=workspace_project_id,
                        service_account_name=service_account_name,
                        collaborator_email="active1@example.com",
                        viewed=False,
                        status=workbench_models.CollaboratorStatus.SUCCESS,
                    ),
                    workbench_models.WorkbenchCollaboratorData(
                        workspace_project_id=workspace_project_id,
                        service_account_name=service_account_name,
                        collaborator_email="active2@example.com",
                        viewed=True,
                        status=workbench_models.CollaboratorStatus.SUCCESS,
                    ),
                    workbench_models.WorkbenchCollaboratorData(
                        workspace_project_id=workspace_project_id,
                        service_account_name=service_account_name,
                        collaborator_email="removed@example.com",
                        viewed=True,
                        status=workbench_models.CollaboratorStatus.REMOVED,
                    ),
                    workbench_models.WorkbenchCollaboratorData(
                        workspace_project_id=workspace_project_id,
                        service_account_name=service_account_name,
                        collaborator_email="failed@example.com",
                        viewed=False,
                        status=workbench_models.CollaboratorStatus.FAILED,
                    ),
                ]
            )
            session.commit()

        response = client.get(
            "/workbench/collaborators",
            query_string={
                "workspace_project_id": workspace_project_id,
                "service_account_name": service_account_name,
            },
        )
        assert response.status_code == 200

        # Contract check: response matches schema.
        data = schemas.WorkbenchCollaboratorList().load(response.json)
        assert data["collaborators"] == ["active1@example.com", "active2@example.com"]

    def test_get_collaborators_empty_result(self, client, db_session, mock_iam_client):
        """GET returns an empty list when no collaborators exist for given key."""
        from research_environment_api.web.workbench_management import schemas

        response = client.get(
            "/workbench/collaborators",
            query_string={
                "workspace_project_id": "non-existent-workspace",
                "service_account_name": "non-existent-sa",
            },
        )
        assert response.status_code == 200

        data = schemas.WorkbenchCollaboratorList().load(response.json)
        assert data["collaborators"] == []

    def test_multiple_workbenches_isolation(
        self, client, db_session, mock_iam_client, mock_iam_operations
    ):
        """Different workbenches must not leak collaborators into each other."""
        from research_environment_api.modules.workbench_management import (
            models as workbench_models,
        )
        from research_environment_api.web.workbench_management import schemas

        with db_session() as session:
            session.add_all(
                [
                    workbench_models.WorkbenchCollaboratorData(
                        workspace_project_id="workspace-1",
                        service_account_name="service-account-1",
                        collaborator_email="wb1-user@example.com",
                        viewed=False,
                        status=workbench_models.CollaboratorStatus.SUCCESS,
                    ),
                    workbench_models.WorkbenchCollaboratorData(
                        workspace_project_id="workspace-2",
                        service_account_name="service-account-2",
                        collaborator_email="wb2-user@example.com",
                        viewed=False,
                        status=workbench_models.CollaboratorStatus.SUCCESS,
                    ),
                ]
            )
            session.commit()

        response1 = client.get(
            "/workbench/collaborators",
            query_string={
                "workspace_project_id": "workspace-1",
                "service_account_name": "service-account-1",
            },
        )
        response2 = client.get(
            "/workbench/collaborators",
            query_string={
                "workspace_project_id": "workspace-2",
                "service_account_name": "service-account-2",
            },
        )

        assert response1.status_code == 200
        assert response2.status_code == 200

        data1 = schemas.WorkbenchCollaboratorList().load(response1.json)
        data2 = schemas.WorkbenchCollaboratorList().load(response2.json)

        assert data1["collaborators"] == ["wb1-user@example.com"]
        assert data2["collaborators"] == ["wb2-user@example.com"]

    def test_add_collaborators_invalid_email(
        self, client, mock_iam_client, mock_iam_operations
    ):
        """Invalid emails are rejected by schema validation; IAM is not called."""
        import marshmallow

        payload = {
            "workspace_project_id": "test-workspace-invalid-email",
            "service_account_name": "test-service-account-invalid-email",
            "collaborators": ["not-an-email"],
        }

        with pytest.raises(marshmallow.exceptions.ValidationError) as exc:
            client.post("/workbench/collaborators", json=payload)

        assert "collaborators" in exc.value.messages
        assert mock_iam_operations["add"].call_count == 0
