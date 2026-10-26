"""Tolerant OPC inventory, independent of Document and the eager package reader."""

from __future__ import annotations

import posixpath
import zlib
from collections import deque
from urllib.parse import unquote, urlsplit
from zipfile import BadZipFile, ZipFile, ZipInfo

from lxml import etree

from docx.inspection.features import MetadataFacts, XmlFacts
from docx.inspection.result import (
    Features,
    Finding,
    PackageInspection,
    PackageInventory,
    PartInventory,
    RelationshipInventory,
)
from docx.inspection.source import PackageSource, open_source

CT_NS = "http://schemas.openxmlformats.org/package/2006/content-types"
REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
OFFICE_REL_BASES = (
    "http://schemas.openxmlformats.org/officeDocument/2006/relationships/",
    "http://purl.oclc.org/ooxml/officeDocument/relationships/",
)
PACKAGE_ERRORS = (
    BadZipFile,
    EOFError,
    OSError,
    RuntimeError,
    NotImplementedError,
    UnicodeError,
    zlib.error,
)
STORIES = {"officeDocument", "header", "footer", "footnotes", "endnotes", "comments"}


def relationship_kind(relationship_type: str) -> str:
    for base in OFFICE_REL_BASES:
        if relationship_type.startswith(base):
            return relationship_type[len(base) :]
    return ""


def relationship_source(name: str) -> str | None:
    if name == "_rels/.rels":
        return "/"
    directory, filename = posixpath.split(name)
    if posixpath.basename(directory) == "_rels" and filename.endswith(".rels"):
        return posixpath.join(posixpath.dirname(directory), filename[:-5])
    return None


def resolve_target(source: str, target: str) -> str:
    path = unquote(urlsplit(target).path)
    if path.startswith("/"):
        return posixpath.normpath(path)[1:]
    directory = "" if source == "/" else posixpath.dirname(source)
    return posixpath.normpath(posixpath.join(directory, path))


def scan_xml(package: ZipFile, member: ZipInfo, target: XmlFacts) -> Features:
    parser = etree.XMLParser(target=target, resolve_entities=False, no_network=True)
    nonblank = False
    with package.open(member) as stream:
        while chunk := stream.read(64 * 1024):
            nonblank |= bool(chunk.strip(b" \t\r\n"))
            parser.feed(chunk)
    if not nonblank:
        raise EmptyXmlError("XML part is empty or contains only whitespace")
    return parser.close()


class EmptyXmlError(ValueError):
    """An XML member contains no document content."""


def is_xml(name: str, content_type: str | None) -> bool:
    return name.endswith((".xml", ".rels")) or bool(
        content_type
        and (content_type.endswith("+xml") or content_type in ("text/xml", "application/xml"))
    )


