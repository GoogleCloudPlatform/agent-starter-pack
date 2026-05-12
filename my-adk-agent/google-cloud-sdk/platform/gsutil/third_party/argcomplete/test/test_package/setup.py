from setuptools import setup

setup(
    name="test-package",
    version="0",
    py_modules=["test_module"],
    packages=["test_package"],
    entry_points={
        "console_scripts": [
            "test-module=test_module:main",
            "test-package=test_package:main",
        ]
    },
)
