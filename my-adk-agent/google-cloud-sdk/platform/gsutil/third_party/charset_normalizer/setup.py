#!/usr/bin/env python
from __future__ import annotations

import os

from setuptools import setup

USE_MYPYC = False

if os.getenv("CHARSET_NORMALIZER_USE_MYPYC", None) == "1":
    USE_MYPYC = True

try:
    from mypyc.build import mypycify
except ImportError:
    mypycify = None  # type: ignore[assignment]

if USE_MYPYC and mypycify is not None:
    MYPYC_MODULES = mypycify(
        [
            "src/charset_normalizer/md.py",
        ],
        debug_level="0",
        opt_level="3",
    )
else:
    MYPYC_MODULES = None

setup(name="charset-normalizer", ext_modules=MYPYC_MODULES)
