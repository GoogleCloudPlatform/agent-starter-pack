from __future__ import annotations

import os
from typing import Any

from setuptools import build_meta as _orig  # type: ignore[import-not-found]

USE_MYPYC = os.getenv("CHARSET_NORMALIZER_USE_MYPYC", "0") == "1"
MYPYC_SPEC = "mypy>=1.4.1,<=1.17.1"

# Expose all the PEP 517 hooks from setuptools
get_requires_for_build_sdist = _orig.get_requires_for_build_sdist
prepare_metadata_for_build_wheel = _orig.prepare_metadata_for_build_wheel
build_wheel = _orig.build_wheel
build_sdist = _orig.build_sdist

if hasattr(_orig, "get_requires_for_build_editable"):
    get_requires_for_build_editable = _orig.get_requires_for_build_editable
if hasattr(_orig, "prepare_metadata_for_build_editable"):
    prepare_metadata_for_build_editable = _orig.prepare_metadata_for_build_editable
if hasattr(_orig, "build_editable"):
    build_editable = _orig.build_editable


# Override the build requirements function to conditionally add Cython
def get_requires_for_build_wheel(
    config_settings: dict[str, Any] | None = None,
) -> list[str]:
    """Get the build requirements, conditionally adding Mypy(C)."""
    requires = _orig.get_requires_for_build_wheel(config_settings)
    if USE_MYPYC and MYPYC_SPEC not in requires:
        requires = list(requires) if requires else []
        requires.append(MYPYC_SPEC)
    return requires  # type: ignore[no-any-return]
