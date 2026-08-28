"""Package-level DOCX sanitization.

Callers use :meth:`docx.document.Document.sanitize`; this package keeps OPC graph
mutation and XML cleanup details behind that single method.
"""

from docx.sanitize.cleaner import sanitize_document
from docx.sanitize.result import RemovedRelationship, SanitizationReport

__all__ = ["RemovedRelationship", "SanitizationReport", "sanitize_document"]
