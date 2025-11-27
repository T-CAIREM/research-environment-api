import pytest
from unittest.mock import MagicMock, patch, call
from datetime import datetime, timedelta, timezone

from research_environment_api.modules.workbench_management import (
    entities,
    services,
    models as workbench_models
)
from research_environment_api.background import enums
from research_environment_api.modules.app import app

# Używamy aliasów dla długich ścieżek importów przy patchowaniu
SCHEDULERS_PATH = "research_environment_api.modules.workbench_management.services.schedulers"
SERVICES_PATH = "research_environment_api.modules.workbench_management.services"


class TestWorkbenchServices:

    # --- 1. LISTING WORKBENCHES ---

    def test_list_workbenches(self, mocker):
        """Sprawdza, czy maszyny z GCP są poprawnie zwracane."""
        mock_instance = MagicMock(
            name="test-wb", id="123", status="RUNNING",
            labels={}, machine_type="n1-standard-1", disks=[]
        )
        mocker.patch(f"{SERVICES_PATH}._fetch_gce_instances_raw", return_value=[mock_instance])

        mock_wb = MagicMock(spec=entities.Workbench, id="123")
        mocker.patch.object(entities.Workbench, "from_gce_instance", return_value=mock_wb)

        result = list(services.list_workbenches("proj", [], "user@test.com", is_owner=True))

        assert len(result) == 1
        assert result[0] == mock_wb

    def test_list_workbenches_deduplication(self, mocker):
        """Sprawdza, czy maszyna istniejąca w GCP nie jest dublowana przez Scaffolding (Creating)."""
        # 1. Maszyna już istnieje w GCP
        mock_instance = MagicMock(id="123")
        mocker.patch(f"{SERVICES_PATH}._fetch_gce_instances_raw", return_value=[mock_instance])
        mocker.patch.object(entities.Workbench, "from_gce_instance", return_value=MagicMock(id="123"))

        # 2. Workflow twierdzi, że maszyna o tym samym ID (123) się tworzy
        workflow = MagicMock(workbench_id="123", build_type=enums.BuildType.WORKBENCH_CREATION)
        workflow.workspace_id = "proj"

        result = list(services.list_workbenches("proj", [workflow], "user@test.com", is_owner=True))

        # Oczekujemy 1 elementu (istniejącego), a nie 2
        assert len(result) == 1
        assert result[0].id == "123"

    def test_list_workbenches_shared_only(self, mocker):
        """Sprawdza, czy osoba niebędąca właścicielem widzi tylko udostępnione maszyny."""
        mocker.patch(f"{SERVICES_PATH}._fetch_gce_instances_raw", return_value=[])
        mock_shared = mocker.patch(f"{SERVICES_PATH}._get_shared_workbenches_for_project", return_value=[])

        result = list(services.list_workbenches("proj", [], "collab@test.com", is_owner=False))

        mock_shared.assert_called_once()
        assert result == []

    # --- 2. GPU VALIDATION ---

    @pytest.mark.parametrize("gpu_name, expected", [
        ("NVIDIA_TESLA_T4", True),
        ("INVALID_POTATO", False),
    ])
    def test_validate_gpu_jupyter(self, gpu_name, expected):
        assert services.validate_gpu_accelerator("proj", gpu_name, "jupyter") is expected

    def test_validate_gpu_rstudio(self, mocker, mock_config):
        """Test walidacji GPU dla RStudio (wymaga zapytania do API)."""
        mock_client = MagicMock()
        # Mock struktury: [(zone, {accelerator_types: [obj]})]
        mock_acc_type = MagicMock()
        mock_acc_type.name = "nvidia-tesla-t4"
        mock_client.aggregated_list.return_value = [("zone", MagicMock(accelerator_types=[mock_acc_type]))]

        mock_config.google_compute_engine_accelerator_types_client = mock_client

        assert services.validate_gpu_accelerator("proj", "nvidia-tesla-t4", "rstudio") is True
        assert services.validate_gpu_accelerator("proj", "invalid", "rstudio") is False

    # --- 3. COLLABORATORS MANAGEMENT ---

    def test_add_collaborators_success(self, mocker, mock_config, mock_db_session):
        """Sprawdza success path: IAM API OK -> DB Status SUCCESS."""
        mock_config.google_iam_client = MagicMock()
        mocker.patch(f"{SERVICES_PATH}.add_iam_binding", return_value=True)

        # Mock brak istniejącego rekordu
        mock_db_session.query.return_value.filter_by.return_value.first.return_value = None

        req = entities.WorkbenchCollaboratorModification("proj", "sa", ["u@test.com"])
        services.add_collaborators_to_workbench(req)

        # Sprawdź czy dodano obiekt do sesji
        assert mock_db_session.add.called
        args, _ = mock_db_session.add.call_args
        obj = args[0]
        assert isinstance(obj, workbench_models.WorkbenchCollaboratorData)
        assert obj.status == workbench_models.CollaboratorStatus.SUCCESS

    def test_remove_collaborators_failure_handling(self, mocker, mock_config, mock_db_session):
        """Sprawdza error path: IAM API Fail -> DB Status FAILED/REMOVED handled correctly."""
        mock_config.google_iam_client = MagicMock()
        mocker.patch(f"{SERVICES_PATH}.remove_iam_binding", side_effect=Exception("IAM Error"))

        # Mock istniejący rekord w bazie
        existing_record = MagicMock(spec=workbench_models.WorkbenchCollaboratorData)
        mock_db_session.query.return_value.filter_by.return_value.first.return_value = existing_record

        req = entities.WorkbenchCollaboratorModification("proj", "sa", ["u@test.com"])
        services.remove_collaborators_from_workbench(req)

        # Status powinien zmienić się na FAILED, bo API rzuciło błąd
        assert existing_record.status == workbench_models.CollaboratorStatus.FAILED

    def test_remove_collaborators_success(self, mocker, mock_config, mock_db_session):
        """Sprawdza success path dla usuwania."""
        mock_config.google_iam_client = MagicMock()
        mocker.patch(f"{SERVICES_PATH}.remove_iam_binding", return_value=True)

        existing_record = MagicMock(spec=workbench_models.WorkbenchCollaboratorData)
        mock_db_session.query.return_value.filter_by.return_value.first.return_value = existing_record

        req = entities.WorkbenchCollaboratorModification("proj", "sa", ["u@test.com"])
        services.remove_collaborators_from_workbench(req)

        assert existing_record.status == workbench_models.CollaboratorStatus.REMOVED
        assert existing_record.viewed is True

    # --- 4. NOTIFICATIONS ---

    def test_get_workbench_notifications(self, mock_db_session):
        """Test pobierania powiadomień."""
        # Mock rekordu w bazie
        notification = MagicMock()
        notification.id = "notif-1"
        notification.collaborator_email = "test@example.com"
        notification.created_at = datetime(2023, 1, 1)

        mock_db_session.query.return_value.filter_by.return_value.order_by.return_value.limit.return_value.all.return_value = [
            notification]

        req = entities.WorkbenchGetNotifications("proj", "sa")
        result = services.get_workbench_notifications(req)

        assert len(result["notifications"]) == 1
        assert result["notifications"][0]["email"] == "test@example.com"

    def test_mark_notification_as_viewed(self, mock_db_session):
        """Test oznaczania powiadomienia jako przeczytane."""
        notification = MagicMock()
        notification.viewed = False
        mock_db_session.query.return_value.filter_by.return_value.first.return_value = notification

        result = services.mark_notification_as_viewed("notif-1")

        assert result is True
        assert notification.viewed is True

    # --- 6. SCHEDULER ROUTING (DRY Version) ---

    @pytest.mark.parametrize("wb_type, expected_func", [
        ("jupyter", "create_jupyter_workbench"),
        ("rstudio", "create_rstudio_workbench"),
        ("collaborative", "create_collaborative_workbench"),
    ])
    def test_schedule_create_routing(self, mocker, wb_type, expected_func):
        """Sparametryzowany test routingu dla tworzenia."""
        mock_sched = mocker.patch(f"{SCHEDULERS_PATH}.{expected_func}")
        req = MagicMock(workbench_type=wb_type)

        services.schedule_workbench_create(req)
        mock_sched.assert_called_once_with(req)

    @pytest.mark.parametrize("wb_type, expected_func", [
        ("jupyter", "stop_jupyter_workbench"),
        ("rstudio", "stop_compute_engine_workbench"),  # RStudio ma inną nazwę funkcji stopu!
        ("collaborative", "stop_collaborative_workbench"),
    ])
    def test_schedule_stop_routing(self, mocker, wb_type, expected_func):
        """Sparametryzowany test routingu dla stopowania."""
        mock_sched = mocker.patch(f"{SCHEDULERS_PATH}.{expected_func}")
        req = MagicMock(workbench_type=wb_type)

        services.schedule_workbench_stop(req)
        mock_sched.assert_called_once_with(req)

    @pytest.mark.parametrize("wb_type, expected_func", [
        ("jupyter", "start_jupyter_workbench"),
        ("rstudio", "start_rstudio_workbench"),
        ("collaborative", "start_collaborative_workbench"),
    ])
    def test_schedule_start_routing(self, mocker, wb_type, expected_func):
        """Sparametryzowany test routingu dla startowania."""
        mock_sched = mocker.patch(f"{SCHEDULERS_PATH}.{expected_func}")
        req = MagicMock(workbench_type=wb_type)

        services.schedule_workbench_start(req)
        mock_sched.assert_called_once_with(req)

    @pytest.mark.parametrize("wb_type, expected_func", [
        ("jupyter", "destroy_jupyter_workbench"),
        ("rstudio", "destroy_rstudio_workbench"),
        ("collaborative", "destroy_collaborative_workbench"),
    ])
    def test_schedule_destroy_routing(self, mocker, wb_type, expected_func):
        mock_sched = mocker.patch(f"{SCHEDULERS_PATH}.{expected_func}")
        req = MagicMock(workbench_type=wb_type)
        services.schedule_workbench_destroy(req)
        mock_sched.assert_called_once_with(req)

    def test_schedule_invalid_type(self):
        req = MagicMock(workbench_type="unknown")
        with pytest.raises(ValueError):
            services.schedule_workbench_create(req)