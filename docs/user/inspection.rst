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

The report contains an immutable package inventory and structured findings.

To search Word story XML, provide a predicate that receives read-only events::

    def find_bookmark(event):
        return event.kind == "start" and event.tag.endswith("}bookmarkStart")

    report = inspect("input.docx", predicate=find_bookmark, stop_on_match=True)
    if report.findings:
        print("The scanned package is damaged")
    elif report.matched:
        print("Bookmark found")

A predicate selects query scope: the main document and reachable headers,
footers, footnotes, endnotes, and comments. Query reports have empty inventory
and ``scope == "query"``. Without a predicate, inspection retains full scope
and inventory. The predicate runs on immutable ``ScanEvent`` objects with
``partname``, ``kind`` (start/end/text), expanded ``tag``, ``attributes`` on
start events, and ``text`` on text events. Text may be delivered in multiple
chunks. A stateful callable may track element nesting and split text.

The default scans the full query scope even after a match; ``stop_on_match=True``
stops at the first match and sets ``scan_complete=False``. Findings report only
scanned content; neither an early match nor a query with no findings proves the
whole package is valid. Predicate exceptions propagate. The source stream is
never handed to the predicate.

``scan_complete`` describes whether the selected scope was scanned successfully,
not whether the package is clean. Findings such as a missing relationship target
can coexist with a complete scan. Empty XML parts cannot be parsed as XML and,
like unreadable or unparseable parts, make the scan incomplete. Early stops also
make the scan incomplete. A query is incomplete if a reachable story is missing.

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

The query scans all reachable Word story parts, including Transitional and Strict
Word namespaces. No built-in hyperlink-specific feature is assumed.

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
empty-element spelling. By default, whitespace-only text directly inside known
element-only Word, DrawingML, MCE, and WordprocessingShape structures is ignored.
This includes whitespace between extension children of a known structure. Text
elements, unknown or unverified extension elements, generic Custom XML parts, and
elements under ``xml:space="preserve"`` retain whitespace. An explicit
``xml:space="default"`` resets inherited preservation. Elements with an
``xsi:type`` override are preserved conservatively. Set ``ignore_structural_whitespace=False`` on the policy
to retain structural whitespace. Namespace prefixes and declarations are preserved,
including declarations referenced only from attribute values. This rule applies
only to parts declared with a known WordprocessingML or DrawingML theme content
type, and to specific structural elements within them. The generated name list
comes from ECMA-376 fifth-edition Transitional and Strict schemas, ECMA-376 Part 3
MCE structures, and Microsoft's MS-ODRAWXML WordprocessingShape schema. It excludes
ambiguous element names, VML, and unverified extensions. The document is not schema
validated; this rule assumes the known elements follow their element-only or empty
content model. Use ``normalize`` for broader application-specific comparison.
Raw XML hashing with
``canonicalize_xml=False`` always preserves the original bytes.
This is not a semantic Word comparison: equivalent rendering can produce
different fingerprints. Compare fingerprints with the same policy and API
algorithm version; the digest is not compatible with arbitrary existing hashes.
The expanded structural-whitespace rules use fingerprint algorithm version 3, so
digest strings differ from earlier versions even when whitespace handling is disabled.

The optional ``normalize`` callback can replace the bytes hashed for a part::

    from docx import FingerprintItem, FingerprintPolicy, serialize_xml
    from lxml import etree

    def normalize(item: FingerprintItem, read_bytes):
        if not item.part_name.endswith(".xml"):
            return "raw"
        content = read_bytes()
        try:
            return serialize_xml(content, part_name=item.part_name)
        except etree.XMLSyntaxError:
            return content

    policy = FingerprintPolicy(normalize=normalize)

The callback receives a part item and an on-demand reader. Return bytes to hash
those bytes directly, ``"raw"`` to hash the original part incrementally, or
``None`` to use the default processing. ``read_bytes()`` returns the original
bytes, can be called repeatedly, and materializes that part in memory only when
called. Errors propagate. The callback must produce deterministic results.
Part exclusions run first. For bytes or raw results, the callback is responsible
for any element-level exclusions; default XML canonicalization and element
exclusion callbacks are bypassed. When every included part is handled by the
callback, Content Types need not be read for classification. Otherwise the
Content Types member is still read to classify parts using default processing.

``serialize_xml()`` is a tree-based helper: it removes blank text using lxml,
optionally excludes XML elements with the same predicate as ``exclude``, and
returns serialized bytes. It preserves attribute order, requires memory
proportional to the XML part, and preserves text following an excluded element
that remains after lxml's blank-text removal.
Its blank-text treatment is broader
than the default structural-whitespace rule; use it only when appropriate.

The default includes document properties, Custom XML, relationships, and binary
content. ``FingerprintPolicy`` can explicitly exclude:

* ``exclude_parts``: shell-style patterns against member names; ``*`` also
  matches ``/``;
* ``exclude_relationship_types``: complete relationship Type URIs;
* ``exclude_xml_tags``: expanded XML names, removing entire subtrees;
* ``exclude_xml_attributes``: expanded XML attribute names.
* ``exclude``: a predicate for package parts and XML elements.

The predicate receives a read-only ``FingerprintItem``. Its ``kind`` is ``part``
or ``xml_element``; ``part_name`` is the package-relative member name. XML
elements also expose expanded-name ``tag`` and ``attributes``, ``ancestors``
(root first), and ``parent_tag`` (or ``None`` for a root). For example::

    from docx import FingerprintItem, FingerprintPolicy

    def exclude(item: FingerprintItem) -> bool:
        if item.kind == "part":
            return item.part_name.startswith("docProps/")
        return item.tag == "{urn:example}color" and item.parent_tag == "{urn:example}properties"

    policy = FingerprintPolicy(exclude=exclude)

Returning true excludes the part or the element and its entire subtree; excluded
subtrees are not visited. Exclusions combine with the other policy settings: any
matching rule excludes the item. XML element callbacks run only when XML
canonicalization is enabled. Part callbacks run even with raw XML hashing.
Content Types are read for default XML classification even when excluded. The
predicate must be deterministic and equivalent for both fingerprints being
compared; its exceptions propagate to the caller.

For example, ``exclude_xml_tags=("{namespace-uri}element",)`` applies to that
element throughout the package. Excluding a member does not automatically
exclude relationships or Content-Type declarations that reference it.
Relationship exclusions do not remove their target parts. Applications must
choose the complete policy appropriate to their comparison.

When default XML processing is used, ``[Content_Types].xml`` is read for
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
