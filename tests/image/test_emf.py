# encoding: utf-8

"""Unit test suite for docx.image.emf module"""

import pytest

from docx.compat import BytesIO
from docx.image.constants import MIME_TYPE
from docx.image.emf import Emf

from ..unitutil.mock import ANY, initializer_mock


class DescribeEmf(object):
    def it_can_construct_from_a_emf_stream(self, Emf__init__):
        cx, cy = 69, 69
        h_dpi, v_dpi = 2540.0, 2540.0
        bytes_ = b"\x01\x00\x00\x00l\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00E\x00\x00\x00E\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00E\x00\x00\x00E\x00\x00\x00"
        stream = BytesIO(bytes_)

        emf = Emf.from_stream(stream)

        Emf__init__.assert_called_once_with(ANY, cx, cy, h_dpi, v_dpi)
        assert isinstance(emf, Emf)

    def it_knows_its_content_type(self):
        emf = Emf(None, None, None, None)
        assert emf.content_type == MIME_TYPE.EMF

    def it_knows_its_default_ext(self):
        emf = Emf(None, None, None, None)
        assert emf.default_ext == "emf"

    # fixture components ---------------------------------------------

    @pytest.fixture
    def Emf__init__(self, request):
        return initializer_mock(request, Emf)
