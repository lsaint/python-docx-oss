<p align="center">
  <img src="https://raw.githubusercontent.com/lsaint/python-docx-oss/master/docs/_static/img/oss.png" width="400" alt="python-docx-oss"/>
</p>

<p align="center">
  <strong>A Python SDK for advanced creation and manipulation of Microsoft Word <code>.docx</code> files.</strong>
</p>

<p align="center">
  <a href="https://pypi.org/project/python-docx-oss/"><img alt="PyPI" src="https://img.shields.io/pypi/v/python-docx-oss"></a>
  <a href="https://pypi.org/project/python-docx-oss/"><img alt="Python versions" src="https://img.shields.io/pypi/pyversions/python-docx-oss.svg"></a>
  <a href="https://github.com/astral-sh/ruff"><img alt="Code style: Ruff" src="https://img.shields.io/badge/code%20style-ruff-FF6B6B.svg?logo=ruff&logoColor=white"></a>
  <a href="https://github.com/lsaint/python-docx-oss/blob/master/LICENSE"><img alt="License: MIT" src="https://img.shields.io/badge/License-MIT-yellow.svg"></a>
</p>

## Overview

`python-docx-oss` is an independently evolving DOCX SDK built on the proven API
foundation of [`python-docx`](https://github.com/python-openxml/python-docx). It keeps
the familiar `docx` programming model while extending it for advanced OOXML and Open
Packaging Convention (OPC) workflows.

Use it when an application needs more than basic paragraphs and tables: custom document
metadata, application-owned XML, vector images, floating pictures, East Asian fonts,
package inspection, configurable fingerprints, repair, or low-level package and relationship access.

## Capability Matrix

| Capability | Status | Primary API |
| --- | --- | --- |
| [Documents, paragraphs, tables, styles, sections, headers, and footers](docs/user/quickstart.rst) | Stable | `Document()` and document object APIs |
| [Custom document properties](docs/user/custom-properties.rst) | Stable | `document.custom_properties` |
| [Custom XML lifecycle](docs/user/custom-xml.rst) | Stable | `add_custom_xml_part()`, `delete_custom_xml_part()` |
| [SVG and EMF images](docs/user/shapes.rst) | Stable | `add_picture()` |
| [Inline and floating pictures](docs/user/shapes.rst) | Stable | `add_picture()`, `add_float_picture()` |
| [Latin and East Asian font controls](docs/user/text.rst) | Stable | `run.font.name`, `run.font.hAnsi`, `run.font.eastAsia` |
| [Low-level OPC parts and relationships](docs/user/api-concepts.rst) | Stable | `document.part.package`, `part.rels` |
| [In-memory read, export, and independent copies](docs/user/documents.rst) | Stable | `Document()`, `to_bytes()`, `copy()` |
| [Document sanitization](docs/user/sanitization.rst) | Stable | `document.sanitize()` |
| [Read-only package inspection and streaming feature scanning](docs/user/inspection.rst) | Stable | `inspect()`, `ScanEvent` |
| [Configurable package-content fingerprints](docs/user/inspection.rst#content-fingerprints) | Stable | `fingerprint()`, `FingerprintPolicy`, `serialize_xml` |
| [Explicit empty Custom XML repair and hyperlink normalization](docs/user/transformations.rst) | Stable | `repair()`, `normalize()` |
| Package and semantic diff | Planned | — |

## Installation

```bash
python -m pip install python-docx-oss
```

The distribution name is `python-docx-oss`, but the Python import namespace remains
`docx`:

```python
from docx import Document
```

> [!WARNING]
> `python-docx` and `python-docx-oss` provide the same `docx` import namespace. Do not
> install both distributions in the same Python environment.

`python-docx-oss` currently supports Python 3.12, 3.13, and 3.14.

## Quick Start

Create a document entirely in memory:

```python
from io import BytesIO

from docx import Document

document = Document()
document.add_heading("Quarterly Report", level=1)
document.add_paragraph("Generated entirely in memory.")

output = BytesIO()
document.save(output)

docx_bytes = output.getvalue()
```

The same APIs also accept filesystem paths:

```python
document = Document("input.docx")
document.add_paragraph("Appended by python-docx-oss.")
document.save("output.docx")
```

## Advanced Capabilities

### Package inspection and fingerprints

Inspect damaged documents before opening them, and compute reproducible content fingerprints
without loading media payloads:

```python
from docx import FingerprintPolicy, fingerprint, inspect

report = inspect("input.docx")
for finding in report.findings:
    print(finding.code, finding.partname)

digest = fingerprint("input.docx", policy=FingerprintPolicy(exclude_parts=("docProps/*",)))
```

These APIs leave inputs unchanged and restore seekable stream positions without loading
media payloads. `inspect()` supports structural inventory, damage detection, and streaming
story XML queries with caller-defined predicates. `fingerprint()` normalizes structural
indentation (C14N 2.0 / fingerprint v3) and supports selective exclusions. See
[Package inspection and fingerprints](docs/user/inspection.rst) for finding codes, streaming
queries, and policy rules.

### Explicit repair and normalization

```python
from docx import normalize, repair

repaired = repair(source_bytes, empty_custom_xml=True)
if repaired.report.succeeded:
    normalized = normalize(repaired.content, hyperlink_fields=True, hyperlink_runs=True)
    if normalized.report.succeeded:
        output_bytes = normalized.content
```

Operations are disabled by default and transactional: validation failures return the
original bytes. Hyperlink normalization converts field codes into native `w:hyperlink`
elements while preserving text box boundaries and proofing markers. See
[Repair and normalization](docs/user/transformations.rst) for supported structures,
selection callbacks, and preservation rules.

### Custom properties

```python
document = Document()
document.custom_properties["workflow_status"] = "approved"
document.custom_properties["revision"] = 3
```

Custom properties are visible in Microsoft Word and stored in
`/docProps/custom.xml`. See [Working with custom
properties](docs/user/custom-properties.rst).

### Custom XML

```python
custom_xml = document.part.add_custom_xml_part(
    '<order xmlns="urn:example:orders" id="A-001"/>',
)
custom_xml.add_item("status", "ready")
```

See [Working with Custom XML](docs/user/custom-xml.rst) for lifecycle and compatibility
considerations.

### East Asian fonts

```python
run = document.add_paragraph().add_run("English 与中文")
run.font.name = "Open Sans"
run.font.eastAsia = "Microsoft YaHei"
```

SVG and EMF streams can be passed to the standard picture APIs. Floating pictures are
available through `Document.add_float_picture()` and `Run.add_float_picture()`.

## Compatibility and Scope

- The project maintains broad compatibility with the public `python-docx` API while
  following its own versioning and product roadmap.
- Clean lxml integration: Low-level OXML elements avoid shadowing lxml's Cython
  `_Element.text` descriptor (using `.texts` internally). This guarantees that standard
  `element.itertext()` on parent elements and untyped revision nodes (`w:ins`, `w:del`,
  `w:txbxContent`) never duplicates text, while high-level proxy APIs (`paragraph.text`,
  `run.text`) remain fully compatible with `python-docx`.
- Compatibility does not extend to every private or internal `python-docx` API. Test
  those integrations before migrating production systems.
- The SDK focuses exclusively on DOCX. It is not a general XLSX/PPTX Office suite.
- It edits document structure but does not implement Word's page-layout rendering
  engine.
- CLI, MCP, web, desktop, and Agent runtimes belong in separate packages that consume
  this SDK.

## Documentation

- [Documentation site](https://python-docx-oss.readthedocs.io/en/latest/)
- [Installation guide](docs/user/install.rst)
- [Quickstart](docs/user/quickstart.rst)
- [User guide](docs/index.rst)
- [API reference](docs/index.rst#api-documentation)
- [Custom properties](docs/user/custom-properties.rst)
- [Custom XML](docs/user/custom-xml.rst)
- [Package inspection and fingerprints](docs/user/inspection.rst)
- [Package repair and normalization](docs/user/transformations.rst)
- [Package sanitization](docs/user/sanitization.rst)
- [python-docx compatibility](docs/user/compatibility.rst)
- [Upstream maintenance](docs/dev/upstream-maintenance.rst)
- [Release history](HISTORY.md)

## Quality and Testing

The test suite combines unit and acceptance coverage with in-memory round-trip tests
using documents created by Microsoft Word. The integration fixtures cover floating
pictures, SVG fallback relationships, East Asian fonts, Custom XML parts, and core OPC
package preservation.

For local development:

```bash
uv sync
uv run pytest
uv run behave
uv run ruff check tests/integration tests/fixtures/customxml/generate_fixture.py
uv run pyright tests/integration tests/fixtures/customxml/generate_fixture.py
```

## Project Status

With version 0.5.0, the independent SDK baseline, in-memory workflows, package
sanitization, streaming inspection, content fingerprinting (v3), and explicit package
repairs are stabilized. Upcoming milestones focus on package and semantic diffing,
composition, and schema-guided validation.

## Credits

This project builds on the original work of
[`python-docx`](https://github.com/python-openxml/python-docx) creator Steve Canny and
its contributors. `python-docx-oss` is maintained by Ethan St Lee and its contributors.

## Why “OSS”?

In Brazilian jiu-jitsu, “oss” is a greeting and an expression of respect. It reflects
the same spirit of discipline and collaboration behind this project.

## License

`python-docx-oss` is released under the [MIT License](LICENSE).

## Support

If this project is useful to you, you can support its continued development through
the [donation page](https://lsaint.github.io/donation/?utm_source=github&utm_medium=readme&utm_campaign=python-docx-oss).
