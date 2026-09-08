python-docx compatibility
=========================

``python-docx-oss`` and the official ``python-docx`` project share the
``docx`` import namespace and a common code lineage. They are separate Python
distributions with independent versions and release schedules.

Compatibility target
--------------------

The current upstream baseline is ``python-docx v1.2.0`` at commit
``e45454602b53e8e572b179ccf1c91093ec9f4ed7``.

Public APIs inherited from that baseline are compatibility targets unless an
intentional difference is documented. Compatibility with private modules,
private attributes, undocumented XML internals, or implementation details is
not guaranteed.

Extensions provided by ``python-docx-oss`` are additive where practical. The
project's current supported and planned features are maintained in the
Capability Matrix rather than duplicated here.

Distribution boundary
---------------------

Do not install ``python-docx`` and ``python-docx-oss`` into the same Python
environment. Both distributions provide the ``docx`` package, so installing
both can produce an environment whose imported files depend on installation
order.

Applications should declare exactly one of the two distributions as a direct
dependency. Migrating an existing application normally does not require import
changes, but its use of undocumented upstream internals must be reviewed.

Intentional differences
-----------------------

An intentional difference is recorded when ``python-docx-oss`` changes a
public inherited API or its observable behavior. Each record must identify:

* the affected public API;
* the behavior of the recorded upstream baseline;
* the ``python-docx-oss`` behavior and rationale; and
* any migration action required by callers.

Preservation of lxml ``_Element.text`` and ``itertext()`` semantics
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

* **Affected API**: Low-level OXML element classes (``CT_P``, ``CT_R``, ``CT_Hyperlink`` in ``docx.oxml``) and observable ``element.itertext()`` / ``element.text`` behavior on XML elements.
* **Upstream baseline (v1.2.0)**: Upstream defined ``@property def text`` on ``CT_P``, ``CT_R``, and ``CT_Hyperlink`` to return concatenated run/paragraph text. Overriding the Cython descriptor ``_Element.text`` on ``ElementBase`` subclasses causes standard ``lxml`` C-level tree iteration (``itertext()``) to invoke the Python property. As a consequence, calling ``itertext()`` on parent elements or on bare ``lxml.etree._Element`` nodes (such as revision tags ``w:ins``, ``w:del``, or container tags like ``w:txbxContent``) visits both the container node and child ``<w:t>`` nodes, causing text to be duplicated (e.g., ``"Beta"`` becomes ``"BetaBeta"``).
* **python-docx-oss behavior and rationale**: ``python-docx-oss`` intentionally does not override the ``.text`` property on any ``BaseOxmlElement`` subclass. Rich-text extraction and assignment at the OXML element level is named ``.texts`` (e.g., ``_r.texts``, ``_p.texts``, ``_hyperlink.texts``). Public proxy classes (|Paragraph|, |Run|, |Hyperlink|, and |_Cell|) continue to expose their standard ``.text`` property, delegating internally to ``.texts``. This design preserves standard ``lxml`` descriptor semantics, ensuring that ``itertext()`` produces clean, single-occurrence text across all XML elements.
* **Migration action**: Callers using public proxy objects (such as ``paragraph.text`` or ``run.text``) require no changes. Callers interacting directly with low-level OXML element instances (e.g., ``run._r``) should use ``.texts`` instead of ``.text`` for rich-text assembly, or standard ``lxml`` methods like ``element.itertext()``.

Additive APIs and capabilities do not require individual divergence records;
they belong in the API documentation and Capability Matrix. Upstream baseline
changes follow the :doc:`../dev/upstream-maintenance` policy.
