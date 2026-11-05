"""Integration test suite for ISO/IEC 29500 Strict Open XML round-trip processing."""

from __future__ import annotations

import io
import zipfile
from pathlib import Path

import pytest
from lxml import etree

from docx import Document
from docx.enum.shape import WD_INLINE_SHAPE
from docx.enum.text import WD_PARAGRAPH_ALIGNMENT
from docx.shared import Pt


def _make_minimal_strict_docx() -> io.BytesIO:
    content_types = (
        b'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
        b'<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">\n'
        b'  <Default Extension="rels" '
        b'ContentType="application/vnd.openxmlformats-package.relationships+xml"/>\n'
        b'  <Default Extension="xml" ContentType="application/xml"/>\n'
        b'  <Override PartName="/word/document.xml" '
        b'ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.'
        b'document.main+xml"/>\n'
        b"</Types>"
    )
    rels = (
        b'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
        b'<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">\n'
        b'  <Relationship Id="rId1" '
        b'Type="http://purl.oclc.org/ooxml/officeDocument/relationships/officeDocument" '
        b'Target="word/document.xml"/>\n'
        b"</Relationships>"
    )
    document_xml = (
        b'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
        b'<w:document xmlns:w="http://purl.oclc.org/ooxml/wordprocessingml/main" '
        b'w:conformance="strict">\n'
        b"  <w:body>\n"
        b"    <w:p>\n"
        b"      <w:pPr>\n"
        b'        <w:ind w:start="720"/>\n'
        b'        <w:jc w:val="start"/>\n'
        b"      </w:pPr>\n"
        b"      <w:r><w:t>Strict Paragraph</w:t></w:r>\n"
        b"    </w:p>\n"
        b"    <w:tbl>\n"
        b'      <w:tblGrid><w:gridCol w:w="4632"/></w:tblGrid>\n'
        b"      <w:tr>\n"
        b"        <w:tc>\n"
        b"          <w:tcPr>\n"
        b'            <w:tcW w:w="231.60pt" w:type="dxa"/>\n'
        b"          </w:tcPr>\n"
        b"          <w:p><w:r><w:t>Cell 1</w:t></w:r></w:p>\n"
        b"        </w:tc>\n"
        b"      </w:tr>\n"
        b"    </w:tbl>\n"
        b"  </w:body>\n"
        b"</w:document>"
    )
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("[Content_Types].xml", content_types)
        z.writestr("_rels/.rels", rels)
        z.writestr("word/document.xml", document_xml)
    buf.seek(0)
    return buf


class DescribeStrictDocxRoundTrip:
    """Integration tests for opening, reading, saving, and reopening Strict DOCX."""

    def it_can_open_read_save_and_reopen_strict_docx(self):
        # 1. Open
        in_buf = _make_minimal_strict_docx()
        doc = Document(in_buf)

        # 2. Read and verify strict features
        assert len(doc.paragraphs) == 1
        p = doc.paragraphs[0]
        assert p.text == "Strict Paragraph"
        assert p.paragraph_format.left_indent == Pt(36)
        assert p.alignment == WD_PARAGRAPH_ALIGNMENT.LEFT

        assert len(doc.tables) == 1
        cell = doc.tables[0].cell(0, 0)
        assert cell.width is not None
        assert round(cell.width.pt, 2) == 231.60

        # 3. Modify and save
        doc.add_paragraph("Appended Paragraph")
        out_buf = io.BytesIO()
        doc.save(out_buf)
        out_buf.seek(0)

        # 4. Reopen and verify content
        doc_reopened = Document(out_buf)
        assert len(doc_reopened.paragraphs) == 2
        assert doc_reopened.paragraphs[0].text == "Strict Paragraph"
        assert doc_reopened.paragraphs[1].text == "Appended Paragraph"

        # 5. Inspect package members
        out_buf.seek(0)
        with zipfile.ZipFile(out_buf) as z:
            for membername in z.namelist():
                if membername.endswith((".xml", ".rels")):
                    member_data = z.read(membername)
                    assert b"http://purl.oclc.org/ooxml" not in member_data, (
                        f"Found Strict PURL namespace in {membername}"
                    )

            doc_xml = z.read("word/document.xml")
            assert b'w:conformance="transitional"' in doc_xml
            assert b'w:conformance="strict"' not in doc_xml

    @pytest.mark.parametrize("encoding", ["UTF-8", "UTF-16", "UTF-16LE", "UTF-16BE"])
    def it_round_trips_alternate_prefixes_encodings_and_user_uris(self, encoding: str):
        uri = "http://purl.oclc.org/ooxml/wordprocessingml/main"
        source = _make_minimal_strict_docx()
        encoded = io.BytesIO()
        with zipfile.ZipFile(source) as src, zipfile.ZipFile(encoded, "w") as dst:
            for name in src.namelist():
                blob = src.read(name)
                if name == "word/document.xml":
                    blob = blob.replace(b"w:", b"x:").replace(b"xmlns:w=", b"xmlns:x=")
                    blob = blob.replace(b"Strict Paragraph", uri.encode())
                root = etree.fromstring(blob)
                dst.writestr(name, etree.tostring(root, encoding=encoding, xml_declaration=True))
        encoded.seek(0)
        doc = Document(encoded)
        assert doc.paragraphs[0].text == uri
        output = io.BytesIO()
        doc.save(output)
        output.seek(0)
        assert Document(output).paragraphs[0].text == uri
        with zipfile.ZipFile(output) as saved:
            root = etree.fromstring(saved.read("word/document.xml"))
            assert (
                root.get(
                    "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}conformance"
                )
                == "transitional"
            )

    def it_recognizes_strict_pictures_after_open_and_save(self):
        doc = Document()
        doc.add_picture(
            str(Path(__file__).parents[2] / "features" / "steps" / "test_files" / "test.png")
        )
        transitional = io.BytesIO()
        doc.save(transitional)
        transitional.seek(0)
        strict = io.BytesIO()
        with zipfile.ZipFile(transitional) as src, zipfile.ZipFile(strict, "w") as dst:
            for name in src.namelist():
                blob = src.read(name)
                if name.endswith((".xml", ".rels")):
                    blob = (
                        blob.replace(
                            b"http://schemas.openxmlformats.org/drawingml/2006/",
                            b"http://purl.oclc.org/ooxml/drawingml/",
                        )
                        .replace(
                            b"http://schemas.openxmlformats.org/wordprocessingml/2006/",
                            b"http://purl.oclc.org/ooxml/wordprocessingml/",
                        )
                        .replace(
                            b"http://schemas.openxmlformats.org/officeDocument/2006/relationships/",
                            b"http://purl.oclc.org/ooxml/officeDocument/relationships/",
                        )
                    )
                dst.writestr(name, blob)
        strict.seek(0)
        opened = Document(strict)
        assert opened.inline_shapes[0].type == WD_INLINE_SHAPE.PICTURE
        saved = io.BytesIO()
        opened.save(saved)
        saved.seek(0)
        assert Document(saved).inline_shapes[0].type == WD_INLINE_SHAPE.PICTURE
        with zipfile.ZipFile(saved) as package:
            xml = package.read("word/document.xml")
            assert b'uri="http://schemas.openxmlformats.org/drawingml/2006/picture"' in xml
            assert b"http://purl.oclc.org/ooxml/drawingml/picture" not in xml
