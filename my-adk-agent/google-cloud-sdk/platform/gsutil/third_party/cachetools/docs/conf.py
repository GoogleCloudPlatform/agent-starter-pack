import pathlib
import sys

src_directory = (pathlib.Path(__file__).parent.parent / "src").resolve()
sys.path.insert(0, str(src_directory))


# Extract the current version from the source.
def get_version():
    """Get the version and release from the source code."""

    text = (src_directory / "cachetools/__init__.py").read_text()
    for line in text.splitlines():
        if not line.strip().startswith("__version__"):
            continue
        full_version = line.partition("=")[2].strip().strip("\"'")
        partial_version = ".".join(full_version.split(".")[:2])
        return full_version, partial_version


project = "cachetools"
copyright = "2014-2025 Thomas Kemmer"
release, version = get_version()

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.coverage",
    "sphinx.ext.doctest",
    "sphinx.ext.intersphinx",
    "sphinx.ext.todo",
]
exclude_patterns = ["_build"]
master_doc = "index"
html_theme = "classic"
intersphinx_mapping = {"python": ("https://docs.python.org/3", None)}
