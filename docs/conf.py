# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Path setup --------------------------------------------------------------

import os
import sys

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#
sys.path.insert(0, os.path.abspath(".."))

from docx import __version__  # noqa

# -- Project information -----------------------------------------------------

project = "python-docx-oss"
copyright = "2022, Ethan St. Lee"
author = "Ethan St. Lee"

# The full version, including alpha/beta/rc tags
release = __version__

# A string of reStructuredText that will be included at the end of every source
# file that is read. This is the right place to add substitutions that should
# be available in every file.
rst_epilog = """
.. |api-Document| replace:: :class:`docx.api.Document`

.. |AttributeError| replace:: :exc:`.AttributeError`

.. |BaseStyle| replace:: :class:`.BaseStyle`

.. |BlockItemContainer| replace:: :class:`.BlockItemContainer`

.. |_Body| replace:: :class:`._Body`

.. |_Cell| replace:: :class:`._Cell`

.. |_CharacterStyle| replace:: :class:`._CharacterStyle`

.. |Cm| replace:: :class:`.Cm`

.. |ColorFormat| replace:: :class:`.ColorFormat`

.. |_Column| replace:: :class:`._Column`

.. |_Columns| replace:: :class:`._Columns`

.. |CoreProperties| replace:: :class:`.CoreProperties`

.. |CustomProperties| replace:: :class:`.CustomProperties`

.. |datetime| replace:: :class:`.datetime.datetime`

.. |Document| replace:: :class:`.Document`

.. |DocumentPart| replace:: :class:`.DocumentPart`

.. |docx| replace:: ``python-docx-oss``

.. |Emu| replace:: :class:`.Emu`

.. |False| replace:: :class:`False`

.. |float| replace:: :class:`.float`

.. |Font| replace:: :class:`.Font`

.. |_Footer| replace:: :class:`._Footer`

.. |FooterPart| replace:: :class:`.FooterPart`

.. |_Header| replace:: :class:`._Header`

.. |HeaderPart| replace:: :class:`.HeaderPart`

.. |ImageParts| replace:: :class:`.ImageParts`

.. |Inches| replace:: :class:`.Inches`

.. |InlineShape| replace:: :class:`.InlineShape`

.. |InlineShapes| replace:: :class:`.InlineShapes`

.. |InvalidSpanError| replace:: :class:`.InvalidSpanError`

.. |int| replace:: :class:`.int`

.. |_LatentStyle| replace:: :class:`._LatentStyle`

.. |LatentStyles| replace:: :class:`.LatentStyles`

.. |Length| replace:: :class:`.Length`

.. |None| replace:: :class:`.None`

.. |NumberingPart| replace:: :class:`.NumberingPart`

.. |_NumberingStyle| replace:: :class:`._NumberingStyle`

.. |OpcPackage| replace:: :class:`.OpcPackage`

.. |Paragraph| replace:: :class:`.Paragraph`

.. |ParagraphFormat| replace:: :class:`.ParagraphFormat`

.. |_ParagraphStyle| replace:: :class:`._ParagraphStyle`

.. |Part| replace:: :class:`.Part`

.. |Pt| replace:: :class:`.Pt`

.. |_Relationship| replace:: :class:`._Relationship`

.. |Relationships| replace:: :class:`._Relationships`

.. |RGBColor| replace:: :class:`.RGBColor`

.. |_Row| replace:: :class:`._Row`

.. |_Rows| replace:: :class:`._Rows`

.. |Run| replace:: :class:`.Run`

.. |Section| replace:: :class:`.Section`

.. |Sections| replace:: :class:`.Sections`

.. |Settings| replace:: :class:`.Settings`

.. |str| replace:: :class:`.str`

.. |Styles| replace:: :class:`.Styles`

.. |StylesPart| replace:: :class:`.StylesPart`

.. |Table| replace:: :class:`.Table`

.. |_TableStyle| replace:: :class:`._TableStyle`

.. |TabStop| replace:: :class:`.TabStop`

.. |TabStops| replace:: :class:`.TabStops`

.. |_Text| replace:: :class:`._Text`

.. |True| replace:: :class:`True`

.. |ValueError| replace:: :class:`ValueError`
"""

# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.intersphinx",
    "sphinx.ext.todo",
    "sphinx.ext.coverage",
    "sphinx.ext.viewcode",
]

# Add any paths that contain templates here, relative to this directory.
templates_path = ["_templates"]

# The root document.
root_doc = "index"

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store", ".build"]


# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
html_theme = "sphinx_book_theme"

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ["_static"]

# Custom sidebar templates, maps document names to template names.
html_sidebars = {
    "**": ["searchbox.html", "globaltoc.html", "sidebarlinks.html"],
}
