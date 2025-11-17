import re
import xml.etree.ElementTree as ET

from .constants import MIME_TYPE
from .image import BaseImageHeader

BASE_PX = 72


class Svg(BaseImageHeader):
    """
    Image header parser for SVG images.
    """

    @classmethod
    def from_stream(cls, stream):
        """
        Return |Svg| instance having header properties parsed from SVG image
        in *stream*.
        """
        px_width, px_height = cls._dimensions_from_stream(stream)
        return cls(px_width, px_height, 72, 72)

    @property
    def content_type(self):
        """
        MIME content type for this image, unconditionally `image/svg+xml` for
        SVG images.
        """
        return MIME_TYPE.SVG

    @property
    def default_ext(self):
        """
        Default filename extension, always 'svg' for SVG images.
        """
        return "svg"

    @classmethod
    def _parse_svg_unit_value(cls, value_str: str) -> float:
        """
        Parse an SVG length value and return it in points (which are 1/72 of an inch).
        Handles units like px, pt, cm, mm, in, pc.
        """
        if not value_str:
            return 0.0

        value_str = value_str.strip().lower()

        # Regex to separate the numeric value from the unit, allowing for spaces
        match = re.match(r"^(-?\d*\.?\d+)\s*([a-z%]*)$", value_str)
        if not match:
            # Handle case where there is no unit (treat as px, as per SVG spec)
            try:
                return float(value_str)
            except ValueError:
                return 0.0

        value, unit = match.groups()
        numeric_value = float(value)

        # ---conversion factors to points (assuming 72 DPI, where 1pt = 1px)---
        # This matches the existing behavior of the Svg class.
        # 1 inch = 72 points
        # 1 cm = 1/2.54 inch = 72/2.54 points
        # 1 mm = 1/25.4 inch = 72/25.4 points
        # 1 pc = 12 points
        # 1 px = 1 point (at 72 DPI)

        if unit in ("pt", "px", ""):
            return numeric_value
        elif unit == "in":
            return numeric_value * 72.0
        elif unit == "pc":
            return numeric_value * 12.0
        elif unit == "cm":
            return numeric_value * 72.0 / 2.54
        elif unit == "mm":
            return numeric_value * 72.0 / 25.4
        # ---treat other units as px for now---
        else:
            return numeric_value

    @classmethod
    def _dimensions_from_stream(cls, stream):
        stream.seek(0)
        data = stream.read()
        root = ET.fromstring(data)

        width_str = root.attrib.get("width")
        height_str = root.attrib.get("height")

        if width_str and height_str:
            width = round(cls._parse_svg_unit_value(width_str))
            height = round(cls._parse_svg_unit_value(height_str))
            return width, height

        if root.attrib.get("viewBox"):
            return cls._calculate_scaled_dimensions(root.attrib["viewBox"])

        return 0, 0

    @classmethod
    def _calculate_scaled_dimensions(
        cls, viewbox: str, base_px: int = BASE_PX
    ) -> tuple[int, int]:
        _, _, logical_width, logical_height = map(float, viewbox.split())

        aspect_ratio = logical_width / logical_height

        if aspect_ratio >= 1:
            final_width = base_px
            final_height = base_px / aspect_ratio
        else:
            final_height = base_px
            final_width = base_px * aspect_ratio

        return round(final_width), round(final_height)
