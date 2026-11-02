"""Stream sorted package members into a versioned, unambiguously framed digest."""

from __future__ import annotations

import hashlib
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from fnmatch import fnmatchcase
from types import MappingProxyType
from typing import Any, Literal
from urllib.parse import unquote
from zipfile import ZipFile

from lxml import etree

from docx.inspection._structural_xml_tags import STRUCTURAL_XML_TAGS
from docx.inspection.features import MetadataFacts
from docx.inspection.reader import CT_NS, REL_NS, is_xml, scan_xml
from docx.inspection.source import PackageSource, open_source

_XML_SPACE = "{http://www.w3.org/XML/1998/namespace}space"
_XSI_TYPE = "{http://www.w3.org/2001/XMLSchema-instance}type"
_THEME_CONTENT_TYPE = "application/vnd.openxmlformats-officedocument.theme+xml"
_WORD_CONTENT_TYPE_PREFIXES = (
    "application/vnd.openxmlformats-officedocument.wordprocessingml.",
    "application/vnd.ms-word.",
)


@dataclass(frozen=True)
class FingerprintItem:
    """A package part or XML element presented to an exclusion predicate."""

    kind: Literal["part", "xml_element"]
    part_name: str
    tag: str = ""
    attributes: Mapping[str, str] = field(default_factory=lambda: MappingProxyType({}))
    ancestors: tuple[str, ...] = ()

    @property
    def parent_tag(self) -> str | None:
        return self.ancestors[-1] if self.ancestors else None


@dataclass(frozen=True)
class FingerprintPolicy:
    """Explicit exclusions and XML whitespace policy.

    Part patterns match package-relative names using shell-style fnmatch (``*``
    also matches ``/``). XML exclusions use expanded names, e.g. ``{namespace}tag``.
    Relationship exclusions match complete Type URIs. Excluding a part does not
    implicitly remove its relationships or Content-Type declaration. Whitespace in
    known schema-derived Word and DrawingML element-only structures is ignored by
    default; unknown elements retain whitespace. Set ignore_structural_whitespace
    to False to retain it, or use normalize for custom comparison rules.
    """

    exclude_parts: tuple[str, ...] = ()
    exclude_relationship_types: tuple[str, ...] = ()
    exclude_xml_tags: tuple[str, ...] = ()
    exclude_xml_attributes: tuple[str, ...] = ()
    canonicalize_xml: bool = True
    ignore_structural_whitespace: bool = True
    exclude: Callable[[FingerprintItem], bool] | None = None
    normalize: (
        Callable[[FingerprintItem, Callable[[], bytes]], bytes | Literal["raw"] | None] | None
    ) = None

    def __post_init__(self) -> None:
        if not self.canonicalize_xml and (
            self.exclude_relationship_types or self.exclude_xml_tags or self.exclude_xml_attributes
        ):
            raise ValueError("XML exclusions require canonicalize_xml=True")


class _ExclusionError(Exception):
    def __init__(self, error: Exception):
        self.error = error


def serialize_xml(
    data: bytes,
    *,
    part_name: str = "",
    exclude: Callable[[FingerprintItem], bool] | None = None,
) -> bytes:
    """Serialize an XML tree after removing blank text and selected subtrees."""
    parser = etree.XMLParser(remove_blank_text=True, resolve_entities=False, no_network=True)
    root = etree.fromstring(data, parser)
    if root.getroottree().docinfo.doctype:
        raise ValueError("DTDs are not supported in package XML")

    def prune(element: Any, ancestors: tuple[str, ...]) -> bool:
        tag = element.tag
        if not isinstance(tag, str):
            return False
        if exclude is not None:
            item = FingerprintItem(
                "xml_element", part_name, tag, MappingProxyType(dict(element.attrib)), ancestors
            )
            if exclude(item):
                return True
        for child in list(element):
            if prune(child, (*ancestors, tag)):
                if child.tail:
                    previous = child.getprevious()
                    if previous is None:
                        element.text = (element.text or "") + child.tail
                    else:
                        previous.tail = (previous.tail or "") + child.tail
                element.remove(child)
        return False

    if prune(root, ()):
        return b""
    return etree.tostring(root, encoding="UTF-8", method="xml")


