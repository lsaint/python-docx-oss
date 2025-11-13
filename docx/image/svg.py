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
    def _dimensions_from_stream(cls, stream):
        stream.seek(0)
        data = stream.read()
        root = ET.fromstring(data)
        if root.attrib.get("width") is None:
            return cls._calculate_scaled_dimensions(root.attrib["viewBox"])

        width = int(float(root.attrib["width"].replace("pt", "")))
        height = int(float(root.attrib["height"].replace("pt", "")))
        return width, height

    @classmethod
    def _calculate_scaled_dimensions(
        cls, viewbox: str, base_px: int = BASE_PX
    ) -> tuple[int, int]:
        _, _, logical_width, logical_height = map(int, viewbox.split())

        aspect_ratio = logical_width / logical_height

        if aspect_ratio >= 1:
            final_width = base_px
            final_height = base_px / aspect_ratio
        else:
            final_height = base_px
            final_width = base_px * aspect_ratio

        return int(final_width), int(final_height)
