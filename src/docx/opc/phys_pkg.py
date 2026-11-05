"""Provides a general interface to a `physical` OPC package, such as a zip file."""

import os
import re
from html import unescape
from xml.sax.saxutils import escape
from zipfile import ZIP_DEFLATED, ZipFile, is_zipfile

from lxml import etree

from docx.opc.exceptions import PackageNotFoundError
from docx.opc.packuri import CONTENT_TYPES_URI, PackURI

_STRICT_TO_TRANSITIONAL_MAPPINGS = (
    # Hyphenated differences in Transitional relationships and parts:
    (
        "http://purl.oclc.org/ooxml/officeDocument/relationships/extendedProperties",
        "http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties",
    ),
    (
        "http://purl.oclc.org/ooxml/officeDocument/relationships/customProperties",
        "http://schemas.openxmlformats.org/officeDocument/2006/relationships/custom-properties",
    ),
    (
        "http://purl.oclc.org/ooxml/officeDocument/extendedProperties",
        "http://schemas.openxmlformats.org/officeDocument/2006/extended-properties",
    ),
    (
        "http://purl.oclc.org/ooxml/officeDocument/customProperties",
        "http://schemas.openxmlformats.org/officeDocument/2006/custom-properties",
    ),
    # General officeDocument rule (covers relationships, math, customXml, etc.):
    (
        "http://purl.oclc.org/ooxml/officeDocument/",
        "http://schemas.openxmlformats.org/officeDocument/2006/",
    ),
    # Domain packages:
    (
        "http://purl.oclc.org/ooxml/wordprocessingml/",
        "http://schemas.openxmlformats.org/wordprocessingml/2006/",
    ),
    (
        "http://purl.oclc.org/ooxml/drawingml/",
        "http://schemas.openxmlformats.org/drawingml/2006/",
    ),
    (
        "http://purl.oclc.org/ooxml/spreadsheetml/",
        "http://schemas.openxmlformats.org/spreadsheetml/2006/",
    ),
    (
        "http://purl.oclc.org/ooxml/presentationml/",
        "http://schemas.openxmlformats.org/presentationml/2006/",
    ),
    (
        "http://purl.oclc.org/ooxml/schemaLibrary/",
        "http://schemas.openxmlformats.org/schemaLibrary/2006/",
    ),
)


def _transitional_uri(uri: str) -> str:
    for strict_base, transitional_base in _STRICT_TO_TRANSITIONAL_MAPPINGS:
        if uri.startswith(strict_base):
            return transitional_base + uri[len(strict_base) :]
    return uri


# Match whole XML tokens so apparent tags inside comments, CDATA, and PIs stay opaque.
_XML_TOKEN = re.compile(
    r"<!--.*?-->|<!\[CDATA\[.*?\]\]>|<\?.*?\?>|</?[^\s<>/]+(?:[^<>\"']|\"[^\"]*\"|'[^']*')*>",
    re.DOTALL,
)
_XML_ATTRIBUTE = re.compile(r"([^\s=<>/]+)(\s*=\s*)([\"'])(.*?)\3", re.DOTALL)
_XML_NAME = re.compile(r"</?([^\s/>]+)")
_WML_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
_DRAWING_NS = "http://schemas.openxmlformats.org/drawingml/2006/main"
_REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"


def _normalize_strict_blob(pack_uri: PackURI, blob: bytes) -> bytes:
    """Normalize selected XML attributes without rebuilding or reserializing the tree.

    Namespace scopes identify semantic attributes regardless of prefix. Text,
    comments, CDATA, unrelated attributes, and original formatting are preserved.
    Malformed or DTD-bearing opaque parts are passed through unchanged.
    """
    if not pack_uri.membername.endswith((".xml", ".rels")):
        return blob
    if b"http://purl.oclc.org/ooxml/" not in blob.replace(b"\x00", b""):
        return blob
    try:
        root = etree.fromstring(blob, etree.XMLParser(resolve_entities=False))
        if root.getroottree().docinfo.doctype:
            return blob
        if blob.startswith((b"\xff\xfe", b"<\x00")):
            encoding = "utf-16-le"
        elif blob.startswith((b"\xfe\xff", b"\x00<")):
            encoding = "utf-16-be"
        else:
            encoding = "utf-8"
        xml = blob.decode(encoding)
    except (etree.XMLSyntaxError, UnicodeError, ValueError):
        return blob

    scopes: list[dict[str, str]] = [{}]

    def convert_tag(match: re.Match[str]) -> str:
        tag = match.group()
        if tag.startswith(("<!", "<?")):
            return tag
        if tag.startswith("</"):
            scopes.pop()
            return tag
        scope = scopes[-1]
        if "xmlns" in tag:
            scope = scope.copy()
            for attr in _XML_ATTRIBUTE.finditer(tag):
                name, _, _, value = attr.groups()
                if name == "xmlns" or name.startswith("xmlns:"):
                    scope[name.partition(":")[2]] = unescape(value)
        if not tag.endswith("/>"):
            scopes.append(scope)
        if "http://purl.oclc.org/ooxml/" not in tag and "conformance" not in tag:
            return tag
        name_match = _XML_NAME.match(tag)
        assert name_match is not None
        prefix, separator, local = name_match[1].rpartition(":")
        element_ns = _transitional_uri(scope.get(prefix if separator else "", ""))

        def convert_attribute(attr: re.Match[str]) -> str:
            name, equals, quote, value = attr.groups()
            decoded = unescape(value)
            converted = decoded
            if (
                name == "xmlns"
                or name.startswith("xmlns:")
                or (element_ns == _REL_NS and local == "Relationship" and name == "Type")
                or (element_ns == _DRAWING_NS and local == "graphicData" and name == "uri")
            ):
                converted = _transitional_uri(decoded)
            elif ":" in name:
                prefix, _, attr_local = name.partition(":")
                if (
                    _transitional_uri(scope.get(prefix, "")) == _WML_NS
                    and attr_local == "conformance"
                    and decoded == "strict"
                ):
                    converted = "transitional"
            if converted == decoded:
                return attr.group()
            return (
                name
                + equals
                + quote
                + escape(converted, {quote: "&quot;" if quote == '"' else "&apos;"})
                + quote
            )

        return _XML_ATTRIBUTE.sub(convert_attribute, tag)

    normalized = _XML_TOKEN.sub(convert_tag, xml)
    return blob if normalized == xml else normalized.encode(encoding)


