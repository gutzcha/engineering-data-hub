import json
from io import StringIO

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from apps.folders.models import FolderChangeEvent, ManagedFolder
from apps.projects.models import Project, ProjectTask
from apps.records.models import Record
from apps.reports.models import Dashboard
from apps.workflows.models import WorkflowTask


@pytest.mark.django_db
def test_client_readiness_seed_refuses_unsafe_target(settings, monkeypatch):
    settings.DEBUG = False
    monkeypatch.delenv("ALLOW_CLIENT_READINESS_SEED", raising=False)

    with pytest.raises(CommandError, match="Refusing to seed"):
        call_command("seed_client_readiness_demo", run_id="pytest-unsafe")


@pytest.mark.django_db
def test_client_readiness_seed_creates_manifest_and_operational_objects(monkeypatch):
    monkeypatch.setenv("ALLOW_CLIENT_READINESS_SEED", "true")
    output = StringIO()

    call_command("seed_client_readiness_demo", run_id="pytest-readiness", stdout=output)

    manifest = json.loads(output.getvalue())
    assert manifest["runId"] == "pytest-readiness"
    assert manifest["activeConfigVersion"] >= 1
    assert Record.objects.filter(pk=manifest["records"]["productRecordId"]).exists()
    assert len(manifest["projects"]) == 4
    assert len(manifest["projectTasks"]) == 16
    assert len(manifest["workflowTasks"]) == 4
    assert len(manifest["folderEvents"]) == 6
    assert len(manifest["managedFolders"]) == 1
    assert manifest["dashboardKey"].startswith("qa_client_readiness_")

    assert Project.objects.count() == 4
    assert ProjectTask.objects.count() == 16
    assert WorkflowTask.objects.filter(state=WorkflowTask.State.OPEN).count() == 4
    assert ManagedFolder.objects.count() == 1
    assert FolderChangeEvent.objects.filter(review_status=FolderChangeEvent.ReviewStatus.PENDING).count() == 4
    assert Dashboard.objects.filter(config__key=manifest["dashboardKey"]).exists()
