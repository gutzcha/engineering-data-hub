# ===
# File Summary
# Path: backend\apps\relationships\services.py
# Type: python
# Purpose: Relationships domain for entity graph APIs and relationship operations.
# Primary responsibilities:
# - Domain behavior is summarized for fast onboarding and avoids full-file reread.
# - Core symbols: get_relationship_type_definition, validate_relationship_type, relationship_label, build_record_graph, _relationship_type_definitions
# Inputs:
# - Downstream and upstream interactions in the same domain.
# Outputs:
# - API payloads, records, side effects, or UI views depending on file role.
# Dependencies:
# - Shared runtime services and adjacent domain modules.
# Known risks:
# - Validate behavior after migrations, dependency upgrades, or contract changes.
# ===
# 

from django.db.models import Q
from rest_framework import serializers

from apps.accounts.permissions import user_can
from apps.config_registry.services import get_active_config
from apps.records.models import Record
from apps.relationships.models import Relationship


def get_relationship_type_definition(relationship_type_key):
    relationship_types = _relationship_type_definitions()
    if not relationship_types:
        raise serializers.ValidationError(
            {"relationship_type_key": ["Unknown relationship type."]}
        )

    for relationship_type in relationship_types:
        if relationship_type.get("key") == relationship_type_key:
            return relationship_type
    raise serializers.ValidationError(
        {"relationship_type_key": ["Unknown relationship type."]}
    )


def validate_relationship_type(source_record, target_record, relationship_type_key):
    relationship_type = get_relationship_type_definition(relationship_type_key)

    errors = {}
    source_object_type = relationship_type.get("source_object_type")
    if source_object_type and source_record.object_type_key != source_object_type:
        errors.setdefault("source_record", []).append(
            f"Source record must be a {source_object_type}."
        )

    target_object_type = relationship_type.get("target_object_type")
    if target_object_type and target_record.object_type_key != target_object_type:
        errors.setdefault("target_record", []).append(
            f"Target record must be a {target_object_type}."
        )

    if errors:
        raise serializers.ValidationError(errors)
    return relationship_type


def relationship_label(relationship_type_key):
    try:
        relationship_type = get_relationship_type_definition(relationship_type_key)
    except serializers.ValidationError:
        relationship_type = None
    if relationship_type:
        return relationship_type.get("label") or relationship_type_key
    return relationship_type_key.replace("_", " ").capitalize()


def build_record_graph(root_record, *, user, max_depth=2):
    nodes = {root_record.pk: root_record}
    edges = {}
    frontier = {root_record.pk}
    visited = set()

    for _depth in range(max_depth):
        if not frontier:
            break
        relationships = (
            Relationship.objects.filter(Q(source_record_id__in=frontier) | Q(target_record_id__in=frontier))
            .select_related("source_record", "target_record")
            .order_by("id")
        )
        next_frontier = set()
        for relationship in relationships:
            source_visible = _user_can_view_record(user, relationship.source_record)
            target_visible = _user_can_view_record(user, relationship.target_record)
            if source_visible and target_visible:
                edges[relationship.pk] = relationship

            for record, visible in [
                (relationship.source_record, source_visible),
                (relationship.target_record, target_visible),
            ]:
                if not visible:
                    continue
                if record.pk not in nodes:
                    nodes[record.pk] = record
                if record.pk not in visited and record.pk not in frontier:
                    next_frontier.add(record.pk)
        visited.update(frontier)
        frontier = next_frontier

    return {
        "nodes": [_serialize_node(record) for record in sorted(nodes.values(), key=_record_sort_key)],
        "edges": [_serialize_edge(edge) for edge in sorted(edges.values(), key=lambda item: item.pk)],
    }


def _relationship_type_definitions():
    active_config = get_active_config()
    data = active_config.data if active_config else {}
    relationship_types = data.get("relationship_types", [])
    if isinstance(relationship_types, list):
        return relationship_types
    return []


def _serialize_node(record: Record):
    return {
        "id": str(record.pk),
        "label": record.title,
        "object_type_key": record.object_type_key,
        "code": record.code,
    }


def _serialize_edge(relationship: Relationship):
    return {
        "id": relationship.pk,
        "source": str(relationship.source_record_id),
        "target": str(relationship.target_record_id),
        "relationship_type_key": relationship.relationship_type_key,
        "label": relationship_label(relationship.relationship_type_key),
        "data": relationship.data,
    }


def _record_sort_key(record):
    return (record.object_type_key, record.code, str(record.pk))


def _user_can_view_record(user, record):
    return user_can(user, "view", record.object_type_key, record_id=str(record.pk))

