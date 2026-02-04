# encoding: utf-8

from .constants import MIME_TYPE
from .helpers import LITTLE_ENDIAN, StreamReader
from .image import BaseImageHeader


class Emf(BaseImageHeader):
    """
    Image header parser for EMF images
    """

    @property
    def content_type(self):
        """
        MIME content type for this image, unconditionally `image/emf` for
        EMF images.
        """
        return MIME_TYPE.EMF

    @property
    def default_ext(self):
        """
        Default filename extension, always 'emf' for EMF images.
        """
        return "emf"

    @classmethod
    def from_stream(cls, stream):
        """
        Return a |Emf| instance having header properties parsed from image in
        *stream*.
        """
        stream_rdr = StreamReader(stream, LITTLE_ENDIAN)
        x0 = stream_rdr.read_long(8)
        y0 = stream_rdr.read_long(12)
        x1 = stream_rdr.read_long(16)
        y1 = stream_rdr.read_long(20)

        frame = tuple(map(stream_rdr.read_long, (24, 28, 32, 36)))
        size = x1 - x0, y1 - y0

        xdpi = 2540.0 * (x1 - x0) / (frame[2] - frame[0])
        ydpi = 2540.0 * (y1 - y0) / (frame[3] - frame[1])

        return cls(x1 - x0, y1 - y0, xdpi, ydpi)