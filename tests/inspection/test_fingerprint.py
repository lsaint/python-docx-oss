"""Fingerprints distinguish content while honoring only explicit exclusions."""

from __future__ import annotations

import io
from collections.abc import Callable
from pathlib import Path
from typing import Any, Literal, cast
from zipfile import ZipExtFile, ZipFile

import pytest

from docx import Document, FingerprintItem, FingerprintPolicy, fingerprint, serialize_xml

from .helpers import RT, W, members, package, relationships, story


class DescribeFingerprint:
    @pytest.mark.parametrize(
        "fragment",
        [
            "<w:pBdr><w:top/></w:pBdr>",
            "<w:ins><w:r/></w:ins>",
            '<a:graphic xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">'
            "<a:graphicData/></a:graphic>",
            '<wp:inline xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing">'
            "<wp:extent/></wp:inline>",
            '<pic:pic xmlns:pic="http://schemas.openxmlformats.org/drawingml/2006/picture">'
            "<pic:nvPicPr/></pic:pic>",
            '<wps:wsp xmlns:wps="http://schemas.microsoft.com/office/word/2010/wordprocessingShape">'
            "<wps:spPr/></wps:wsp>",
            '<mc:AlternateContent xmlns:mc="http://schemas.openxmlformats.org/markup-compatibility/2006">'
            '<mc:Choice Requires="w"/><mc:Fallback/></mc:AlternateContent>',
            '<s:p xmlns:s="http://purl.oclc.org/ooxml/wordprocessingml/main"><s:r/></s:p>',
        ],
    )
    def it_ignores_indentation_in_schema_derived_structures(self, fragment: str):
        parts = members()
        parts["word/document.xml"] = story(fragment)
        original = fingerprint(package(parts))
        parts["word/document.xml"] = story(fragment.replace("><", ">\n  <"))
        assert fingerprint(package(parts)) == original

    def it_normalizes_known_drawing_structure_in_a_theme_part(self):
        parts = members()
        parts["[Content_Types].xml"] = parts["[Content_Types].xml"].replace(
            b"</Types>",
            b'<Override PartName="/word/theme/theme1.xml" '
            b'ContentType="application/vnd.openxmlformats-officedocument.theme+xml"/></Types>',
        )
        parts["word/theme/theme1.xml"] = (
            b'<a:theme xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">'
            b"<a:themeElements/></a:theme>"
        )
        original = fingerprint(package(parts))
        parts["word/theme/theme1.xml"] = parts["word/theme/theme1.xml"].replace(b"><", b">\n  <")
        assert fingerprint(package(parts)) == original

    def it_ignores_structural_whitespace_between_extension_elements(self):
        parts = members()
        parts["word/document.xml"] = story('<w:p xmlns:x="urn:example"><x:one/><x:two/></w:p>')
        original = fingerprint(package(parts))
        parts["word/document.xml"] = parts["word/document.xml"].replace(b"/><x:two", b"/> <x:two")
        assert fingerprint(package(parts)) == original

    def it_respects_preserve_and_default_xml_space_on_schema_elements(self):
        parts = members()
        parts["word/document.xml"] = story(
            '<w:p xml:space="preserve"><w:r xml:space="default"><w:rPr/></w:r></w:p>'
        )
        original = fingerprint(package(parts))
        parts["word/document.xml"] = parts["word/document.xml"].replace(
            b'<w:r xml:space="default">', b'<w:r xml:space="default"> '
        )
        assert fingerprint(package(parts)) == original
        parts["word/document.xml"] = parts["word/document.xml"].replace(
            b'<w:p xml:space="preserve">', b'<w:p xml:space="preserve"> '
        )
        assert fingerprint(package(parts)) != original

    def it_preserves_whitespace_when_xsi_type_overrides_a_known_element(self):
        parts = members()
        parts["word/document.xml"] = story(
            '<w:p xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" '
            'xmlns:x="urn:example" xsi:type="x:Mixed"><x:b/></w:p>'
        )
        original = fingerprint(package(parts))
        parts["word/document.xml"] = parts["word/document.xml"].replace(b"<x:b/>", b" <x:b/>")
        assert fingerprint(package(parts)) != original

    @pytest.mark.parametrize(
        "fragment",
        [
            '<v:shape xmlns:v="urn:schemas-microsoft-com:vml"><v:child/></v:shape>',
            '<w14:shape xmlns:w14="http://schemas.microsoft.com/office/word/2010/wordml">'
            "<w14:child/></w14:shape>",
        ],
    )
    def it_preserves_unverified_vml_and_office_extension_whitespace(self, fragment: str):
        parts = members()
        parts["word/document.xml"] = story(fragment)
        original = fingerprint(package(parts))
        parts["word/document.xml"] = story(fragment.replace("><", "> <"))
        assert fingerprint(package(parts)) != original

    def it_preserves_large_text_whitespace_across_parser_chunks(self):
        parts = members()
        text = "A" * 65530 + " " * 65540 + "B"
        parts["word/document.xml"] = story(f"<w:p><w:r><w:t>{text}</w:t></w:r></w:p>")
        original = fingerprint(package(parts))
        parts["word/document.xml"] = story(
            f"<w:p><w:r><w:t>{text[:-2] + text[-1:]}</w:t></w:r></w:p>"
        )
        assert fingerprint(package(parts)) != original

    @pytest.mark.parametrize(
        "xml",
        [
            b'<!DOCTYPE p [<!ENTITY x "expanded">]><p>&x;</p>',
            b'<!DOCTYPE p SYSTEM "https://example.invalid/external.dtd"><p/>',
            b"<!DOCTYPE p><p/>",
        ],
    )
    def it_rejects_dtds_in_the_xml_tree_serializer(self, xml: bytes):
        with pytest.raises(ValueError, match="DTD"):
            serialize_xml(xml)

    def it_ignores_indentation_in_additional_word_structures(self):
        parts = members()
        parts["word/document.xml"] = story(
            "<w:p><w:pPr><w:pBdr><w:top/></w:pBdr></w:pPr>"
            "<w:ins><w:r><w:t>text</w:t></w:r></w:ins></w:p>"
        )
        original = fingerprint(package(parts))
        parts["word/document.xml"] = (
            parts["word/document.xml"]
            .replace(b"<w:pBdr>", b"<w:pBdr>\n  ")
            .replace(b"<w:ins>", b"<w:ins>\n  ")
        )
        assert fingerprint(package(parts)) == original

    def it_retains_mixed_extension_whitespace_inside_word_parts(self):
        parts = members()
        parts["word/document.xml"] = story(
            '<w:p><x:p xmlns:x="urn:example"><x:b>A</x:b> <x:b>B</x:b></x:p></w:p>'
        )
        original = fingerprint(package(parts))
        parts["word/document.xml"] = parts["word/document.xml"].replace(
            b"</x:b> <x:b>", b"</x:b><x:b>"
        )
        assert fingerprint(package(parts)) != original

    @pytest.mark.parametrize(
        ("original", "expected"),
        [
            (b"<p>A<drop/>B<keep/>C</p>", b"<p>AB<keep/>C</p>"),
            (b"<p><drop/>A<keep/>B</p>", b"<p>A<keep/>B</p>"),
            (b"<p>A<drop/>B<drop/>C<keep/>D</p>", b"<p>ABC<keep/>D</p>"),
            (b"<p><keep/>A<drop/>B</p>", b"<p><keep/>AB</p>"),
            (
                b'<p xml:space="preserve"><drop/> <keep/></p>',
                b'<p xml:space="preserve"> <keep/></p>',
            ),
            (b"<p><drop/><keep/></p>", b"<p><keep/></p>"),
        ],
    )
    def it_preserves_text_after_excluded_elements(self, original: bytes, expected: bytes):
        assert serialize_xml(original, exclude=lambda item: item.tag == "drop") == expected

    def it_normalizes_selected_parts_with_a_callback(self):
        parts = members()
        parts["word/document.xml"] = story(
            '<w:p><w:r><w:rPr><w:color w:val="red"/></w:rPr><w:t>text</w:t></w:r></w:p>'
        )

        def normalize(
            item: FingerprintItem, read_bytes: Callable[[], bytes]
        ) -> bytes | Literal["raw"]:
            if not item.part_name.endswith(".xml"):
                return "raw"
            data = read_bytes()
            return serialize_xml(
                data,
                part_name=item.part_name,
                exclude=lambda node: node.tag == f"{{{W}}}color"
                and node.parent_tag == f"{{{W}}}rPr",
            )

        policy = FingerprintPolicy(normalize=normalize)
        original = fingerprint(package(parts), policy=policy)
        parts["word/document.xml"] = (
            parts["word/document.xml"]
            .replace(b'<w:color w:val="red"/>', b'<w:color w:val="blue"/>')
            .replace(b"<w:p>", b"<w:p>\n  ")
        )
        assert fingerprint(package(parts), policy=policy) == original
        parts["word/document.xml"] = parts["word/document.xml"].replace(b"text", b"changed")
        assert fingerprint(package(parts), policy=policy) != original

    def it_supports_raw_parts_and_lazy_default_processing(self):
        parts = members()
        parts["[Content_Types].xml"] = b"<broken>"
        parts["data.bin"] = b"payload"
        reads: list[str] = []

        def normalize(
            item: FingerprintItem, read_bytes: Callable[[], bytes]
        ) -> bytes | Literal["raw"]:
            if item.part_name == "word/document.xml":
                reads.append(item.part_name)
                assert read_bytes() == read_bytes()
                return read_bytes()
            return "raw"

        policy = FingerprintPolicy(normalize=normalize)
        fingerprint(package(parts), policy=policy)
        assert reads == ["word/document.xml"]
        with pytest.raises(ValueError, match="Content_Types"):
            fingerprint(package(parts))

    def it_restores_content_after_callback_falls_back_to_default(self):
        parts = members()

        def read_then_default(item: FingerprintItem, read_bytes: Callable[[], bytes]) -> None:
            read_bytes()
            return None

        assert fingerprint(
            package(parts), policy=FingerprintPolicy(normalize=read_then_default)
        ) == (fingerprint(package(parts)))

    def it_propagates_normalizer_errors_and_rejects_invalid_results(self):
        def fail(item: FingerprintItem, read_bytes: Callable[[], bytes]) -> None:
            raise ValueError("normalizer failed")

        def invalid(item: FingerprintItem, read_bytes: Callable[[], bytes]) -> int:
            return 3

        with pytest.raises(ValueError, match="^normalizer failed$"):
            fingerprint(package(members()), policy=FingerprintPolicy(normalize=fail))
        with pytest.raises(TypeError, match="normalize must return"):
            fingerprint(
                package(members()),
                policy=FingerprintPolicy(normalize=cast(Any, invalid)),
            )

    def it_ignores_font_and_table_property_indentation(self):
        with ZipFile(io.BytesIO(Document().to_bytes())) as archive:
            parts = {name: archive.read(name) for name in archive.namelist()}
        original = package(parts)
        xml = parts["word/fontTable.xml"]
        font_start = xml.index(b">", xml.index(b"<w:font ")) + 1
        parts["word/fontTable.xml"] = xml[:font_start] + b"\n  " + xml[font_start:]
        assert fingerprint(package(parts)) == fingerprint(original)

        parts = members()
        parts["word/document.xml"] = story(
            "<w:p><w:pPr><w:tabs><w:tab/></w:tabs></w:pPr></w:p>"
            "<w:tbl><w:tblPr><w:tblCellMar><w:top/></w:tblCellMar></w:tblPr>"
            "<w:tr><w:tc><w:tcPr><w:tcBorders><w:top/></w:tcBorders>"
            "<w:tcMar><w:top/></w:tcMar></w:tcPr></w:tc></w:tr></w:tbl>"
        )
        original = fingerprint(package(parts))
        for tag in (b"tabs", b"tblCellMar", b"tcBorders", b"tcMar"):
            parts["word/document.xml"] = parts["word/document.xml"].replace(
                b"<w:" + tag + b">", b"<w:" + tag + b">\n  "
            )
        assert fingerprint(package(parts)) == original

    def it_preserves_namespace_bindings_referenced_in_attribute_values(self):
        parts = members()
        parts["customXml/item.xml"] = (
            b'<root xmlns:mc="http://schemas.openxmlformats.org/markup-compatibility/2006" '
            b'xmlns:x="urn:first" mc:Ignorable="x"/>'
        )
        original = fingerprint(package(parts))
        parts["customXml/item.xml"] = parts["customXml/item.xml"].replace(
            b"urn:first", b"urn:second"
        )
        assert fingerprint(package(parts)) != original

    def it_ignores_namespace_declaration_order_and_excluded_subtrees(self):
        parts = members()
        parts["customXml/item.xml"] = (
            b'<root xmlns:a="urn:a" xmlns:b="urn:b"><skip xmlns:x="urn:first"/><keep/></root>'
        )
        policy = FingerprintPolicy(exclude=lambda item: item.tag == "skip")
        original = fingerprint(package(parts), policy=policy)
        parts["customXml/item.xml"] = (
            b'<root xmlns:b="urn:b" xmlns:a="urn:a"><skip xmlns:x="urn:second"/><keep/></root>'
        )
        assert fingerprint(package(parts), policy=policy) == original

    def it_excludes_parts_and_selected_elements_with_a_callback(self):
        seen: list[FingerprintItem] = []

        def exclude(item: FingerprintItem) -> bool:
            seen.append(item)
            return (item.kind == "part" and item.part_name == "media.bin") or (
                item.kind == "xml_element"
                and item.tag == f"{{{W}}}color"
                and item.parent_tag == f"{{{W}}}rPr"
            )

        parts = members()
        parts["media.bin"] = b"first"
        parts["word/document.xml"] = story(
            '<w:p><w:r><w:rPr><w:color w:val="red"/></w:rPr><w:t>text</w:t>'
            '</w:r></w:p><w:frameset><w:framesetSplitbar><w:color w:val="red"/>'
            "</w:framesetSplitbar></w:frameset>"
        )
        policy = FingerprintPolicy(exclude=exclude)
        original = fingerprint(package(parts), policy=policy)
        parts["media.bin"] = b"second"
        parts["word/document.xml"] = parts["word/document.xml"].replace(
            b'<w:color w:val="red"/>', b'<w:color w:val="blue"/>', 1
        )
        assert fingerprint(package(parts), policy=policy) == original
        parts["word/document.xml"] = parts["word/document.xml"].replace(
            b'<w:color w:val="red"/>', b'<w:color w:val="blue"/>'
        )
        assert fingerprint(package(parts), policy=policy) != original
        colors = [item for item in seen if item.tag == f"{{{W}}}color"]
        assert any(item.parent_tag == f"{{{W}}}rPr" for item in colors)
        assert any(item.attributes[f"{{{W}}}val"] == "red" for item in colors)
        assert all(item.part_name == "word/document.xml" for item in colors)

    def it_skips_excluded_subtrees_and_preserves_callback_errors(self):
        parts = members()
        parts["customXml/item.xml"] = b"<root><skip><nested/></skip><keep/></root>"
        seen: list[str] = []

        def exclude(item: FingerprintItem) -> bool:
            if item.kind == "xml_element":
                seen.append(item.tag)
            return item.tag == "skip"

        policy = FingerprintPolicy(exclude=exclude)
        original = fingerprint(package(parts), policy=policy)
        parts["customXml/item.xml"] = b"<root><skip><changed/></skip><keep/></root>"
        assert fingerprint(package(parts), policy=policy) == original
        assert "nested" not in seen
        assert "changed" not in seen

        def fail(item: FingerprintItem) -> bool:
            if item.kind == "xml_element":
                raise ValueError("predicate failed")
            return False

        with pytest.raises(ValueError, match="^predicate failed$"):
            fingerprint(package(parts), policy=FingerprintPolicy(exclude=fail))

    def it_ignores_only_word_structural_indentation_by_default(self):
        parts = members()
        parts["word/document.xml"] = story("<w:p><w:r><w:t>text</w:t></w:r></w:p>")
        original = package(parts)
        parts["word/document.xml"] = story(
            "\n  <w:p>\n    <w:r>\n      <w:t>text</w:t>\n    </w:r>\n  </w:p>\n"
        )
        formatted = package(parts)
        assert fingerprint(original) == fingerprint(formatted)
        policy = FingerprintPolicy(ignore_structural_whitespace=False)
        assert fingerprint(original, policy=policy) != fingerprint(formatted, policy=policy)

    def it_preserves_text_spaces_and_inherited_xml_space(self):
        parts = members()
        parts["word/document.xml"] = story("<w:p><w:r><w:t>text </w:t></w:r></w:p>")
        before = fingerprint(package(parts))
        parts["word/document.xml"] = story("<w:p><w:r><w:t>text</w:t></w:r></w:p>")
        assert fingerprint(package(parts)) != before
        parts["word/document.xml"] = story("<w:p><w:r><w:t> </w:t></w:r></w:p>")
        space = fingerprint(package(parts))
        parts["word/document.xml"] = story("<w:p><w:r><w:t/></w:r></w:p>")
        assert fingerprint(package(parts)) != space
        parts["word/document.xml"] = story(
            '<w:p xml:space="preserve"><w:r><w:t>text</w:t></w:r></w:p>'
        )
        before = fingerprint(package(parts))
        parts["word/document.xml"] = story(
            '<w:p xml:space="preserve"> <w:r><w:t>text</w:t></w:r></w:p>'
        )
        assert fingerprint(package(parts)) != before

    def it_preserves_custom_xml_mixed_content(self):
        parts = members()
        parts["customXml/item.xml"] = b"<p><b>A</b> <b>B</b></p>"
        before = fingerprint(package(parts))
        parts["customXml/item.xml"] = b"<p><b>A</b><b>B</b></p>"
        assert fingerprint(package(parts)) != before

    def it_preserves_word_named_elements_in_generic_custom_xml(self):
        parts = members()
        parts["customXml/item.xml"] = f'<w:p xmlns:w="{W}"><w:r/></w:p>'.encode()
        before = fingerprint(package(parts))
        parts["customXml/item.xml"] = f'<w:p xmlns:w="{W}"> <w:r/></w:p>'.encode()
        assert fingerprint(package(parts)) != before

    def it_ignores_indentation_in_real_word_styles_parts(self):
        with ZipFile(io.BytesIO(Document().to_bytes())) as archive:
            parts = {name: archive.read(name) for name in archive.namelist()}
        original = package(parts)
        xml = parts["word/styles.xml"]
        root_end = xml.index(b">", xml.index(b"<w:styles")) + 1
        root_close = xml.rindex(b"</w:styles>")
        parts["word/styles.xml"] = (
            xml[:root_end] + b"\n  " + xml[root_end:root_close] + b"\n" + xml[root_close:]
        )
        formatted = package(parts)
        assert fingerprint(original) == fingerprint(formatted)
        policy = FingerprintPolicy(ignore_structural_whitespace=False)
        assert fingerprint(original, policy=policy) != fingerprint(formatted, policy=policy)

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
