.. _package_transformations:

Repairing and normalizing packages
============================================

``repair()`` and ``normalize()`` perform explicit package edits. Every operation
is disabled by default. They accept the same path, bytes, and binary stream
inputs as :ref:`package_inspection`, and return a ``TransformationResult`` with
``content`` bytes and an immutable ``report``::

    from docx import normalize, repair

    repaired = repair(source_bytes, empty_custom_xml=True)
    if repaired.report.succeeded:
        normalized = normalize(
            repaired.content,
            hyperlink_fields=True,
            hyperlink_runs=True,
        )
        if normalized.report.succeeded:
            output_bytes = normalized.content

Inputs are never overwritten. Seekable streams are read from the beginning and
their positions restored; borrowed streams stay open. Forward-only streams are
consumed. Source access failures and invalid argument types raise because original
bytes cannot be obtained. Application selector exceptions also propagate.

Reports and transactional behavior
--------------------------------------------

The report exposes:

* ``before`` and ``after``: package inspection reports for the original and
  returned content;
* ``changes``: committed operations with member name, count, and, where relevant,
  relationship ID and target;
* ``skipped``: unsupported or unselected hyperlink operations, with member context;
* ``errors``: conditions that prevented the operation;
* ``succeeded``: whether the operation completed without errors;
* ``changed``: whether any changes were committed.

When all options are disabled, the original bytes are returned with an inspection
report, without attempting repair or document-open validation. Existing findings
remain visible in ``before``; ``succeeded`` does not imply those findings were fixed.

With an operation enabled, input inspection runs first. Unsupported damage blocks
the operation. A candidate is inspected again and opened as a ``Document``; its
main part must be a supported Word document with a body. On failure, the original
bytes are returned, ``errors`` explains why, and ``changes`` is empty. Thus
``after`` always describes the bytes actually returned. Successful operations may
still contain ``skipped`` entries; inspect those before assuming every hyperlink
was normalized.

This validates package relationships and library readability, not full OOXML
schema conformance or Microsoft Word rendering. Operations currently target the
Transitional Word namespace supported by ``Document()``.

Empty Custom XML repair
--------------------------------------------

``repair(source, empty_custom_xml=True)`` replaces empty Custom XML data with
``<root/>``. Eligibility requires both:

* all incoming internal relationships to the part are ``customXml``; and
* the Content-Type is generic ``application/xml`` or ``text/xml``.

Zero-byte and XML-whitespace-only parts qualify as empty. The original schema,
business tags, or lost data cannot be reconstructed: the replacement is a neutral
well-formed placeholder. The report records ``filled_empty_custom_xml`` for each
part. Relationships, Custom XML properties, and other package members are retained.

The API does not fill empty main documents, headers, Custom XML properties, or
unidentified orphan XML. Malformed nonempty XML and other inspection findings
cause the whole repair to fail, preserving the original bytes. Run normalization
separately after a successful repair. Repeating repair on its output is a byte
identical no-op.

Hyperlink normalization
--------------------------------------------

``hyperlink_fields=True`` converts supported ``HYPERLINK`` fields into standard
``w:hyperlink`` elements. It handles simple fields and paragraph-local complex
fields with separate begin, instruction, separator, result, and end runs. Field
instructions may span runs. Result runs retain their text and formatting.

Supported targets include quoted or unquoted addresses, bookmark-only links,
and address plus bookmark. Supported switches are ``\l`` (anchor), ``\o``
(tooltip), ``\t`` (target frame), and ``\* MERGEFORMAT``. Unknown switches,
locked or nested fields, revision markup, mixed delimiter/content runs, and
bookmark or comment range boundaries are left unchanged and reported. Other
field types, such as TOC and REF, are untouched.

Quoted field arguments decode escaped backslashes and escaped double quotes.
Unknown or malformed escapes, unclosed strings, and doubled-quote notation are
preserved and reported as skipped rather than converted into potentially wrong targets.

External hyperlink relationships are reused when possible. New IDs avoid existing
IDs in that story part. Missing relationship members and their Content-Type
declarations are added when needed. Main document, headers, footers, footnotes,
endnotes, and comments are processed through their reachable story relationships.

``hyperlink_runs=True`` merges adjacent text-only runs inside a hyperlink only
when explicit run properties and attributes other than ``w:rsidR`` and
``w:rsidRPr`` match. The surviving run retains its original session identifiers;
per-run session provenance is coalesced. Text and spaces are preserved.
Different formatting, other attributes (including ``w:rsidDel``), drawings,
tabs, breaks, revision containers,
and intervening markup prevent merging across that boundary. Safe adjacent groups
can still be merged while unsupported groups are reported as skipped.

Application-owned selection
--------------------------------------------

The optional ``select_hyperlink`` callback receives an immutable
``HyperlinkTarget(partname, address, anchor)``. Return ``True`` to select a
supported field conversion or existing-link run merge::

    def select_link(target):
        return target.address is not None and target.address.startswith(
            "https://example.test/documents/"
        )

    result = normalize(
        source_bytes,
        hyperlink_fields=True,
        hyperlink_runs=True,
        select_hyperlink=select_link,
    )

Without a callback all supported hyperlinks are selected. The SDK contains no
application URL or tag rules. For existing hyperlinks ``address`` comes from the
story relationship target; bookmark-only links have ``address=None``. The callback
must be deterministic: it may be called for conversion and then again for merging
the resulting link. Returning ``False`` is reported as skipped.

Preservation and resource use
--------------------------------------------

Only edited XML members are serialized. Other member contents, including opaque
media, embedded objects, macros, unknown XML, and unreachable parts, are copied
unchanged. ZIP member metadata and archive comments are retained where supported
by Python's ZIP writer; compressed bytes and ZIP offsets may change. The package
is not saved through ``Document`` during transformation.

These editing APIs retain input and output bytes, build a tree for the story
currently being edited, and open the result for validation. They do not have the
streaming memory profile of ``inspect()``. No-op results retain the original bytes
exactly. Repeated normalization with the same deterministic selection is a byte
identical no-op once supported changes have been applied.
