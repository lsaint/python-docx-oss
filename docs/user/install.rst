.. _install:

Installing
==========

|docx| is hosted on `PyPI <https://pypi.org/project/python-docx-oss/>`_.

Install it with ``pip``::

    python -m pip install python-docx-oss

To work from a source checkout, install it in editable mode from the repository
root::

    python -m pip install -e .

.. warning::

   ``python-docx-oss`` and ``python-docx`` both provide the top-level ``docx``
   import package. Do not install them in the same Python environment. Remove
   the other distribution before switching between the two projects.


Dependencies
------------

* Python 3.12, 3.13, or 3.14
* lxml >= 3.1.0
* typing_extensions >= 4.9.0

``pip`` installs the required dependencies automatically.
