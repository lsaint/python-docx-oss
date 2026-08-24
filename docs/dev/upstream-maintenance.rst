Upstream maintenance
====================

``python-docx-oss`` evolves as an independent DOCX SDK. Its source, tests,
versioning, and releases are authoritative in this repository. The official
`python-docx repository <https://github.com/python-openxml/python-docx>`_ is an
upstream source of compatible APIs, bug fixes, and OPC/WordprocessingML
improvements; it is not the development repository for ``python-docx-oss``.

Upstream baseline
-----------------

The current upstream baseline is ``python-docx v1.2.0`` at commit
``e45454602b53e8e572b179ccf1c91093ec9f4ed7``.

This baseline identifies the last official release whose changes have been
evaluated as a whole. It does not imply compatibility with every private or
internal upstream API.

No local repository layout is required. A maintainer may obtain upstream source
using a temporary clone, a read-only Git remote, a release archive, or another
equivalent method. Maintenance instructions and project documentation must not
depend on sibling directories, personal filesystem paths, or local-only
branches.

When to evaluate upstream
-------------------------

Evaluate upstream changes when:

* ``python-docx`` publishes a release;
* upstream fixes a security, data-loss, or document-compatibility issue;
* a supported downstream workflow needs a new standard API; or
* an upcoming ``python-docx-oss`` release needs a baseline refresh.

Continuous synchronization with individual upstream commits is not required.

Integration workflow
--------------------

#. Obtain the target upstream tag or commit and compare it with the recorded
   baseline.
#. Review release notes and classify changes to public APIs, OPC packaging,
   XML handling, templates, schemas, tests, and documentation.
#. Create a dedicated branch in ``python-docx-oss`` for the integration. The
   branch name and the location used to obtain upstream source are not part of
   the public maintenance contract.
#. Integrate the relevant changes as a reviewable change set. Preserve upstream
   history when practical, but prefer a clear, auditable result over a blind
   merge.
#. Resolve conflicts according to the compatibility rules below.
#. Run the full verification gates and review the package artifacts.
#. Update this baseline, compatibility notes, and ``HISTORY.md`` in the same
   integration change.

Compatibility and conflict rules
--------------------------------

Standard public ``python-docx`` behavior is preferred unless adopting it would
break an API intentionally supported by ``python-docx-oss``. An upstream
integration must preserve the supported capabilities documented in the
Capability Matrix and covered by the regression test suite.

Compatibility with upstream private APIs is not guaranteed. Intentional public
API differences must be recorded in compatibility or divergence notes rather
than hidden in conflict-resolution commits.

Verification gates
------------------

An upstream integration is complete only when the repository CI passes. This
includes:

* unit, integration, and acceptance tests on all supported Python versions;
* lint, formatting, and scoped type checks;
* documentation and distribution builds; and
* real-DOCX round trips required by the Capability Matrix and regression test
  suite.

The resulting wheel and source distribution must contain the expected package
data and install without also installing the official ``python-docx``
distribution, because both projects provide the ``docx`` import namespace.

Recording the result
--------------------

For each completed baseline refresh, record:

* the upstream tag and resolved commit;
* the material APIs and fixes adopted;
* intentionally omitted upstream changes and their rationale; and
* any new compatibility boundary visible to users.

Temporary comparison checkouts, remotes, and branches are local implementation
details and are not part of the permanent project record.
