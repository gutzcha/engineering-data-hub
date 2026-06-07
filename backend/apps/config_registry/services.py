import copy
import re

from django.db import transaction

from apps.audit.services import record_audit_event
from apps.config_registry.models import (
    ConfigurationDraft,
    ConfigurationSequence,
    ConfigurationVersion,
    DashboardDefinition,
    FieldDefinition,
    FolderTemplateDefinition,
    FormLayoutDefinition,
    ObjectTypeDefinition,
)
from apps.config_registry.seed import starter_configuration_data


ALLOWED_FIELD_TYPES = {
    "text",
    "long_text",
    "number",
    "date",
    "boolean",
    "choice",
    "multi_choice",
    "record_ref",
    "file_ref",
    "url",
    "user_ref",
}
SNAKE_CASE_RE = re.compile(r"^[a-z][a-z0-9_]*$")
CONFIG_REGISTRY_MANAGED_KEY = "config_registry_managed"


class ConfigurationValidationError(ValueError):
    def __init__(self, errors):
        self.errors = errors
        super().__init__("Configuration draft is invalid.")


def create_draft_from_current(user) -> ConfigurationDraft:
    active_config = ConfigurationVersion.objects.order_by("-version").first()
    data = copy.deepcopy(active_config.data if active_config else starter_configuration_data())
    return ConfigurationDraft.objects.create(data=data, created_by=user, updated_by=user)


def validate_draft(draft: ConfigurationDraft) -> list[dict]:
    errors = []
    data = draft.data
    if not isinstance(data, dict):
        return [
            {
                "path": "",
                "code": "invalid_configuration",
                "message": "Configuration data must be an object.",
            }
        ]

    object_types = data.get("object_types")

    if not isinstance(object_types, list):
        errors.append(
            {
                "path": "object_types",
                "code": "invalid_object_types",
                "message": "Object types must be a list.",
            }
        )
    else:
        _validate_object_types(object_types, errors)

    object_type_keys = _valid_object_type_keys(object_types)
    _validate_relationship_types(data, object_type_keys, errors)

    _validate_keyed_definition_section(
        data,
        "form_layouts",
        "form layout",
        "form_layout",
        errors,
    )
    _validate_keyed_definition_section(
        data,
        "folder_templates",
        "folder template",
        "folder_template",
        errors,
    )
    _validate_keyed_definition_section(data, "dashboards", "dashboard", "dashboard", errors)

    return errors


def _valid_object_type_keys(object_types):
    if not isinstance(object_types, list):
        return set()
    return {
        object_type.get("key")
        for object_type in object_types
        if isinstance(object_type, dict) and _is_snake_case_key(object_type.get("key"))
    }


def _validate_object_types(object_types, errors):
    seen_object_type_keys = set()
    for object_index, object_type in enumerate(object_types):
        object_path = f"object_types[{object_index}]"
        if not _validate_mapping(object_type, object_path, "object type", "object_type", errors):
            continue

        object_key = object_type.get("key")
        if not _is_snake_case_key(object_key):
            errors.append(
                {
                    "path": f"{object_path}.key",
                    "code": "invalid_object_type_key",
                    "message": "Object type keys must use lowercase snake case.",
                }
            )
        elif object_key in seen_object_type_keys:
            errors.append(
                {
                    "path": f"{object_path}.key",
                    "code": "duplicate_object_type_key",
                    "message": "Object type keys must be unique.",
                }
            )
        else:
            seen_object_type_keys.add(object_key)

        fields = object_type.get("fields")
        if not isinstance(fields, list):
            errors.append(
                {
                    "path": f"{object_path}.fields",
                    "code": "invalid_fields",
                    "message": "Fields must be a list.",
                }
            )
            continue

        _validate_fields(fields, object_path, errors)


