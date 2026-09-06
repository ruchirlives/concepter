"""Container relationship model with tuple-compatible traversal semantics."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterator
import uuid


@dataclass(eq=False)
class ContainerRelationship:
    """A positioned parent-to-child edge.

    Existing Orch code commonly unpacks relationships as ``child, position`` or
    indexes them as a two-tuple.  This class deliberately preserves that API
    while providing a home for relationship metadata such as an xref path.
    """

    child: Any
    position: Any = 0
    child_id: str = ""
    relationship_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    xref: str = ""
    xref_source_id: str = ""
    xref_target_root_id: str = ""
    xref_read_only: bool = False
    xref_status: str = ""
    xref_error: str = ""

    def __post_init__(self):
        if not self.child_id and self.child is not None:
            get_value = getattr(self.child, "getValue", None)
            if callable(get_value):
                self.child_id = str(get_value("id") or "")

    def __iter__(self) -> Iterator[Any]:
        yield self.child
        yield self.position

    def __len__(self) -> int:
        return 2

    def __getitem__(self, index):
        return (self.child, self.position)[index]

    def __eq__(self, other):
        if isinstance(other, ContainerRelationship):
            return (
                self.child is other.child
                and self.position == other.position
                and self.relationship_id == other.relationship_id
                and self.xref == other.xref
                and self.xref_source_id == other.xref_source_id
                and self.xref_target_root_id == other.xref_target_root_id
                and self.xref_read_only == other.xref_read_only
                and self.xref_status == other.xref_status
                and self.xref_error == other.xref_error
            )
        if isinstance(other, (tuple, list)) and len(other) == 2:
            return self.child is other[0] and self.position == other[1]
        return NotImplemented

    def with_position(self, position):
        return ContainerRelationship(
            child=self.child,
            position=position,
            child_id=self.child_id,
            relationship_id=self.relationship_id,
            xref=self.xref,
            xref_source_id=self.xref_source_id,
            xref_target_root_id=self.xref_target_root_id,
            xref_read_only=self.xref_read_only,
            xref_status=self.xref_status,
            xref_error=self.xref_error,
        )

    def with_child(self, child):
        return ContainerRelationship(
            child=child,
            position=self.position,
            child_id=str(child.getValue("id") or "") if child is not None else self.child_id,
            relationship_id=self.relationship_id,
            xref=self.xref,
            xref_source_id=self.xref_source_id,
            xref_target_root_id=self.xref_target_root_id,
            xref_read_only=self.xref_read_only,
            xref_status=self.xref_status,
            xref_error=self.xref_error,
        )

    def to_metadata_dict(self):
        metadata = {"relationship_id": self.relationship_id}
        if self.xref:
            metadata["xref"] = self.xref
            metadata["xref_read_only"] = bool(self.xref_read_only)
            if self.xref_source_id:
                metadata["xref_source_id"] = self.xref_source_id
            if self.xref_target_root_id:
                metadata["xref_target_root_id"] = self.xref_target_root_id
        if self.xref_status:
            metadata["xref_status"] = self.xref_status
        if self.xref_error:
            metadata["xref_error"] = self.xref_error
        return metadata


def relationship_metadata(relationship, child=None):
    """Return serialized metadata, migrating legacy child xref fields on write."""

    if isinstance(relationship, ContainerRelationship):
        metadata = relationship.to_metadata_dict()
    else:
        metadata = {"relationship_id": str(uuid.uuid4())}

    if child is not None:
        values = getattr(child, "values", {}) or {}
        legacy_xref = values.get("xref")
        if legacy_xref and not metadata.get("xref"):
            metadata["xref"] = legacy_xref
            metadata["xref_read_only"] = bool(values.get("xref_read_only"))
    return metadata


def make_relationship(child, position=0, metadata=None):
    metadata = metadata or {}
    return ContainerRelationship(
        child=child,
        position=position,
        child_id=str(metadata.get("id") or metadata.get("child_id") or ""),
        relationship_id=str(metadata.get("relationship_id") or uuid.uuid4()),
        xref=str(metadata.get("xref") or ""),
        xref_source_id=str(metadata.get("xref_source_id") or ""),
        xref_target_root_id=str(metadata.get("xref_target_root_id") or ""),
        xref_read_only=bool(metadata.get("xref_read_only", False)),
        xref_status=str(metadata.get("xref_status") or ""),
        xref_error=str(metadata.get("xref_error") or ""),
    )


def is_xref_relationship(relationship) -> bool:
    return isinstance(relationship, ContainerRelationship) and bool(relationship.xref)


def ensure_relationship(relationship):
    if isinstance(relationship, ContainerRelationship):
        return relationship
    child, position = relationship
    result = make_relationship(child, position)
    values = getattr(child, "values", {}) or {} if child is not None else {}
    if values.get("xref"):
        result.xref = str(values["xref"])
        result.xref_read_only = bool(values.get("xref_read_only", True))
        result.xref_status = "unresolved"
        result.legacy_shell = child
        result.legacy_xref_id = str(values.get("xref_id") or "")
    return result
