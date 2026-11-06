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

[Documentation](https://python-docx-oss.readthedocs.io/en/latest/) · [API Reference](docs/index.rst#api-documentation) · [Release History](HISTORY.md)

## Capability Matrix

| Capability | Primary API / Behavior |
| --- | --- |
| **Major additions** | |
| [Custom document properties](docs/user/custom-properties.rst) | `document.custom_properties` |
| [Custom XML lifecycle](docs/user/custom-xml.rst) | `add_custom_xml_part()`, `delete_custom_xml_part()` |
| [SVG and EMF images](docs/user/shapes.rst) | `add_picture()` |
| [Floating pictures](docs/user/shapes.rst) | `add_float_picture()` |
| [Latin and East Asian font controls](docs/user/text.rst) | `run.font.name`, `run.font.hAnsi`, `run.font.eastAsia` |
| [Low-level OPC parts and relationships](docs/user/api-concepts.rst) | `document.part.package`, `part.rels` |
| [In-memory read, export, and independent copies](docs/user/documents.rst) | `Document(bytes)`, `to_bytes()`, `copy()` |
| [Document sanitization](docs/user/sanitization.rst) | `document.sanitize()` |
| [Read-only package inspection and streaming feature scanning](docs/user/inspection.rst) | `inspect()`, `ScanEvent` |
| [Configurable package-content fingerprints](docs/user/inspection.rst#content-fingerprints) | `fingerprint()`, `FingerprintPolicy`, `serialize_xml` |
| [Explicit empty Custom XML repair and hyperlink normalization](docs/user/transformations.rst) | `repair()`, `normalize()` |
| **Major fixes and compatibility** | |
| [Strict Open XML compatibility](HISTORY.md#release-history) | Open Strict documents through `Document()` with transparent package normalization |
| [Table width and logical layout compatibility](HISTORY.md#release-history) | Read measurement and percentage widths, logical indentation, and `start` / `end` alignment |
| [lxml text extraction](docs/user/compatibility.rst#preservation-of-lxml-element-text-and-itertext-semantics) | Prevent duplicate `itertext()` output; preserve public `.text` APIs |

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

## Quick Start

Prepare a sharing copy with custom metadata, East Asian fonts, and a content fingerprint:

```python
from docx import Document, fingerprint

internal = Document("internal-report.docx")
public = internal.copy()  # Keep the original unchanged.

public.custom_properties["distribution"] = "public"  # Set document metadata.
public.part.add_custom_xml_part('<report xmlns="urn:example:reports" id="Q4"/>')
public.add_paragraph().add_run("中文内容").font.eastAsia = "Microsoft YaHei"

public.sanitize(personal_metadata=True, comments=True)  # Remove private info.
content = public.to_bytes()  # Export without temporary files.
digest = fingerprint(content)  # Compute a normalized package-content fingerprint.
```

## Compatibility and Scope

- The project maintains broad compatibility with the public `python-docx` API while
  following its own versioning and product roadmap.
- Compatibility does not extend to every private or internal `python-docx` API. Test
  those integrations before migrating production systems.
- The SDK focuses exclusively on DOCX. It is not a general XLSX/PPTX Office suite.
- It edits document structure but does not implement Word's page-layout rendering
  engine.
- CLI, MCP, web, desktop, and Agent runtimes belong in separate packages that consume
  this SDK.

## Why “OSS”?

In Brazilian jiu-jitsu, “oss” is a greeting and an expression of respect. It reflects
the same spirit of discipline and collaboration behind this project.

## Support

If this project is useful to you, you can support its continued development through
the [donation page](https://lsaint.github.io/donation/?utm_source=github&utm_medium=readme&utm_campaign=python-docx-oss).
