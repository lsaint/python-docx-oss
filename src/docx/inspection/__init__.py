"""Read-only package inspection and configurable content fingerprints."""

from docx.inspection.features import ScanEvent
from docx.inspection.fingerprint import (
    FingerprintItem,
    FingerprintPolicy,
    fingerprint,
    serialize_xml,
)
from docx.inspection.reader import inspect
from docx.inspection.result import (
    Finding,
    PackageInspection,
    PackageInventory,
    PartInventory,
    RelationshipInventory,
)

__all__ = [
    "ScanEvent",
    "Finding",
    "FingerprintItem",
    "FingerprintPolicy",
    "PackageInspection",
    "PackageInventory",
    "PartInventory",
    "RelationshipInventory",
    "fingerprint",
    "serialize_xml",
    "inspect",
]