class _Inspection:
    def __init__(self, package: ZipFile):
        self.package = package
        self.findings: list[Finding] = []
        self.members: dict[str, ZipInfo] = {}
        self.defaults: dict[str, str] = {}
        self.overrides: dict[str, str] = {}
        self.relationships: list[RelationshipInventory] = []
        for member in package.infolist():
            name = member.filename
            if member.is_dir():
                continue
            if name in self.members:
                self.findings.append(Finding("duplicate_member", name))
            else:
                self.members[name] = member
            if name.startswith("/") or "\\" in name or ".." in name.split("/"):
                self.findings.append(Finding("unsafe_member_name", name))

    def _scan(self, name: str, target: XmlFacts) -> Features:
        member = self.members[name]
        if member.file_size == 0:
            self.findings.append(Finding("empty_xml_part", name))
            return Features()
        try:
            return scan_xml(self.package, member, target)
        except EmptyXmlError:
            self.findings.append(Finding("empty_xml_part", name))
        except (etree.XMLSyntaxError, ValueError) as exc:
            self.findings.append(Finding("unparseable_xml_part", name, str(exc)))
        except PACKAGE_ERRORS as exc:
            self.findings.append(Finding("unreadable_part", name, str(exc)))
        return Features()

    def _read_metadata(self) -> None:
        if "[Content_Types].xml" not in self.members:
            self.findings.append(Finding("missing_content_types"))
        else:
            target = MetadataFacts()
            self._scan("[Content_Types].xml", target)
            if target.root_tag != f"{{{CT_NS}}}Types":
                self.findings.append(Finding("invalid_content_types", "[Content_Types].xml"))
            for tag, attrs in target.elements:
                if tag == f"{{{CT_NS}}}Default":
                    self.defaults[attrs.get("Extension", "").lower()] = attrs.get("ContentType", "")
                elif tag == f"{{{CT_NS}}}Override":
                    self.overrides[unquote(attrs.get("PartName", "")).lstrip("/")] = attrs.get(
                        "ContentType", ""
                    )
        for name in sorted(self.members):
            source = relationship_source(name)
            if source is None:
                continue
            target = MetadataFacts()
            self._scan(name, target)
            if target.root_tag != f"{{{REL_NS}}}Relationships":
                self.findings.append(Finding("invalid_relationships", name))
                continue
            ids: set[str] = set()
            for tag, attrs in target.elements:
                if tag != f"{{{REL_NS}}}Relationship":
                    continue
                raw_target = attrs.get("Target", "")
                rel_id = attrs.get("Id", "")
                if not raw_target or not rel_id or not attrs.get("Type") or rel_id in ids:
                    self.findings.append(Finding("invalid_relationships", name))
                    continue
                ids.add(rel_id)
                external = attrs.get("TargetMode") == "External"
                try:
                    resolved = raw_target if external else resolve_target(source, raw_target)
                except ValueError as exc:
                    self.findings.append(Finding("invalid_relationships", name, str(exc)))
                    continue
                relationship = RelationshipInventory(
                    source, rel_id, attrs["Type"], resolved, external
                )
                self.relationships.append(relationship)
                if not external and resolved not in self.members:
                    self.findings.append(
                        Finding("missing_relationship_target", name, target=resolved)
                    )

    def _reachable(self) -> set[str]:
        edges: dict[str, list[str]] = {}
        for rel in self.relationships:
            if not rel.external:
                edges.setdefault(rel.source, []).append(rel.target)
        reached = {"/"}
        pending = deque(["/"])
        while pending:
            for target in edges.get(pending.popleft(), []):
                if target not in reached and target in self.members:
                    reached.add(target)
                    pending.append(target)
        reached.add("[Content_Types].xml")
        reached.update(name for name in self.members if relationship_source(name) in reached)
        return reached

    def content_type(self, name: str) -> str | None:
        return self.overrides.get(name) or self.defaults.get(name.rsplit(".", 1)[-1].lower())

    def report(self) -> PackageInspection:
        self._read_metadata()
        reachable = self._reachable()
        main_parts = {
            rel.target
            for rel in self.relationships
            if rel.source == "/"
            and relationship_kind(rel.relationship_type) == "officeDocument"
            and not rel.external
            and rel.target in self.members
        }
        if not main_parts:
            self.findings.append(Finding("missing_main_document"))
        story_parts = main_parts | {
            rel.target
            for rel in self.relationships
            if rel.source in reachable
            and relationship_kind(rel.relationship_type) in STORIES
            and not rel.external
        }
        features = Features()
        for name in sorted(self.members):
            if name == "[Content_Types].xml" or relationship_source(name) is not None:
                continue
            if not is_xml(name, self.content_type(name)):
                continue
            observed = self._scan(name, XmlFacts(name in story_parts))
            features = Features(
                features.field_hyperlink or observed.field_hyperlink,
                features.split_hyperlink_runs or observed.split_hyperlink_runs,
            )
        inventory = PackageInventory(
            tuple(
                PartInventory(name, member.file_size, self.content_type(name), name in reachable)
                for name, member in sorted(self.members.items())
            ),
            tuple(self.relationships),
        )
        return PackageInspection(inventory, tuple(self.findings), features)


def inspect(source: PackageSource) -> PackageInspection:
    """Observe package structure and Word story features without constructing a Document.

    Format failures become findings. Source opening failures propagate, and invalid
    argument types raise TypeError.
    Seekable streams are read from the beginning and restored; borrowed streams stay open.
    Binary members are inventoried without reading their payloads.
    """
    with open_source(source) as stream:
        try:
            with ZipFile(stream) as package:
                return _Inspection(package).report()
        except PACKAGE_ERRORS as exc:
            return PackageInspection(findings=(Finding("not_a_package", message=str(exc)),))
