"""Explicit package repair and conservative hyperlink normalization."""

from docx.transforms.normalize import normalize
from docx.transforms.repair import repair
from docx.transforms.result import (
    Change,
    HyperlinkTarget,
    TransformationReport,
    TransformationResult,
)

__all__ = [
    "Change",
    "HyperlinkTarget",
    "TransformationReport",
    "TransformationResult",
    "normalize",
    "repair",
]