class PhysPkgReader:
    """Factory for physical package reader objects."""

    def __new__(cls, pkg_file):
        # if `pkg_file` is a string, treat it as a path
        if isinstance(pkg_file, str):
            if os.path.isdir(pkg_file):
                reader_cls = _DirPkgReader
            elif is_zipfile(pkg_file):
                reader_cls = _ZipPkgReader
            else:
                raise PackageNotFoundError("Package not found at '%s'" % pkg_file)
        else:  # assume it's a stream and pass it to Zip reader to sort out
            reader_cls = _ZipPkgReader

        return super(PhysPkgReader, cls).__new__(reader_cls)


class PhysPkgWriter:
    """Factory for physical package writer objects."""

    def __new__(cls, pkg_file):
        return super(PhysPkgWriter, cls).__new__(_ZipPkgWriter)


class _DirPkgReader(PhysPkgReader):
    """Implements |PhysPkgReader| interface for an OPC package extracted into a
    directory."""

    def __init__(self, path):
        """`path` is the path to a directory containing an expanded package."""
        super(_DirPkgReader, self).__init__()
        self._path = os.path.abspath(path)

    def blob_for(self, pack_uri):
        """Return contents of file corresponding to `pack_uri` in package directory."""
        path = os.path.join(self._path, pack_uri.membername)
        with open(path, "rb") as f:
            blob = f.read()
        return _normalize_strict_blob(pack_uri, blob)

    def close(self):
        """Provides interface consistency with |ZipFileSystem|, but does nothing, a
        directory file system doesn't need closing."""
        pass

    @property
    def content_types_xml(self):
        """Return the `[Content_Types].xml` blob from the package."""
        return self.blob_for(CONTENT_TYPES_URI)

    def rels_xml_for(self, source_uri):
        """Return rels item XML for source with `source_uri`, or None if the item has no
        rels item."""
        try:
            rels_xml = self.blob_for(source_uri.rels_uri)
        except IOError:
            rels_xml = None
        return rels_xml


class _ZipPkgReader(PhysPkgReader):
    """Implements |PhysPkgReader| interface for a zip file OPC package."""

    def __init__(self, pkg_file):
        super(_ZipPkgReader, self).__init__()
        self._zipf = ZipFile(pkg_file, "r")

    def blob_for(self, pack_uri):
        """Return blob corresponding to `pack_uri`.

        Raises |ValueError| if no matching member is present in zip archive.
        """
        return _normalize_strict_blob(pack_uri, self._zipf.read(pack_uri.membername))

    def close(self):
        """Close the zip archive, releasing any resources it is using."""
        self._zipf.close()

    @property
    def content_types_xml(self):
        """Return the `[Content_Types].xml` blob from the zip package."""
        return self.blob_for(CONTENT_TYPES_URI)

    def rels_xml_for(self, source_uri):
        """Return rels item XML for source with `source_uri` or None if no rels item is
        present."""
        try:
            rels_xml = self.blob_for(source_uri.rels_uri)
        except KeyError:
            rels_xml = None
        return rels_xml


class _ZipPkgWriter(PhysPkgWriter):
    """Implements |PhysPkgWriter| interface for a zip file OPC package."""

    def __init__(self, pkg_file):
        super(_ZipPkgWriter, self).__init__()
        self._zipf = ZipFile(pkg_file, "w", compression=ZIP_DEFLATED)

    def close(self):
        """Close the zip archive, flushing any pending physical writes and releasing any
        resources it's using."""
        self._zipf.close()

    def write(self, pack_uri, blob):
        """Write `blob` to this zip package with the membername corresponding to
        `pack_uri`."""
        self._zipf.writestr(pack_uri.membername, blob)
