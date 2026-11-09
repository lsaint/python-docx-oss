BEHAVE = behave
MAKE   = make
PYTHON = python
VERSION := $(shell sed -n 's/^__version__ = "\(.*\)"/\1/p' src/docx/__init__.py)
SDIST  = dist/python_docx_oss-$(VERSION).tar.gz
WHEEL  = dist/python_docx_oss-$(VERSION)-py3-none-any.whl

.PHONY: accept build clean cleandocs coverage docs install opendocs sdist test wheel

help:
	@echo "Please use \`make <target>' where <target> is one or more of"
	@echo "  accept       run acceptance tests using behave"
	@echo "  build        generate both sdist and wheel suitable for upload to PyPI"
	@echo "  clean        delete intermediate work product and start fresh"
	@echo "  cleandocs    delete intermediate documentation files"
	@echo "  coverage     run pytest with coverage"
	@echo "  docs         generate documentation"
	@echo "  opendocs     open browser to local version of documentation"
	@echo "  sdist        generate a source distribution into dist/"
	@echo "  test         run unit tests using pytest"
	@echo "  wheel        generate a binary distribution into dist/"

accept:
	uv run $(BEHAVE) --stop

build:
	uv build

clean:
	# find . -type f -name \*.pyc -exec rm {} \;
	fd -e pyc -I -x rm
	rm -rf dist *.egg-info .coverage .DS_Store

cleandocs:
	$(MAKE) -C docs clean

coverage:
	uv run pytest --cov-report term-missing --cov=docx tests/

docs:
	$(MAKE) -C docs html SPHINXBUILD="uv run sphinx-build"

install:
	pip install -Ue .

opendocs:
	open docs/.build/html/index.html

sdist:
	uv build --sdist

test:
	uv run pytest -x

wheel:
	uv build --wheel
