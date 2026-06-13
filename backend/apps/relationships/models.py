# ===
# File Summary
# Path: backend\apps\relationships\models.py
# Type: python
# Purpose: Relationships domain for entity graph APIs and relationship operations.
# Primary responsibilities:
# - Domain behavior is summarized for fast onboarding and avoids full-file reread.
# - Core symbols: Relationship, Meta, __str__
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

from django.db import models


class Relationship(models.Model):
    source_record = models.ForeignKey(
        "records.Record",
        on_delete=models.CASCADE,
        related_name="outgoing_relationships",
    )
    target_record = models.ForeignKey(
        "records.Record",
        on_delete=models.CASCADE,
        related_name="incoming_relationships",
    )
    relationship_type_key = models.CharField(max_length=120)
    data = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["source_record", "target_record", "relationship_type_key"],
                name="unique_relationship_edge",
            )
        ]
        indexes = [
            models.Index(fields=["relationship_type_key"]),
            models.Index(fields=["source_record", "relationship_type_key"]),
            models.Index(fields=["target_record", "relationship_type_key"]),
        ]
        ordering = ["id"]

    def __str__(self):
        return (
            f"{self.source_record_id} -[{self.relationship_type_key}]-> "
            f"{self.target_record_id}"
        )

