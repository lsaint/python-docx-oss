# pyright: reportPrivateUsage=false

"""This module is for elements which has extLst child."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

from docx.oxml.ns import nsdecls, qn
from docx.oxml.parser import parse_xml
from docx.oxml.xmlchemy import BaseOxmlElement, ZeroOrOne

if TYPE_CHECKING:
    from docx.oxml.shape import CT_Extension


class CT_ExtensionList(BaseOxmlElement):
    """Base class for `extLst` element in DrawingML."""

    ext: CT_Extension = ZeroOrOne("a:ext")
    _add_ext: Any

    @classmethod
    def new(cls):
        """Return a new `extLst` element."""
        extLst = cast(
            CT_ExtensionList,
            parse_xml(f"<a:extLst {nsdecls('a')}/>"),
        )
        extLst._add_ext()
        return extLst


class CT_Extension(BaseOxmlElement):
    """
    `<a:ext>` element in `extLst`, which can hold a `svgBlip` element.
    """

    @property
    def svgBlip(self) -> "CT_Transform2D":
        from docx.oxml.shape import CT_Transform2D

        return self.xpath("./asvg:svgBlip")[0]

    @classmethod
    def new(cls):
        """Return a new `ext` element."""
        return cast(CT_Extension, parse_xml(f"<a:ext {nsdecls('a')}/>"))
