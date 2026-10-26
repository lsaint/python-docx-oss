"""Stream sorted package members into a versioned, unambiguously framed digest."""

from __future__ import annotations

import hashlib
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from fnmatch import fnmatchcase
from urllib.parse import unquote
from zipfile import ZipFile

from lxml import etree

from docx.inspection.features import MetadataFacts
from docx.inspection.reader import CT_NS, REL_NS, is_xml, scan_xml
from docx.inspection.source import PackageSource, open_source


@dataclass(frozen=True)
class FingerprintPolicy:
    """Explicit exclusions; the default includes every member and all XML content.

    Part patterns match package-relative names using shell-style fnmatch (``*``
    also matches ``/``). XML exclusions use expanded names, e.g. ``{namespace}tag``.
    Relationship exclusions match complete Type URIs. Excluding a part does not
    implicitly remove its relationships or Content-Type declaration.
    """

    exclude_parts: tuple[str, ...] = ()
    exclude_relationship_types: tuple[str, ...] = ()
    exclude_xml_tags: tuple[str, ...] = ()
    exclude_xml_attributes: tuple[str, ...] = ()
    canonicalize_xml: bool = True

    def __post_init__(self) -> None:
        if not self.canonicalize_xml and (
            self.exclude_relationship_types or self.exclude_xml_tags or self.exclude_xml_attributes
        ):
            raise ValueError("XML exclusions require canonicalize_xml=True")


class _CanonicalXml:
    def __init__(self, write: Callable[[str], None], policy: FingerprintPolicy):
        self._writer = etree.C14NWriterTarget(
            write,
            with_comments=True,
            exclude_tags=set(policy.exclude_xml_tags),
            exclude_attrs=set(policy.exclude_xml_attributes),
        )
        self._excluded_relationships = policy.exclude_relationship_types
        self._skip_depth = 0

    def start_ns(self, prefix: str | None, uri: str) -> None:
        self._writer.start_ns(prefix or "", uri)

    def end_ns(self, prefix: str | None) -> None:
        pass

    def start(self, tag: str, attrs: Mapping[str, str]) -> None:
        if self._skip_depth or (
            tag == f"{{{REL_NS}}}Relationship" and attrs.get("Type") in self._excluded_relationships
        ):
            self._skip_depth += 1
        else:
            self._writer.start(tag, dict(attrs))

    def end(self, tag: str) -> None:
        if self._skip_depth:
            self._skip_depth -= 1
        else:
            self._writer.end(tag)

    def data(self, text: str) -> None:
        if not self._skip_depth:
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

    XML uses C14N 2.0 with comments, preserving text whitespace and namespace
    prefixes. This is a package-content comparison, not a semantic Word diff.
    Malformed XML and ambiguous duplicate names raise; no partial hash is returned.
    Stream ownership and position guarantees match inspect().
    """
    policy = FingerprintPolicy() if policy is None else policy
    with open_source(source) as stream, ZipFile(stream) as package:
        members = [member for member in package.infolist() if not member.is_dir()]
        if len({member.filename for member in members}) != len(members):
            raise ValueError("Cannot fingerprint a package with duplicate member names")
        defaults, overrides = _xml_types(package) if policy.canonicalize_xml else ({}, {})
        digest = hashlib.sha256(b"python-docx-oss package fingerprint v1\0")
        for member in sorted(members, key=lambda member: member.filename):
            name = member.filename
            if any(fnmatchcase(name, pattern) for pattern in policy.exclude_parts):
                continue
            part_digest = hashlib.sha256()
            content_type = overrides.get(name) or defaults.get(name.rsplit(".", 1)[-1].lower())
            with package.open(member) as content:
                if policy.canonicalize_xml and is_xml(name, content_type):
                    target = _CanonicalXml(
                        lambda text: part_digest.update(text.encode("utf-8")), policy
                    )
                    parser = etree.XMLParser(target=target, resolve_entities=False, no_network=True)
                    try:
                        while chunk := content.read(64 * 1024):
                            parser.feed(chunk)
                        parser.close()
                    except (etree.XMLSyntaxError, ValueError) as exc:
                        raise ValueError(f"Cannot fingerprint XML part {name!r}: {exc}") from exc
                else:
                    while chunk := content.read(64 * 1024):
                        part_digest.update(chunk)
            encoded_name = name.encode("utf-8")
            digest.update(len(encoded_name).to_bytes(8, "big"))
            digest.update(encoded_name)
            digest.update(part_digest.digest())
        return digest.hexdigest()
