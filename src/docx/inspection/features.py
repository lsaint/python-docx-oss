"""XML event targets keep no element tree, including for very large story parts."""

from __future__ import annotations

from collections.abc import Mapping

from docx.inspection.result import Features

W_NAMESPACES = (
    "http://schemas.openxmlformats.org/wordprocessingml/2006/main",
    "http://purl.oclc.org/ooxml/wordprocessingml/main",
)


def word_tag(tag: str) -> str:
    for namespace in W_NAMESPACES:
        prefix = "{" + namespace + "}"
        if tag.startswith(prefix):
            return tag[len(prefix) :]
    return ""


class _FieldCommand:
    """Match only the first token, keeping constant state across parser callbacks."""

    def __init__(self):
        self._length = 0
        self._done = False
        self.matched = False

    def feed(self, text: str) -> None:
        for char in text:
            if self._done:
                break
            if char.isspace():
                if self._length:
                    self.finish()
            elif self._length < len("HYPERLINK") and char.upper() == "HYPERLINK"[self._length]:
                self._length += 1
            else:
                self._done = True

    def finish(self) -> None:
        if not self._done:
            self.matched = self._length == len("HYPERLINK")
            self._done = True


class XmlFacts:
    """Observe field instructions across runs, without retaining instruction text."""

    def __init__(self, scan_features: bool = False):
        self.scan_features = scan_features
        self.field_hyperlink = False
        self.split_hyperlink_runs = False
        self._stack: list[str] = []
        self._hyperlinks: list[tuple[int, int]] = []
        self._instruction = False
        self._fields: list[_FieldCommand] = []
        self._loose_command = _FieldCommand()

    def _finish_command(self, command: _FieldCommand) -> None:
        command.finish()
        self.field_hyperlink |= command.matched

    def start(self, tag: str, attrs: Mapping[str, str]) -> None:
        name = word_tag(tag) if self.scan_features else ""
        self._stack.append(name)
        if name == "hyperlink":
            self._hyperlinks.append((len(self._stack), 0))
        elif name == "r" and self._hyperlinks:
            depth, count = self._hyperlinks[-1]
            if len(self._stack) == depth + 1:
                self._hyperlinks[-1] = (depth, count + 1)
                self.split_hyperlink_runs |= count >= 1
        elif name == "fldChar":
            namespace = tag[: tag.index("}") + 1]
            kind = attrs.get(namespace + "fldCharType")
            if kind == "begin":
                self._fields.append(_FieldCommand())
            elif kind in ("separate", "end"):
                command = self._fields[-1] if self._fields else self._loose_command
                self._finish_command(command)
                if kind == "end":
                    if self._fields:
                        self._fields.pop()
                    self._loose_command = _FieldCommand()
        elif name == "instrText":
            self._instruction = True
        elif name == "fldSimple":
            namespace = tag[: tag.index("}") + 1]
            command = _FieldCommand()
            command.feed(attrs.get(namespace + "instr", ""))
            self._finish_command(command)
        elif name == "p":
            self._loose_command = _FieldCommand()

    def end(self, tag: str) -> None:
        name = self._stack.pop()
        if name == "hyperlink":
            self._hyperlinks.pop()
        elif name == "instrText":
            self._instruction = False
        elif name == "p":
            self._finish_command(self._loose_command)
            self._loose_command = _FieldCommand()

    def data(self, text: str) -> None:
        if self._instruction:
            command = self._fields[-1] if self._fields else self._loose_command
            command.feed(text)
            self.field_hyperlink |= command.matched

    def start_ns(self, prefix: str | None, uri: str) -> None:
        pass

    def end_ns(self, prefix: str | None) -> None:
        pass

    def comment(self, text: str) -> None:
        pass

    def pi(self, target: str, data: str) -> None:
        pass

    def doctype(self, name: str | None, public_id: str | None, system_id: str | None) -> None:
        raise ValueError("DTDs are not supported in package XML")

    def close(self) -> Features:
        self._finish_command(self._loose_command)
        for command in self._fields:
            self._finish_command(command)
        return Features(self.field_hyperlink, self.split_hyperlink_runs)


class MetadataFacts(XmlFacts):
    """Keep OPC metadata entries, never arbitrary XML text or unrelated elements."""

    def __init__(self):
        super().__init__()
        self.elements: list[tuple[str, dict[str, str]]] = []
        self.root_tag: str | None = None
        self._depth = 0

    def start(self, tag: str, attrs: Mapping[str, str]) -> None:
        if self._depth == 0:
            self.root_tag = tag
        self._depth += 1
        if self._depth == 2 and tag in (
            "{http://schemas.openxmlformats.org/package/2006/content-types}Default",
            "{http://schemas.openxmlformats.org/package/2006/content-types}Override",
            "{http://schemas.openxmlformats.org/package/2006/relationships}Relationship",
        ):
            self.elements.append((tag, dict(attrs)))

    def end(self, tag: str) -> None:
        self._depth -= 1
