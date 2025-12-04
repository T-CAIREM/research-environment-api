import pytest
from unittest.mock import MagicMock
from research_environment_api.modules.billing_management import services, enums
from research_environment_api.library.google import billing as billing_api


class TestBillingServices:
    """Test billing service layer logic."""

    def test_list_billing_accounts_for_user(self, mocker, mock_config):
        """Test listing billing accounts with role mapping."""
        # Arrange
        mock_client = MagicMock()
        mock_acct = MagicMock()
        mock_acct.name = "billingAccounts/123"
        mock_acct.display_name = "Test Billing"
        mock_client.list_active_billing_accounts.return_value = [mock_acct]
        mocker.patch.object(mock_config, "google_billing_client", mock_client)

        mocker.patch(
            "research_environment_api.modules.billing_management.services._billing_account_role_for",
            return_value=enums.BillingAccountRole.OWNER,
        )

        # Act
        result = services.list_billing_accounts_for("user@test.com")

        # Assert
        assert len(result) == 1
        assert result[0].id == "123"
        assert result[0].is_owner is True

    def test_share_billing_account(self, mocker, mock_config):
        """Test delegation to Google library."""
        # Arrange
        mock_client = MagicMock()
        mocker.patch.object(mock_config, "google_billing_client", mock_client)

        # Act
        services.share_billing_account_to("owner@t.com", "user@t.com", "123")

        # Assert
        mock_client.create_membership_binding_for_billing_account.assert_called_once_with(
            owner_email="owner@t.com", user_email="user@t.com", billing_account_id="123"
        )

    def test_revoke_billing_account(self, mocker, mock_config):
        """Test revocation delegation."""
        # Arrange
        mock_client = MagicMock()
        mocker.patch.object(mock_config, "google_billing_client", mock_client)

        # Act
        services.revoke_billing_account_access("owner@t.com", "user@t.com", "123")

        # Assert
        mock_client.remove_membership_binding_for_billing_account.assert_called_once()

    def test_format_billing_account_resource_name(self):
        """Test billing account name formatting."""
        # Act
        result = services._format_billing_account_resource_name(
            "billingAccounts/123456-ABCDEF"
        )

        # Assert
        assert result == "123456-ABCDEF"

    def test_billing_account_cloud_link(self):
        """Test cloud console link generation."""
        # Act
        result = services._billing_account_cloud_link("test-account-id")

        # Assert
        assert result == "https://console.cloud.google.com/billing/test-account-id"
