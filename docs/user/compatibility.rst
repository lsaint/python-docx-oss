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

Additive APIs and capabilities do not require individual divergence records;
they belong in the API documentation and Capability Matrix. Upstream baseline
changes follow the :doc:`../dev/upstream-maintenance` policy.
