"""Provides a general interface to a `physical` OPC package, such as a zip file."""

import os
from zipfile import ZIP_DEFLATED, ZipFile, is_zipfile

from docx.opc.exceptions import PackageNotFoundError
from docx.opc.packuri import CONTENT_TYPES_URI

_STRICT_TO_TRANSITIONAL_MAPPINGS = (
    # Hyphenated differences in Transitional relationships and parts:
    (
        b"http://purl.oclc.org/ooxml/officeDocument/relationships/extendedProperties",
        b"http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties",
    ),
    (
        b"http://purl.oclc.org/ooxml/officeDocument/relationships/customProperties",
        b"http://schemas.openxmlformats.org/officeDocument/2006/relationships/custom-properties",
    ),
    (
        b"http://purl.oclc.org/ooxml/officeDocument/extendedProperties",
        b"http://schemas.openxmlformats.org/officeDocument/2006/extended-properties",
    ),
    (
        b"http://purl.oclc.org/ooxml/officeDocument/customProperties",
        b"http://schemas.openxmlformats.org/officeDocument/2006/custom-properties",
    ),
    # General officeDocument rule (covers relationships, math, customXml, etc.):
    (
        b"http://purl.oclc.org/ooxml/officeDocument/",
        b"http://schemas.openxmlformats.org/officeDocument/2006/",
    ),
    # Domain packages:
    (
        b"http://purl.oclc.org/ooxml/wordprocessingml/",
        b"http://schemas.openxmlformats.org/wordprocessingml/2006/",
    ),
    (
        b"http://purl.oclc.org/ooxml/drawingml/",
        b"http://schemas.openxmlformats.org/drawingml/2006/",
    ),
    (
        b"http://purl.oclc.org/ooxml/spreadsheetml/",
        b"http://schemas.openxmlformats.org/spreadsheetml/2006/",
    ),
    (
        b"http://purl.oclc.org/ooxml/presentationml/",
        b"http://schemas.openxmlformats.org/presentationml/2006/",
    ),
    (
        b"http://purl.oclc.org/ooxml/schemaLibrary/",
        b"http://schemas.openxmlformats.org/schemaLibrary/2006/",
    ),
)


def _normalize_strict_blob(pack_uri, blob):
    """Normalize ISO/IEC 29500 Strict Open XML namespaces to Transitional.

    If an XML or relationship blob contains Strict namespaces under
    'purl.oclc.org/ooxml', convert them to standard Transitional namespaces so
    the package parts and relationships can be processed uniformly.

    Limitations and Edge Cases:
    1. Byte substring replacement: If document user text or Custom XML data
       coincidentally contains the exact PURL URI string, it will also be
       replaced.
    2. Encoding: Assumes UTF-8/ASCII XML encoding (the OOXML standard default).
       UTF-16 encoded XML parts are not matched by ASCII byte patterns.
    3. Part filtering: Triggered by filename extensions ('.xml', '.rels') rather
       than inspecting MIME Content-Types.
    """
    if not pack_uri.membername.endswith((".xml", ".rels")):
        return blob
    if b"http://purl.oclc.org/ooxml/" not in blob:
        return blob
    for strict_ns, trans_ns in _STRICT_TO_TRANSITIONAL_MAPPINGS:
        blob = blob.replace(strict_ns, trans_ns)
    if b'w:conformance="strict"' in blob:
        blob = blob.replace(b'w:conformance="strict"', b'w:conformance="transitional"')
    elif b"w:conformance='strict'" in blob:
        blob = blob.replace(b"w:conformance='strict'", b"w:conformance='transitional'")
    return blob


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
