"""Read-only package inspection and configurable content fingerprints."""

from docx.inspection.fingerprint import FingerprintPolicy, fingerprint
from docx.inspection.reader import inspect
from docx.inspection.result import (
    Features,
    Finding,
    PackageInspection,
    PackageInventory,
    PartInventory,
    RelationshipInventory,
)

__all__ = [
    "Features",
    "Finding",
    "FingerprintPolicy",
    "PackageInspection",
    "PackageInventory",
    "PartInventory",
    "RelationshipInventory",
    "fingerprint",
    "inspect",
]
