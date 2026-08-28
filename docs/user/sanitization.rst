.. _sanitization:

Document sanitization
=====================

Sanitization removes selected package-level information before a document is
shared. Every operation is disabled by default because removal is destructive.

Use :meth:`Document.sanitize() <docx.document.Document.sanitize>` with explicit
options and inspect its report before saving::

    from docx import Document

    document = Document("input.docx")
    report = document.sanitize(
        personal_metadata=True,
        comments=True,
        web_extensions=True,
        formatting_revisions=True,
    )

    if report.changed:
        document.save("sanitized.docx")

The returned :class:`~docx.sanitize.SanitizationReport` identifies scrubbed
properties, removed XML markers, parts, and relationships, plus any warnings.
Each removed relationship is represented by
:class:`~docx.sanitize.RemovedRelationship`. Repeating the same sanitization is
idempotent: the second report has ``changed == False`` when nothing new was
added.

Options
-------

``personal_metadata``
    Clears author and last-modified-by values and canonicalizes the revision
    number. Duplicate property elements are removed.

``comments``
    Removes comment markers from all reachable Word XML story parts and removes
    the complete comments relationship tree, including modern comments extension
    parts when present.

``web_extensions``
    Removes web-extension task panes and their related package parts.

``formatting_revisions``
    Removes property-change history such as ``rPrChange`` and ``pPrChange`` while
    retaining the currently effective formatting.

Scope boundary
--------------

This API does not accept or reject tracked content revisions. It also does not
remove Custom XML, macros, OLE objects, external links, or application-specific
business metadata. Those operations require separate policy decisions.
