# encoding: utf-8

"""
Provides objects that can characterize image streams as to content type and
size, as a required step in including them in a document.
"""

from __future__ import absolute_import, division, print_function, unicode_literals

from docx.image.bmp import Bmp
from docx.image.emf import Emf
from docx.image.gif import Gif
from docx.image.jpeg import Exif, Jfif, IncompleteJpeg
from docx.image.png import Png
from docx.image.svg import Svg
from docx.image.tiff import Tiff


SIGNATURES = (
    # class, offset, signature_bytes
    (Png, 0, b"\x89PNG\x0D\x0A\x1A\x0A"),
    (Jfif, 6, b"JFIF"),
    (Exif, 6, b"Exif"),
    (IncompleteJpeg, 0, b"\xff\xd8"),
    (Gif, 0, b"GIF87a"),
    (Gif, 0, b"GIF89a"),
    (Tiff, 0, b"MM\x00*"),  # big-endian (Motorola) TIFF
    (Tiff, 0, b"II*\x00"),  # little-endian (Intel) TIFF
    (Bmp, 0, b"BM"),
    (Emf, 0, b"\x01\x00\x00\x00"),
    (Svg, 0, b"<svg "),
    (Svg, 0, b"<?xml version="),
)
