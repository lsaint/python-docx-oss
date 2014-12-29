# encoding: utf-8

"""
Custom element classes related to text runs (CT_R).
"""

from ...enum.text import WD_UNDERLINE
from ..ns import qn
from ..simpletypes import ST_BrClear, ST_BrType, ST_String
from ..xmlchemy import (
    BaseOxmlElement, OptionalAttribute, ZeroOrMore, ZeroOrOne
)


class CT_Br(BaseOxmlElement):
    """
    ``<w:br>`` element, indicating a line, page, or column break in a run.
    """
    type = OptionalAttribute('w:type', ST_BrType)
    clear = OptionalAttribute('w:clear', ST_BrClear)


class CT_Fonts(BaseOxmlElement):
    """
    ``<w:rFonts>`` element, specifying typeface name for the various language
    types.
    """
    ascii = OptionalAttribute('w:ascii', ST_String)


class CT_R(BaseOxmlElement):
    """
    ``<w:r>`` element, containing the properties and text for a run.
    """
    rPr = ZeroOrOne('w:rPr')
    t = ZeroOrMore('w:t')
    br = ZeroOrMore('w:br')
    cr = ZeroOrMore('w:cr')
    tab = ZeroOrMore('w:tab')
    drawing = ZeroOrMore('w:drawing')

    def _insert_rPr(self, rPr):
        self.insert(0, rPr)
        return rPr

    def add_t(self, text):
        """
        Return a newly added ``<w:t>`` element containing *text*.
        """
        t = self._add_t(text=text)
        if len(text.strip()) < len(text):
            t.set(qn('xml:space'), 'preserve')
        return t

    def add_drawing(self, inline_or_anchor):
        """
        Return a newly appended ``CT_Drawing`` (``<w:drawing>``) child
        element having *inline_or_anchor* as its child.
        """
        drawing = self._add_drawing()
        drawing.append(inline_or_anchor)
        return drawing

    def clear_content(self):
        """
        Remove all child elements except the ``<w:rPr>`` element if present.
        """
        content_child_elms = self[1:] if self.rPr is not None else self[:]
        for child in content_child_elms:
            self.remove(child)

    @property
    def style(self):
        """
        String contained in w:val attribute of <w:rStyle> grandchild, or
        |None| if that element is not present.
        """
        rPr = self.rPr
        if rPr is None:
            return None
        return rPr.style

    @style.setter
    def style(self, style):
        """
        Set the character style of this <w:r> element to *style*. If *style*
        is None, remove the style element.
        """
        rPr = self.get_or_add_rPr()
        rPr.style = style

    @property
    def text(self):
        """
        A string representing the textual content of this run, with content
        child elements like ``<w:tab/>`` translated to their Python
        equivalent.
        """
        text = ''
        for child in self:
            if child.tag == qn('w:t'):
                t_text = child.text
                text += t_text if t_text is not None else ''
            elif child.tag == qn('w:tab'):
                text += '\t'
            elif child.tag in (qn('w:br'), qn('w:cr')):
                text += '\n'
        return text

    @text.setter
    def text(self, text):
        self.clear_content()
        _RunContentAppender.append_to_run_from_text(self, text)

    @property
    def underline(self):
        """
        String contained in w:val attribute of ./w:rPr/w:u grandchild, or
        |None| if not present.
        """
        rPr = self.rPr
        if rPr is None:
            return None
        return rPr.underline

    @underline.setter
    def underline(self, value):
        rPr = self.get_or_add_rPr()
        rPr.underline = value