def _validate_relationship_types(data, object_type_keys, errors):
    if "relationship_types" not in data:
        return

    relationship_types = data["relationship_types"]
    if not isinstance(relationship_types, list):
        errors.append(
            {
                "path": "relationship_types",
                "code": "invalid_relationship_types",
                "message": "Relationship types must be a list.",
            }
        )
        return

    seen_keys = set()
    for relationship_index, relationship_type in enumerate(relationship_types):
        path = f"relationship_types[{relationship_index}]"
        if not _validate_mapping(
            relationship_type,
            path,
            "relationship type",
            "relationship_type",
            errors,
        ):
            continue

        key = relationship_type.get("key")
        if not _is_snake_case_key(key):
            errors.append(
                {
                    "path": f"{path}.key",
                    "code": "invalid_relationship_type_key",
                    "message": "Relationship type keys must use lowercase snake case.",
                }
            )
        elif key in seen_keys:
            errors.append(
                {
                    "path": f"{path}.key",
                    "code": "duplicate_relationship_type_key",
                    "message": "Relationship type keys must be unique.",
                }
            )
        else:
            seen_keys.add(key)

        _validate_relationship_object_type_reference(
            relationship_type,
            "source_object_type",
            "source",
            object_type_keys,
            path,
            errors,
        )
        _validate_relationship_object_type_reference(
            relationship_type,
            "target_object_type",
            "target",
            object_type_keys,
            path,
            errors,
        )


def _validate_relationship_object_type_reference(
    relationship_type,
    field,
    direction,
    object_type_keys,
    path,
    errors,
):
    if field not in relationship_type:
        return

    object_type_key = relationship_type.get(field)
    if object_type_key not in object_type_keys:
        errors.append(
            {
                "path": f"{path}.{field}",
                "code": f"unknown_relationship_{direction}_object_type",
                "message": f"Relationship {direction} object type must reference an object type.",
            }
        )


def _validate_fields(fields, object_path, errors):
    seen_field_keys = set()
    for field_index, field in enumerate(fields):
        field_path = f"{object_path}.fields[{field_index}]"
        if not _validate_mapping(field, field_path, "field", "field", errors):
            continue

        field_key = field.get("key")
        if not _is_snake_case_key(field_key):
            errors.append(
                {
                    "path": f"{field_path}.key",
                    "code": "invalid_field_key",
                    "message": "Field keys must use lowercase snake case.",
                }
            )
        elif field_key in seen_field_keys:
            errors.append(
                {
                    "path": f"{field_path}.key",
                    "code": "duplicate_field_key",
                    "message": "Field keys must be unique within an object type.",
                }
            )
        else:
            seen_field_keys.add(field_key)

        if field.get("type") not in ALLOWED_FIELD_TYPES:
            errors.append(
                {
                    "path": f"{field_path}.type",
                    "code": "invalid_field_type",
                    "message": "Field type must be one of the v1 allowed field types.",
                }
            )


def _validate_keyed_definition_section(data, section, singular_label, code_label, errors):
    if section not in data:
        return

    definitions = data[section]
    if not isinstance(definitions, list):
        errors.append(
            {
                "path": section,
                "code": f"invalid_{section}",
                "message": f"{section.replace('_', ' ').capitalize()} must be a list.",
            }
        )
        return

    seen_keys = set()
    for index, definition in enumerate(definitions):
        path = f"{section}[{index}]"
        if not _validate_mapping(definition, path, singular_label, code_label, errors):
            continue

        key = definition.get("key")
        if not _is_snake_case_key(key):
            errors.append(
                {
                    "path": f"{path}.key",
                    "code": f"invalid_{code_label}_key",
                    "message": f"{singular_label.capitalize()} keys must use lowercase snake case.",
                }
            )
        elif key in seen_keys:
            errors.append(
                {
                    "path": f"{path}.key",
                    "code": f"duplicate_{code_label}_key",
                    "message": f"{singular_label.capitalize()} keys must be unique.",
                }
            )
        else:
            seen_keys.add(key)


def _validate_mapping(value, path, label, code_label, errors):
    if isinstance(value, dict):
        return True

    errors.append(
        {
            "path": path,
            "code": f"invalid_{code_label}",
            "message": f"{label.capitalize()} definitions must be objects.",
        }
    )
    return False


