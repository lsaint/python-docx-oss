
.. _custom_properties:

Working with custom properties
==============================
The custom properties can be accessed/modified by navigating to 
File menu --> Properties --> Advanced properties --> Customization in Word. 
These properties are stored in the ``/docProps/custom.xml`` file.

we can CRUD them via python-docx-oss::

    from docx import Document
    document = Document()

    >>> print(document.custom_properties["not-exist-key"])
    None

    >>> document.custom_properties["bjj"] = "oss"
    >>> print(document.custom_properties["bjj"])
    oss
    
    >>> document.custom_properties["bjj"] = "rnc"
    >>> print(document.custom_properties["bjj"])
    rnc

    >>> document.custom_properties["bjj"] = None
    >>> print(document.custom_properties["bjj"])
    None

Be careful, users also can see & modify these properties in Word.
Use :ref:`customXml<custom-xml>` if you need them hidden.