class _CanonicalXml:
    def __init__(
        self,
        write: Callable[[str], None],
        policy: FingerprintPolicy,
        content_type: str | None,
        part_name: str,
    ):
        self._writer = etree.C14NWriterTarget(
            write,
            with_comments=True,
            exclude_attrs=set(policy.exclude_xml_attributes),
        )
        self._excluded_relationships = policy.exclude_relationship_types
        self._excluded_tags = set(policy.exclude_xml_tags)
        self._exclude = policy.exclude
        self._part_name = part_name
        self._skip_depth = 0
        self._namespaces = hashlib.sha256()
        self._pending_namespaces: list[tuple[str, str]] = []
        self._element_index = 0
        self._ignore_structural_whitespace = bool(
            policy.ignore_structural_whitespace
            and content_type
            and (
                content_type == _THEME_CONTENT_TYPE
                or (
                    content_type.startswith(_WORD_CONTENT_TYPE_PREFIXES)
                    and content_type.endswith("+xml")
                )
            )
        )
        self._elements: list[tuple[str, bool, bool]] = []

    def start_ns(self, prefix: str | None, uri: str) -> None:
        if not self._skip_depth:
            self._pending_namespaces.append((prefix or "", uri))
            self._writer.start_ns(prefix or "", uri)

    def end_ns(self, prefix: str | None) -> None:
        pass

    def start(self, tag: str, attrs: Mapping[str, str]) -> None:
        excluded = (
            self._skip_depth
            or tag in self._excluded_tags
            or (
                tag == f"{{{REL_NS}}}Relationship"
                and attrs.get("Type") in self._excluded_relationships
            )
        )
        if not excluded and self._exclude is not None:
            item = FingerprintItem(
                "xml_element",
                self._part_name,
                tag,
                MappingProxyType(dict(attrs)),
                tuple(element[0] for element in self._elements),
            )
            try:
                excluded = self._exclude(item)
            except Exception as exc:
                raise _ExclusionError(exc) from exc
        if excluded:
            self._pending_namespaces.clear()
            self._skip_depth += 1
        else:
            if self._pending_namespaces:
                self._namespaces.update(self._element_index.to_bytes(8, "big"))
                self._namespaces.update(len(self._pending_namespaces).to_bytes(8, "big"))
                for prefix, uri in sorted(self._pending_namespaces):
                    for value in (prefix, uri):
                        encoded = value.encode("utf-8")
                        self._namespaces.update(len(encoded).to_bytes(8, "big"))
                        self._namespaces.update(encoded)
                self._pending_namespaces.clear()
            self._element_index += 1
            inherited = self._elements[-1][1] if self._elements else False
            space = attrs.get(_XML_SPACE)
            preserve = True if space == "preserve" else False if space == "default" else inherited
            self._elements.append((tag, preserve, _XSI_TYPE not in attrs))
            self._writer.start(tag, dict(attrs))

    def end(self, tag: str) -> None:
        if self._skip_depth:
            self._skip_depth -= 1
        else:
            self._writer.end(tag)
            self._elements.pop()

    def data(self, text: str) -> None:
        if self._skip_depth:
            return
        if (
            self._ignore_structural_whitespace
            and self._elements
            and self._elements[-1][0] in STRUCTURAL_XML_TAGS
            and not self._elements[-1][1]
            and self._elements[-1][2]
            and not text.strip(" \t\r\n")
        ):
            return
        self._writer.data(text)

    def comment(self, text: str) -> None:
        if not self._skip_depth:
            self._writer.comment(text)

    def pi(self, target: str, data: str) -> None:
        if not self._skip_depth:
            self._writer.pi(target, data)

    def doctype(self, name: str | None, public_id: str | None, system_id: str | None) -> None:
        raise ValueError("DTDs are not supported in package XML")

    def close(self) -> None:
        self._writer.close()

    def namespace_digest(self) -> bytes:
        return self._namespaces.digest()


