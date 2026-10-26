"""Inspection contracts at package, XML, stream, and memory boundaries."""

from __future__ import annotations

import io
import tracemalloc
from dataclasses import FrozenInstanceError
from pathlib import Path
from typing import Any, BinaryIO, Literal
from zipfile import ZipFile

import pytest

from docx import inspect

from .helpers import RT, members, package, relationships, story


class DescribeInspection:
    @pytest.mark.parametrize("content", [b"", b"not a ZIP", b"PK\x03\x04broken"])
    def it_reports_invalid_packages(self, content: bytes):
        assert inspect(content).has_finding("not_a_package")

    def it_propagates_source_open_failures(self, tmp_path: Path):
        with pytest.raises(FileNotFoundError):
            inspect(tmp_path / "missing.docx")

    def it_propagates_permission_errors(self, monkeypatch: pytest.MonkeyPatch):
        def denied(*args: Any, **kwargs: Any) -> Any:
            raise PermissionError("Source access denied")

        monkeypatch.setattr("builtins.open", denied)
        with pytest.raises(PermissionError, match="Source access denied"):
            inspect("denied.docx")

    def it_reports_missing_package_metadata_and_main_document(self):
        report = inspect(package({"orphan.xml": b"<orphan/>"}))
        assert report.has_finding("missing_content_types")
        assert report.has_finding("missing_main_document")

    def it_preserves_partial_inventory_for_broken_xml_and_relationships(self):
        parts = members()
        parts.update(
            {
                "customXml/item1.xml": b"",
                "word/broken.xml": b"<broken>",
                "word/_rels/document.xml.rels": b"<broken>",
            }
        )
        report = inspect(package(parts))
        assert report.findings_by_code("empty_xml_part")[0].partname == "customXml/item1.xml"
        assert {f.partname for f in report.findings_by_code("unparseable_xml_part")} == {
            "word/broken.xml",
            "word/_rels/document.xml.rels",
        }
        assert {part.partname for part in report.inventory.parts} == set(parts)

    def it_resolves_relationships_and_reachability_without_following_external_uris(self):
        parts = members()
        parts.update(
            {
                "word/_rels/document.xml.rels": relationships(
                    ("image", "image", "media/a%20b.bin", False),
                    ("missing", "image", "media/missing.bin", False),
                    ("external", "hyperlink", "https://example.test/doc#section", True),
                ),
                "word/media/a b.bin": b"binary data",
                "orphan.xml": b"<orphan/>",
                "orphan/_rels/source.xml.rels": relationships(
                    ("orphan", "image", "../other.bin", False),
                ),
                "other.bin": b"unreachable",
            }
        )
        report = inspect(package(parts))
        by_name = {part.partname: part for part in report.inventory.parts}
        assert by_name["word/document.xml"].reachable
        assert by_name["word/media/a b.bin"].reachable
        assert by_name["word/_rels/document.xml.rels"].reachable
        assert not by_name["orphan.xml"].reachable
        assert not by_name["other.bin"].reachable
        assert by_name["word/document.xml"].content_type is not None
        assert (
            report.findings_by_code("missing_relationship_target")[0].target
            == "word/media/missing.bin"
        )
        external = [rel for rel in report.inventory.relationships if rel.external]
        assert len(external) == 1
        assert external[0].target == "https://example.test/doc#section"

    def it_restores_streams_and_never_changes_source_bytes(self, tmp_path: Path):
        content = package(members())
        stream = io.BytesIO(content)
        stream.seek(12)
        path = tmp_path / "input.docx"
        path.write_bytes(content)
        assert inspect(stream) == inspect(content) == inspect(path) == inspect(str(path))
        assert stream.tell() == 12
        assert not stream.closed
        assert stream.getvalue() == path.read_bytes() == content
        with pytest.raises(FrozenInstanceError):
            inspect(content).features.field_hyperlink = True  # type: ignore[misc]

    def it_restores_streams_on_failure(self):
        stream = io.BytesIO(b"bad package")
        stream.seek(3)
        assert inspect(stream).has_finding("not_a_package")
        assert stream.tell() == 3
        assert not stream.closed

    def it_accepts_forward_only_binary_streams(self):
        class ForwardOnly(io.BytesIO):
            def seekable(self) -> bool:
                return False

        stream = ForwardOnly(package(members()))
        assert not inspect(stream).findings
        assert not stream.closed

    def it_rejects_programming_errors(self):
        with pytest.raises(TypeError):
            inspect(None)  # type: ignore[arg-type]

    def it_closes_owned_path_handles(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        path = tmp_path / "input.docx"
        path.write_bytes(package(members()))
        original = io.open
        opened: list[BinaryIO] = []

        def track_open(file: Path, mode: Literal["rb"]) -> BinaryIO:
            handle = original(file, mode)
            opened.append(handle)
            return handle

        monkeypatch.setattr("builtins.open", track_open)
        inspect(path)
        assert opened
        assert all(handle.closed for handle in opened)

    def it_never_opens_binary_members(self, monkeypatch: pytest.MonkeyPatch):
        parts = members()
        parts["word/media/large.bin"] = b"x" * (8 * 1024 * 1024)
        content = package(parts, compressed=True)
        original = ZipFile.open

        def guarded_open(self: ZipFile, name: Any, *args: Any, **kwargs: Any) -> Any:
            member_name = name if isinstance(name, str) else name.filename
            assert not member_name.startswith("word/media/")
            return original(self, name, *args, **kwargs)

        monkeypatch.setattr(ZipFile, "open", guarded_open)
        report = inspect(content)
        assert not report.findings
        media = next(p for p in report.inventory.parts if p.partname.endswith("large.bin"))
        assert media.size == 8 * 1024 * 1024

    def it_rejects_dtds_without_resolving_entities(self):
        parts = members()
        parts["customXml/item.xml"] = (
            b'<!DOCTYPE root [<!ENTITY secret SYSTEM "file:///must-not-be-read">]>'
            b"<root>&secret;</root>"
        )
        report = inspect(package(parts))
        finding = report.findings_by_code("unparseable_xml_part")[0]
        assert finding.partname == "customXml/item.xml"
        assert "DTD" in finding.message

    def it_reports_unsafe_member_names(self):
        parts = members()
        parts["../outside.xml"] = b"<root/>"
        assert inspect(package(parts)).has_finding("unsafe_member_name")

    @pytest.mark.parametrize(
        "relationships_xml",
        [
            b"<wrong-root/>",
            relationships(("missing-type", "", "http://[", False)),
            relationships(
                ("duplicate", "header", "one.xml", False), ("duplicate", "header", "two.xml", False)
            ),
        ],
    )
    def it_reports_invalid_relationship_metadata(self, relationships_xml: bytes):
        parts = members()
        parts["word/_rels/document.xml.rels"] = relationships_xml
        report = inspect(package(parts))
        assert report.has_finding("invalid_relationships")
        assert any(part.partname == "word/document.xml" for part in report.inventory.parts)

    def it_reports_unexpected_content_type_root(self):
        parts = members()
        parts["[Content_Types].xml"] = b"<wrong-root/>"
        assert inspect(package(parts)).has_finding("invalid_content_types")

    def it_reports_duplicate_members_and_uses_the_first_entry(self):
        stream = io.BytesIO(package(members()))
        with ZipFile(stream, "a") as archive, pytest.warns(UserWarning, match="Duplicate name"):
            archive.writestr("word/document.xml", b"<broken>")
        report = inspect(stream.getvalue())
        assert report.has_finding("duplicate_member")
        assert not report.has_finding("unparseable_xml_part")

    def it_detects_xml_by_content_type_even_without_an_xml_extension(self):
        parts = members()
        parts["[Content_Types].xml"] = parts["[Content_Types].xml"].replace(
            b"</Types>",
            b'<Default Extension="data" ContentType="application/xml"/></Types>',
        )
        parts["customXml/item.data"] = b"<broken>"
        assert inspect(package(parts)).findings_by_code("unparseable_xml_part")[0].partname == (
            "customXml/item.data"
        )

    def it_reports_unreadable_xml_members(self):
        content = package(members())
        # Stored member bytes can be changed without updating the ZIP CRC.
        content = content.replace(b"<w:body>", b"<w:bady>")
        report = inspect(content)
        assert report.findings_by_code("unreadable_part")[0].partname == "word/document.xml"


class DescribeStoryFeatures:
    @pytest.mark.parametrize(
        ("instruction", "expected"),
        [
            ('HYPERLINK "https://example.test"', True),
            (' hyperlink "https://example.test"', True),
            ("REF HYPERLINK_ref", False),
            ("TOC HYPERLINK", False),
            ("HYPERLINK_ref", False),
        ],
    )
    @pytest.mark.parametrize("strict", [False, True])
    def it_detects_simple_fields_by_the_first_instruction_token(
        self,
        instruction: str,
        expected: bool,
        strict: bool,
    ):
        escaped = instruction.replace('"', "&quot;")
        parts = members(f'<w:p><w:fldSimple w:instr="{escaped}"><w:r/></w:fldSimple></w:p>')
        if strict:
            parts["word/document.xml"] = parts["word/document.xml"].replace(
                b"http://schemas.openxmlformats.org/wordprocessingml/2006/main",
                b"http://purl.oclc.org/ooxml/wordprocessingml/main",
            )
        assert inspect(package(parts)).features.field_hyperlink is expected

    @pytest.mark.parametrize(
        ("first", "second", "expected"),
        [
            ("HYPER", 'LINK "https://example.test"', True),
            ("HYPERLINK", "_ref", False),
            ("REF ", "HYPERLINK_ref", False),
            ("TOC ", "HYPERLINK", False),
            ("HYPERLINK", "", True),
        ],
    )
    def it_matches_only_the_first_token_across_instruction_runs(
        self,
        first: str,
        second: str,
        expected: bool,
    ):
        body = (
            '<w:p><w:r><w:fldChar w:fldCharType="begin"/></w:r>'
            f"<w:r><w:instrText>{first}</w:instrText></w:r>"
            f"<w:r><w:instrText>{second}</w:instrText></w:r>"
            '<w:r><w:fldChar w:fldCharType="separate"/></w:r>'
            '<w:r><w:t>label</w:t></w:r><w:r><w:fldChar w:fldCharType="end"/></w:r></w:p>'
        )
        assert inspect(package(members(body))).features.field_hyperlink is expected

    @pytest.mark.parametrize(
        ("body", "field", "split"),
        [
            (
                '<w:p><w:r><w:instrText> HYPERLINK "https://example.test" '
                "</w:instrText></w:r></w:p>",
                True,
                False,
            ),
            ("<w:p><w:hyperlink><w:r/><w:r/></w:hyperlink></w:p>", False, True),
            (
                "<w:p><w:r><w:instrText>HYPER</w:instrText></w:r>"
                '<w:r><w:instrText>LINK "https://example.test"</w:instrText></w:r></w:p>',
                True,
                False,
            ),
            ("<w:p><w:r><w:instrText>TOC REF _Ref</w:instrText></w:r></w:p>", False, False),
            (
                "<w:p><w:r><w:instrText>HYPER</w:instrText></w:r></w:p>"
                "<w:p><w:r><w:instrText>LINK</w:instrText></w:r></w:p>",
                False,
                False,
            ),
            (
                '<w:p><w:r><w:instrText>HYPER</w:instrText><w:fldChar w:fldCharType="end"/>'
                '<w:fldChar w:fldCharType="begin"/><w:instrText>LINK</w:instrText></w:r></w:p>',
                False,
                False,
            ),
            ("<w:p><w:hyperlink><w:r/></w:hyperlink><w:r/></w:p>", False, False),
        ],
    )
    def it_scans_hyperlink_shapes(self, body: str, field: bool, split: bool):
        report = inspect(package(members(body)))
        assert not report.findings
        assert report.features.field_hyperlink is field
        assert report.features.split_hyperlink_runs is split

    @pytest.mark.parametrize("kind", ["header", "footer", "footnotes", "endnotes"])
    def it_scans_related_story_parts_at_nonstandard_paths(self, kind: str):
        parts = members()
        parts["word/_rels/document.xml.rels"] = relationships(
            ("story", kind, "../stories/part.xml", False),
        )
        parts["stories/part.xml"] = story("<w:p><w:hyperlink><w:r/><w:r/></w:hyperlink></w:p>")
        assert inspect(package(parts)).features.split_hyperlink_runs

    def it_does_not_treat_configuration_or_unreachable_xml_as_story_content(self):
        parts = members()
        parts["word/styles.xml"] = story("<w:instrText>HYPERLINK</w:instrText>")
        parts["word/_rels/document.xml.rels"] = relationships(
            ("styles", "styles", "styles.xml", False),
        )
        assert not inspect(package(parts)).features.field_hyperlink

    def it_supports_strict_word_namespaces(self):
        parts = members("<w:p><w:hyperlink><w:r/><w:r/></w:hyperlink></w:p>")
        parts["word/document.xml"] = parts["word/document.xml"].replace(
            b"http://schemas.openxmlformats.org/wordprocessingml/2006/main",
            b"http://purl.oclc.org/ooxml/wordprocessingml/main",
        )
        parts["_rels/.rels"] = parts["_rels/.rels"].replace(
            RT.encode(),
            b"http://purl.oclc.org/ooxml/officeDocument/relationships/",
        )
        assert inspect(package(parts)).features.split_hyperlink_runs

    def it_keeps_python_memory_bounded_as_story_xml_grows(self):
        def peak(paragraphs: int) -> int:
            parts = members()
            parts["word/document.xml"] = story("<w:p><w:r><w:t>text</w:t></w:r></w:p>" * paragraphs)
            content = package(parts, compressed=True)
            tracemalloc.start()
            try:
                report = inspect(content)
                _, memory = tracemalloc.get_traced_memory()
            finally:
                tracemalloc.stop()
            assert not report.findings
            return memory

        small = peak(1000)
        large = peak(100000)
        assert large < small + 1024 * 1024


class DescribeRealWordInspection:
    @pytest.mark.parametrize(
        "relative",
        [
            "documents/word-blank.docx",
            "comments/word-comments-rich.docx",
            "fonts/word-east-asian-fonts.docx",
            "drawing/word-floating-picture.docx",
            "images/word-svg-image.docx",
            "customxml/multiple-custom-xml-parts.docx",
        ],
    )
    def it_inspects_real_word_packages_without_modification(self, relative: str):
        path = Path(__file__).parents[1] / "fixtures" / relative
        if not path.exists():
            pytest.fail(f"Missing Word fixture: {path}")
        before = path.read_bytes()
        report = inspect(path)
        assert not report.findings
        assert path.read_bytes() == before
        assert any(part.reachable for part in report.inventory.parts)