@transaction.atomic
def publish_draft(draft: ConfigurationDraft, user, request=None) -> ConfigurationVersion:
    if draft.pk:
        draft = ConfigurationDraft.objects.select_for_update().get(pk=draft.pk)

    if draft.status != ConfigurationDraft.Status.DRAFT:
        raise ConfigurationValidationError(
            [
                {
                    "path": "status",
                    "code": "draft_not_publishable",
                    "message": "Only draft configurations can be published.",
                }
            ]
        )

    errors = validate_draft(draft)
    if errors:
        raise ConfigurationValidationError(errors)

    configuration_version = ConfigurationVersion.objects.create(
        version=_allocate_next_version(),
        data=copy.deepcopy(draft.data),
        published_by=user,
    )
    _sync_definition_models(configuration_version)
    _sync_runtime_models(configuration_version)

    draft.status = ConfigurationDraft.Status.PUBLISHED
    draft.published_version = configuration_version
    draft.updated_by = user
    draft.save(update_fields=["status", "published_version", "updated_by", "updated_at"])
    record_audit_event(
        user,
        "configuration.published",
        configuration_version,
        before=None,
        after={
            "id": configuration_version.pk,
            "version": configuration_version.version,
            "data": copy.deepcopy(configuration_version.data),
        },
        request=request,
    )
    return configuration_version


def get_active_config() -> ConfigurationVersion:
    return ConfigurationVersion.objects.order_by("-version").first()


def _is_snake_case_key(value):
    return isinstance(value, str) and SNAKE_CASE_RE.fullmatch(value) is not None


def _allocate_next_version():
    sequence, _created = ConfigurationSequence.objects.select_for_update().get_or_create(
        pk=1,
        defaults={"next_version": 1},
    )
    version = sequence.next_version
    sequence.next_version += 1
    sequence.save(update_fields=["next_version"])
    return version


def _sync_definition_models(configuration_version):
    data = configuration_version.data
    object_type_models = {}

    for object_type in data.get("object_types", []):
        object_model = ObjectTypeDefinition.objects.create(
            configuration_version=configuration_version,
            key=object_type["key"],
            label=object_type.get("label", object_type["key"]),
            plural_label=object_type.get("plural_label", ""),
            payload=copy.deepcopy(object_type),
        )
        object_type_models[object_type["key"]] = object_model
        for field in object_type.get("fields", []):
            FieldDefinition.objects.create(
                object_type=object_model,
                key=field["key"],
                label=field.get("label", field["key"]),
                field_type=field["type"],
                required=field.get("required", False),
                payload=copy.deepcopy(field),
            )

    for layout in data.get("form_layouts", []):
        FormLayoutDefinition.objects.create(
            configuration_version=configuration_version,
            key=layout["key"],
            label=layout.get("label", ""),
            payload=copy.deepcopy(layout),
        )

    for template in data.get("folder_templates", []):
        FolderTemplateDefinition.objects.create(
            configuration_version=configuration_version,
            key=template["key"],
            label=template.get("label", ""),
            payload=copy.deepcopy(template),
        )

    for dashboard in data.get("dashboards", []):
        DashboardDefinition.objects.create(
            configuration_version=configuration_version,
            key=dashboard["key"],
            label=dashboard.get("label", ""),
            payload=copy.deepcopy(dashboard),
        )


def _sync_runtime_models(configuration_version):
    data = configuration_version.data
    _sync_runtime_workflows(configuration_version, data)
    _sync_runtime_dashboards(configuration_version, data)


