"""Immutable results for explicit, transactional package transformations."""

from __future__ import annotations

from dataclasses import dataclass

from docx.inspection import Finding, PackageInspection


@dataclass(frozen=True)
class Change:
    code: str
    partname: str
    count: int = 1
    relationship_id: str | None = None
    target: str | None = None


@dataclass(frozen=True)
class TransformationReport:
    before: PackageInspection
    after: PackageInspection
    changes: tuple[Change, ...] = ()
    skipped: tuple[Finding, ...] = ()
    errors: tuple[Finding, ...] = ()

    @property
    def succeeded(self) -> bool:
        return not self.errors

    @property
    def changed(self) -> bool:
        return bool(self.changes)


@dataclass(frozen=True)
class TransformationResult:
    content: bytes
    report: TransformationReport


@dataclass(frozen=True)
class HyperlinkTarget:
    """Application-neutral selection context for a hyperlink operation."""

    partname: str
    address: str | None = None
    anchor: str | None = None
