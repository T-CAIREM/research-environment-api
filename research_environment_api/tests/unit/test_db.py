from unittest.mock import MagicMock

from research_environment_api.modules import db


class TestEnginePooling:
    """Stale pooled connections caused production 500s on 2026-08-19.

    Cloud SQL drops pooled connections when the IAM auth token expires (~1h) and
    when idle sockets are reaped. Without pre-ping/recycle SQLAlchemy hands the
    dead socket to the next request, which surfaces as
    `pg8000.exceptions.InterfaceError: network error` and a 500.
    """

    def test_cloud_sql_engine_validates_and_recycles_pooled_connections(self, mocker):
        # Arrange
        create_engine = mocker.patch("sqlalchemy.create_engine")
        credentials = MagicMock()
        credentials.service_account_email = "svc@project.iam.gserviceaccount.com"

        # Act
        db.create_cloud_sql_engine(credentials, "project:region:instance", "db")

        # Assert
        kwargs = create_engine.call_args.kwargs
        assert kwargs["pool_pre_ping"] is True
        assert kwargs["pool_recycle"] <= 3600

    def test_sql_engine_validates_and_recycles_pooled_connections(self, mocker):
        # Arrange
        create_engine = mocker.patch("sqlalchemy.create_engine")

        # Act
        db.create_sql_engine("postgresql+pg8000://user:pw@localhost/db")

        # Assert
        kwargs = create_engine.call_args.kwargs
        assert kwargs["pool_pre_ping"] is True
        assert kwargs["pool_recycle"] <= 3600
