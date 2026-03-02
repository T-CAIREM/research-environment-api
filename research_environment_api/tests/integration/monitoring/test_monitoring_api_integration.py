"""Integration tests for Monitoring API endpoints.

Scope
-----
These tests exercise the HTTP endpoints under /monitoring/* using:
- a real Flask app (test client)
- a real Postgres DB (container + Alembic migrations)

We seed WorkbenchMonitoringData rows directly and verify the aggregated
responses returned by the API.

What we validate
----------------
- GET /monitoring/datasets
    - returns 200 with a list of WorkbenchMonitoringDataEntry objects
    - entries contain expected user_email, dataset_identifier, instance_type
    - total_time is computed and non-empty for finished sessions
    - empty DB returns empty list

- GET /monitoring/active_users
    - returns 200 with a list of UsersPerDatasetEntry objects
    - only rows with deleted_at=None are considered "active"
    - multiple users on the same dataset are aggregated correctly
    - finished sessions (deleted_at set) are excluded
"""

import uuid
from datetime import datetime, timedelta
from research_environment_api.background.enums import InstanceType


class TestMonitoringAPIIntegration:
    """Dataset monitoring and active-user endpoints."""

    # ------------------------------------------------------------------
    # helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _seed_monitoring_row(
        db_session,
        *,
        user_email,
        dataset_identifier,
        instance_type,
        created_at=None,
        deleted_at=None,
        workbench_id=None,
    ):
        """Insert a WorkbenchMonitoringData row and return its id."""
        from research_environment_api.modules.monitoring_management import models

        row_id = str(uuid.uuid4())
        created_at = created_at or datetime(2025, 1, 1, 10, 0, 0)
        with db_session() as session:
            with session.begin():
                row = models.WorkbenchMonitoringData(
                    id=row_id,
                    user_email=user_email,
                    dataset_identifier=dataset_identifier,
                    instance_type=instance_type,
                    created_at=created_at,
                    deleted_at=deleted_at,
                    workbench_id=workbench_id or str(uuid.uuid4()),
                )
                session.add(row)
        return row_id

    # ------------------------------------------------------------------
    # GET /monitoring/datasets
    # ------------------------------------------------------------------

    def test_list_datasets_returns_200_with_list(self, client, db_session):
        """GET /monitoring/datasets returns 200 and a list (may be empty)."""
        response = client.get("/monitoring/datasets")
        assert response.status_code == 200
        assert isinstance(response.json, list)

    def test_list_datasets_contains_seeded_entry(self, client, db_session):
        """A seeded monitoring row appears in the /datasets response."""
        from research_environment_api.background.enums import InstanceType

        email = "monitor-user@example.com"
        dataset = "ds-integration-001"

        self._seed_monitoring_row(
            db_session,
            user_email=email,
            dataset_identifier=dataset,
            instance_type=InstanceType.JUPYTER,
            created_at=datetime(2025, 3, 1, 9, 0, 0),
            deleted_at=datetime(2025, 3, 1, 11, 0, 0),
        )

        response = client.get("/monitoring/datasets")
        assert response.status_code == 200

        data = response.json
        matching = [
            e
            for e in data
            if e["user_email"] == email and e["dataset_identifier"] == dataset
        ]
        assert len(matching) == 1
        entry = matching[0]
        assert entry["instance_type"] == "jupyter"
        # 2 hours -> "2 Hours" formatted string
        assert "2" in entry["total_time"]
        assert "Hour" in entry["total_time"]

    def test_list_datasets_response_shape(self, client, db_session):
        """Each element in the /datasets response has the required schema fields."""
        from research_environment_api.background.enums import InstanceType

        self._seed_monitoring_row(
            db_session,
            user_email="shape-check@example.com",
            dataset_identifier="ds-shape",
            instance_type=InstanceType.RSTUDIO,
            created_at=datetime(2025, 4, 1, 8, 0, 0),
            deleted_at=datetime(2025, 4, 1, 9, 0, 0),
        )

        response = client.get("/monitoring/datasets")
        assert response.status_code == 200

        assert len(response.json) > 0
        for entry in response.json:
            assert "user_email" in entry
            assert "dataset_identifier" in entry
            assert "instance_type" in entry
            assert "total_time" in entry

    def test_list_datasets_active_session_uses_current_time(self, client, db_session):
        """An active session (deleted_at=None) still contributes to total_time."""
        from research_environment_api.background.enums import InstanceType

        email = "active-session@example.com"
        dataset = "ds-active"

        # Session started 1 hour ago, not finished
        started = datetime.now() - timedelta(hours=1)
        self._seed_monitoring_row(
            db_session,
            user_email=email,
            dataset_identifier=dataset,
            instance_type=InstanceType.JUPYTER,
            created_at=started,
            deleted_at=None,  # still running
        )

        response = client.get("/monitoring/datasets")
        assert response.status_code == 200

        matching = [
            e
            for e in response.json
            if e["user_email"] == email and e["dataset_identifier"] == dataset
        ]
        assert len(matching) == 1
        assert matching[0]["total_time"] != ""

    def test_list_datasets_count_matches_distinct_identifiers(self, client, db_session):
        """The number of entries in /datasets matches the number of distinct user+dataset combos seeded."""
        combos = [
            ("user-a@example.com", "ds-cnt-1"),
            ("user-b@example.com", "ds-cnt-2"),
            ("user-c@example.com", "ds-cnt-3"),
        ]
        for email, ds in combos:
            self._seed_monitoring_row(
                db_session,
                user_email=email,
                dataset_identifier=ds,
                instance_type=InstanceType.JUPYTER,
                created_at=datetime(2025, 7, 1, 10, 0, 0),
                deleted_at=datetime(2025, 7, 1, 11, 0, 0),
            )

        response = client.get("/monitoring/datasets")
        assert response.status_code == 200

        seeded_entries = [
            e
            for e in response.json
            if (e["user_email"], e["dataset_identifier"]) in combos
        ]
        assert len(seeded_entries) == len(combos)

    def test_list_datasets_aggregates_multiple_sessions_for_same_identifier(
        self, client, db_session
    ):
        """Two separate sessions for the same user+dataset are summed."""
        from research_environment_api.background.enums import InstanceType

        email = "agg-user@example.com"
        dataset = "ds-agg"

        # Session 1: 1 hour
        self._seed_monitoring_row(
            db_session,
            user_email=email,
            dataset_identifier=dataset,
            instance_type=InstanceType.JUPYTER,
            created_at=datetime(2025, 5, 1, 9, 0, 0),
            deleted_at=datetime(2025, 5, 1, 10, 0, 0),
        )
        # Session 2: 2 hours
        self._seed_monitoring_row(
            db_session,
            user_email=email,
            dataset_identifier=dataset,
            instance_type=InstanceType.JUPYTER,
            created_at=datetime(2025, 5, 2, 9, 0, 0),
            deleted_at=datetime(2025, 5, 2, 11, 0, 0),
        )

        response = client.get("/monitoring/datasets")
        assert response.status_code == 200

        matching = [
            e
            for e in response.json
            if e["user_email"] == email and e["dataset_identifier"] == dataset
        ]
        assert len(matching) == 1
        assert "3" in matching[0]["total_time"]
        assert "Hour" in matching[0]["total_time"]

    # ------------------------------------------------------------------
    # GET /monitoring/active_users
    # ------------------------------------------------------------------

    def test_active_users_returns_200_with_list(self, client, db_session):
        """GET /monitoring/active_users returns 200 and a list."""
        response = client.get("/monitoring/active_users")
        assert response.status_code == 200
        assert isinstance(response.json, list)

    def test_active_users_user_emails_count_matches_seeded_users(
        self, client, db_session
    ):
        """user_emails list length for a dataset equals the number of distinct users seeded."""
        dataset = "ds-email-count"
        emails = [f"email-count-{i}@example.com" for i in range(4)]

        for email in emails:
            self._seed_monitoring_row(
                db_session,
                user_email=email,
                dataset_identifier=dataset,
                instance_type=InstanceType.JUPYTER,
                created_at=datetime.now() - timedelta(hours=1),
                deleted_at=None,
            )

        response = client.get("/monitoring/active_users")
        assert response.status_code == 200

        matching = [e for e in response.json if e["dataset_identifier"] == dataset]
        assert len(matching) == 1
        assert len(matching[0]["user_emails"]) == len(emails)

    def test_active_users_includes_user_with_running_session(self, client, db_session):
        """A user whose session is still running appears in active_users."""
        from research_environment_api.background.enums import InstanceType

        email = "running-user@example.com"
        dataset = "ds-running"

        self._seed_monitoring_row(
            db_session,
            user_email=email,
            dataset_identifier=dataset,
            instance_type=InstanceType.JUPYTER,
            created_at=datetime.now() - timedelta(minutes=30),
            deleted_at=None,
        )

        response = client.get("/monitoring/active_users")
        assert response.status_code == 200

        matching = [e for e in response.json if e["dataset_identifier"] == dataset]
        assert len(matching) == 1
        assert email in matching[0]["user_emails"]

    def test_active_users_excludes_finished_sessions(self, client, db_session):
        """Users whose sessions are finished (deleted_at set) do NOT appear."""
        from research_environment_api.background.enums import InstanceType

        email = "finished-user@example.com"
        dataset = "ds-finished-unique"

        self._seed_monitoring_row(
            db_session,
            user_email=email,
            dataset_identifier=dataset,
            instance_type=InstanceType.JUPYTER,
            created_at=datetime(2025, 6, 1, 8, 0, 0),
            deleted_at=datetime(2025, 6, 1, 9, 0, 0),  # finished
        )

        response = client.get("/monitoring/active_users")
        assert response.status_code == 200

        matching = [e for e in response.json if e["dataset_identifier"] == dataset]
        assert len(matching) == 0

    def test_active_users_response_shape(self, client, db_session):
        """Each element has dataset_identifier and user_emails list."""
        from research_environment_api.background.enums import InstanceType

        self._seed_monitoring_row(
            db_session,
            user_email="shape-active@example.com",
            dataset_identifier="ds-shape-active",
            instance_type=InstanceType.RSTUDIO,
            created_at=datetime.now() - timedelta(hours=1),
            deleted_at=None,
        )

        response = client.get("/monitoring/active_users")
        assert response.status_code == 200

        for entry in response.json:
            assert "dataset_identifier" in entry
            assert "user_emails" in entry
            assert isinstance(entry["user_emails"], list)

    def test_active_users_multiple_users_same_dataset(self, client, db_session):
        """Multiple active users on the same dataset are grouped together."""
        from research_environment_api.background.enums import InstanceType

        dataset = "ds-multi-users"
        emails = [f"user{i}-multi@example.com" for i in range(3)]

        for email in emails:
            self._seed_monitoring_row(
                db_session,
                user_email=email,
                dataset_identifier=dataset,
                instance_type=InstanceType.JUPYTER,
                created_at=datetime.now() - timedelta(hours=1),
                deleted_at=None,
            )

        response = client.get("/monitoring/active_users")
        assert response.status_code == 200

        matching = [e for e in response.json if e["dataset_identifier"] == dataset]
        assert len(matching) == 1
        for email in emails:
            assert email in matching[0]["user_emails"]

    def test_active_users_different_datasets_produce_separate_entries(
        self, client, db_session
    ):
        """Active users on different datasets produce separate response entries."""
        from research_environment_api.background.enums import InstanceType

        datasets = ["ds-sep-alpha", "ds-sep-beta"]
        for ds in datasets:
            self._seed_monitoring_row(
                db_session,
                user_email="sep-user@example.com",
                dataset_identifier=ds,
                instance_type=InstanceType.JUPYTER,
                created_at=datetime.now() - timedelta(hours=1),
                deleted_at=None,
            )

        response = client.get("/monitoring/active_users")
        assert response.status_code == 200

        returned_datasets = {e["dataset_identifier"] for e in response.json}
        for ds in datasets:
            assert ds in returned_datasets