def _sync_runtime_workflows(configuration_version, data):
    from apps.workflows.models import WorkflowDefinition, WorkflowTransition

    workflow_by_key = {
        workflow.get("key"): workflow
        for workflow in data.get("workflows", [])
        if isinstance(workflow, dict) and _is_snake_case_key(workflow.get("key"))
    }
    assignments = _workflow_assignments(data, workflow_by_key)
    current_runtime_keys = set()

    for workflow_key, object_type_keys in assignments.items():
        workflow = workflow_by_key[workflow_key]
        for index, object_type_key in enumerate(object_type_keys):
            runtime_key = _runtime_workflow_key(
                workflow_key,
                object_type_key,
                index,
                len(object_type_keys),
            )
            existing = WorkflowDefinition.objects.filter(key=runtime_key).first()
            if existing and not _is_config_registry_managed(existing.data):
                continue
            current_runtime_keys.add(runtime_key)

            definition, _created = WorkflowDefinition.objects.update_or_create(
                key=runtime_key,
                defaults={
                    "name": workflow.get("label") or workflow.get("name") or workflow_key,
                    "object_type_key": object_type_key,
                    "initial_state": _initial_workflow_state(workflow),
                    "version": configuration_version.version,
                    "is_active": True,
                    "data": _managed_runtime_payload(
                        configuration_version,
                        workflow,
                        source_key=workflow_key,
                        object_type_key=object_type_key,
                    ),
                },
            )
            WorkflowTransition.objects.filter(definition=definition).delete()
            for sort_order, transition in enumerate(
                _runtime_transitions(workflow, object_type_key, data)
            ):
                WorkflowTransition.objects.create(
                    definition=definition,
                    sort_order=sort_order,
                    **transition,
                )
    _deactivate_stale_config_managed_workflows(current_runtime_keys)


def _workflow_assignments(data, workflow_by_key):
    assignments = {workflow_key: [] for workflow_key in workflow_by_key}

    for object_type in data.get("object_types", []):
        if not isinstance(object_type, dict):
            continue
        workflow_key = object_type.get("default_workflow_key")
        object_type_key = object_type.get("key")
        if workflow_key in assignments and _is_snake_case_key(object_type_key):
            _append_unique(assignments[workflow_key], object_type_key)

    for workflow_key, workflow in workflow_by_key.items():
        for object_type_key in _explicit_workflow_object_types(workflow):
            if _is_snake_case_key(object_type_key):
                _append_unique(assignments[workflow_key], object_type_key)

    return {
        workflow_key: object_type_keys
        for workflow_key, object_type_keys in assignments.items()
        if object_type_keys
    }


def _explicit_workflow_object_types(workflow):
    object_type_keys = []
    object_type_key = workflow.get("object_type_key")
    if isinstance(object_type_key, str):
        object_type_keys.append(object_type_key)
    if isinstance(workflow.get("object_type_keys"), list):
        object_type_keys.extend(
            object_type_key
            for object_type_key in workflow["object_type_keys"]
            if isinstance(object_type_key, str)
        )
    return object_type_keys


def _append_unique(items, value):
    if value not in items:
        items.append(value)


def _runtime_workflow_key(workflow_key, object_type_key, index, assignment_count):
    if assignment_count == 1 or index == 0:
        return workflow_key
    return f"{workflow_key}_{object_type_key}"


def _initial_workflow_state(workflow):
    states = workflow.get("states")
    if isinstance(states, list) and states and isinstance(states[0], str):
        return states[0]
    return "draft"


def _runtime_transitions(workflow, object_type_key, data):
    transitions = []
    for transition in workflow.get("transitions", []):
        if not isinstance(transition, dict):
            continue
        from_state = transition.get("from") or transition.get("from_state")
        to_state = transition.get("to") or transition.get("to_state")
        if not isinstance(from_state, str) or not isinstance(to_state, str):
            continue
        transitions.append(
            {
                "key": transition.get("key") or _snake_case_token(f"{from_state}_to_{to_state}"),
                "label": transition.get("label") or _transition_label(from_state, to_state),
                "from_state": from_state,
                "to_state": to_state,
                "guards": _runtime_transition_guards(transition, object_type_key, data),
                "task_templates": _runtime_transition_task_templates(transition),
            }
        )
    return transitions


def _transition_label(from_state, to_state):
    return f"{from_state.replace('_', ' ').title()} to {to_state.replace('_', ' ').title()}"


