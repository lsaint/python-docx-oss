python-docx-oss documentation
=============================

Release v\ |release| (:ref:`Installation <install>`)

*python-docx-oss* is an independently developed Python SDK for creating,
reading, and updating Microsoft Word (``.docx``) files. It combines familiar
document APIs with advanced WordprocessingML capabilities such as floating and
vector images, East Asian font control, custom properties, and Custom XML.


What it can do
--------------

.. |img| image:: /_static/img/example-docx-01.png 

The library supports common document operations, including paragraphs, text
formatting, tables, sections, headers, footers, comments, and images. It also
supports capabilities needed by more demanding document workflows:

* floating images with position and text wrapping;
* SVG and EMF vector images;
* separate Latin and East Asian font settings;
* document custom properties; and
* multiple Custom XML parts that survive a load/save round trip.

Here is a small example:

::

    from docx import Document
    from docx.shared import Inches

    document = Document()

    document.add_heading('Document Title', 0)

    p = document.add_paragraph('A plain paragraph having some ')
    p.add_run('bold').bold = True
    p.add_run(' and some ')
    p.add_run('italic.').italic = True

    document.add_heading('Heading, level 1', level=1)
    document.add_paragraph('Intense quote', style='Intense Quote')

    document.add_paragraph(
        'first item in unordered list', style='List Bullet'
    )
    document.add_paragraph(
        'first item in ordered list', style='List Number'
    )

    document.add_picture('500miles.png', width=Inches(5.9))

    records = (
        (3, '101', 'Spam'),
        (7, '422', 'Eggs'),
        (4, '631', 'Spam, spam, eggs, and spam')
    )

    table = document.add_table(rows=1, cols=3)
    hdr_cells = table.rows[0].cells
    hdr_cells[0].text = 'Qty'
    hdr_cells[1].text = 'Id'
    hdr_cells[2].text = 'Desc'
    for qty, id, desc in records:
        row_cells = table.add_row().cells
        row_cells[0].text = str(qty)
        row_cells[1].text = id
        row_cells[2].text = desc

    document.add_page_break()

    document.save('demo.docx')


|img|


User Guide
----------

.. toctree::
   :maxdepth: 1

   user/install
   user/quickstart
   user/documents
   user/tables
   user/text
   user/sections
   user/hdrftr
   user/api-concepts
   user/styles-understanding
   user/styles-using
   user/comments
   user/shapes
   user/custom-properties
   user/custom-xml
   user/compatibility


API Documentation
-----------------

.. toctree::
   :maxdepth: 2

   api/document
   api/settings
   api/style
   api/text
   api/table
   api/section
   api/comments
   api/shape
   api/dml
   api/shared
   api/enum/index

Contributor Guide
-----------------

.. toctree::
   :maxdepth: 1

   dev/upstream-maintenance
   dev/analysis/index
