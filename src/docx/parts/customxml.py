"""
|CustomXmlPart| and closely related objects
"""

from lxml import etree
from lxml.etree import fromstring

from docx.opc.package import OpcPackage
from docx.opc.packuri import PackURI
from docx.opc.part import XmlPart


class CustomXmlPart(XmlPart):
    """
    Proxy for the /customXml/*.xml part containing custom items definitions
    """

    @classmethod
    def default(
        cls,
        file_name: str | None,
        content_type: str,
        xml: str,
        package: OpcPackage,
    ) -> "CustomXmlPart":
        """Create a Custom XML part with a unique package partname."""
        if file_name is None:
            partname = package.next_partname("/customXml/item%d.xml")
        else:
            partname = PackURI(f"/customXml/{file_name}.xml")
            if any(part.partname == partname for part in package.iter_parts()):
                raise ValueError(f"part already exists at '{partname}'")

        return cls(
            partname,
            content_type,
            fromstring(xml),
            package,
        )

    @property
    def tag(self) -> str:
        """
        Return the root element tag name.
        """
        return self.element.tag

    @property
    def attrib(self) -> dict:
        """
        Return the root element attributes.
        """
        return self.element.attrib

    @property
    def items(self) -> list[etree._Element]:
        """
        Return all children belong to root element.
        """
        return self.element.getchildren()

    def add_item(self, tag: str, text: str = "", **attrib):
        """
        Add a child element to root.
        """
        etree.SubElement(self.element, tag, **attrib).text = text

    def delete_item(self, item_element: etree._Element):
        """
        Delete a item element. other nodes index may change after deletion.
        """
        self.element.remove(item_element)
