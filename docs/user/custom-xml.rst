.. _custom_xml:

Working with Custom XML
=======================

A ``.docx`` file is an Open Packaging Conventions package. Custom XML parts
store application-specific XML inside its ``customXml`` directory without
placing that data in the visible document body.

.. warning::

   Some applications that edit ``.docx`` files may remove Custom XML parts.
   Test the complete editing workflow used by your application. For simple
   scalar metadata, :ref:`Custom Properties <custom_properties>` may be a more
   interoperable choice.


Creating a part
---------------

Create a Custom XML part from a well-formed XML string::

    from docx import Document

    document = Document()
    customers = document.part.add_custom_xml_part(
        '<customers xmlns="urn:example:customers"><customer id="1">Ada</customer></customers>'
    )
    document.save("customers.docx")

When no ``file_name`` is supplied, |docx| selects the next available package
name matching ``/customXml/itemN.xml``. For example, if ``item1.xml`` and
``item3.xml`` already exist, the new part is named ``item2.xml``.

An explicit name can be supplied without the ``.xml`` suffix::

    audit = document.part.add_custom_xml_part(
        "<audit><event>created</event></audit>",
        file_name="audit",
    )

The resulting part name is ``/customXml/audit.xml``. A ``ValueError`` is raised
if that part name already exists.


Finding parts
-------------

``document.part.custom_xml_parts`` returns all Custom XML parts related to the
main document. Select a part by its package name or root element rather than by
list position::

    parts_by_name = {
        str(part.partname): part
        for part in document.part.custom_xml_parts
    }
    customers = parts_by_name["/customXml/item1.xml"]

    print(customers.tag)
    print(customers.attrib)
    print(customers.items)


Updating child elements
-----------------------

``items`` contains the child elements of the part's root element. These are
``lxml`` elements, so their text and attributes can be updated directly::

    customer = customers.items[0]
    customer.text = "Grace"
    customer.attrib["status"] = "active"

Use Clark notation when adding an element in a namespace::

    customers.add_item(
        "{urn:example:customers}customer",
        "Linus",
        id="2",
    )


Deleting child elements
-----------------------

Delete a child by passing the element itself::

    customer = customers.items[0]
    customers.delete_item(customer)

The indexes in ``items`` can change after deletion. Removing an entire Custom
XML part is not currently provided by this API.

Existing relationships to Custom XML property parts, such as
``itemPropsN.xml``, are preserved during load/save round trips.