def _xml_types(package: ZipFile) -> tuple[dict[str, str], dict[str, str]]:
    if "[Content_Types].xml" not in package.namelist():
        return {}, {}
    target = MetadataFacts()
    try:
        scan_xml(package, package.getinfo("[Content_Types].xml"), target)
    except (etree.XMLSyntaxError, ValueError) as exc:
        raise ValueError(f"Cannot fingerprint XML part '[Content_Types].xml': {exc}") from exc
    defaults: dict[str, str] = {}
    overrides: dict[str, str] = {}
    for tag, attrs in target.elements:
        if tag == f"{{{CT_NS}}}Default":
            defaults[attrs.get("Extension", "").lower()] = attrs.get("ContentType", "")
        elif tag == f"{{{CT_NS}}}Override":
            overrides[unquote(attrs.get("PartName", "")).lstrip("/")] = attrs.get("ContentType", "")
    return defaults, overrides


def fingerprint(source: PackageSource, *, policy: FingerprintPolicy | None = None) -> str:
    """Return a SHA-256 content fingerprint, ignoring ZIP order and ZIP metadata.

    By default, XML uses C14N 2.0 with comments and ignores whitespace-only text
    in a limited set of schema-derived Word, DrawingML, MCE, and WPS structures,
    unless xml:space preserves it. Other text and namespaces are preserved. This
    is not a semantic Word diff.
    Malformed XML raises by default; ambiguous duplicate names always raise.
    Stream ownership and position guarantees match inspect().
    """
    policy = FingerprintPolicy() if policy is None else policy
    with open_source(source) as stream, ZipFile(stream) as package:
        members = [member for member in package.infolist() if not member.is_dir()]
        if len({member.filename for member in members}) != len(members):
            raise ValueError("Cannot fingerprint a package with duplicate member names")
        xml_types: tuple[dict[str, str], dict[str, str]] | None = (
            _xml_types(package) if policy.canonicalize_xml and policy.normalize is None else None
        )
        digest = hashlib.sha256(b"python-docx-oss package fingerprint v3\0")
        for member in sorted(members, key=lambda member: member.filename):
            name = member.filename
            if any(fnmatchcase(name, pattern) for pattern in policy.exclude_parts) or (
                policy.exclude is not None and policy.exclude(FingerprintItem("part", name))
            ):
                continue
            part_digest = hashlib.sha256()
            with package.open(member) as content:
                cached: bytes | None = None

                def read_bytes() -> bytes:
                    nonlocal cached
                    if cached is None:
                        cached = content.read()
                    return cached

                normalized = (
                    policy.normalize(FingerprintItem("part", name), read_bytes)
                    if policy.normalize is not None
                    else None
                )
                if (
                    normalized is not None
                    and not isinstance(normalized, bytes)
                    and normalized != "raw"
                ):
                    raise TypeError("normalize must return bytes, 'raw', or None")
                if isinstance(normalized, bytes):
                    part_digest.update(normalized)
                else:
                    if cached is not None:
                        content.seek(0)
                if normalized == "raw" or (normalized is None and not policy.canonicalize_xml):
                    while chunk := content.read(64 * 1024):
                        part_digest.update(chunk)
                elif normalized is None:
                    if xml_types is None:
                        xml_types = _xml_types(package)
                    defaults, overrides = xml_types
                    content_type = overrides.get(name) or defaults.get(
                        name.rsplit(".", 1)[-1].lower()
                    )
                    if not is_xml(name, content_type):
                        while chunk := content.read(64 * 1024):
                            part_digest.update(chunk)
                        encoded_name = name.encode("utf-8")
                        digest.update(len(encoded_name).to_bytes(8, "big"))
                        digest.update(encoded_name)
                        digest.update(part_digest.digest())
                        continue
                    target = _CanonicalXml(
                        lambda text: part_digest.update(text.encode("utf-8")),
                        policy,
                        content_type,
                        name,
                    )
                    parser = etree.XMLParser(target=target, resolve_entities=False, no_network=True)
                    try:
                        while chunk := content.read(64 * 1024):
                            parser.feed(chunk)
                        parser.close()
                        part_digest.update(target.namespace_digest())
                    except _ExclusionError as exc:
                        raise exc.error from exc
                    except (etree.XMLSyntaxError, ValueError) as exc:
                        raise ValueError(f"Cannot fingerprint XML part {name!r}: {exc}") from exc
            encoded_name = name.encode("utf-8")
            digest.update(len(encoded_name).to_bytes(8, "big"))
            digest.update(encoded_name)
            digest.update(part_digest.digest())
        return digest.hexdigest()
