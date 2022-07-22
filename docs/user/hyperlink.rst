Hyperlink
=========

Word allows hyperlinks to be placed in a document.

The target of a hyperlink may be external, such as a web site, or internal,
to another location in the document.

A hyperlink can contain multiple runs of text, each with its own distinct
text formatting (font).


Candidate protocol
------------------

An external hyperlink has an address and an optional anchor. An internal
hyperlink has only an anchor.

.. highlight:: python

**Add the external hyperlink** `http://us.com#about`::

    >>> hyperlink = paragraph.add_hyperlink('About', address='http://us.com', anchor='about')
    >>> hyperlink
    <docx.text.hyperlink.Hyperlink at 0x7f...>
    >>> hyperlink.text
    'About'
    >>> hyperlink.address
    'http://us.com'
    >>> hyperlink.anchor
    'about'

**Add an internal hyperlink (to a bookmark)**::

    >>> hyperlink = paragraph.add_hyperlink('Section 1', anchor='Section_1')
    >>> hyperlink.text
    'Section 1'
    >>> hyperlink.anchor
    'Section_1'
    >>> hyperlink.address
    None

**Modify hyperlink properties**::

    >>> hyperlink.text = 'Froogle'
    >>> hyperlink.text
    'Froogle'
    >>> hyperlink.address = 'mailto:info@froogle.com?subject=sup dawg?'
    >>> hyperlink.address
    'mailto:info@froogle.com?subject=sup%20dawg%3F'
    >>> hyperlink.anchor = None
    >>> hyperlink.anchor
    None

**Add additional runs to a hyperlink**::

    >>> hyperlink.text = 'A '
    >>> # .insert_run inserts a new run at idx, defaults to idx=-1
    >>> hyperlink.insert_run(' link').bold = True
    >>> hyperlink.insert_run('formatted', idx=1).bold = True
    >>> hyperlink.text
    'A formatted link'
    >>> [r for r in hyperlink.iter_runs()]
    [<docx.text.run.Run at 0x7fa...>,
     <docx.text.run.Run at 0x7fb...>,
     <docx.text.run.Run at 0x7fc...>]

**Iterate over the run-level items a paragraph contains**::

    >>> paragraph = document.add_paragraph('A paragraph having a link to: ')
    >>> paragraph.add_hyperlink(text='github', address='http://github.com')
    >>> [item for item in paragraph.iter_run_level_items()]:
    [<docx.text.paragraph.Run at 0x7fd...>, <docx.text.paragraph.Hyperlink at 0x7fe...>]

**Paragraph.text now includes text contained in a hyperlink**::

    >>> paragraph.text
    'A paragraph having a link to: github'


Word Behaviors
--------------

* What are the semantics of the w:history attribute on w:hyperlink? I'm
  suspecting this indicates whether the link should show up blue (unvisited)
  or purple (visited). I'm inclined to think we need that as a read/write
  property on hyperlink. We should see what the MS API does on this count.

* We probably need to enforce some character-set restrictions on w:anchor.
  Word doesn't seem to like spaces or hyphens, for example. The simple type
  ST_String doesn't look like it takes care of this.

* We'll need to test URL escaping of special characters like spaces and
  question marks in Hyperlink.address.

* What does Word do when loading a document containing an internal hyperlink
  having an anchor value that doesn't match an existing bookmark? We'll want
  to know because we're sure to get support inquiries from folks who don't
  match those up and wonder why they get a repair error or whatever.


Specimen XML
------------

.. highlight:: xml


External links
~~~~~~~~~~~~~~

The address (URL) of an external hyperlink is stored in the document.xml.rels
file, keyed by the w:hyperlink@r:id attribute::

    <w:p>
      <w:r>
        <w:t xml:space="preserve">This is an external link to </w:t>
      </w:r>
      <w:hyperlink r:id="rId4">
        <w:r>
          <w:rPr>
            <w:rStyle w:val="Hyperlink"/>
          </w:rPr>
          <w:t>Google</w:t>
        </w:r>
      </w:hyperlink>
    </w:p>

... mapping to relationship in document.xml.rels::

    <Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
      <Relationship Id="rId4" Mode="External" Type="http://..." Target="http://google.com/"/>
    </Relationships>

A hyperlink can contain multiple runs of text (and a whole lot of other
stuff, including nested hyperlinks, at least as far as the schema indicates)::

    <w:p>
      <w:hyperlink r:id="rId2">
        <w:r>
          <w:rPr>
            <w:rStyle w:val="Hyperlink"/>
          </w:rPr>
          <w:t xml:space="preserve">A hyperlink containing an </w:t>
        </w:r>
        <w:r>
          <w:rPr>
            <w:rStyle w:val="Hyperlink"/>
            <w:i/>
          </w:rPr>
          <w:t>italicized</w:t>
        </w:r>
        <w:r>
          <w:rPr>
            <w:rStyle w:val="Hyperlink"/>
          </w:rPr>
          <w:t xml:space="preserve"> word</w:t>
        </w:r>
      </w:hyperlink>
    </w:p>


Internal links
~~~~~~~~~~~~~~

An internal link provides "jump to another document location" behavior in the
Word UI. An internal link is distinguished by the absence of an r:id
attribute. In this case, the w:anchor attribute is required. The value of the
anchor attribute is the name of a bookmark in the document.

Example::

    <w:p>
      <w:r>
        <w:t xml:space="preserve">See </w:t>
      </w:r>
      <w:hyperlink w:anchor="Section_4">
        <w:r>
          <w:rPr>
            <w:rStyle w:val="Hyperlink"/>
          </w:rPr>
          <w:t>Section 4</w:t>
        </w:r>
      </w:hyperlink>
      <w:r>
        <w:t xml:space="preserve"> for more details.</w:t>
      </w:r>
    </w:p>

... referring to this bookmark elsewhere in the document::

    <w:p>
      <w:bookmarkStart w:id="0" w:name="Section_4"/>
        <w:r>
          <w:t>Section 4</w:t>
        </w:r>
      <w:bookmarkEnd w:id="0"/>
    </w:p>


