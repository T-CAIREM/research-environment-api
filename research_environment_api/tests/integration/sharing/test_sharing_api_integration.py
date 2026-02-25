"""Integration tests for Sharing Management API endpoints.

Scope
-----
These tests exercise the HTTP endpoints under `/sharing/*` using:
- a real Flask app (test client)
- a real Postgres DB (container + Alembic migrations) for sharing metadata
- a fake GCS server (fsouza/fake-gcs-server) via the ``mock_gcp_environment``
  fixture — bucket CRUD operations go to the emulator

GCP IAM policy calls (get_iam_policy / set_iam_policy) are mocked because
the fake-gcs-server emulator does not implement the GCS IAM API.

What we validate
----------------
- POST /sharing/bucket/create      -> 201, bucket exists in GCS emulator
- DELETE /sharing/bucket/delete    -> 200, sharing DB rows revoked
- POST /sharing/bucket/share       -> 200, SharingData row created
- POST /sharing/bucket/revoke_access -> 200, SharingData row revoked
- GET  /sharing/<email>/<name>     -> 200, returns SharedBucket shape
- GET  /sharing/<name>             -> 200, returns bucket content list
- Validation / bad-request cases
"""

from unittest.mock import MagicMock

import pytest


class TestSharingBucketIntegration:
    """Bucket lifecycle: create / delete / share / revoke."""

    # ------------------------------------------------------------------
    # IAM policy mock (fake-gcs-server does not support /iam endpoint)
    # ------------------------------------------------------------------

    @pytest.fixture(autouse=True)
    def mock_gcs_metadata(self, mocker):
        """Patch IAM and labels on every Bucket instance.

        Two limitations of the fake-gcs-server emulator are worked around here:

        1. The emulator does not implement the GCS IAM API (/b/<name>/iam),
           so get_iam_policy() / set_iam_policy() are replaced with in-memory
           equivalents keyed by bucket name.

        2. The emulator does not persist labels that are set on a Bucket object
           before create_bucket() is called; subsequent get_bucket() calls
           return an object with empty labels.  We replace the ``labels``
           property with an in-memory dict so both the write
           (``bucket.labels = {...}``) and the read (``bucket.labels``) share
           the same store.
        """
        import google.cloud.storage

        def _make_policy(bindings=None):
            policy = MagicMock()
            policy.bindings = bindings if bindings is not None else []
            return policy

        # Per-bucket-name stores (reset each test via fixture scope).
        policies: dict = {}
        labels_store: dict = {}

        # ---- IAM policy helpers ----
        def _get_iam_policy(bucket_self, requested_policy_version=None):
            name = bucket_self.name
            if name not in policies:
                policies[name] = _make_policy()
            return policies[name]

        def _set_iam_policy(bucket_self, policy, *args, **kwargs):
            policies[bucket_self.name] = policy

        mocker.patch(
            "google.cloud.storage.Bucket.get_iam_policy",
            _get_iam_policy,
        )
        mocker.patch(
            "google.cloud.storage.Bucket.set_iam_policy",
            _set_iam_policy,
        )

        # ---- Labels property helpers ----
        # Replace the ``labels`` descriptor on the Bucket class with one that
        # reads/writes from our in-memory store so labels survive across the
        # create -> get_bucket round-trip.

        def _labels_getter(bucket_self):
            return labels_store.get(bucket_self.name, {})

        def _labels_setter(bucket_self, value):
            labels_store[bucket_self.name] = dict(value)

        mocker.patch.object(
            google.cloud.storage.Bucket,
            "labels",
            new=property(_labels_getter, _labels_setter),
        )

        return {"policies": policies, "labels": labels_store}

    # ------------------------------------------------------------------
    # helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _create_bucket(
        client,
        *,
        bucket_name="testbucket",
        email="owner@example.com",
        project_id="ws-proj-abc123",
        region="us-central1",
    ):
        """POST /sharing/bucket/create with sane defaults."""
        return client.post(
            "/sharing/bucket/create",
            json={
                "region": region,
                "workspace_project_id": project_id,
                "user_email": email,
                "user_defined_bucket_name": bucket_name,
            },
        )

    # ------------------------------------------------------------------
    # create bucket
    # ------------------------------------------------------------------

    def test_create_shared_bucket_returns_201(self, client, mock_gcp_environment):
        """POST /sharing/bucket/create returns 201."""
        response = self._create_bucket(client)
        assert response.status_code == 201

    def test_create_shared_bucket_bucket_exists_in_gcs(
        self, client, mock_gcp_environment, fake_gcs_client
    ):
        """After create the bucket exists in the GCS emulator."""
        response = self._create_bucket(
            client,
            bucket_name="integration-create",
            email="creator@example.com",
            project_id="ws-proj-create",
        )
        assert response.status_code == 201

        # fake_gcs_client talks to the same emulator instance
        buckets = [
            b.name for b in fake_gcs_client.list_buckets(project="ws-proj-create")
        ]
        assert any("integration-create" in name for name in buckets)

    def test_create_shared_bucket_missing_region_returns_validation_error(
        self, client, mock_gcp_environment
    ):
        """POST without region raises a marshmallow ValidationError."""
        import marshmallow

        with pytest.raises(marshmallow.exceptions.ValidationError) as exc_info:
            client.post(
                "/sharing/bucket/create",
                json={
                    "workspace_project_id": "ws-proj-abc123",
                    "user_email": "owner@example.com",
                    "user_defined_bucket_name": "mybucket",
                    # region intentionally omitted
                },
            )

        assert "region" in exc_info.value.messages

    def test_create_shared_bucket_invalid_bucket_name_returns_validation_error(
        self, client, mock_gcp_environment
    ):
        """Bucket names with uppercase chars are rejected by the schema."""
        import marshmallow

        with pytest.raises(marshmallow.exceptions.ValidationError) as exc_info:
            client.post(
                "/sharing/bucket/create",
                json={
                    "region": "us-central1",
                    "workspace_project_id": "ws-proj-abc123",
                    "user_email": "owner@example.com",
                    "user_defined_bucket_name": "INVALID_UPPERCASE",
                },
            )

        assert "user_defined_bucket_name" in exc_info.value.messages

    # ------------------------------------------------------------------
    # delete bucket
    # ------------------------------------------------------------------

    def test_delete_shared_bucket_returns_200(
        self, client, mock_gcp_environment, fake_gcs_client
    ):
        """DELETE /sharing/bucket/delete on a known bucket returns 200."""
        # Create first
        self._create_bucket(
            client,
            bucket_name="tobedeleted",
            email="owner@example.com",
            project_id="ws-proj-delete",
        )

        # Find the bucket name the service generated (contains 'tobedeleted')
        all_buckets = list(fake_gcs_client.list_buckets(project="ws-proj-delete"))
        bucket = next(b for b in all_buckets if "tobedeleted" in b.name)

        response = client.delete(
            "/sharing/bucket/delete",
            json={"bucket_name": bucket.name},
        )
        assert response.status_code == 200

    def test_delete_shared_bucket_revokes_sharing_db_rows(
        self, client, db_session, mock_gcp_environment, fake_gcs_client
    ):
        """SharingData rows for the bucket are marked REVOKED after deletion."""
        from research_environment_api.modules.sharing_management import models, enums

        # Create bucket in GCS
        self._create_bucket(
            client,
            bucket_name="sharedbucket",
            email="owner@example.com",
            project_id="ws-proj-share",
        )
        all_buckets = list(fake_gcs_client.list_buckets(project="ws-proj-share"))
        bucket = next(b for b in all_buckets if "sharedbucket" in b.name)

        # Seed a SharingData row
        with db_session() as session:
            with session.begin():
                row = models.SharingData(
                    sharer_email="owner@example.com",
                    accessor_email="accessor@example.com",
                    bucket_name=bucket.name,
                    project_id="ws-proj-share",
                    state=enums.SharingState.SHARED,
                )
                session.add(row)

        # Delete bucket
        client.delete("/sharing/bucket/delete", json={"bucket_name": bucket.name})

        # Verify DB row is now REVOKED
        with db_session() as session:
            sharing_row = (
                session.query(models.SharingData)
                .filter_by(bucket_name=bucket.name)
                .first()
            )
            assert sharing_row is not None
            assert sharing_row.state == enums.SharingState.REVOKED

    # ------------------------------------------------------------------
    # share bucket
    # ------------------------------------------------------------------

    def test_share_bucket_creates_sharing_data_row(
        self, client, db_session, mock_gcp_environment, fake_gcs_client
    ):
        """POST /sharing/bucket/share creates a SharingData row with state SHARED."""
        from research_environment_api.modules.sharing_management import models, enums

        self._create_bucket(
            client,
            bucket_name="sharebkt",
            email="sharer@example.com",
            project_id="ws-proj-sharebkt",
        )
        all_buckets = list(fake_gcs_client.list_buckets(project="ws-proj-sharebkt"))
        bucket = next(b for b in all_buckets if "sharebkt" in b.name)

        response = client.post(
            "/sharing/bucket/share",
            json={
                "sharer_email": "sharer@example.com",
                "project_id": "ws-proj-sharebkt",
                "accessor_email": "reader@example.com",
                "bucket_name": bucket.name,
                "permissions": "read",
            },
        )
        assert response.status_code == 200

        with db_session() as session:
            row = (
                session.query(models.SharingData)
                .filter_by(
                    bucket_name=bucket.name,
                    accessor_email="reader@example.com",
                )
                .first()
            )
            assert row is not None
            assert row.state == enums.SharingState.SHARED
            assert row.sharer_email == "sharer@example.com"

    def test_share_bucket_idempotent_for_existing_row(
        self, client, db_session, mock_gcp_environment, fake_gcs_client
    ):
        """Sharing the same bucket twice still results in a single SHARED row."""
        from research_environment_api.modules.sharing_management import models

        self._create_bucket(
            client,
            bucket_name="idempotenttbkt",
            email="sharer2@example.com",
            project_id="ws-proj-idempotent",
        )
        all_buckets = list(fake_gcs_client.list_buckets(project="ws-proj-idempotent"))
        bucket = next(b for b in all_buckets if "idempotenttbkt" in b.name)

        payload = {
            "sharer_email": "sharer2@example.com",
            "project_id": "ws-proj-idempotent",
            "accessor_email": "reader2@example.com",
            "bucket_name": bucket.name,
            "permissions": "read",
        }

        client.post("/sharing/bucket/share", json=payload)
        client.post("/sharing/bucket/share", json=payload)

        with db_session() as session:
            rows = (
                session.query(models.SharingData)
                .filter_by(
                    bucket_name=bucket.name,
                    accessor_email="reader2@example.com",
                )
                .all()
            )
            assert len(rows) == 1

    # ------------------------------------------------------------------
    # revoke access
    # ------------------------------------------------------------------

    def test_revoke_access_updates_sharing_data_row(
        self, client, db_session, mock_gcp_environment, fake_gcs_client
    ):
        """POST /sharing/bucket/revoke_access transitions the DB row to REVOKED."""
        from research_environment_api.modules.sharing_management import models, enums

        self._create_bucket(
            client,
            bucket_name="revokebkt",
            email="revoker@example.com",
            project_id="ws-proj-revoke",
        )
        all_buckets = list(fake_gcs_client.list_buckets(project="ws-proj-revoke"))
        bucket = next(b for b in all_buckets if "revokebkt" in b.name)

        # Share first
        client.post(
            "/sharing/bucket/share",
            json={
                "sharer_email": "revoker@example.com",
                "project_id": "ws-proj-revoke",
                "accessor_email": "tobe-revoked@example.com",
                "bucket_name": bucket.name,
                "permissions": "read",
            },
        )

        # Now revoke
        response = client.post(
            "/sharing/bucket/revoke_access",
            json={
                "sharer_email": "revoker@example.com",
                "accessor_email": "tobe-revoked@example.com",
                "bucket_name": bucket.name,
            },
        )
        assert response.status_code == 200

        with db_session() as session:
            row = (
                session.query(models.SharingData)
                .filter_by(
                    bucket_name=bucket.name,
                    accessor_email="tobe-revoked@example.com",
                )
                .first()
            )
            assert row is not None
            assert row.state == enums.SharingState.REVOKED

    # ------------------------------------------------------------------
    # get shared bucket
    # ------------------------------------------------------------------

    def test_get_shared_bucket_returns_200_with_expected_shape(
        self, client, mock_gcp_environment, fake_gcs_client
    ):
        """GET /sharing/<email>/<name> returns a SharedBucket payload."""
        email = "getowner@example.com"
        self._create_bucket(
            client,
            bucket_name="getbucket",
            email=email,
            project_id="ws-proj-get",
        )
        all_buckets = list(fake_gcs_client.list_buckets(project="ws-proj-get"))
        bucket = next(b for b in all_buckets if "getbucket" in b.name)

        response = client.get(f"/sharing/{email}/{bucket.name}")
        assert response.status_code == 200
        data = response.json
        assert "bucket_name" in data
        assert "is_owner" in data
        assert "is_admin" in data

    def test_get_shared_bucket_is_owner_true_for_creator(
        self, client, mock_gcp_environment, fake_gcs_client
    ):
        """The creator's GET response must show is_owner=True."""
        email = "ownercheck@example.com"
        self._create_bucket(
            client,
            bucket_name="ownercheckbkt",
            email=email,
            project_id="ws-proj-ownercheck",
        )
        all_buckets = list(fake_gcs_client.list_buckets(project="ws-proj-ownercheck"))
        bucket = next(b for b in all_buckets if "ownercheckbkt" in b.name)

        response = client.get(f"/sharing/{email}/{bucket.name}")
        assert response.status_code == 200
        assert response.json["is_owner"] is True

    # ------------------------------------------------------------------
    # bucket content
    # ------------------------------------------------------------------

    def test_get_bucket_content_returns_empty_list_for_new_bucket(
        self, client, mock_gcp_environment, fake_gcs_client
    ):
        """GET /sharing/<name>?user_email=... on a fresh bucket returns []."""
        email = "contentowner@example.com"
        self._create_bucket(
            client,
            bucket_name="contentbkt",
            email=email,
            project_id="ws-proj-content",
        )
        all_buckets = list(fake_gcs_client.list_buckets(project="ws-proj-content"))
        bucket = next(b for b in all_buckets if "contentbkt" in b.name)

        response = client.get(
            f"/sharing/{bucket.name}",
            query_string={"user_email": email, "subdir": ""},
        )
        assert response.status_code == 200
        assert isinstance(response.json, list)

    # ------------------------------------------------------------------
    # validation – bad request cases
    # ------------------------------------------------------------------

    def test_share_bucket_missing_accessor_email_raises_validation_error(
        self, client, mock_gcp_environment
    ):
        """POST /sharing/bucket/share without accessor_email raises ValidationError."""
        import marshmallow

        with pytest.raises(marshmallow.exceptions.ValidationError) as exc_info:
            client.post(
                "/sharing/bucket/share",
                json={
                    "sharer_email": "sharer@example.com",
                    "project_id": "ws-proj-abc",
                    "bucket_name": "some-bucket",
                    "permissions": "read",
                    # accessor_email intentionally omitted
                },
            )
        assert "accessor_email" in exc_info.value.messages

    def test_revoke_access_missing_bucket_raises_validation_error(
        self, client, mock_gcp_environment
    ):
        """POST /sharing/bucket/revoke_access without bucket_name raises ValidationError."""
        import marshmallow

        with pytest.raises(marshmallow.exceptions.ValidationError) as exc_info:
            client.post(
                "/sharing/bucket/revoke_access",
                json={
                    "sharer_email": "sharer@example.com",
                    "accessor_email": "accessor@example.com",
                    # bucket_name intentionally omitted
                },
            )
        assert "bucket_name" in exc_info.value.messages
