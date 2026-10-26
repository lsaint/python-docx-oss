"""Narrow pre-open repairs; content that cannot be reconstructed is never guessed."""

from __future__ import annotations

from docx.inspection import inspect
from docx.inspection.reader import relationship_kind
from docx.inspection.source import PackageSource
from docx.transforms.package import finish, snapshot, unchanged
from docx.transforms.result import Change, TransformationResult


def repair(source: PackageSource, *, empty_custom_xml: bool = False) -> TransformationResult:
    """Optionally replace empty Custom XML data parts with a neutral ``<root/>``.

    Only parts exclusively targeted by customXml relationships and typed as generic
    XML qualify. Relationships and Custom XML properties are preserved. Any other
    finding prevents the operation. Failure returns the original bytes and errors.
    """
    original = snapshot(source)
    before = inspect(original)
    if not empty_custom_xml:
        return unchanged(original, before)
    incoming: dict[str, set[str]] = {}
    for rel in before.inventory.relationships:
        if not rel.external:
            incoming.setdefault(rel.target, set()).add(relationship_kind(rel.relationship_type))
    data_parts = {
        part.partname
        for part in before.inventory.parts
        if incoming.get(part.partname) == {"customXml"}
        and part.content_type in ("application/xml", "text/xml")
    }
    errors = tuple(
        finding
        for finding in before.findings
        if finding.code != "empty_xml_part" or finding.partname not in data_parts
    )
    if errors:
        return unchanged(original, before, errors=errors)
    replacements = {
        finding.partname: b'<?xml version="1.0" encoding="UTF-8"?><root/>'
        for finding in before.findings
        if finding.code == "empty_xml_part" and finding.partname is not None
    }
    changes = [Change("filled_empty_custom_xml", name) for name in sorted(replacements)]
    return finish(original, before, replacements, changes, [])
