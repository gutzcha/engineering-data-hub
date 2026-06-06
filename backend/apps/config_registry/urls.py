from django.urls import path

from apps.config_registry import views

urlpatterns = [
    path("active/", views.active_config, name="config-active"),
    path("drafts/", views.create_draft, name="config-draft-create"),
    path("drafts/<int:draft_id>/validate/", views.validate_config_draft, name="config-draft-validate"),
    path("drafts/<int:draft_id>/publish/", views.publish_config_draft, name="config-draft-publish"),
]
