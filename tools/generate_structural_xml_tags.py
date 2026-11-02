"""Generate element-only OOXML names from the published 2016 ECMA schemas.

Usage: python tools/generate_structural_xml_tags.py TRANSITIONAL.zip STRICT.zip WPS.html
The zip files are the XMLSchema archives inside the ECMA-376 fifth edition parts
4 and 1. WPS.html is the Microsoft MS-ODRAWXML section 5.2 schema page.
"""

from __future__ import annotations

import hashlib
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any
from zipfile import ZipFile

from lxml import etree, html

XS = "{http://www.w3.org/2001/XMLSchema}"
NAMESPACES = {
    "http://schemas.openxmlformats.org/wordprocessingml/2006/main",
    "http://schemas.openxmlformats.org/drawingml/2006/main",
    "http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing",
    "http://schemas.openxmlformats.org/drawingml/2006/picture",
    "http://purl.oclc.org/ooxml/wordprocessingml/main",
    "http://purl.oclc.org/ooxml/drawingml/main",
    "http://purl.oclc.org/ooxml/drawingml/wordprocessingDrawing",
    "http://purl.oclc.org/ooxml/drawingml/picture",
    "http://schemas.microsoft.com/office/word/2010/wordprocessingShape",
}
EXPECTED = (
    "d34187520749998af306faf1b730e568b0ca6d88ad24638a407c0a9bb4ca04fc",
    "73fab4b04ddd93da020ed07583f755466dcaf69f115b2ff6649af7ae16a816f7",
    "caa6cc8cc744a44337cfa0b41a3d9b5a694ce074573649e7ad6820ea7535c45e",
)


def qualified(node: Any, value: str) -> str:
    first, separator, name = value.partition(":")
    prefix: str | None = first
    if not separator:
        name, prefix = first, None
    namespace: str | None = node.nsmap.get(prefix)
    return f"{{{namespace}}}{name}" if namespace else name


def main() -> None:
    transitional, strict, wps_html = map(Path, sys.argv[1:])
    raw: list[str] = []
    for archive in (transitional, strict):
        payload = archive.read_bytes()
        raw.append(hashlib.sha256(payload).hexdigest())
    page: Any = html.fromstring(wps_html.read_bytes())
    schemas: list[str] = [
        block.text_content().replace("\u00a0", " ").strip()
        for block in page.xpath("//pre")
        if "<xsd:schema" in block.text_content() and "wordprocessingShape" in block.text_content()
    ]
    if len(schemas) != 1:
        raise ValueError("Expected one WordprocessingShape schema")
    wps = schemas[0].encode()
    raw.append(hashlib.sha256(wps).hexdigest())
    if tuple(raw) != EXPECTED:
        raise ValueError(f"Unexpected schema hashes: {raw}")

    roots: list[Any] = []
    for archive in (transitional, strict):
        with ZipFile(archive) as zf:
            roots.extend(
                etree.fromstring(zf.read(name)) for name in zf.namelist() if name.endswith(".xsd")
            )
    roots.append(etree.fromstring(wps))
    types: dict[str, list[Any]] = defaultdict(list)
    for root in roots:
        namespace = root.get("targetNamespace")
        for node in root.findall(f"{XS}complexType"):
            types[f"{{{namespace}}}{node.get('name')}"].append(node)

    def pure_type(node: Any, visiting: frozenset[str] = frozenset()) -> bool:
        if node.tag != f"{XS}complexType" or node.get("mixed") in ("true", "1"):
            return False
        if node.find(f"{XS}simpleContent") is not None:
            return False
        content = node.find(f"{XS}complexContent")
        if content is None:
            return True
        if content.get("mixed") in ("true", "1"):
            return False
        derivation = content.find(f"{XS}extension")
        if derivation is None:
            derivation = content.find(f"{XS}restriction")
        if derivation is None or not derivation.get("base"):
            return False
        base = qualified(derivation, derivation.get("base"))
        if base in visiting or base not in types:
            return False
        return all(pure_type(parent, visiting | {base}) for parent in types[base])

    declarations: dict[tuple[str, str], list[bool]] = defaultdict(list)
    for root in roots:
        namespace = root.get("targetNamespace")
        if namespace not in NAMESPACES:
            continue
        for element in root.iter(f"{XS}element"):
            name = element.get("name")
            if not name:
                continue
            if (
                element.getparent() is not root
                and element.get("form", root.get("elementFormDefault", "unqualified"))
                != "qualified"
            ):
                continue
            type_name = element.get("type")
            if type_name:
                key = qualified(element, type_name)
                eligible = key in types and all(
                    pure_type(node, frozenset({key})) for node in types[key]
                )
            else:
                inline = element.find(f"{XS}complexType")
                eligible = inline is not None and pure_type(inline)
            declarations[(namespace, name)].append(eligible)

    tags = {key for key, possibilities in declarations.items() if all(possibilities)}
    mc = "http://schemas.openxmlformats.org/markup-compatibility/2006"
    tags.update((mc, name) for name in ("AlternateContent", "Choice", "Fallback"))
    print('"""Generated by tools/generate_structural_xml_tags.py; do not edit manually.')
    print()
    print("ECMA-376 fifth edition: Part 1 and Part 4 (2016) XML schemas, and Part 3")
    print("(2015), sections 7.5–7.7. WPS: MS-ODRAWXML section 5.2 (2023-05-16).")
    print("Sources: https://ecma-international.org/publications-and-standards/standards/ecma-376/")
    print("https://learn.microsoft.com/en-us/openspecs/office_standards/ms-odrawxml/")
    print("f73ea06d-4749-4611-b20b-755df087eb21")
    print("Only names whose resolved declarations all forbid text are included.")
    print('"""')
    print()
    print("_STRUCTURAL_NAMES: dict[str, tuple[str, ...]] = {")
    for namespace in sorted({item[0] for item in tags}):
        names = sorted(name for ns, name in tags if ns == namespace)
        print(f'    "{namespace}": (')
        for name in names:
            print(f'        "{name}",')
        print("    ),")
    print("}")
    print()
    print("STRUCTURAL_XML_TAGS: frozenset[str] = frozenset(")
    print(
        '    f"{{{namespace}}}{name}" for namespace, names in '
        "_STRUCTURAL_NAMES.items() for name in names"
    )
    print(")")
    print(file=sys.stderr)
    print(
        "Generated",
        len(tags),
        "names; excluded",
        sum(not all(v) for v in declarations.values()),
        "ambiguous or non-element-only names",
        file=sys.stderr,
    )


if __name__ == "__main__":
    main()
