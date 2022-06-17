# encoding: utf-8

"""Unit test suite for docx.package module"""

from __future__ import absolute_import, division, print_function, unicode_literals

import pytest

from docx.image.image import Image
from docx.opc.package import OpcPackage
from docx.opc.packuri import PackURI
from docx.opc.rel import Relationships, _Relationship
from docx.package import ImageParts, Package
from docx.parts.image import ImagePart

from .unitutil.file import docx_path
from .unitutil.mock import class_mock, instance_mock, method_mock, property_mock


class DescribePackage(object):
    def it_can_get_or_add_an_image_part_containing_a_specified_image(
        self, image_parts_prop_, image_parts_, image_part_
    ):
        image_parts_prop_.return_value = image_parts_
        image_parts_.get_or_add_image_part.return_value = image_part_
        package = Package()

        image_part = package.get_or_add_image_part("image.png")

        image_parts_.get_or_add_image_part.assert_called_once_with("image.png")
        assert image_part is image_part_

    def it_gathers_package_image_parts_after_unmarshalling(self):
        package = Package.open(docx_path("having-images"))
        image_parts = package.image_parts
        assert len(image_parts) == 3
        for image_part in image_parts:
            assert isinstance(image_part, ImagePart)

    # fixture components ---------------------------------------------

    @pytest.fixture
    def image_part_(self, request):
        return instance_mock(request, ImagePart)

    @pytest.fixture
    def image_parts_(self, request):
        return instance_mock(request, ImageParts)

    @pytest.fixture
    def image_parts_prop_(self, request):
        return property_mock(request, Package, "image_parts")


class DescribeImageParts(object):
    def it_can_get_a_matching_image_part(
        self, Image_, image_, _get_by_sha1_, image_part_
    ):
        Image_.from_file.return_value = image_
        image_.sha1 = "f005ba11"
        _get_by_sha1_.return_value = image_part_
        image_parts = ImageParts()

        image_part = image_parts.get_or_add_image_part("image.jpg")

        Image_.from_file.assert_called_once_with("image.jpg")
        _get_by_sha1_.assert_called_once_with(image_parts, "f005ba11")
        assert image_part is image_part_

    def but_it_adds_a_new_image_part_when_match_fails(
        self, Image_, image_, _get_by_sha1_, _add_image_part_, image_part_
    ):
        Image_.from_file.return_value = image_
        image_.sha1 = "fa1afe1"
        _get_by_sha1_.return_value = None
        _add_image_part_.return_value = image_part_
        image_parts = ImageParts()

        image_part = image_parts.get_or_add_image_part("image.png")

        Image_.from_file.assert_called_once_with("image.png")
        _get_by_sha1_.assert_called_once_with(image_parts, "fa1afe1")
        _add_image_part_.assert_called_once_with(image_parts, image_)
        assert image_part is image_part_

    def it_knows_the_next_available_image_partname(self, next_partname_fixture):
        image_parts, ext, expected_partname = next_partname_fixture
        assert image_parts._next_image_partname(ext) == expected_partname

    def it_can_really_add_a_new_image_part(
        self, _next_image_partname_, partname_, image_, ImagePart_, image_part_
    ):
        _next_image_partname_.return_value = partname_
        ImagePart_.from_image.return_value = image_part_
        image_parts = ImageParts()

        image_part = image_parts._add_image_part(image_)

        ImagePart_.from_image.assert_called_once_with(image_, partname_)
        assert image_part in image_parts
        assert image_part is image_part_

    # fixtures -------------------------------------------------------

    @pytest.fixture(params=[((2, 3), 1), ((1, 3), 2), ((1, 2), 3)])
    def next_partname_fixture(self, request):
        def image_part_with_partname_(n):
            partname = image_partname(n)
            return instance_mock(request, ImagePart, partname=partname)

        def image_partname(n):
            return PackURI("/word/media/image%d.png" % n)

        existing_partname_numbers, expected_partname_number = request.param
        image_parts = ImageParts()
        for n in existing_partname_numbers:
            image_part_ = image_part_with_partname_(n)
            image_parts.append(image_part_)
        ext = "png"
        expected_image_partname = image_partname(expected_partname_number)
        return image_parts, ext, expected_image_partname

    # fixture components ---------------------------------------------

    @pytest.fixture
    def _add_image_part_(self, request):
        return method_mock(request, ImageParts, "_add_image_part")

    @pytest.fixture
    def _get_by_sha1_(self, request):
        return method_mock(request, ImageParts, "_get_by_sha1")

    @pytest.fixture
    def Image_(self, request):
        return class_mock(request, "docx.package.Image")

    @pytest.fixture
    def image_(self, request):
        return instance_mock(request, Image)

    @pytest.fixture
    def ImagePart_(self, request):
        return class_mock(request, "docx.package.ImagePart")

    @pytest.fixture
    def image_part_(self, request):
        return instance_mock(request, ImagePart)

    @pytest.fixture
    def _next_image_partname_(self, request):
        return method_mock(request, ImageParts, "_next_image_partname")

    @pytest.fixture
    def partname_(self, request):
        return instance_mock(request, PackURI)


class TestOpcPackage:
    def test_drop_rels(self, package_with_rels):
        def cmp(rel):
            return "2" in rel.reltype

        ret = package_with_rels.drop_rels(cmp)
        assert len(package_with_rels.rels) == 2
        assert package_with_rels.rels["rId3"].reltype == "reltype3"
        assert ret == ["rId2"]

    @pytest.fixture
    def package_with_rels(self, mocker, rels):
        mocker.patch(
            "docx.opc.package.OpcPackage.rels",
            new_callable=mocker.PropertyMock,
            return_value=rels,
        )
        return OpcPackage()

    @pytest.fixture
    def rels(self):
        rels = Relationships(None)
        rels["rId1"] = _Relationship("rId1", "reltype1", "target1", "base1")
        rels["rId2"] = _Relationship("rId2", "reltype2", "target2", "base2")
        rels["rId3"] = _Relationship("rId3", "reltype3", "target3", "base3")
        return rels
