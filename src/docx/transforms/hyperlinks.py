"""Conservative field conversion: preserve result runs, skip ambiguous boundaries."""

from __future__ import annotations

import posixpath
from collections.abc import Callable
from dataclasses import dataclass

from lxml import etree
from lxml.etree import _Element as etree_Element  # pyright: ignore[reportPrivateUsage]

from docx.inspection import Finding
from docx.inspection.reader import OFFICE_REL_BASES, REL_NS
from docx.transforms.result import Change, HyperlinkTarget

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
XML_SPACE = "{http://www.w3.org/XML/1998/namespace}space"
Selector = Callable[[HyperlinkTarget], bool]


def w(name: str) -> str:
    return f"{{{W}}}{name}"


@dataclass(frozen=True)
class _Instruction:
    address: str | None
    anchor: str | None
    tooltip: str | None = None
    frame: str | None = None


def _instruction(text: str) -> _Instruction | None:
    tokens = _field_tokens(text)
    if not tokens or tokens[0][1] or tokens[0][0].upper() != "HYPERLINK":
        return None
    index = 1
    address = None
    if index < len(tokens) and (tokens[index][1] or not tokens[index][0].startswith("\\")):
        address = tokens[index][0]
        index += 1
    options: dict[str, str] = {}
    while index < len(tokens):
        key, quoted = tokens[index]
        key = key.lower()
        index += 1
        if (
            quoted
            or key not in ("\\l", "\\o", "\\t", "\\*")
            or index == len(tokens)
            or not tokens[index][1]
            and tokens[index][0].startswith("\\")
            or key in options
        ):
            return None
        options[key] = tokens[index][0]
        index += 1
    if "\\*" in options and options["\\*"].upper() != "MERGEFORMAT":
        return None
    anchor = options.get("\\l")
    if not address and not anchor:
        return None
    return _Instruction(address or None, anchor, options.get("\\o"), options.get("\\t"))


def _field_tokens(text: str) -> list[tuple[str, bool]] | None:
    """Decode Word quoted strings; reject ambiguous or unsupported escapes."""
    tokens: list[tuple[str, bool]] = []
    index = 0
    while index < len(text):
        if text[index].isspace():
            index += 1
            continue
        quoted = text[index] == '"'
        if quoted:
            index += 1
            value: list[str] = []
            while index < len(text) and text[index] != '"':
                char = text[index]
                if char == "\\":
                    index += 1
                    if index == len(text) or text[index] not in ("\\", '"'):
                        return None
                    char = text[index]
                value.append(char)
                index += 1
            if index == len(text):
                return None
            index += 1
            if index < len(text) and not text[index].isspace():
                return None
            tokens.append(("".join(value), True))
        else:
            start = index
            while index < len(text) and not text[index].isspace():
                index += 1
            token = text[start:index]
            if '"' in token or "\\" in token and token.lower() not in ("\\l", "\\o", "\\t", "\\*"):
                return None
            tokens.append((token, False))
    return tokens


def relationship_partname(source: str) -> str:
    directory, filename = posixpath.split(source)
    return posixpath.join(directory, "_rels", filename + ".rels")


