.. _custom-xml:

Working with customXml
=======================

As we know, Word documents are .zip files under the hook. 
Can we add any file in a docx file? Literally yes. 
After we unzip a docx file, We can add a ``customXml`` folder at the root of it, 
which contains any XML files. Files in other formats and paths are invalid. 
But it's enough for us to store custom data. 
It can not be seen or modified in Word like ``CustomProperties``. 

python-docx-oss will create a default XML file in the folder if there are not.
Then developer can add/delete/modify items in it.

eg::

    from docx import Document

    document = Document()
    cx = document.part.custom_xml_parts[0]

    cx.add_item("my_tag", "some_texts", foo="foo_attrib_value")
    cx.add_item("your_tag", "a_word", bar="bar_attrib_value")

2 new xml elements::

    <my_tag foo="foo_attrib_value">some_texts</my_tag>
    <your_tag bar1="value1" bar2="value2">a_word</your_tag>

will be add to ``customXml/item1.xml``

you can retrieve it::

    >>> cx.items[0].tag
    my_tag

    >>> cx.items[0].text)
    some_texts

    >>> cx.items[0].attrib["foo"]
    foo_attrib_value

    >>> cx.items[1].tag
    your_tag

    >>> cx.items[1].text)
    a_word

    >>> cx.items[1].attrib["bar2"]
    value2

or delete it::

    >>> cx.delete_item(cx.items[0])

Be careful. Items are stored as a list, the index may change after deletion::

    >>> cx.items[0].tag
    your_tag
