"""Repair is opt-in, narrowly scoped, transactional, and graph-preserving."""

from __future__ import annotations

import io
from pathlib import Path
from zipfile import ZipFile

import pytest

from docx import Document, inspect, repair
from tests.inspection.helpers import package

from .helpers import custom_xml_package, document_parts, unzip


class DescribeCustomXmlRepair:
    @pytest.mark.parametrize("empty", [b"", b" \t\n\r", b" " * 100000])
    def it_repairs_empty_data_without_changing_relationships_or_other_members(self, empty: bytes):
        content = custom_xml_package(empty)
        before = unzip(content)
        assert inspect(content).has_finding("empty_xml_part")
        result = repair(content, empty_custom_xml=True)
        assert result.report.succeeded
        assert result.report.changed
        assert not result.report.after.findings
        after = unzip(result.content)
        changed = {name for name in before if before[name] != after[name]}
        assert changed == {"customXml/repair-data.xml"}
        assert b"<root/>" in after["customXml/repair-data.xml"]
        assert Document(result.content).paragraphs[0].text == "Keep this content"
        assert (
            result.report.before.inventory.relationships
            == result.report.after.inventory.relationships
        )
        assert result.report.changes[0].code == "filled_empty_custom_xml"
        again = repair(result.content, empty_custom_xml=True)
        assert again.report.succeeded
        assert not again.report.changed
        assert again.content == result.content

    def it_is_disabled_by_default_even_for_damaged_input(self):
        content = custom_xml_package()
        result = repair(content)
        assert result.content is content
        assert not result.report.changed
        assert result.report.before.has_finding("empty_xml_part")

    def it_preserves_custom_xml_properties(self):
        props = (
            b"<ds:datastoreItem "
            b'xmlns:ds="http://schemas.openxmlformats.org/officeDocument/2006/customXml" '
            b'ds:itemID="{00000000-0000-0000-0000-000000000001}"><ds:schemaRefs/></ds:datastoreItem>'
        )
        content = custom_xml_package(property_content=props)
        result = repair(content, empty_custom_xml=True)
        assert result.report.succeeded
        assert unzip(result.content)["customXml/repair-props.xml"] == props
        assert (
            unzip(result.content)["customXml/_rels/repair-data.xml.rels"]
            == (unzip(content)["customXml/_rels/repair-data.xml.rels"])
        )

    @pytest.mark.parametrize("name", ["word/document.xml", "customXml/repair-props.xml"])
    def it_does_not_guess_main_document_or_custom_xml_property_content(self, name: str):
        content = custom_xml_package(property_content=b"")
        parts = unzip(content)
        parts[name] = b""
        content = package(parts)
        result = repair(content, empty_custom_xml=True)
        assert not result.report.succeeded
        assert not result.report.changed
        assert result.content == content
        assert any(error.partname == name for error in result.report.errors)

    def it_rolls_back_all_repairs_when_another_member_is_malformed(self):
        parts = unzip(custom_xml_package())
        parts["customXml/unrelated.xml"] = b"<broken>"
        content = package(parts)
        result = repair(content, empty_custom_xml=True)
        assert not result.report.succeeded
        assert result.content == content
        assert not result.report.changes

    def it_rolls_back_when_document_open_validation_fails(self):
        parts = unzip(custom_xml_package())
        parts["word/document.xml"] = b"<wrong-root/>"
        content = package(parts)
        result = repair(content, empty_custom_xml=True)
        assert not result.report.succeeded
        assert result.content == content
        assert result.report.errors[0].code == "document_open_failed"

    @pytest.mark.parametrize("content", [b"", b"broken zip"])
    def it_reports_bad_packages_without_returning_a_partial_output(self, content: bytes):
        result = repair(content, empty_custom_xml=True)
        assert not result.report.succeeded
        assert result.content == content

    def it_restores_streams_and_does_not_overwrite_paths(self, tmp_path: Path):
        content = custom_xml_package()
        stream = io.BytesIO(content)
        stream.seek(15)
        path = tmp_path / "input.docx"
        path.write_bytes(content)
        assert repair(stream, empty_custom_xml=True).report.succeeded
        assert stream.tell() == 15
        assert not stream.closed
        assert stream.getvalue() == content
        assert repair(path, empty_custom_xml=True).report.succeeded
        assert path.read_bytes() == content

    def it_preserves_opaque_members_and_archive_metadata(self):
        parts = unzip(custom_xml_package())
        parts["word/embeddings/object.bin"] = b"\x00opaque OLE\xff"
        parts["word/vbaProject.bin"] = b"opaque macro"
        parts["application/unknown.xml"] = b'<private xmlns="urn:example:private">keep</private>'
        content = package(parts)
        result = repair(content, empty_custom_xml=True)
        assert result.report.succeeded
        after = unzip(result.content)
        assert all(
            after[name] == parts[name] for name in parts if name != "customXml/repair-data.xml"
        )

    def it_keeps_healthy_packages_byte_identical(self):
        content = package(document_parts())
        result = repair(content, empty_custom_xml=True)
        assert result.report.succeeded
        assert not result.report.changed
        assert result.content is content

    def it_preserves_archive_comments_and_member_metadata(self):
        stream = io.BytesIO(custom_xml_package())
        with ZipFile(stream, "a") as archive:
            archive.comment = b"Package provenance"
        content = stream.getvalue()
        result = repair(content, empty_custom_xml=True)
        assert result.report.succeeded
        with ZipFile(io.BytesIO(content)) as before, ZipFile(io.BytesIO(result.content)) as after:
            assert after.comment == before.comment
            assert after.namelist() == before.namelist()
            for member in before.infolist():
                actual = after.getinfo(member.filename)
                assert actual.date_time == member.date_time
                assert actual.compress_type == member.compress_type
                assert actual.external_attr == member.external_attr
                assert actual.extra == member.extra

    def it_rolls_back_if_a_binary_member_fails_its_checksum(self):
        parts = unzip(custom_xml_package())
        parts["word/media/opaque.bin"] = b"binary member with checksum"
        content = package(parts).replace(
            b"binary member with checksum", b"binary member with checksun"
        )
        result = repair(content, empty_custom_xml=True)
        assert not result.report.succeeded
        assert not result.report.changed
        assert result.content is content
        assert result.report.errors[0].code == "package_write_failed"
