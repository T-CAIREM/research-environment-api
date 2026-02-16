import pytest
from unittest.mock import MagicMock
from research_environment_api.modules.user_group_management import entities, services
from research_environment_api.modules.user_group_management.exceptions import (
    GoogleGroupAlreadyExists,
)
from googleapiclient.errors import HttpError


class TestUserGroupServices:
    def test_get_full_group_name(self):
        """Test group name formatting."""
        # Act
        result = services._get_full_group_name("test-group")

        # Assert
        assert result == "hdn-test-group@healthdatanexus.ai"

    def test_extract_group_name(self):
        """Test extracting group name from full string."""
        # Act
        result = services._extract_group_name("group:hdn-test-group@healthdatanexus.ai")

        # Assert
        assert result == "test-group"

    def test_create_group_success(self, mocker, mock_config):
        """Test successful group creation."""
        # Arrange
        mock_identity_client = MagicMock()
        mock_groups = MagicMock()
        mock_create = MagicMock()

        mock_identity_client.groups.return_value = mock_groups
        mock_groups.create.return_value = mock_create
        mock_create.execute.return_value = {
            "name": "groups/123",
            "displayName": "hdn-test-group",
        }

        mocker.patch.object(mock_config, "cloud_identity_client", mock_identity_client)

        creation_entity = entities.UserGroupCreation(
            group_name="test-group", description="Test group description"
        )

        # Act
        result = services.create_group(creation_entity)

        # Assert
        assert result["name"] == "groups/123"
        mock_groups.create.assert_called_once()
        call_args = mock_groups.create.call_args
        assert call_args[1]["initialGroupConfig"] == "WITH_INITIAL_OWNER"

    def test_create_group_already_exists(self, mocker, mock_config):
        """Test creating a group that already exists raises exception."""
        # Arrange
        mock_identity_client = MagicMock()
        mock_groups = MagicMock()
        mock_create = MagicMock()

        http_error = HttpError(
            resp=MagicMock(status=409), content=b"Group already exists"
        )

        mock_identity_client.groups.return_value = mock_groups
        mock_groups.create.return_value = mock_create
        mock_create.execute.side_effect = http_error

        mocker.patch.object(mock_config, "cloud_identity_client", mock_identity_client)

        creation_entity = entities.UserGroupCreation(
            group_name="existing-group", description="Test group"
        )

        # Act & Assert
        with pytest.raises(GoogleGroupAlreadyExists):
            services.create_group(creation_entity)

    def test_create_group_other_error_propagates(self, mocker, mock_config):
        """Test that non-409 HTTP errors are propagated."""
        # Arrange
        mock_identity_client = MagicMock()
        mock_groups = MagicMock()
        mock_create = MagicMock()

        http_error = HttpError(
            resp=MagicMock(status=500), content=b"Internal server error"
        )

        mock_identity_client.groups.return_value = mock_groups
        mock_groups.create.return_value = mock_create
        mock_create.execute.side_effect = http_error

        mocker.patch.object(mock_config, "cloud_identity_client", mock_identity_client)

        creation_entity = entities.UserGroupCreation(
            group_name="test-group", description="Test group"
        )

        # Act & Assert
        with pytest.raises(HttpError) as exc_info:
            services.create_group(creation_entity)
        assert exc_info.value.status_code == 500

    def test_delete_group(self, mocker, mock_config):
        """Test group deletion."""
        # Arrange
        mock_identity_client = MagicMock()
        mock_groups = MagicMock()
        mock_lookup = MagicMock()
        mock_delete = MagicMock()

        mock_identity_client.groups.return_value = mock_groups
        mock_groups.lookup.return_value = mock_lookup
        mock_lookup.execute.return_value = {"name": "groups/123"}
        mock_groups.delete.return_value = mock_delete
        mock_delete.execute.return_value = {}

        mocker.patch.object(mock_config, "cloud_identity_client", mock_identity_client)

        deletion_entity = entities.UserGroupDeletion(group_name="test-group")

        # Act
        result = services.delete_group(deletion_entity)

        # Assert
        mock_groups.lookup.assert_called_once()
        mock_groups.delete.assert_called_once_with(name="groups/123")
        assert result == {}

    def test_get_roles_associated_with_group(self, mocker, mock_config):
        """Test retrieving IAM roles associated with a group."""
        # Arrange
        mock_org_client = MagicMock()

        # Create mock bindings
        binding1 = MagicMock()
        binding1.role = "roles/viewer"
        binding1.members = [
            "group:hdn-test-group@healthdatanexus.ai",
            "user:other@example.com",
        ]

        binding2 = MagicMock()
        binding2.role = "roles/editor"
        binding2.members = ["user:someone@example.com"]

        binding3 = MagicMock()
        binding3.role = "roles/owner"
        binding3.members = ["group:hdn-test-group@healthdatanexus.ai"]

        mock_policy = MagicMock()
        mock_policy.bindings = [binding1, binding2, binding3]

        mock_org_client.get_iam_policy.return_value = mock_policy
        mocker.patch.object(mock_config, "organization_client", mock_org_client)

        # Act
        roles = services._get_roles_associated_with_group("test-group", "123456789")

        # Assert
        assert len(roles) == 2
        assert "roles/viewer" in roles
        assert "roles/owner" in roles
        assert "roles/editor" not in roles  # Group not in this binding

    def test_get_roles_associated_with_service_account(self, mocker, mock_config):
        """Test retrieving IAM roles associated with a service account."""
        # Arrange
        mock_projects_client = MagicMock()

        # Create mock bindings
        binding1 = MagicMock()
        binding1.role = "roles/compute.admin"
        binding1.members = [
            "serviceAccount:test-sa@healthdatanexus.ai",
            "user:other@example.com",
        ]

        binding2 = MagicMock()
        binding2.role = "roles/storage.admin"
        binding2.members = ["serviceAccount:other-sa@healthdatanexus.ai"]

        mock_policy = MagicMock()
        mock_policy.bindings = [binding1, binding2]

        mock_projects_client.get_iam_policy.return_value = mock_policy
        mocker.patch.object(
            mock_config, "google_cloud_resource_client", mock_projects_client
        )

        # Act
        roles = services.get_roles_associated_with_service_account(
            "test-sa", "test-project"
        )

        # Assert
        assert len(roles) == 1
        assert "roles/compute.admin" in roles
        assert "roles/storage.admin" not in roles
