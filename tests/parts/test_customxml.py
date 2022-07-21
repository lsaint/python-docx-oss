import pytest

from docx.opc.constants import CONTENT_TYPE as CT
from docx.parts.customxml import CustomXmlPart


class TestCustomXml:
    def test_custom_xml(self, custom_xml_part):
        assert custom_xml_part.tag == "python-docx-oss"
        assert custom_xml_part.attrib["version"] == "1"
        assert len(custom_xml_part.items) == 2
        assert custom_xml_part.items[1].text == "some texts"

    def test_add_item(self, custom_xml_part):
        custom_xml_part.add_item("my-tag", "my-text", my_attrib="my_attrib_value")
        assert len(custom_xml_part.items) == 3
        assert custom_xml_part.items[2].tag == "my-tag"
        assert custom_xml_part.items[2].text == "my-text"
        assert custom_xml_part.items[2].attrib["my_attrib"] == "my_attrib_value"

    def test_delete_item(self, custom_xml_part):
        custom_xml_part.delete_item(custom_xml_part.items[0])
        assert custom_xml_part.items[0].tag == "bar"
        assert len(custom_xml_part.items) == 1

    @pytest.fixture
    def custom_xml_part(self, mocker, default_xml):
        return CustomXmlPart.default("default_file", CT.XML, default_xml, mocker.MagicMock())

    @pytest.fixture
    def default_xml(self):
        return """
        <python-docx-oss version="1">
            <foo k1="v1"/>
            <bar k2="v2">some texts</bar>
        </python-docx-oss>
        """
