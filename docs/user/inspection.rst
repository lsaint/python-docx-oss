.. _package_inspection:

Inspecting packages and comparing content
================================================

``inspect()`` observes a DOCX before it can be opened as a ``Document``. It does
not repair or rewrite the input. Both inspection and fingerprinting accept a
filesystem path (including ``pathlib.Path``), raw bytes, or a binary stream::

    from docx import inspect

    report = inspect("input.docx")
    for finding in report.findings:
        print(finding.code, finding.partname, finding.target)

    if report.features.field_hyperlink or report.features.split_hyperlink_runs:
        print("Hyperlink shapes requiring application review were found")

The report consists of three immutable values:

* ``inventory.parts`` lists ZIP members, uncompressed sizes, Content-Types, and
  whether each member is reachable from package relationships.
* ``inventory.relationships`` lists source names, IDs, Type URIs, resolved
  internal targets, and external URIs. External targets are never fetched.
* ``findings`` identifies damaged or suspicious structures. ``features`` records
  Word story facts; it does not decide whether an application should normalize
  or reject a document.

Names are package-relative without a leading slash. The relationship source
``/`` denotes the package root. Internal target paths are resolved relative to
their source, with URI percent escapes decoded. Reachability does not imply
that a part is well-formed or safe to open.

Findings
--------

Use ``report.has_finding(code)`` or ``report.findings_by_code(code)`` rather than
matching human-readable exception messages. Findings carry the affected member
name when one is available, and missing-target findings carry ``target``.

.. list-table::
   :header-rows: 1
   :widths: 35 65

   * - Code
     - Meaning
   * - ``not_a_package``
     - An opened source cannot be read as a ZIP package.
   * - ``missing_content_types``
     - The package has no ``[Content_Types].xml`` member.
   * - ``missing_main_document``
     - No package-root officeDocument relationship resolves to an existing part.
   * - ``invalid_content_types``
     - The Content-Types member has an unexpected root element.
   * - ``invalid_relationships``
     - A relationship member has an unexpected root, missing required attributes,
       duplicate IDs, or an invalid target URI.
   * - ``empty_xml_part``
     - An XML member has zero bytes or contains only XML whitespace.
   * - ``unparseable_xml_part``
     - XML is malformed or uses a DTD, which this API rejects.
   * - ``missing_relationship_target``
     - An internal relationship points to an absent member.
   * - ``unreadable_part``
     - An XML member cannot be decompressed or fails its ZIP integrity check.
   * - ``duplicate_member``
     - The ZIP contains the same member name more than once; inventory uses the first.
   * - ``unsafe_member_name``
     - A ZIP member has an absolute name, backslash, or parent-directory component.

All recognizable XML parts are checked, including unreachable XML. A broken
relationship part does not prevent other parts from being inventoried. Findings
are observations, not a complete OPC/schema/security validation; an empty list
does not guarantee that ``Document()`` or Microsoft Word can open the input.
Invalid source argument types raise ``TypeError``. Source opening failures, such
as ``FileNotFoundError`` or ``PermissionError``, propagate to the caller rather
than being classified as package damage. This matches ``repair()`` and ``normalize()``.

Story scanning and resource use
--------------------------------------

``field_hyperlink`` detects a first instruction token of ``HYPERLINK``, including
simple fields (``w:fldSimple/@w:instr``) and complex field instructions split across
runs. Other commands containing the word, such as ``REF HYPERLINK_ref``, do not
match. ``split_hyperlink_runs`` detects ``w:hyperlink``
elements with more than one direct ``w:r`` child. The scanner covers the main
document and reachable header, footer, footnote, endnote, and comment story parts;
configuration XML such as styles and settings does not contribute features.
Transitional and Strict Word namespaces are supported.

Inspection reads XML incrementally without building an element tree. Media,
embedded objects, and other binary member payloads are never opened. Memory use
scales with package inventory and XML/field nesting depth, rather than story text or
media size. Metadata lists still scale with the number of parts and relationships.
Binary payload checksums are therefore not validated by inspection.

Seekable streams are read from the beginning, then restored to their original
position on success or failure. Caller-owned streams are never closed. A
forward-only stream is consumed and spooled, spilling to a temporary file beyond
1 MiB. Paths and temporary handles are closed internally.

Content fingerprints
--------------------

``fingerprint()`` computes a versioned SHA-256 package-content fingerprint::

    from docx import FingerprintPolicy, fingerprint

    unchanged = fingerprint(before_bytes) == fingerprint(after_bytes)

    policy = FingerprintPolicy(exclude_parts=("docProps/*",))
    unchanged_except_properties = (
        fingerprint(before_bytes, policy=policy)
        == fingerprint(after_bytes, policy=policy)
    )

Member ordering, compression, ZIP timestamps, directory entries, and other ZIP
metadata do not affect the fingerprint. Member names and contents do. XML uses
C14N 2.0 with comments, which normalizes attribute ordering, quote style, and
empty-element spelling. Text whitespace and namespace prefixes are preserved.
This is not a semantic Word comparison: equivalent rendering can produce
different fingerprints. Compare fingerprints with the same policy and API
algorithm version; the digest is not compatible with arbitrary existing hashes.

The default includes document properties, Custom XML, relationships, and binary
content. ``FingerprintPolicy`` can explicitly exclude:

* ``exclude_parts``: shell-style patterns against member names; ``*`` also
  matches ``/``;
* ``exclude_relationship_types``: complete relationship Type URIs;
* ``exclude_xml_tags``: expanded XML names, removing entire subtrees;
* ``exclude_xml_attributes``: expanded XML attribute names.

For example, ``exclude_xml_tags=("{namespace-uri}element",)`` applies to that
element throughout the package. Excluding a member does not automatically
exclude relationships or Content-Type declarations that reference it.
Relationship exclusions do not remove their target parts. Applications must
choose the complete policy appropriate to their comparison.

When XML canonicalization is enabled, ``[Content_Types].xml`` is always read for
XML classification, even if excluded from the digest. XML parts with nonstandard
extensions therefore retain the same comparison rules. A malformed or empty
Content-Types member raises a member-specific ``ValueError`` even when excluded.

Set ``canonicalize_xml=False`` to hash XML bytes exactly. XML exclusions cannot
be combined with that mode. Unlike ``inspect()``, fingerprinting raises on
unreadable packages or malformed included XML rather than returning a partial
digest. Duplicate member names are rejected. DTDs are rejected when XML is
canonicalized. Binary and XML contents are processed incrementally; the function
does not collect all member payloads in memory. Stream guarantees match
``inspect()``.
