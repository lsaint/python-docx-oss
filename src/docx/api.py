"""Directly exposed API functions and classes, :func:`Document` for now.

Provides a syntactically more convenient API for interacting with the OpcPackage graph.
"""

from __future__ import annotations

import io
import os
from typing import IO, TYPE_CHECKING, cast

from docx.opc.constants import CONTENT_TYPE as CT
from docx.package import Package

if TYPE_CHECKING:
    from docx.document import Document as DocumentObject
    from docx.parts.document import DocumentPart


def Document(docx: str | bytes | IO[bytes] | None = None) -> DocumentObject:
    """Return a |Document| object loaded from `docx`, where `docx` can be either a path
    to a ``.docx`` file, raw DOCX bytes, or a binary file-like object.

    If `docx` is missing or ``None``, the built-in default document "template" is
    loaded.
    """
    docx = _default_docx_path() if docx is None else docx
    source_name = "<bytes>" if isinstance(docx, bytes) else docx
    docx = io.BytesIO(docx) if isinstance(docx, bytes) else docx
    document_part = cast("DocumentPart", Package.open(docx).main_document_part)
    if document_part.content_type != CT.WML_DOCUMENT_MAIN:
        tmpl = "file '%s' is not a Word file, content type is '%s'"
        raise ValueError(tmpl % (source_name, document_part.content_type))
    return document_part.document


def _default_docx_path():
    """Return the path to the built-in default .docx package."""
    _thisdir = os.path.split(__file__)[0]
    return os.path.join(_thisdir, "templates", "default.docx")
