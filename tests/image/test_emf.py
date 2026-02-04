# encoding: utf-8

from __future__ import absolute_import, division, print_function, unicode_literals

import pytest

import io
from docx.image.emf import Emf
from docx.image.helpers import LITTLE_ENDIAN, StreamReader

from ..unitutil.file import test_file


class DescribeEmf(object):
    def it_can_construct_from_an_emf_stream(self, from_stream_fixture):
        stream, cx, cy, xdpi, ydpi = from_stream_fixture
        emf = Emf.from_stream(stream)
        assert isinstance(emf, Emf)
        assert emf.px_width == cx
        assert emf.px_height == cy
        assert emf.horz_dpi == xdpi
        assert emf.vert_dpi == ydpi

    # fixtures -------------------------------------------------------

    @pytest.fixture
    def from_stream_fixture(self):
        path = test_file("sonic.emf")
        with open(path, "rb") as f:
            stream = io.BytesIO(f.read())
        stream_rdr = StreamReader(stream, LITTLE_ENDIAN)
        x0 = stream_rdr.read_long(8)
        y0 = stream_rdr.read_long(12)
        x1 = stream_rdr.read_long(16)
        y1 = stream_rdr.read_long(20)

        frame = tuple(map(stream_rdr.read_long, (24, 28, 32, 36)))

        xdpi = 2540.0 * (x1 - x0) / (frame[2] - frame[0])
        ydpi = 2540.0 * (y1 - y0) / (frame[3] - frame[1])
        return stream, x1 - x0, y1 - y0, xdpi, ydpi