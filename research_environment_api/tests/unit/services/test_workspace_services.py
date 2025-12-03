from unittest.mock import MagicMock

from research_environment_api.background import enums
from research_environment_api.modules.workspace_management import entities, services

SERVICES_PATH = "research_environment_api.modules.workspace_management.services"


class TestWorkspaceServices:


    def test_compute_accessibility_no_billing_account(self):
        """Test workspace is inaccessible when no billing account is connected."""
        billing_info = MagicMock(billing_account_id="", billing_enabled=False)
        is_accessible, reason = services._compute_accessibility(billing_info, [])
        assert is_accessible is False
        assert "No billing account connected" in reason

    def test_compute_accessibility_billing_disabled(self):
        """Test workspace is inaccessible when billing is disabled."""
        billing_info = MagicMock(billing_account_id="billing-123", billing_enabled=False)
        is_accessible, reason = services._compute_accessibility(billing_info, [])
        assert is_accessible is False
        assert "Billing account inactive or closed" in reason

    def test_compute_accessibility_service_errors(self):
        """Test workspace is inaccessible on specific service errors."""
        billing_info = MagicMock(billing_account_id="billing-123", billing_enabled=True)

        # Error that affects accessibility
        crit_error = MagicMock(error_type="permission_denied", message="Access denied")

        is_accessible, reason = services._compute_accessibility(billing_info, [crit_error])
        assert is_accessible is False
        assert "Access denied" in reason

    def test_compute_accessibility_success(self):
        """Test workspace is accessible with valid billing and no errors."""
        billing_info = MagicMock(billing_account_id="billing-123", billing_enabled=True)
        is_accessible, reason = services._compute_accessibility(billing_info, [])
        assert is_accessible is True
        assert reason is None


    def test_create_workspace(self, mocker):
        mock_scheduler = mocker.patch(f"{SERVICES_PATH}.schedulers.create_workspace")
        req = MagicMock(spec=entities.WorkspaceCreation)
        services.create_workspace(req)
        mock_scheduler.assert_called_once_with(req)

    def test_delete_workspace(self, mocker):
        mock_scheduler = mocker.patch(f"{SERVICES_PATH}.schedulers.destroy_workspace")
        req = MagicMock(spec=entities.WorkspaceDeletion)
        services.delete_workspace(req)
        mock_scheduler.assert_called_once_with(req)

    def test_create_shared_workspace(self, mocker):
        mock_scheduler = mocker.patch(f"{SERVICES_PATH}.schedulers.create_shared_workspace")
        req = MagicMock(spec=entities.SharedWorkspaceCreation)
        services.create_shared_workspace(req)
        mock_scheduler.assert_called_once_with(req)

    def test_delete_shared_workspace(self, mocker):
        mock_scheduler = mocker.patch(f"{SERVICES_PATH}.schedulers.destroy_shared_workspace")
        req = MagicMock(spec=entities.SharedWorkspaceDeletion)
        services.delete_shared_workspace(req)
        mock_scheduler.assert_called_once_with(req)


    def test_list_active_workspaces_flow(self, mocker):
        """Tests the listing flow"""
        # Arrange
        owned_proj = MagicMock(project_id="owned-1")
        collab_proj = MagicMock(project_id="collab-1")

        mocker.patch(f"{SERVICES_PATH}._list_active_google_projects", return_value=[owned_proj])
        mocker.patch(f"{SERVICES_PATH}._get_collaborative_workspaces", return_value=[collab_proj])

        workflow = MagicMock(
            id="flow-1", workspace_id="new-ws",
            build_type=enums.BuildType.WORKSPACE_CREATION
        )
        mocker.patch(f"{SERVICES_PATH}.monitoring_services.list_active_workflows", return_value=[workflow])

        mock_ws_owned = MagicMock(gcp_project_id="owned-1", status=entities.WorkspaceStatus.CREATED)

        builder_mock = mocker.patch(f"{SERVICES_PATH}._build_workspace_entity")
        builder_mock.side_effect = [mock_ws_owned, None]  # First call -> WS, second -> None (simulate no access)
        query = entities.WorkspaceListQuery(email="user@test.com")

        # Act
        result = list(services.list_active_workspaces(query))

        # Assert
        # Expect: 1 owned (built), 0 collab, 1 scaffolding
        assert len(result) == 2

        assert result[0].gcp_project_id == "owned-1"
        assert result[1].status == entities.WorkspaceStatus.CREATING
        assert result[1].gcp_project_id == "new-ws"

    def test_build_workspace_entity_happy_path(self, mocker):
        """Test building a Workspace entity when everything works."""
        # Arrange
        gcp_project = MagicMock(project_id="p1", name="projects/p1",
                                labels={"region": "us", "cloud_identity_username": "user"})

        billing_info = entities.BillingInfo(billing_account_id="123", billing_enabled=True)
        workbenches = [MagicMock()]

        mocker.patch(f"{SERVICES_PATH}._build_billing_entity", return_value=billing_info)

        mock_safe_call = mocker.patch(f"{SERVICES_PATH}.safe_google_service_call")
        mock_safe_call.side_effect = [
            (billing_info, None),
            (workbenches, None)
        ]

        # Act
        entity = services._build_workspace_entity(
            gcp_project,
            workflows_in_progress=[],
            user_email="user@test.com"
        )

        # Assert
        assert entity is not None
        assert entity.gcp_project_id == "p1"
        assert entity.is_accessible is True
        assert len(entity.workbenches) == 1
        assert len(entity.service_errors) == 0

    def test_build_workspace_entity_hides_non_owned_empty(self, mocker):
        """
        Checks if the function hides a project if:
        - We are not the owner
        - There are no workbenches
        - There are no errors
        """
        # Arrange

        gcp_project = MagicMock(project_id="p1", name="projects/p1",
                                labels={"region": "us", "cloud_identity_username": "owner"})

        mocker.patch(f"{SERVICES_PATH}._build_billing_entity", return_value=MagicMock())

        mock_safe_call = mocker.patch(f"{SERVICES_PATH}.safe_google_service_call")
        mock_safe_call.side_effect = [
            (MagicMock(), None),
            ([], None)
        ]

        # Act
        entity = services._build_workspace_entity(
            gcp_project,
            workflows_in_progress=[],
            user_email="collaborator@test.com"
        )

        # Assert
        assert entity is None

    def test_build_workspace_entity_with_service_errors(self, mocker):
        """Test building entity when external services throw errors."""
        # Arrange
        gcp_project = MagicMock(project_id="p1", name="projects/p1",
                                labels={"region": "us", "cloud_identity_username": "user"})

        billing_error = MagicMock(error_type="permission_denied", message="Err")

        mocker.patch(f"{SERVICES_PATH}._build_billing_entity", return_value=MagicMock())

        mock_safe_call = mocker.patch(f"{SERVICES_PATH}.safe_google_service_call")
        mock_safe_call.side_effect = [
            (MagicMock(billing_enabled=False), billing_error),
            ([], None)
        ]

        # Act
        entity = services._build_workspace_entity(
            gcp_project,
            workflows_in_progress=[],
            user_email="user@test.com"
        )

        # Assert
        assert entity is not None
        assert len(entity.service_errors) == 1
        assert entity.is_accessible is False


    def test_build_shared_workspace_entity(self, mocker):
        """Test building entity for Shared Workspace."""
        # Arrange
        gcp_project = MagicMock(project_id="p1", name="projects/p1", labels={"cloud_identity_username": "owner"})

        buckets = [MagicMock(name="bucket-1")]

        mocker.patch(f"{SERVICES_PATH}._build_billing_entity", return_value=MagicMock())

        mock_safe_call = mocker.patch(f"{SERVICES_PATH}.safe_google_service_call")
        mock_safe_call.side_effect = [
            (MagicMock(), None),
            (buckets, None)
        ]

        # Act
        entity = services._build_shared_workspace_entity(
            gcp_project, [], "user@test.com", "user"
        )

        # Assert
        assert isinstance(entity, entities.SharedWorkspace)
        assert entity.buckets == buckets
        assert entity.is_owner is False


    def test_update_workspace_billing_account(self, mock_config):
        """Test updating billing account."""
        # Act
        services.update_workspace_billing_account("ws-1", "bill-123")

        # Assert
        mock_config.google_cloud_billing_client.update_project_billing_info.assert_called_once()
        call_args = mock_config.google_cloud_billing_client.update_project_billing_info.call_args
        assert call_args.kwargs['name'] == "projects/ws-1"
        assert call_args.kwargs['project_billing_info'].billing_account_name == "billingAccounts/bill-123"