def _runtime_transition_guards(transition, object_type_key, data):
    guards = transition.get("guards")
    if isinstance(guards, dict):
        return copy.deepcopy(guards)
    guard = transition.get("guard")
    if isinstance(guard, str) and guard:
        return _symbolic_guard_to_runtime_guard(guard, object_type_key, data)
    return {}


def _symbolic_guard_to_runtime_guard(guard, object_type_key, data):
    if guard == "required_fields_complete":
        return {"required_fields": _required_field_keys(data, object_type_key)}
    if guard == "engineering_approval":
        return {"required_tasks_complete": ["engineering_review"]}
    if guard == "quality_approval":
        return {"required_tasks_complete": ["quality_review"]}
    if guard == "spec_number_and_product_required":
        return {"required_fields": _field_keys_present(data, object_type_key, ["spec_number", "product", "revision"])}
    if guard == "controlled_document_attached":
        return {
            "required_tasks_complete": ["technical_spec_review"],
            "required_document_types": ["controlled_document"],
        }
    if guard == "approval_complete":
        return {"required_tasks_complete": ["approver_signoff"]}
    if guard == "supplier_selected":
        return {"required_fields": _field_keys_present(data, object_type_key, ["supplier_material_code", "material_family", "supplier"])}
    if guard == "compliance_documents_available":
        return {
            "required_tasks_complete": ["supplier_qualification_review"],
            "required_document_types": ["tds", "sds", "compliance"],
        }
    if guard == "technical_and_quality_approval":
        return {"required_tasks_complete": ["material_technical_review"]}
    if guard == "project_owner_assigned":
        return {"required_fields": _field_keys_present(data, object_type_key, ["project_name", "project_type", "project_owner"])}
    if guard == "scope_and_target_launch_confirmed":
        return {
            "required_fields": _field_keys_present(data, object_type_key, ["target_launch_date"]),
            "required_tasks_complete": ["gate_0_scoping_review"],
        }
    if guard == "trial_and_spec_package_ready":
        return {"required_tasks_complete": ["gate_1_development_approval"]}
    if guard == "launch_approval_complete":
        return {"required_tasks_complete": ["gate_2_launch_readiness"]}
    return {}


def _required_field_keys(data, object_type_key):
    for object_type in data.get("object_types", []):
        if isinstance(object_type, dict) and object_type.get("key") == object_type_key:
            return [
                field["key"]
                for field in object_type.get("fields", [])
                if isinstance(field, dict)
                and field.get("required") is True
                and _is_snake_case_key(field.get("key"))
            ]
    return []


def _field_keys_present(data, object_type_key, candidate_keys):
    field_keys = set()
    for object_type in data.get("object_types", []):
        if isinstance(object_type, dict) and object_type.get("key") == object_type_key:
            field_keys = {
                field.get("key")
                for field in object_type.get("fields", [])
                if isinstance(field, dict)
            }
            break
    return [field_key for field_key in candidate_keys if field_key in field_keys]


def _runtime_transition_task_templates(transition):
    task_templates = transition.get("task_templates")
    if isinstance(task_templates, list):
        return copy.deepcopy(task_templates)
    task_template = transition.get("task_template")
    if isinstance(task_template, str) and task_template:
        return [
            {
                "key": _snake_case_token(task_template),
                "title": task_template,
                "assignee_role": _starter_task_assignee_role(task_template),
                "required": True,
            }
        ]
    return []


def _starter_task_assignee_role(task_template):
    task_text = task_template.lower()
    if "supplier" in task_text:
        return "Supplier Quality"
    if "gate" in task_text or "project" in task_text or "launch" in task_text:
        return "Project Reviewer"
    if "quality" in task_text or "approver" in task_text or "approval" in task_text or "approve" in task_text:
        return "Quality Reviewer"
    if "technical" in task_text or "engineering" in task_text or "material" in task_text:
        return "Engineering Reviewer"
    return "Engineering Reviewer"


