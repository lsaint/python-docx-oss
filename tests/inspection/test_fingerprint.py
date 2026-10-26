"""Fingerprints distinguish content while honoring only explicit exclusions."""

from __future__ import annotations

import io
from pathlib import Path
from typing import Any
from zipfile import ZipExtFile, ZipFile

import pytest

from docx import Document, FingerprintPolicy, fingerprint

from .helpers import RT, W, members, package, relationships, story


class DescribeFingerprint:
    def it_ignores_zip_order_compression_and_timestamps(self):
        parts = members()
        assert fingerprint(package(parts)) == fingerprint(
            package(parts, reverse=True, compressed=True)
        )

    def it_includes_metadata_custom_xml_relationships_and_binary_content_by_default(self):
        parts = members()
        parts.update(
            {"docProps/custom.xml": b"<root/>", "customXml/item.xml": b"<root/>", "media.bin": b"x"}
        )
        before = fingerprint(package(parts))
        for name, content in (
            ("word/document.xml", story("<w:p/>")),
            ("docProps/custom.xml", b"<changed/>"),
            ("customXml/item.xml", b"<changed/>"),
            (
                "_rels/.rels",
                relationships(("changed", "officeDocument", "word/document.xml", False)),
            ),
            ("media.bin", b"y"),
        ):
            assert fingerprint(package({**parts, name: content})) != before

    def it_normalizes_xml_serialization_but_preserves_text_whitespace(self):
        parts = members()
        parts["customXml/item.xml"] = b'<root a="1" b="2"><child/></root>'
        before = fingerprint(package(parts))
        parts["customXml/item.xml"] = (
            b"<?xml version='1.0'?><root b='2' a='1'><child></child></root>"
        )
        assert fingerprint(package(parts)) == before
        parts["customXml/item.xml"] = b'<root a="1" b="2"> <child/></root>'
        assert fingerprint(package(parts)) != before

    def it_excludes_only_configured_parts_relationship_types_and_xml_nodes(self):
        parts = members()
        parts["docProps/custom.xml"] = b"<root>before</root>"
        parts["word/document.xml"] = story(
            '<w:p><w:r w:rsidR="first"><w:rPr><w:color w:val="red"/></w:rPr>'
            "<w:t>text</w:t></w:r></w:p>"
        )
        parts["word/_rels/document.xml.rels"] = relationships(
            ("url", "hyperlink", "https://example.test/first", True),
        )
        changed = {
            **parts,
            "docProps/custom.xml": b"<root>after</root>",
            "word/document.xml": parts["word/document.xml"]
            .replace(b"first", b"second")
            .replace(b"red", b"blue"),
            "word/_rels/document.xml.rels": relationships(
                ("url", "hyperlink", "https://example.test/second", True),
            ),
        }
        policy = FingerprintPolicy(
            exclude_parts=("docProps/*",),
            exclude_relationship_types=(RT + "hyperlink",),
            exclude_xml_tags=(f"{{{W}}}color",),
            exclude_xml_attributes=(f"{{{W}}}rsidR",),
        )
        assert fingerprint(package(parts)) != fingerprint(package(changed))
        assert fingerprint(package(parts), policy=policy) == fingerprint(
            package(changed), policy=policy
        )
        changed["word/document.xml"] = changed["word/document.xml"].replace(b"text", b"different")
        assert fingerprint(package(parts), policy=policy) != fingerprint(
            package(changed), policy=policy
        )

    def it_supports_raw_xml_hashing_without_silent_exclusions(self):
        parts = members()
        policy = FingerprintPolicy(canonicalize_xml=False)
        changed = {
            **parts,
            "word/document.xml": parts["word/document.xml"].replace(b"<w:body>", b"<w:body >"),
        }
        assert fingerprint(package(parts), policy=policy) != fingerprint(
            package(changed), policy=policy
        )
        with pytest.raises(ValueError, match="XML exclusions"):
            FingerprintPolicy(canonicalize_xml=False, exclude_xml_tags=("tag",))

    def it_restores_streams_and_preserves_inputs_even_when_xml_is_broken(self, tmp_path: Path):
        content = package(members())
        path = tmp_path / "input.docx"
        path.write_bytes(content)
        stream = io.BytesIO(content)
        stream.seek(23)
        assert fingerprint(stream) == fingerprint(path) == fingerprint(content)
        assert stream.tell() == 23
        assert not stream.closed
        assert stream.getvalue() == path.read_bytes() == content
        broken = io.BytesIO(package({**members(), "customXml/item.xml": b"<bad>"}))
        broken.seek(7)
        with pytest.raises(ValueError, match="customXml/item.xml"):
            fingerprint(broken)
        assert broken.tell() == 7
        assert not broken.closed

    def it_rejects_dtds(self):
        parts = members()
        parts["customXml/item.xml"] = b'<!DOCTYPE root [<!ENTITY x "secret">]><root>&x;</root>'
        with pytest.raises(ValueError, match="DTD"):
            fingerprint(package(parts))

    def it_rejects_duplicate_members(self):
        stream = io.BytesIO(package(members()))
        with ZipFile(stream, "a") as archive, pytest.warns(UserWarning, match="Duplicate name"):
            archive.writestr("word/document.xml", story())
        with pytest.raises(ValueError, match="duplicate member"):
            fingerprint(stream.getvalue())

    def it_does_not_parse_excluded_xml_members(self):
        parts = members()
        parts["customXml/broken.xml"] = b"<broken>"
        # fnmatch treats brackets as character classes; this pattern escapes a literal '['.
        policy = FingerprintPolicy(exclude_parts=("[[]Content_Types].xml", "customXml/*"))
        assert len(fingerprint(package(parts), policy=policy)) == 64

    @pytest.mark.parametrize("excluded", [False, True])
    @pytest.mark.parametrize("manifest", [b"", b" \t\n", b"<broken>"])
    def it_identifies_manifest_errors_consistently_even_if_excluded(
        self,
        excluded: bool,
        manifest: bytes,
    ):
        parts = members()
        parts["[Content_Types].xml"] = manifest
        policy = FingerprintPolicy(exclude_parts=("[[]Content_Types].xml",) if excluded else ())
        with pytest.raises(
            ValueError, match=r"Cannot fingerprint XML part '\[Content_Types\].xml'"
        ):
            fingerprint(package(parts), policy=policy)

    def it_uses_excluded_content_types_to_canonicalize_nonstandard_xml_extensions(self):
        parts = members()
        parts["[Content_Types].xml"] = parts["[Content_Types].xml"].replace(
            b"</Types>",
            b'<Default Extension="data" ContentType="application/xml"/></Types>',
        )
        parts["customXml/item.data"] = b'<root a="1" b="2"/>'
        policy = FingerprintPolicy(exclude_parts=("[[]Content_Types].xml",))
        original = fingerprint(package(parts), policy=policy)
        parts["customXml/item.data"] = b'<root b="2" a="1"></root>'
        assert fingerprint(package(parts), policy=policy) == original

    def it_rejects_xml_exclusion_policies_that_would_be_silently_ignored(self):
        with pytest.raises(ValueError, match="XML exclusions"):
            FingerprintPolicy(canonicalize_xml=False, exclude_relationship_types=(RT + "header",))

    def it_reads_large_binary_parts_in_bounded_chunks(self, monkeypatch: pytest.MonkeyPatch):
        parts = members()
        parts["word/media/image.bin"] = b"x" * (8 * 1024 * 1024)
        content = package(parts, compressed=True)
        original = ZipExtFile.read

        def guarded_read(self: ZipExtFile, n: int = -1) -> Any:
            assert 0 < n <= 64 * 1024
            return original(self, n)

        monkeypatch.setattr(ZipExtFile, "read", guarded_read)
        assert len(fingerprint(content)) == 64

    def it_fingerprints_real_word_documents_without_affecting_round_trips(self):
        path = Path(__file__).parents[1] / "fixtures/documents/word-blank.docx"
        before = path.read_bytes()
        original = fingerprint(before)
        doc = Document(before)
        doc.add_paragraph("A content change")
        assert fingerprint(doc.to_bytes()) != original
        assert fingerprint(path) == original
        assert path.read_bytes() == before
