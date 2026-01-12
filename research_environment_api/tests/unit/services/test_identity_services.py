import pytest
from unittest.mock import MagicMock
from research_environment_api.modules.identity_management import (
    services,
    entities,
    exceptions,
)
from research_environment_api.library.google import workspace as google_workspace


class TestIdentityServices:
    def test_provision_cloud_identity_orchestration(self, mocker):
        """Ensure provision calls both user creation and billing permission steps."""
        # Arrange
        mock_create_user = mocker.patch(
            "research_environment_api.modules.identity_management.services._create_google_workspace_user"
        )
        mock_allow_billing = mocker.patch(
            "research_environment_api.modules.identity_management.services._allow_to_create_billing_accounts"
        )

        request = MagicMock(spec=entities.CloudIdentityCreation)

        # Act
        services.provision_cloud_identity(request)

        # Assert
        mock_create_user.assert_called_once_with(request)
        mock_allow_billing.assert_called_once_with(request)

    def test_create_user_handles_existing_user(self, mocker):
        """Test that UserAlreadyExistsError is caught and logged (idempotency)."""
        # Arrange
        mock_client = MagicMock()
        # Simulate Google throwing "User Exists"
        mock_client.create_user.side_effect = google_workspace.UserAlreadyExistsError(
            "Exists"
        )

        mocker.patch(
            "research_environment_api.modules.identity_management.services._build_google_workspace_client",
            return_value=mock_client,
        )
        mock_logger = mocker.patch(
            "research_environment_api.modules.identity_management.services.logger"
        )

        request = entities.CloudIdentityCreation(
            user_name="test",
            password="pw",
            recovery_email="rec@test.com",
            given_name="A",
            family_name="B",
        )

        # Act
        services._create_google_workspace_user(request)

        # Assert
        mock_logger.warning.assert_called()
        assert "already created" in mock_logger.warning.call_args[0][0]

    def test_allow_billing_handles_existing_membership(self, mocker, mock_config):
        """Test that GroupMembershipAlreadyExistsError is caught and logged."""
        # Arrange
        mock_client = MagicMock()
        mock_client.add_user_to_group.side_effect = (
            google_workspace.GroupMembershipAlreadyExistsError("Exists")
        )

        mocker.patch(
            "research_environment_api.modules.identity_management.services._build_google_workspace_client",
            return_value=mock_client,
        )
        mock_logger = mocker.patch(
            "research_environment_api.modules.identity_management.services.logger"
        )
        mock_config.billing_account_creator_group_id = "billing-group"

        request = MagicMock(primary_email="test@healthdatanexus.ai")

        # Act
        services._allow_to_create_billing_accounts(request)

        # Assert
        mock_logger.warning.assert_called()
        assert "already a member" in mock_logger.warning.call_args[0][0]
