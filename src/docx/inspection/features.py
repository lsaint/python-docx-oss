"""Streaming XML events used by package inspection."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Literal


@dataclass(frozen=True)
class ScanEvent:
    """A read-only XML event; text may arrive in multiple chunks."""

    partname: str
    kind: Literal["start", "end", "text"]
    tag: str
    attributes: Mapping[str, str] = field(default_factory=lambda: MappingProxyType({}))
    text: str = ""


Predicate = Callable[[ScanEvent], bool]


class StopScan(Exception):
    pass


class PredicateError(Exception):
    def __init__(self, error: Exception):
        self.error = error


class XmlFacts:
    """Validate XML and optionally emit events without retaining an element tree."""

    def __init__(self, partname: str = "", predicate: Predicate | None = None, stop: bool = False):
        self.partname = partname
        self.predicate = predicate
        self.stop = stop
        self.matched = False
        self.stack: list[str] = []

    def _emit(self, event: ScanEvent) -> None:
        if self.predicate is None:
            return
        try:
            matched = self.predicate(event)
        except Exception as exc:
            raise PredicateError(exc) from exc
        if matched:
            self.matched = True
            if self.stop:
                raise StopScan()

    def start(self, tag: str, attrs: Mapping[str, str]) -> None:
        if self.predicate is not None:
            self.stack.append(tag)
            self._emit(ScanEvent(self.partname, "start", tag, MappingProxyType(dict(attrs))))

    def end(self, tag: str) -> None:
        if self.predicate is not None:
            self._emit(ScanEvent(self.partname, "end", tag))
            self.stack.pop()

    def data(self, text: str) -> None:
        if self.predicate is not None and self.stack:
            self._emit(ScanEvent(self.partname, "text", self.stack[-1], text=text))

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

    def close(self) -> bool:
        return self.matched


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
