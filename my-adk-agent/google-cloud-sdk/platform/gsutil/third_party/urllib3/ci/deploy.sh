#!/bin/bash

set -exo pipefail

python3 -m pip install --upgrade twine wheel build
python3 -m build
python3 -m twine upload dist/* -u $PYPI_USERNAME -p $PYPI_PASSWORD --skip-existing
