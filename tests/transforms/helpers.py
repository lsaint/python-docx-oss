"""Transformation fixtures preserve real Word package structure."""

from __future__ import annotations

import io
from pathlib import Path
from zipfile import ZipFile

from lxml import etree

from docx import Document
from tests.inspection.helpers import CT, RT, R, W, package

REL_ATTR = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"


def document_parts(body: str = "") -> dict[str, bytes]:
    path = Path(__file__).parents[1] / "fixtures/documents/word-blank.docx"
    with ZipFile(path) as archive:
        parts = {name: archive.read(name) for name in archive.namelist()}
    root = etree.fromstring(parts["word/document.xml"])
    body_element = root.find(f"{{{W}}}body")
    assert body_element is not None
    for child in list(body_element):
        if child.tag != f"{{{W}}}sectPr":
            body_element.remove(child)
    fragment = etree.fromstring(f'<root xmlns:w="{W}" xmlns:r="{REL_ATTR}">{body}</root>'.encode())
    for index, child in enumerate(list(fragment)):
        body_element.insert(index, child)
    parts["word/document.xml"] = etree.tostring(root)
    return parts


def unzip(content: bytes) -> dict[str, bytes]:
    with ZipFile(io.BytesIO(content)) as archive:
        return {name: archive.read(name) for name in archive.namelist()}


def complex_field(instruction: str = ' HYPERLINK "https://example.test/doc" ') -> str:
    escaped = instruction.replace("&", "&amp;").replace("<", "&lt;")
    return (
        '<w:p><w:r><w:fldChar w:fldCharType="begin"/></w:r>'
        f'<w:r><w:instrText xml:space="preserve">{escaped}</w:instrText></w:r>'
        '<w:r><w:fldChar w:fldCharType="separate"/></w:r>'
        '<w:r><w:rPr><w:b/></w:rPr><w:t xml:space="preserve">Hello </w:t></w:r>'
        "<w:r><w:rPr><w:i/></w:rPr><w:t>world</w:t></w:r>"
        '<w:r><w:fldChar w:fldCharType="end"/></w:r></w:p>'
    )


def link_runs(second_properties: str = "<w:b/>") -> str:
    return (
        '<w:p><w:hyperlink w:anchor="bookmark">'
        '<w:r><w:rPr><w:b/></w:rPr><w:t xml:space="preserve">Hello </w:t></w:r>'
        f"<w:r><w:rPr>{second_properties}</w:rPr><w:t>world</w:t></w:r>"
        "</w:hyperlink></w:p>"
    )


def custom_xml_package(content: bytes = b"", *, property_content: bytes | None = None) -> bytes:
    doc = Document()
    doc.add_paragraph("Keep this content")
    part = doc.part.add_custom_xml_part(
        '<payload xmlns="urn:example:payload">original</payload>',
        file_name="repair-data",
    )
    parts = unzip(doc.to_bytes())
    parts[str(part.partname).lstrip("/")] = content
    if property_content is not None:
        parts["customXml/repair-props.xml"] = property_content
        rels_name = "customXml/_rels/repair-data.xml.rels"
        parts[rels_name] = (
            f'<Relationships xmlns="{R}"><Relationship Id="props" '
            f'Type="{RT}customXmlProps" Target="repair-props.xml"/></Relationships>'
        ).encode()
        types = etree.fromstring(parts["[Content_Types].xml"])
        etree.SubElement(
            types,
            f"{{{CT}}}Override",
            PartName="/customXml/repair-props.xml",
            ContentType="application/vnd.openxmlformats-officedocument.customXmlProperties+xml",
        )
        parts["[Content_Types].xml"] = etree.tostring(types)
    return package(parts)
