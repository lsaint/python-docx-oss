"""Test suite for docx.oxml.simpletypes module."""

from docx.oxml.simpletypes import ST_MeasurementOrPercent
from docx.shared import Inches, Length, Pt, Twips


class DescribeST_MeasurementOrPercent:
    """Unit tests for ST_MeasurementOrPercent."""

    def it_converts_universal_measure_from_xml(self):
        val = ST_MeasurementOrPercent.convert_from_xml("231.60pt")
        assert isinstance(val, Length)
        assert round(val.pt, 2) == 231.60
        assert val == Pt(231.60)

    def it_converts_integer_twips_from_xml(self):
        val = ST_MeasurementOrPercent.convert_from_xml("1440")
        assert isinstance(val, Length)
        assert val == Inches(1)
        assert val == Twips(1440)

    def it_converts_percent_from_xml(self):
        val = ST_MeasurementOrPercent.convert_from_xml("25%")
        assert val == "25%"

    def it_converts_to_xml(self):
        assert ST_MeasurementOrPercent.convert_to_xml(Pt(231.60)) == "4632"
        assert ST_MeasurementOrPercent.convert_to_xml(Twips(1440)) == "1440"
        assert ST_MeasurementOrPercent.convert_to_xml(Inches(1)) == "1440"
        assert ST_MeasurementOrPercent.convert_to_xml("25%") == "25%"
