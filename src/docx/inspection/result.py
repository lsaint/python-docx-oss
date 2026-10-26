"""Immutable observations of a package; findings do not prescribe repair policy."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Finding:
    code: str
    partname: str | None = None
    message: str = ""
    target: str | None = None


@dataclass(frozen=True)
class PartInventory:
    """ZIP member metadata. Names are package-relative, without a leading slash."""

    partname: str
    size: int
    content_type: str | None
    reachable: bool


@dataclass(frozen=True)
class RelationshipInventory:
    """A relationship with its resolved internal target or original external URI."""

    source: str
    relationship_id: str
    relationship_type: str
    target: str
    external: bool


@dataclass(frozen=True)
class PackageInventory:
    parts: tuple[PartInventory, ...] = ()
    relationships: tuple[RelationshipInventory, ...] = ()


@dataclass(frozen=True)
class Features:
    field_hyperlink: bool = False
    split_hyperlink_runs: bool = False


@dataclass(frozen=True)
class PackageInspection:
    inventory: PackageInventory = PackageInventory()
    findings: tuple[Finding, ...] = ()
    features: Features = Features()

    def has_finding(self, code: str) -> bool:
        return any(finding.code == code for finding in self.findings)

    def findings_by_code(self, code: str) -> tuple[Finding, ...]:
        return tuple(finding for finding in self.findings if finding.code == code)
