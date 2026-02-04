import io
from xml.etree.ElementTree import Element, tostring

import pytest

from docx.image.svg import BASE_PX, Svg


@pytest.fixture
def svg_with_dimensions():
    """Fixture for SVG stream with width and height."""
    root = Element("svg", width="200", height="100")
    return io.BytesIO(tostring(root))


@pytest.fixture
def svg_with_viewbox():
    """Fixture for SVG stream with viewBox but no width and height."""
    root = Element("svg", viewBox="0 0 400 200")
    return io.BytesIO(tostring(root))


@pytest.fixture(
    params=[
        ("0 0 400 200", 72, 36, 72),  # Landscape
        ("0 0 200 400", 100, 200, 200),  # Portrait
        ("0 0 100 100", 50, 50, 50),  # Square
        ("0 0 100.5 100.5", 50, 50, 50),  # Float
    ]
)
def viewbox_data(request):
    """Fixture for different viewBox test cases as tuples."""
    return request.param


@pytest.fixture(
    params=[
        (b'<svg width="200" height="100"/>', 200, 100),
        (b'<svg width="200.5" height="100.5"/>', 200, 100),  # round-half-to-even
        (b'<svg viewBox="0 0 400 200"/>', BASE_PX, BASE_PX // 2),
        (b'<svg viewBox="0 0 400.5 200.5"/>', BASE_PX, 36),
        (b'<svg width="1in" height="0.5in"/>', 72, 36),
        (b'<svg width="2.54cm" height="1.27cm"/>', 72, 36),
        (b'<svg width="25.4mm" height="12.7mm"/>', 72, 36),
        (b'<svg width="6pc" height="3pc"/>', 72, 36),
        (b'<svg width="72pt" height="36pt"/>', 72, 36),
        (b'<svg width="96px" height="48px"/>', 96, 48),
        (b"<svg/>", 0, 0),
    ]
)
def svg_stream_data(request):
    return request.param


@pytest.fixture(
    params=[
        ("100", 100.0),
        ("150.5", 150.5),
        ("100pt", 100.0),
        ("100px", 100.0),
        ("1in", 72.0),
        ("1pc", 12.0),
        ("2.54cm", 72.0),
        ("25.4mm", 72.0),
        (" 150.5 px ", 150.5),
        ("-20.5", -20.5),
        ("", 0.0),
        ("invalid", 0.0),
        ("12em", 12.0),  # fallback to px
    ]
)
def unit_value_data(request):
    """Fixture for different SVG unit value strings."""
    return request.param


class DescribeSvg:
    def it_parses_svg_unit_values(self, unit_value_data):
        value_str, expected_value = unit_value_data
        assert Svg._parse_svg_unit_value(value_str) == pytest.approx(expected_value)

    def it_gets_dimensions_from_stream(self, svg_stream_data):
        stream_data, expected_width, expected_height = svg_stream_data
        stream = io.BytesIO(stream_data)
        width, height = Svg._dimensions_from_stream(stream)
        assert width == expected_width
        assert height == expected_height

    def it_calculates_scaled_dimensions(self, viewbox_data):
        viewbox, expected_width, expected_height, base_px = viewbox_data
        width, height = Svg._calculate_scaled_dimensions(viewbox, base_px)
        assert width == expected_width
        assert height == expected_height