def _deactivate_stale_config_managed_workflows(current_runtime_keys):
    from apps.workflows.models import WorkflowDefinition

    WorkflowDefinition.objects.filter(data__config_registry_managed=True).exclude(
        key__in=current_runtime_keys
    ).update(is_active=False)


def _sync_runtime_dashboards(configuration_version, data):
    from apps.reports.models import Dashboard, DashboardWidget

    valid_widget_types = set(DashboardWidget.WidgetType.values)
    current_dashboard_keys = set()
    for dashboard_definition in data.get("dashboards", []):
        if not isinstance(dashboard_definition, dict):
            continue
        dashboard_key = dashboard_definition.get("key")
        if not _is_snake_case_key(dashboard_key):
            continue

        dashboard = Dashboard.objects.filter(
            owner__isnull=True,
            config__key=dashboard_key,
            config__config_registry_managed=True,
        ).first()
        if dashboard is None:
            unmanaged_dashboard_exists = Dashboard.objects.filter(
                owner__isnull=True,
                config__key=dashboard_key,
            ).exists()
            if unmanaged_dashboard_exists:
                continue
            current_dashboard_keys.add(dashboard_key)
            dashboard = Dashboard.objects.create(
                name=dashboard_definition.get("name")
                or dashboard_definition.get("label")
                or dashboard_key,
                description=dashboard_definition.get("description", ""),
                config=_managed_dashboard_config(configuration_version, dashboard_definition),
            )
        else:
            current_dashboard_keys.add(dashboard_key)
            dashboard.name = (
                dashboard_definition.get("name") or dashboard_definition.get("label") or dashboard_key
            )
            dashboard.description = dashboard_definition.get("description", "")
            dashboard.config = _managed_dashboard_config(
                configuration_version,
                dashboard_definition,
            )
            dashboard.save(update_fields=["name", "description", "config", "updated_at"])

        dashboard.widgets.all().delete()
        for sort_order, widget in enumerate(dashboard_definition.get("widgets", [])):
            if not isinstance(widget, dict):
                continue
            widget_type = widget.get("widget_type") or widget.get("type")
            if widget_type not in valid_widget_types:
                continue
            DashboardWidget.objects.create(
                dashboard=dashboard,
                title=widget.get("title") or widget.get("label") or widget_type,
                widget_type=widget_type,
                config=copy.deepcopy(widget.get("config") if isinstance(widget.get("config"), dict) else {}),
                sort_order=sort_order,
            )
    _delete_stale_config_managed_dashboards(current_dashboard_keys)


def _delete_stale_config_managed_dashboards(current_dashboard_keys):
    from apps.reports.models import Dashboard

    Dashboard.objects.filter(
        owner__isnull=True,
        config__config_registry_managed=True,
    ).exclude(config__key__in=current_dashboard_keys).delete()


def _managed_dashboard_config(configuration_version, dashboard_definition):
    dashboard_config = copy.deepcopy(
        dashboard_definition.get("config") if isinstance(dashboard_definition.get("config"), dict) else {}
    )
    dashboard_config.update(
        {
            "key": dashboard_definition["key"],
            CONFIG_REGISTRY_MANAGED_KEY: True,
            "configuration_version": configuration_version.version,
        }
    )
    return dashboard_config


def _managed_runtime_payload(configuration_version, payload, *, source_key, object_type_key=None):
    runtime_payload = copy.deepcopy(payload)
    runtime_payload[CONFIG_REGISTRY_MANAGED_KEY] = True
    runtime_payload["configuration_version"] = configuration_version.version
    runtime_payload["source_key"] = source_key
    if object_type_key:
        runtime_payload["object_type_key"] = object_type_key
    return runtime_payload


def _is_config_registry_managed(payload):
    return isinstance(payload, dict) and payload.get(CONFIG_REGISTRY_MANAGED_KEY) is True


def _snake_case_token(value):
    token = re.sub(r"[^a-zA-Z0-9]+", "_", str(value).strip().lower())
    token = re.sub(r"_+", "_", token).strip("_")
    return token or "configured"