class CT_RPr(BaseOxmlElement):
    """
    ``<w:rPr>`` element, containing the properties for a run.
    """
    _tag_seq = (
        'w:rStyle', 'w:rFonts', 'w:b', 'w:bCs', 'w:i', 'w:iCs', 'w:caps',
        'w:smallCaps', 'w:strike', 'w:dstrike', 'w:outline', 'w:shadow',
        'w:emboss', 'w:imprint', 'w:noProof', 'w:snapToGrid', 'w:vanish',
        'w:webHidden', 'w:color', 'w:spacing', 'w:w', 'w:kern', 'w:position',
        'w:sz', 'w:szCs', 'w:highlight', 'w:u', 'w:effect', 'w:bdr', 'w:shd',
        'w:fitText', 'w:vertAlign', 'w:rtl', 'w:cs', 'w:em', 'w:lang',
        'w:eastAsianLayout', 'w:specVanish', 'w:oMath'
    )
    rStyle = ZeroOrOne('w:rStyle', successors=_tag_seq[1:])
    rFonts = ZeroOrOne('w:rFonts', successors=_tag_seq[2:])
    b = ZeroOrOne('w:b', successors=_tag_seq[3:])
    bCs = ZeroOrOne('w:bCs', successors=_tag_seq[4:])
    i = ZeroOrOne('w:i', successors=_tag_seq[5:])
    iCs = ZeroOrOne('w:iCs', successors=_tag_seq[6:])
    caps = ZeroOrOne('w:caps', successors=_tag_seq[7:])
    smallCaps = ZeroOrOne('w:smallCaps', successors=_tag_seq[8:])
    strike = ZeroOrOne('w:strike', successors=_tag_seq[9:])
    dstrike = ZeroOrOne('w:dstrike', successors=_tag_seq[10:])
    outline = ZeroOrOne('w:outline', successors=_tag_seq[11:])
    shadow = ZeroOrOne('w:shadow', successors=_tag_seq[12:])
    emboss = ZeroOrOne('w:emboss', successors=_tag_seq[13:])
    imprint = ZeroOrOne('w:imprint', successors=_tag_seq[14:])
    noProof = ZeroOrOne('w:noProof', successors=_tag_seq[15:])
    snapToGrid = ZeroOrOne('w:snapToGrid', successors=_tag_seq[16:])
    vanish = ZeroOrOne('w:vanish', successors=_tag_seq[17:])
    webHidden = ZeroOrOne('w:webHidden', successors=_tag_seq[18:])
    u = ZeroOrOne('w:u', successors=_tag_seq[27:])
    rtl = ZeroOrOne('w:rtl', successors=_tag_seq[33:])
    cs = ZeroOrOne('w:cs', successors=_tag_seq[34:])
    specVanish = ZeroOrOne('w:specVanish', successors=_tag_seq[38:])
    oMath = ZeroOrOne('w:oMath', successors=_tag_seq[39:])
    del _tag_seq

    @property
    def rFonts_ascii(self):
        """
        The value of `w:rFonts/@w:ascii` or |None| if not present. Represents
        the assigned typeface name. The rFonts element also specifies other
        special-case typeface names; this method handles the case where just
        the common name is required.
        """
        rFonts = self.rFonts
        if rFonts is None:
            return None
        return rFonts.ascii

    @property
    def style(self):
        """
        String contained in <w:rStyle> child, or None if that element is not
        present.
        """
        rStyle = self.rStyle
        if rStyle is None:
            return None
        return rStyle.val

    @style.setter
    def style(self, style):
        """
        Set val attribute of <w:rStyle> child element to *style*, adding a
        new element if necessary. If *style* is |None|, remove the <w:rStyle>
        element if present.
        """
        if style is None:
            self._remove_rStyle()
        elif self.rStyle is None:
            self._add_rStyle(val=style)
        else:
            self.rStyle.val = style

    @property
    def underline(self):
        """
        Underline type specified in <w:u> child, or None if that element is
        not present.
        """
        u = self.u
        if u is None:
            return None
        return u.val

    @underline.setter
    def underline(self, value):
        self._remove_u()
        if value is not None:
            u = self._add_u()
            u.val = value


class CT_Text(BaseOxmlElement):
    """
    ``<w:t>`` element, containing a sequence of characters within a run.
    """


class CT_Underline(BaseOxmlElement):
    """
    ``<w:u>`` element, specifying the underlining style for a run.
    """
    @property
    def val(self):
        """
        The underline type corresponding to the ``w:val`` attribute value.
        """
        val = self.get(qn('w:val'))
        underline = WD_UNDERLINE.from_xml(val)
        if underline == WD_UNDERLINE.SINGLE:
            return True
        if underline == WD_UNDERLINE.NONE:
            return False
        return underline

    @val.setter
    def val(self, value):
        # works fine without these two mappings, but only because True == 1
        # and False == 0, which happen to match the mapping for WD_UNDERLINE
        # .SINGLE and .NONE respectively.
        if value is True:
            value = WD_UNDERLINE.SINGLE
        elif value is False:
            value = WD_UNDERLINE.NONE

        val = WD_UNDERLINE.to_xml(value)
        self.set(qn('w:val'), val)


class _RunContentAppender(object):
    """
    Service object that knows how to translate a Python string into run
    content elements appended to a specified ``<w:r>`` element. Contiguous
    sequences of regular characters are appended in a single ``<w:t>``
    element. Each tab character ('\t') causes a ``<w:tab/>`` element to be
    appended. Likewise a newline or carriage return character ('\n', '\r')
    causes a ``<w:cr>`` element to be appended.
    """
    def __init__(self, r):
        self._r = r
        self._bfr = []

    @classmethod
    def append_to_run_from_text(cls, r, text):
        """
        Create a "one-shot" ``_RunContentAppender`` instance and use it to
        append the run content elements corresponding to *text* to the
        ``<w:r>`` element *r*.
        """
        appender = cls(r)
        appender.add_text(text)

    def add_text(self, text):
        """
        Append the run content elements corresponding to *text* to the
        ``<w:r>`` element of this instance.
        """
        for char in text:
            self.add_char(char)
        self.flush()

    def add_char(self, char):
        """
        Process the next character of input through the translation finite
        state maching (FSM). There are two possible states, buffer pending
        and not pending, but those are hidden behind the ``.flush()`` method
        which must be called at the end of text to ensure any pending
        ``<w:t>`` element is written.
        """
        if char == '\t':
            self.flush()
            self._r.add_tab()
        elif char in '\r\n':
            self.flush()
            self._r.add_br()
        else:
            self._bfr.append(char)

    def flush(self):
        text = ''.join(self._bfr)
        if text:
            self._r.add_t(text)
        del self._bfr[:]
