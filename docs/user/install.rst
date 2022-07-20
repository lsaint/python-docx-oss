.. _install:

Installing
==========

|docx| is hosted on `PyPI <https://pypi.org/project/python-docx-oss/>`_,
so installation is relatively simple, and just
depends on what installation utilities you have installed.

|docx| may be installed with ``pip`` if you have it available::

    pip install python-docx-oss

It can be installed manually by downloading the distribution from PyPI, unpacking the tarball,
and running ``setup.py``::

    tar xvzf python-docx-{version}.tar.gz
    cd python-docx-oss-{version}
    python setup.py install

|docx| depends on the ``lxml`` package. 
``pip`` will take care of satisfying those dependencies for you, 
but if you use this last method you will need to install those yourself.


Dependencies
------------

* Python 3.8, 3.9 or 3.10
* lxml >= 4.6.5
