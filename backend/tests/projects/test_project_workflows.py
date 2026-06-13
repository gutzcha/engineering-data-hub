import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from rest_framework.test import APIClient


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def privileged_user(db):
    User = get_user_model()
    user = User.objects.create_user(username="project-privileged", password="test-pass")
    manager_group, _created = Group.objects.get_or_create(name="Project Manager")
    user.groups.add(manager_group)
    return user


@pytest.mark.django_db
def test_project_assignee_lookup_returns_users_only(api_client, privileged_user):
    api_client.force_authenticate(privileged_user)
    response = api_client.get("/api/accounts/lookup/users/?q=alex&scope=project")

    assert response.status_code == 200
    results = response.json()
    assert results
    assert {"id", "username", "display_name", "level"} <= set(results[0].keys())
