# encoding: utf-8

"""
Simple type classes, providing validation and format translation for values
stored in XML element attributes. Naming generally corresponds to the simple
type in the associated XML schema.
"""

from __future__ import absolute_import, print_function

from ..shared import Emu


class BaseSimpleType(object):

    @classmethod
    def from_xml(cls, str_value):
        return cls.convert_from_xml(str_value)

    @classmethod
    def to_xml(cls, value):
        cls.validate(value)
        str_value = cls.convert_to_xml(value)
        return str_value

    @classmethod
    def validate_int(cls, value):
        if not isinstance(value, int):
            raise TypeError(
                "value must be <type 'int'>, got %s" % type(value)
            )

    @classmethod
    def validate_int_in_range(cls, value, min_inclusive, max_inclusive):
        cls.validate_int(value)
        if value < min_inclusive or value > max_inclusive:
            raise ValueError(
                "value must be in range %d to %d inclusive, got %d" %
                (min_inclusive, max_inclusive, value)
            )

    @classmethod
    def validate_string(cls, value):
        if isinstance(value, str):
            return value
        try:
            if isinstance(value, basestring):
                return value
        except NameError:  # means we're on Python 3
            pass
        raise TypeError(
            "value must be a string, got %s" % type(value)
        )


class BaseStringType(BaseSimpleType):

    @classmethod
    def convert_from_xml(cls, str_value):
        return str_value

    @classmethod
    def convert_to_xml(cls, value):
        return value

    @classmethod
    def validate(cls, value):
        cls.validate_string(value)


class BaseIntType(BaseSimpleType):

    @classmethod
    def convert_from_xml(cls, str_value):
        return int(str_value)

    @classmethod
    def convert_to_xml(cls, value):
        return str(value)

    @classmethod
    def validate(cls, value):
        cls.validate_int(value)


class XsdAnyUri(BaseStringType):
    """
    There's a regular expression this is supposed to meet but so far thinking
    spending cycles on validating wouldn't be worth it for the number of
    programming errors it would catch.
    """


class XsdBoolean(BaseSimpleType):

    @classmethod
    def convert_from_xml(cls, str_value):
        return str_value in ('1', 'true')

    @classmethod
    def convert_to_xml(cls, value):
        return {True: '1', False: '0'}[value]

    @classmethod
    def validate(cls, value):
        if value not in (True, False):
            raise TypeError(
                "only True or False (and possibly None) may be assigned, got"
                " '%s'" % value
            )


class XsdId(BaseStringType):
    """
    String that must begin with a letter or underscore and cannot contain any
    colons. Not fully validated because not used in external API.
    """
    pass


class XsdInt(BaseIntType):

    @classmethod
    def validate(cls, value):
        cls.validate_int_in_range(value, -2147483648, 2147483647)


class XsdLong(BaseIntType):

    @classmethod
    def validate(cls, value):
        cls.validate_int_in_range(
            value, -9223372036854775808, 9223372036854775807
        )


class XsdString(BaseStringType):
    pass


class XsdToken(BaseStringType):
    """
    xsd:string with whitespace collapsing, e.g. multiple spaces reduced to
    one, leading and trailing space stripped.
    """
    pass


class XsdUnsignedInt(BaseIntType):

    @classmethod
    def validate(cls, value):
        cls.validate_int_in_range(value, 0, 4294967295)


class ST_BrClear(XsdString):

    @classmethod
    def validate(cls, value):
        cls.validate_string(value)
        valid_values = ('none', 'left', 'right', 'all')
        if value not in valid_values:
            raise ValueError(
                "must be one of %s, got '%s'" % (valid_values, value)
            )


class ST_BrType(XsdString):

    @classmethod
    def validate(cls, value):
        cls.validate_string(value)
        valid_values = ('page', 'column', 'textWrapping')
        if value not in valid_values:
            raise ValueError(
                "must be one of %s, got '%s'" % (valid_values, value)
            )


class ST_Coordinate(BaseIntType):

    @classmethod
    def convert_from_xml(cls, str_value):
        if 'i' in str_value or 'm' in str_value or 'p' in str_value:
            return ST_UniversalMeasure.convert_from_xml(str_value)
        return Emu(int(str_value))

    @classmethod
    def validate(cls, value):
        ST_CoordinateUnqualified.validate(value)


class ST_CoordinateUnqualified(XsdLong):

    @classmethod
    def validate(cls, value):
        cls.validate_int_in_range(value, -27273042329600, 27273042316900)


class ST_DecimalNumber(XsdInt):
    pass


class ST_DrawingElementId(XsdUnsignedInt):
    pass


class ST_OnOff(XsdBoolean):

    @classmethod
    def convert_from_xml(cls, str_value):
        return str_value in ('1', 'true', 'on')


class ST_PositiveCoordinate(XsdLong):

    @classmethod
    def convert_from_xml(cls, str_value):
        return Emu(int(str_value))

    @classmethod
    def validate(cls, value):
        cls.validate_int_in_range(value, 0, 27273042316900)


class ST_RelationshipId(XsdString):
    pass


class ST_String(XsdString):
    pass


class ST_UniversalMeasure(BaseSimpleType):

    @classmethod
    def convert_from_xml(cls, str_value):
        float_part, units_part = str_value[:-2], str_value[-2:]
        quantity = float(float_part)
        multiplier = {
            'mm': 36000, 'cm': 360000, 'in': 914400, 'pt': 12700,
            'pc': 152400, 'pi': 152400
        }[units_part]
        emu_value = Emu(int(round(quantity * multiplier)))
        return emu_value