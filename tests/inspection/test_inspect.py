"""Inspection contracts at package, XML, stream, and memory boundaries."""

from __future__ import annotations

import io
import tracemalloc
from dataclasses import FrozenInstanceError
from pathlib import Path
from typing import Any, BinaryIO, Literal, cast
from zipfile import ZipFile

import pytest

from docx import inspect
from docx.inspection import ScanEvent

from .helpers import members, package, relationships, story


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
            inspect(content).matched = True  # type: ignore[misc]

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


class DescribeCustomStoryQueries:
    def it_stops_on_a_match_and_does_not_claim_complete_validation(self):
        parts = members("<w:p><w:r><w:t>first</w:t></w:r></w:p>")
        parts["word/styles.xml"] = b"<broken>"
        content = package(parts)
        events: list[ScanEvent] = []

        def predicate(event: ScanEvent) -> bool:
            events.append(event)
            return event.kind == "start" and event.tag.endswith("}t")

        result = inspect(content, predicate=predicate, stop_on_match=True)
        assert result.scope == "query"
        assert result.matched
        assert not result.scan_complete
        assert not result.inventory.parts
        assert not result.findings
        assert events[-1].tag.endswith("}t")
        assert inspect(content).has_finding("unparseable_xml_part")

    def it_scans_all_stories_and_preserves_readonly_event_attributes(self):
        parts = members("<w:p><w:r><w:t>body</w:t></w:r></w:p>")
        parts["word/_rels/document.xml.rels"] = relationships(
            ("header", "header", "header1.xml", False)
        )
        parts["word/header1.xml"] = story("<w:p><w:r><w:t>header</w:t></w:r></w:p>")
        seen: list[tuple[str, str]] = []

        def predicate(event: ScanEvent) -> bool:
            if event.kind == "text" and event.tag.endswith("}t"):
                seen.append((event.partname, event.text))
            return event.text == "body"

        report = inspect(package(parts), predicate=predicate)
        assert report.matched
        assert report.scan_complete
        assert ("word/header1.xml", "header") in seen
        assert report.scope == "query"
        assert not report.inventory.parts

    def it_reports_errors_in_a_scanned_story_and_marks_scan_incomplete(self):
        parts = members()
        parts["word/document.xml"] = b"<broken>"
        report = inspect(package(parts), predicate=lambda event: False)
        assert report.has_finding("unparseable_xml_part")
        assert not report.scan_complete

    def it_retains_a_match_if_later_xml_is_malformed(self):
        parts = members()
        parts["word/document.xml"] = story("<w:p><w:r><w:t>match</w:t></w:r></w:p>")[:-20]
        report = inspect(
            package(parts), predicate=lambda event: event.kind == "text" and event.text == "match"
        )
        assert report.matched
        assert report.has_finding("unparseable_xml_part")
        assert not report.scan_complete

    def it_restores_stream_position_and_never_closes_the_borrowed_stream(self):
        content = package(members())
        stream = io.BytesIO(content)
        stream.seek(13)
        assert inspect(stream, predicate=lambda event: False).scan_complete
        assert stream.tell() == 13
        assert stream.getvalue() == content
        assert not stream.closed

    def it_propagates_predicate_errors_and_restores_the_stream(self):
        stream = io.BytesIO(package(members()))
        stream.seek(7)

        def fail(event: ScanEvent) -> bool:
            raise ValueError("predicate failed")

        with pytest.raises(ValueError, match="predicate failed"):
            inspect(stream, predicate=fail)
        assert stream.tell() == 7
        assert not stream.closed

    def it_exposes_immutable_attributes_to_the_predicate(self):
        def modify(event: ScanEvent) -> bool:
            if event.kind == "start":
                cast(Any, event.attributes)["changed"] = "value"
            return False

        with pytest.raises(TypeError):
            inspect(package(members()), predicate=modify)

    def it_rejects_stop_without_a_predicate(self):
        with pytest.raises(ValueError, match="requires a predicate"):
            inspect(package(members()), stop_on_match=True)

    def it_does_not_open_unrelated_xml_or_media(self, monkeypatch: pytest.MonkeyPatch):
        parts = members()
        parts["word/styles.xml"] = b"<styles/>"
        parts["word/media/image.bin"] = b"binary"
        content = package(parts)
        original = ZipFile.open

        def guarded_open(self: ZipFile, name: Any, *args: Any, **kwargs: Any) -> Any:
            member_name = name if isinstance(name, str) else name.filename
            assert member_name not in {"word/styles.xml", "word/media/image.bin"}
            return original(self, name, *args, **kwargs)

        monkeypatch.setattr(ZipFile, "open", guarded_open)
        assert not inspect(content, predicate=lambda event: False).findings

    def it_keeps_memory_bounded_for_large_stories(self):
        parts = members()
        parts["word/document.xml"] = story("<w:p><w:r><w:t>text</w:t></w:r></w:p>" * 100000)
        content = package(parts, compressed=True)
        tracemalloc.start()
        try:
            report = inspect(content, predicate=lambda event: False)
            _, memory = tracemalloc.get_traced_memory()
        finally:
            tracemalloc.stop()
        assert report.scan_complete
        assert memory < 2 * 1024 * 1024


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
