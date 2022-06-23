from lxml import etree

from docx.opc.part import XmlPart


class CustomXmlPart(XmlPart):
    """
    customXml part of a WordprocessingML (WML) package.
    """

    @classmethod
    def default(cls, tag, **attrib):
        return etree.tostring(etree.Element(tag, **attrib))
