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
        file_name: str,
        content_type: str,
        xml: str,
        package: OpcPackage,
    ) -> "CustomXmlPart":
        """
        Create a default xml file in /customXml/*file_name*.xml
        with default content *xml* and type *content_type*
        """
        return cls(
            PackURI(f"/customXml/{file_name}.xml"),
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
