"""Read-only package inspection and configurable content fingerprints."""

from docx.inspection.features import ScanEvent
from docx.inspection.fingerprint import FingerprintPolicy, fingerprint
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
    "FingerprintPolicy",
    "PackageInspection",
    "PackageInventory",
    "PartInventory",
    "RelationshipInventory",
    "fingerprint",
    "inspect",
]
