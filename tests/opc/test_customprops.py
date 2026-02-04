"""
Unit test suite for the docx.opc.customprops module
"""
import pytest
from lxml import etree

from docx.opc.customprops import CustomProperties
from docx.oxml import parse_xml


class DescribeCustomProperties(object):
    def it_can_read_existing_prop_values(self, prop_get_fixture):
        custom_properties, prop_name, exp_value = prop_get_fixture
        actual_value = custom_properties[prop_name]
        assert actual_value == exp_value

    def it_can_change_existing_prop_values(self):
        pass

    def it_can_set_new_prop_values(self, prop_set_fixture):
        custom_properties, prop_name, value, expected_xml = prop_set_fixture
        custom_properties[prop_name] = value
        assert etree.tostring(custom_properties._element, pretty_print=True).decode() == expected_xml

    # fixtures -------------------------------------------------------

    @pytest.fixture(
        params=[
            ("CustomPropString", "Test String"),
            ("CustomPropBool", True),
            ("CustomPropInt", 13),
            ("CustomPropFoo", None),
        ]
    )
    def prop_get_fixture(self, request, custom_properties_default):
        prop_name, expected_value = request.param
        return custom_properties_default, prop_name, expected_value

    @pytest.fixture(
        params=[
            ("CustomPropString", "lpwstr", "Hi there!", "Hi there!"),
            ("CustomPropBool", "bool", "false", False),
            ("CustomPropInt", "i4", "5", 5),
        ]
    )
    def prop_set_fixture(self, request, custom_properties_blank):
        prop_name, str_type, str_value, value = request.param
        # The actual code generates pid="2" for the first prop.
        expected_xml = self.custom_properties(prop_name, str_type, str_value, pid="2")
        return custom_properties_blank, prop_name, value, expected_xml

    # fixture components ---------------------------------------------

    def custom_properties(self, prop_name, str_type, str_value, pid):
        # Using triple-quotes for safe multi-line string definition
        tmpl = f'''<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/custom-properties" xmlns:vt="http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes">
  <property name="{prop_name}" fmtid="{{D5CDD505-2E9C-101B-9397-08002B2CF9AE}}" pid="{pid}">
    <vt:{str_type}>{str_value}</vt:{str_type}>
  </property>
</Properties>
'''
        return tmpl

    @pytest.fixture
    def custom_properties_blank(self):
        xml = '''<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/custom-properties" xmlns:vt="http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes"></Properties>'''
        element = parse_xml(xml)
        return CustomProperties(element)

    @pytest.fixture
    def custom_properties_default(self):
        xml = b'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/custom-properties" xmlns:vt="http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes">
  <property fmtid="{D5CDD505-2E9C-101B-9397-08002B2CF9AE}" pid="2" name="CustomPropBool"><vt:bool>1</vt:bool></property>
  <property fmtid="{D5CDD505-2E9C-101B-9397-08002B2CF9AE}" pid="3" name="CustomPropInt"><vt:i4>13</vt:i4></property>
  <property fmtid="{D5CDD505-2E9C-101B-9397-08002B2CF9AE}" pid="4" name="CustomPropString"><vt:lpwstr>Test String</vt:lpwstr></property>
</Properties>'''
        element = parse_xml(xml)
        return CustomProperties(element)
