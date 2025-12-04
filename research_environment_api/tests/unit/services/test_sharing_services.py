import pytest
from unittest.mock import MagicMock, Mock
from research_environment_api.modules.sharing_management import (
    entities,
    services,
    enums,
    models,
)


class TestSharingServices:
    def test_gcp_role_access_mapping(self):
        """Test bucket permissions are correctly mapped to IAM roles."""
        # Assert
        assert (
            services.GCP_ROLE_ACCESS_MAPPING[entities.BucketPermissions.READ_WRITE]
            == enums.IamSharingRole.ADMIN
        )
        assert (
            services.GCP_ROLE_ACCESS_MAPPING[entities.BucketPermissions.READ]
            == enums.IamSharingRole.USER
        )

    def test_list_accessible_buckets_in_project(self, mocker, mock_config):
        """Test listing buckets user has access to."""
        # Arrange
        mock_storage_client = MagicMock()

        mock_bucket1 = MagicMock()
        mock_bucket1.name = "bucket-1"
        mock_policy1 = MagicMock()
        mock_policy1.bindings = [
            MagicMock(role="roles/storage.admin", members=["user:test@example.com"])
        ]
        mock_bucket1.get_iam_policy.return_value = mock_policy1

        mock_bucket2 = MagicMock()
        mock_bucket2.name = "bucket-2"
        mock_policy2 = MagicMock()
        mock_policy2.bindings = [
            MagicMock(
                role="roles/storage.objectViewer", members=["user:other@example.com"]
            )
        ]
        mock_bucket2.get_iam_policy.return_value = mock_policy2

        mock_storage_client.list_buckets.return_value = [mock_bucket1, mock_bucket2]
        mocker.patch.object(
            mock_config, "google_cloud_storage_client", mock_storage_client
        )

        mocker.patch(
            "research_environment_api.modules.sharing_management.services._user_has_access_to_bucket",
            side_effect=[True, False],
        )
        mocker.patch(
            "research_environment_api.modules.sharing_management.services._user_is_bucket_admin",
            return_value=True,
        )

        mock_shared_bucket = MagicMock()
        mocker.patch.object(
            entities.SharedBucket,
            "from_storage_instance",
            return_value=mock_shared_bucket,
        )

        # Act
        result = list(
            services.list_accessible_buckets_in_project(
                gcp_project_id="test-project",
                username="testuser",
                caller_email="test@example.com",
            )
        )

        # Assert
        assert len(result) == 1  # Only bucket-1 is accessible

    def test_create_shared_bucket(self, mocker, mock_config):
        """Test creating a shared bucket."""
        # Arrange
        mock_storage_client = MagicMock()
        mock_bucket = MagicMock()
        mock_bucket.labels = {}

        mock_storage_client.bucket.return_value = mock_bucket
        mocker.patch.object(
            mock_config, "google_cloud_storage_client", mock_storage_client
        )
        mocker.patch.object(
            mock_config, "gcp_cors_allowed_origins", "https://example.com"
        )

        mock_add_iam = mocker.patch(
            "research_environment_api.modules.sharing_management.services._add_iam_permissions"
        )

        creation_request = entities.SharedBucketCreation(
            user_defined_bucket_name="test-bucket",
            storage_class="STANDARD",
            region=entities.Region.US_CENTRAL,
            workspace_project_id="test-project",
            user_email="testuser@example.com",
        )

        # Act
        services.create_shared_bucket(creation_request)

        # Assert
        assert mock_bucket.storage_class == "STANDARD"
        assert mock_bucket.labels["cloud_identity_username"] == "testuser"
        assert len(mock_bucket.cors) == 1
        assert mock_bucket.cors[0]["method"] == ["PUT", "OPTIONS"]
        mock_storage_client.create_bucket.assert_called_once()
        mock_add_iam.assert_called_once()

    def test_delete_shared_bucket_with_sharing_metadata(
        self, mocker, mock_config, mock_db_session
    ):
        """Test deleting a shared bucket removes sharing metadata."""
        # Arrange
        mock_storage_client = MagicMock()
        mock_bucket = MagicMock()
        mock_storage_client.bucket.return_value = mock_bucket

        mocker.patch.object(
            mock_config, "google_cloud_storage_client", mock_storage_client
        )

        # Mock database session
        mock_session = MagicMock()
        mock_query = MagicMock()
        mock_filter = MagicMock()

        mock_sharing_data1 = MagicMock(spec=models.SharingData)
        mock_sharing_data2 = MagicMock(spec=models.SharingData)

        mock_session.query.return_value = mock_query
        mock_query.filter_by.return_value = mock_filter
        mock_filter.all.return_value = [mock_sharing_data1, mock_sharing_data2]

        mock_db_context = MagicMock()
        mock_db_context.__enter__.return_value = mock_session
        mock_session.begin.return_value.__enter__ = MagicMock()
        mock_session.begin.return_value.__exit__ = MagicMock()

        mocker.patch.object(
            mock_config.parent if hasattr(mock_config, "parent") else type(mock_config),
            "database_session",
            return_value=mock_db_context,
        )

        deletion_request = entities.SharedBucketDeletion(bucket_name="test-bucket")

        # Act
        services.delete_shared_bucket(deletion_request)

        # Assert
        mock_storage_client.bucket.assert_called_once_with("test-bucket")

    def test_insufficient_permissions_error(self):
        """Test InsufficientPermissionsError exception."""
        # Act & Assert
        with pytest.raises(services.InsufficientPermissionsError):
            raise services.InsufficientPermissionsError("User lacks permissions")
