"""Change selected members without round-tripping unrelated XML through Document."""

from __future__ import annotations

import io
import shutil
from copy import copy
from zipfile import ZIP_DEFLATED, ZipFile

from lxml import etree
from lxml.etree import _Element as etree_Element  # pyright: ignore[reportPrivateUsage]

from docx.api import Document
from docx.inspection import Finding, PackageInspection, inspect
from docx.inspection.reader import PACKAGE_ERRORS
from docx.inspection.source import PackageSource, open_source
from docx.transforms.result import Change, TransformationReport, TransformationResult


def snapshot(source: PackageSource) -> bytes:
    if isinstance(source, bytes):
        return source
    with open_source(source) as stream:
        return stream.read()


def parse_xml(content: bytes) -> etree_Element:
    return etree.fromstring(content, etree.XMLParser(resolve_entities=False, no_network=True))


def xml_bytes(element: etree_Element) -> bytes:
    return etree.tostring(element, encoding="UTF-8", xml_declaration=True)


def rewrite(original: bytes, replacements: dict[str, bytes]) -> bytes:
    if not replacements:
        return original
    output = io.BytesIO()
    with ZipFile(io.BytesIO(original)) as source, ZipFile(output, "w") as destination:
        destination.comment = source.comment
        for member in source.infolist():
            if member.filename in replacements:
                destination.writestr(copy(member), replacements[member.filename])
            else:
                with source.open(member) as reader, destination.open(copy(member), "w") as writer:
                    shutil.copyfileobj(reader, writer, length=64 * 1024)
        existing = set(source.namelist())
        for name in sorted(replacements.keys() - existing):
            destination.writestr(name, replacements[name], compress_type=ZIP_DEFLATED)
    return output.getvalue()


def unchanged(
    original: bytes,
    before: PackageInspection,
    *,
    errors: tuple[Finding, ...] = (),
    skipped: tuple[Finding, ...] = (),
) -> TransformationResult:
    return TransformationResult(
        original, TransformationReport(before, before, skipped=skipped, errors=errors)
    )


def finish(
    original: bytes,
    before: PackageInspection,
    replacements: dict[str, bytes],
    changes: list[Change],
    skipped: list[Finding],
) -> TransformationResult:
    try:
        candidate = rewrite(original, replacements)
    except PACKAGE_ERRORS as exc:
        return unchanged(
            original,
            before,
            errors=(Finding("package_write_failed", message=str(exc)),),
            skipped=tuple(skipped),
        )
    after = inspect(candidate)
    if after.findings:
        return unchanged(original, before, errors=after.findings, skipped=tuple(skipped))
    # Open for validation only. Saving through Document could discard orphan parts.
    try:
        document = Document(candidate)
        namespace = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
        if (
            document.element.tag != f"{{{namespace}}}document"
            or document.element.find(f"{{{namespace}}}body") is None
        ):
            raise ValueError("The main part is not a supported Word document with a body")
    except Exception as exc:
        return unchanged(
            original,
            before,
            errors=(Finding("document_open_failed", message=str(exc)),),
            skipped=tuple(skipped),
        )
    return TransformationResult(
        candidate, TransformationReport(before, after, tuple(changes), tuple(skipped))
    )
