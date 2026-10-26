"""Normalize supported hyperlink structures while preserving unrelated package data."""

from __future__ import annotations

import io
from zipfile import ZipFile

from lxml import etree

from docx.inspection import Finding, inspect
from docx.inspection.reader import CT_NS, REL_NS, STORIES, relationship_kind
from docx.inspection.source import PackageSource
from docx.transforms.hyperlinks import HyperlinkNormalizer, Selector, relationship_partname
from docx.transforms.package import finish, parse_xml, snapshot, unchanged, xml_bytes
from docx.transforms.result import Change, TransformationResult


def normalize(
    source: PackageSource,
    *,
    hyperlink_fields: bool = False,
    hyperlink_runs: bool = False,
    select_hyperlink: Selector | None = None,
) -> TransformationResult:
    """Explicitly convert hyperlink fields and/or merge compatible adjacent text runs.

    Selection is application-owned; None selects all supported hyperlinks. Unsafe
    or unsupported field structures are preserved and reported as skipped. Any
    validation failure rolls back the complete operation to the original bytes.
    """
    original = snapshot(source)
    before = inspect(original)
    if not hyperlink_fields and not hyperlink_runs:
        return unchanged(original, before)
    if before.findings:
        return unchanged(original, before, errors=before.findings)
    reachable = {part.partname for part in before.inventory.parts if part.reachable}
    stories = {
        rel.target
        for rel in before.inventory.relationships
        if not rel.external
        and rel.source in reachable | {"/"}
        and relationship_kind(rel.relationship_type) in STORIES
    }
    replacements: dict[str, bytes] = {}
    changes: list[Change] = []
    skipped: list[Finding] = []
    with ZipFile(io.BytesIO(original)) as package:
        names = set(package.namelist())
        for name in sorted(stories):
            root = parse_xml(package.read(name))
            rels_name = relationship_partname(name)
            rels = (
                parse_xml(package.read(rels_name))
                if rels_name in names
                else etree.Element(
                    f"{{{REL_NS}}}Relationships",
                    nsmap={None: REL_NS},
                )
            )
            normalizer = HyperlinkNormalizer(name, rels, select_hyperlink, changes, skipped)
            previous_count = len(changes)
            if hyperlink_fields:
                normalizer.convert_fields(root)
            if hyperlink_runs:
                normalizer.merge_runs(root)
            if len(changes) != previous_count:
                replacements[name] = xml_bytes(root)
            if normalizer.relationships_changed:
                replacements[rels_name] = xml_bytes(rels)
                if rels_name not in names:
                    types = parse_xml(
                        replacements.get("[Content_Types].xml")
                        or package.read("[Content_Types].xml")
                    )
                    relationship_type = "application/vnd.openxmlformats-package.relationships+xml"
                    has_default = any(
                        node.get("Extension", "").lower() == "rels"
                        and node.get("ContentType") == relationship_type
                        for node in types.findall(f"{{{CT_NS}}}Default")
                    )
                    if not has_default:
                        etree.SubElement(
                            types,
                            f"{{{CT_NS}}}Override",
                            PartName="/" + rels_name,
                            ContentType=relationship_type,
                        )
                        replacements["[Content_Types].xml"] = xml_bytes(types)
                        changes.append(
                            Change("added_relationship_content_type", "[Content_Types].xml")
                        )
    return finish(original, before, replacements, changes, skipped)