class HyperlinkNormalizer:
    def __init__(
        self,
        partname: str,
        relationships: etree_Element,
        selector: Selector | None,
        changes: list[Change],
        skipped: list[Finding],
    ):
        self.partname = partname
        self.relationships = relationships
        self.selector = selector
        self.changes = changes
        self.skipped = skipped
        self.relationships_changed = False

    def _skip(self, message: str) -> None:
        self.skipped.append(Finding("hyperlink_not_normalized", self.partname, message))

    def _selected(self, address: str | None, anchor: str | None) -> bool:
        return self.selector is None or self.selector(
            HyperlinkTarget(self.partname, address, anchor)
        )

    def _relationship_id(self, address: str) -> str:
        used: set[str] = set()
        for rel in self.relationships:
            rel_id = rel.get("Id", "")
            used.add(rel_id)
            if (
                rel.get("Type") == OFFICE_REL_BASES[0] + "hyperlink"
                and rel.get("Target") == address
                and rel.get("TargetMode") == "External"
            ):
                return rel_id
        index = 1
        while f"rId{index}" in used:
            index += 1
        rel_id = f"rId{index}"
        etree.SubElement(
            self.relationships,
            f"{{{REL_NS}}}Relationship",
            Id=rel_id,
            Type=OFFICE_REL_BASES[0] + "hyperlink",
            Target=address,
            TargetMode="External",
        )
        self.relationships_changed = True
        self.changes.append(
            Change(
                "added_hyperlink_relationship",
                relationship_partname(self.partname),
                relationship_id=rel_id,
                target=address,
            )
        )
        return rel_id

    def _link(self, instruction: _Instruction) -> etree_Element:
        link = etree.Element(w("hyperlink"), nsmap={"w": W, "r": R})
        if instruction.address:
            link.set(f"{{{R}}}id", self._relationship_id(instruction.address))
        for name, value in (
            ("anchor", instruction.anchor),
            ("tooltip", instruction.tooltip),
            ("tgtFrame", instruction.frame),
        ):
            if value is not None:
                link.set(w(name), value)
        return link

    def _protected(self, element: etree_Element) -> bool:
        protected = {
            w(name) for name in ("ins", "del", "moveFrom", "moveTo", "hyperlink", "fldSimple")
        }
        return any(ancestor.tag in protected for ancestor in element.iterancestors())

    def convert_fields(self, root: etree_Element) -> None:
        for field in list(root.iter(w("fldSimple"))):
            text = field.get(w("instr"), "")
            if not text.lstrip().upper().startswith("HYPERLINK"):
                continue
            instruction = _instruction(text)
            if (
                self._protected(field)
                or instruction is None
                or not self._result_runs(list(field))
                or set(field.attrib) - {w("instr"), w("dirty")}
            ):
                self._skip("Unsupported simple field instruction or result structure")
                continue
            if not self._selected(instruction.address, instruction.anchor):
                self._skip("Excluded by hyperlink selector")
                continue
            parent = field.getparent()
            if parent is None:
                continue
            link = self._link(instruction)
            link.extend(list(field))
            link.tail = field.tail
            parent.replace(field, link)
            self.changes.append(
                Change(
                    "converted_hyperlink_field",
                    self.partname,
                    relationship_id=link.get(f"{{{R}}}id"),
                    target=instruction.address or instruction.anchor,
                )
            )
        for paragraph in root.iter(w("p")):
            self._convert_complex_fields(paragraph)

    @staticmethod
    def _result_runs(elements: list[etree_Element]) -> bool:
        forbidden = {
            w(name)
            for name in (
                "fldChar",
                "fldSimple",
                "instrText",
                "ins",
                "del",
                "moveFrom",
                "moveTo",
                "bookmarkStart",
                "bookmarkEnd",
                "commentRangeStart",
                "commentRangeEnd",
            )
        }
        return bool(elements) and all(
            element.tag == w("r") and not any(node.tag in forbidden for node in element.iter())
            for element in elements
        )

    def _convert_complex_fields(self, paragraph: etree_Element) -> None:
        children = list(paragraph)
        index = 0
        while index < len(children):
            child = children[index]
            markers = list(child.iter(w("fldChar")))
            if not any(marker.get(w("fldCharType")) == "begin" for marker in markers):
                index += 1
                continue
            end, depth = index, 0
            found_end = False
            for end in range(index, len(children)):
                for marker in children[end].iter(w("fldChar")):
                    kind = marker.get(w("fldCharType"))
                    depth += (kind == "begin") - (kind == "end")
                if depth == 0:
                    found_end = True
                    break
            group = children[index : end + 1]
            instruction_text = "".join(
                node.text or "" for element in group for node in element.iter(w("instrText"))
            )
            if instruction_text.lstrip().upper().startswith("HYPERLINK") and (
                not found_end or not self._convert_group(paragraph, group, instruction_text)
            ):
                self._skip("Unsupported complex field boundaries, instruction, or result")
            index = end + 1

    def _convert_group(
        self,
        paragraph: etree_Element,
        group: list[etree_Element],
        text: str,
    ) -> bool:
        instruction = _instruction(text)
        if instruction is None or self._protected(paragraph):
            return False
        markers = [node for element in group for node in element.iter(w("fldChar"))]
        if [node.get(w("fldCharType")) for node in markers] != ["begin", "separate", "end"]:
            return False
        if any(
            len(marker) or set(marker.attrib) - {w("fldCharType"), w("dirty")} for marker in markers
        ):
            return False
        if any(element.tag != w("r") for element in group):
            return False
        separator = next(
            (index for index, element in enumerate(group) if markers[1].getparent() is element), -1
        )
        if separator <= 0 or not self._result_runs(group[separator + 1 : -1]):
            return False
        # Delimiters must occupy separate runs; no text or markup may be discarded.
        for index, element in enumerate(group):
            if separator < index < len(group) - 1:
                continue
            allowed = {w("rPr"), w("instrText"), w("fldChar")}
            run_metadata = {w(name) for name in ("rsidR", "rsidRPr", "rsidDel")}
            if (
                any(node.tag not in allowed for node in element)
                or set(element.attrib) - run_metadata
            ):
                return False
        if list(group[0].iter(w("fldChar"))) != [markers[0]]:
            return False
        if list(group[-1].iter(w("fldChar"))) != [markers[-1]]:
            return False
        if not self._selected(instruction.address, instruction.anchor):
            self._skip("Excluded by hyperlink selector")
            return True
        link = self._link(instruction)
        paragraph.insert(paragraph.index(group[0]), link)
        link.extend(group[separator + 1 : -1])
        link.tail = group[-1].tail
        for element in group:
            if element.getparent() is paragraph:
                paragraph.remove(element)
        self.changes.append(
            Change(
                "converted_hyperlink_field",
                self.partname,
                relationship_id=link.get(f"{{{R}}}id"),
                target=instruction.address or instruction.anchor,
            )
        )
        return True

    def merge_runs(self, root: etree_Element) -> None:
        for link in root.iter(w("hyperlink")):
            if self._protected(link):
                self._skip("Hyperlink is inside revision markup or another hyperlink")
                continue
            address = None
            rel_id = link.get(f"{{{R}}}id")
            if rel_id is not None:
                rel = next((rel for rel in self.relationships if rel.get("Id") == rel_id), None)
                if rel is None or rel.get("Type") != OFFICE_REL_BASES[0] + "hyperlink":
                    self._skip("Hyperlink relationship is missing or has an unexpected type")
                    continue
                address = rel.get("Target")
            if not self._selected(address, link.get(w("anchor"))):
                self._skip("Excluded by hyperlink selector")
                continue
            previous: etree_Element | None = None
            merged = 0
            for run in list(link):
                if previous is not None and self._compatible(previous, run):
                    texts = list(previous.findall(w("t"))) + list(run.findall(w("t")))
                    text = "".join(node.text or "" for node in texts)
                    texts[0].text = text
                    texts[0].set(XML_SPACE, "preserve")
                    for node in texts[1:]:
                        parent = node.getparent()
                        if parent is not None:
                            parent.remove(node)
                    link.remove(run)
                    merged += 1
                else:
                    previous = run
            if merged:
                self.changes.append(
                    Change(
                        "merged_hyperlink_runs",
                        self.partname,
                        merged,
                        relationship_id=rel_id,
                        target=address or link.get(w("anchor")),
                    )
                )
            if len(link.findall(w("r"))) > 1:
                self._skip(
                    "Remaining runs differ in formatting, attributes, or contain non-text content"
                )

    @staticmethod
    def _compatible(first: etree_Element, second: etree_Element) -> bool:
        for run in (first, second):
            if run.tag != w("r") or not run.findall(w("t")):
                return False
            if any(node.tag not in (w("rPr"), w("t")) for node in run):
                return False
            if any(set(node.attrib) - {XML_SPACE} for node in run.findall(w("t"))):
                return False
            if any(len(node) for node in run.findall(w("t"))):
                return False
        # These session IDs do not change formatting; the surviving run retains its IDs.
        session_ids = {w("rsidR"), w("rsidRPr")}
        attributes = [
            {key: value for key, value in run.attrib.items() if key not in session_ids}
            for run in (first, second)
        ]
        if attributes[0] != attributes[1]:
            return False
        properties = [run.find(w("rPr")) for run in (first, second)]
        serialized = [
            etree.tostring(node, method="c14n") if node is not None else b"" for node in properties
        ]
        return serialized[0] == serialized[1]
