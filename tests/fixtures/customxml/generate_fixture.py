"""Generate the multiple-Custom-XML-parts integration fixture."""

from __future__ import annotations

from pathlib import Path
from xml.etree import ElementTree
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

FIXTURE_ROOT = Path(__file__).parent.parent
SOURCE = FIXTURE_ROOT / "documents" / "word-blank.docx"
TARGET = Path(__file__).parent / "multiple-custom-xml-parts.docx"

CONTENT_TYPES_NS = "http://schemas.openxmlformats.org/package/2006/content-types"
DATA_STORE_NS = "http://schemas.openxmlformats.org/officeDocument/2006/customXml"
RELATIONSHIPS_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
CUSTOM_XML_RELATIONSHIP = (
    "http://schemas.openxmlformats.org/officeDocument/2006/relationships/customXml"
)
CUSTOM_XML_PROPS_RELATIONSHIP = (
    "http://schemas.openxmlformats.org/officeDocument/2006/relationships/customXmlProps"
)
CUSTOM_XML_PROPS_CONTENT_TYPE = (
    "application/vnd.openxmlformats-officedocument.customXmlProperties+xml"
)


def _serialize(element: ElementTree.Element) -> bytes:
    return ElementTree.tostring(element, encoding="utf-8", xml_declaration=True)


def _zip_info(name: str) -> ZipInfo:
    info = ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
    info.compress_type = ZIP_DEFLATED
    return info


def _add_content_types(parts: dict[str, bytes]) -> None:
    ElementTree.register_namespace("", CONTENT_TYPES_NS)
    root = ElementTree.fromstring(parts["[Content_Types].xml"])
    for number in (1, 3):
        ElementTree.SubElement(
            root,
            f"{{{CONTENT_TYPES_NS}}}Override",
            PartName=f"/customXml/itemProps{number}.xml",
            ContentType=CUSTOM_XML_PROPS_CONTENT_TYPE,
        )
    parts["[Content_Types].xml"] = _serialize(root)


def _add_document_relationships(parts: dict[str, bytes]) -> None:
    ElementTree.register_namespace("", RELATIONSHIPS_NS)
    path = "word/_rels/document.xml.rels"
    root = ElementTree.fromstring(parts[path])
    for relationship_id, number in (("rId8", 1), ("rId9", 3)):
        ElementTree.SubElement(
            root,
            f"{{{RELATIONSHIPS_NS}}}Relationship",
            Id=relationship_id,
            Type=CUSTOM_XML_RELATIONSHIP,
            Target=f"../customXml/item{number}.xml",
        )
    parts[path] = _serialize(root)


def _custom_xml_parts() -> dict[str, bytes]:
    return {
        "customXml/item1.xml": b"""<?xml version="1.0" encoding="UTF-8"?>
<customers xmlns="urn:python-docx-oss:customers" version="1">
  <customer id="C001"><name>Alice</name></customer>
  <customer id="C002"><name>Bob</name></customer>
</customers>
""",
        "customXml/item3.xml": b"""<?xml version="1.0" encoding="UTF-8"?>
<inventory xmlns="urn:python-docx-oss:inventory" warehouse="east">
  <item sku="SKU-001">Paper</item>
  <item sku="SKU-002">Ink</item>
</inventory>
""",
    }


def _property_parts() -> dict[str, bytes]:
    parts: dict[str, bytes] = {}
    for number, item_id in (
        (1, "11111111-1111-1111-1111-111111111111"),
        (3, "33333333-3333-3333-3333-333333333333"),
    ):
        properties = ElementTree.Element(
            f"{{{DATA_STORE_NS}}}datastoreItem",
            {f"{{{DATA_STORE_NS}}}itemID": f"{{{item_id}}}"},
        )
        ElementTree.SubElement(properties, f"{{{DATA_STORE_NS}}}schemaRefs")
        parts[f"customXml/itemProps{number}.xml"] = _serialize(properties)

        relationships = ElementTree.Element(f"{{{RELATIONSHIPS_NS}}}Relationships")
        ElementTree.SubElement(
            relationships,
            f"{{{RELATIONSHIPS_NS}}}Relationship",
            Id="rId1",
            Type=CUSTOM_XML_PROPS_RELATIONSHIP,
            Target=f"itemProps{number}.xml",
        )
        parts[f"customXml/_rels/item{number}.xml.rels"] = _serialize(relationships)
    return parts


def build_fixture() -> None:
    """Build the deterministic fixture at `TARGET`."""
    with ZipFile(SOURCE) as source:
        source_infos = source.infolist()
        parts = {info.filename: source.read(info.filename) for info in source_infos}

    _add_content_types(parts)
    _add_document_relationships(parts)
    parts.update(_custom_xml_parts())
    parts.update(_property_parts())

    source_names = {info.filename for info in source_infos}
    with ZipFile(TARGET, "w") as target:
        for info in source_infos:
            target.writestr(info, parts[info.filename])
        for name in sorted(parts.keys() - source_names):
            target.writestr(_zip_info(name), parts[name])


if __name__ == "__main__":
    build_fixture()
