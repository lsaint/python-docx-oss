"""Value objects returned by document sanitization."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RemovedRelationship:
    """A package relationship removed during sanitization."""

    source: str
    relationship_id: str
    relationship_type: str
    target: str


@dataclass(frozen=True)
class SanitizationReport:
    """Immutable summary of changes made by ``Document.sanitize()``."""

    scrubbed_properties: tuple[str, ...] = ()
    removed_comment_markers: int = 0
    removed_formatting_revisions: int = 0
    removed_parts: tuple[str, ...] = ()
    removed_relationships: tuple[RemovedRelationship, ...] = ()
    warnings: tuple[str, ...] = ()

    @property
    def changed(self) -> bool:
        """Whether the document package was modified."""
        return bool(
            self.scrubbed_properties
            or self.removed_comment_markers
            or self.removed_formatting_revisions
            or self.removed_parts
            or self.removed_relationships
        )
