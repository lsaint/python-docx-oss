"""Implementation of the package-level sanitization boundary."""

from __future__ import annotations

from typing import TYPE_CHECKING, Iterator

from lxml import etree

from docx.opc.oxml import serialize_part_xml
from docx.opc.part import Part, XmlPart
from docx.oxml.ns import qn
from docx.oxml.parser import parse_xml
from docx.sanitize.result import RemovedRelationship, SanitizationReport

if TYPE_CHECKING:
    from lxml.etree import _Element as etree_Element  # pyright: ignore[reportPrivateUsage]

    from docx.document import Document
    from docx.opc.package import OpcPackage
    from docx.oxml.xmlchemy import BaseOxmlElement


_COMMENT_MARKER_TAGS = (
    qn("w:commentRangeStart"),
    qn("w:commentRangeEnd"),
    qn("w:commentReference"),
)
_COMMENT_RELATIONSHIP_NAMES = frozenset(
    {
        "commentauthors",
        "comments",
        "commentsextended",
        "commentsextensible",
        "commentsids",
        "people",
    }
)
_FORMATTING_REVISION_TAGS = tuple(
    qn(tag)
    for tag in (
        "w:rPrChange",
        "w:pPrChange",
        "w:tblPrChange",
        "w:trPrChange",
        "w:tcPrChange",
        "w:sectPrChange",
    )
)
_WEB_EXTENSION_RELATIONSHIP_NAMES = frozenset({"webextension", "webextensiontaskpanes"})


def sanitize_document(
    document: Document,
    *,
    personal_metadata: bool,
    comments: bool,
    web_extensions: bool,
    formatting_revisions: bool,
) -> SanitizationReport:
    """Apply selected sanitizers while keeping all graph mechanics internal."""
    package = document.part.package
    assert package is not None

    if not any((personal_metadata, comments, web_extensions, formatting_revisions)):
        return SanitizationReport()

    parts_before = _reachable_part_names(package)
    scrubbed_properties: list[str] = []
    removed_relationships: list[RemovedRelationship] = []
    warnings: list[str] = []
    removed_comment_markers = 0
    removed_formatting_revisions = 0

    if personal_metadata:
        scrubbed_properties.extend(_scrub_personal_metadata(package))

    if comments or formatting_revisions:
        for part, root in _iter_word_xml(package, warnings):
            part_changed = False
            if comments:
                count = _remove_elements(root, _COMMENT_MARKER_TAGS)
                removed_comment_markers += count
                part_changed = part_changed or count > 0
            if formatting_revisions:
                count = _remove_elements(root, _FORMATTING_REVISION_TAGS)
                removed_formatting_revisions += count
                part_changed = part_changed or count > 0
            if part_changed and not isinstance(part, XmlPart):
                part.replace_blob(serialize_part_xml(root))

    if comments:
        removed_relationships.extend(_drop_relationships(package, _COMMENT_RELATIONSHIP_NAMES))
    if web_extensions:
        removed_relationships.extend(
            _drop_relationships(package, _WEB_EXTENSION_RELATIONSHIP_NAMES)
        )

    parts_after = _reachable_part_names(package)
    return SanitizationReport(
        scrubbed_properties=tuple(scrubbed_properties),
        removed_comment_markers=removed_comment_markers,
        removed_formatting_revisions=removed_formatting_revisions,
        removed_parts=tuple(sorted(parts_before - parts_after)),
        removed_relationships=tuple(removed_relationships),
        warnings=tuple(warnings),
    )


def _drop_relationships(
    package: OpcPackage, relationship_names: frozenset[str]
) -> list[RemovedRelationship]:
    removed: list[RemovedRelationship] = []
    for source_name, source in _relationship_sources(package):
        for rId, rel in list(source.rels.items()):
            if _relationship_name(rel.reltype) not in relationship_names:
                continue
            target = rel.target_ref if rel.is_external else str(rel.target_part.partname)
            removed.append(RemovedRelationship(source_name, rId, rel.reltype, target))
            del source.rels[rId]
    return removed


def _iter_word_xml(
    package: OpcPackage, warnings: list[str]
) -> Iterator[tuple[Part, BaseOxmlElement]]:
    for part in _reachable_parts(package):
        if not str(part.partname).startswith("/word/"):
            continue
        if isinstance(part, XmlPart):
            yield part, part.element
            continue
        if not part.content_type.endswith("+xml") and part.content_type != "application/xml":
            continue
        try:
            yield part, parse_xml(part.blob)
        except etree.XMLSyntaxError as exc:
            warnings.append(f"Could not sanitize XML part {part.partname}: {exc}")


def _reachable_parts(package: OpcPackage) -> list[Part]:
    parts: list[Part] = []
    visited: set[int] = set()

    def walk(source: OpcPackage | Part) -> None:
        for rel in source.rels.values():
            if rel.is_external:
                continue
            part = rel.target_part
            identity = id(part)
            if identity in visited:
                continue
            visited.add(identity)
            parts.append(part)
            walk(part)

    walk(package)
    return parts


def _reachable_part_names(package: OpcPackage) -> set[str]:
    return {str(part.partname) for part in _reachable_parts(package)}


def _relationship_name(relationship_type: str) -> str:
    return relationship_type.rstrip("/").rsplit("/", 1)[-1].lower()


def _relationship_sources(package: OpcPackage) -> list[tuple[str, OpcPackage | Part]]:
    return [("/", package), *[(str(part.partname), part) for part in _reachable_parts(package)]]


def _remove_elements(root: BaseOxmlElement, tags: tuple[str, ...]) -> int:
    tag_set = set(tags)
    elements = [
        element
        for tag in tags
        for element in root.iter(tag)
        if not any(ancestor.tag in tag_set for ancestor in element.iterancestors())
    ]
    for element in elements:
        parent = element.getparent()
        if parent is not None:
            comment_run = _empty_comment_reference_run(element)
            parent.remove(element)
            if comment_run is not None:
                comment_run_parent = comment_run.getparent()
                if comment_run_parent is not None:
                    comment_run_parent.remove(comment_run)
    return len(elements)


def _scrub_personal_metadata(package: OpcPackage) -> list[str]:
    core_properties = package.core_properties
    changed = core_properties.deduplicate("author", "last_modified_by", "revision")
    if core_properties.author:
        changed.add("author")
    if core_properties.last_modified_by:
        changed.add("last_modified_by")
    if core_properties.revision != 1:
        changed.add("revision")
    core_properties.author = ""
    core_properties.last_modified_by = ""
    core_properties.revision = 1
    return [name for name in ("author", "last_modified_by", "revision") if name in changed]


def _empty_comment_reference_run(element: etree_Element) -> etree_Element | None:
    if element.tag != qn("w:commentReference"):
        return None
    run = element.getparent()
    if run is None or run.tag != qn("w:r"):
        return None
    remaining = [child for child in run if child is not element]
    if not remaining:
        return run
    if len(remaining) != 1 or remaining[0].tag != qn("w:rPr"):
        return None
    run_properties = remaining[0]
    if len(run_properties) != 1 or run_properties[0].tag != qn("w:rStyle"):
        return None
    return run if run_properties[0].get(qn("w:val")) == "CommentReference" else None
