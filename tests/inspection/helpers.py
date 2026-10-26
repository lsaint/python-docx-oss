"""Small, neutral OPC fixtures whose broken structures are deliberate."""

from __future__ import annotations

import io
from zipfile import ZIP_DEFLATED, ZIP_STORED, ZipFile, ZipInfo

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
R = "http://schemas.openxmlformats.org/package/2006/relationships"
RT = "http://schemas.openxmlformats.org/officeDocument/2006/relationships/"
CT = "http://schemas.openxmlformats.org/package/2006/content-types"


def story(body: str = "") -> bytes:
    return f'<w:document xmlns:w="{W}"><w:body>{body}</w:body></w:document>'.encode()


def relationships(*items: tuple[str, str, str, bool]) -> bytes:
    nodes: list[str] = []
    for rel_id, kind, target, external in items:
        mode = ' TargetMode="External"' if external else ""
        nodes.append(f'<Relationship Id="{rel_id}" Type="{RT}{kind}" Target="{target}"{mode}/>')
    return f'<Relationships xmlns="{R}">{"".join(nodes)}</Relationships>'.encode()


def members(body: str = "") -> dict[str, bytes]:
    return {
        "[Content_Types].xml": (
            f'<Types xmlns="{CT}">'
            '<Default Extension="xml" ContentType="application/xml"/>'
            '<Default Extension="rels" '
            'ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
            '<Override PartName="/word/document.xml" '
            'ContentType="application/vnd.openxmlformats-officedocument.'
            'wordprocessingml.document.main+xml"/></Types>'
        ).encode(),
        "_rels/.rels": relationships(("main", "officeDocument", "word/document.xml", False)),
        "word/document.xml": story(body),
    }


def package(parts: dict[str, bytes], *, reverse: bool = False, compressed: bool = False) -> bytes:
    output = io.BytesIO()
    with ZipFile(output, "w") as archive:
        for name in sorted(parts, reverse=reverse):
            info = ZipInfo(name, date_time=(2025 if reverse else 2024, 1, 1, 0, 0, 0))
            info.compress_type = ZIP_DEFLATED if compressed else ZIP_STORED
            archive.writestr(info, parts[name])
    return output.getvalue()
