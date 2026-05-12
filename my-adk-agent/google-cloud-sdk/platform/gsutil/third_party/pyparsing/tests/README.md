## Development
     
After forking the pyparsing repo, and cloning your fork locally, install the libraries needed to run tests

    pip install -Ur tests/requirements.txt
    pre-commit install
         
Run the simple unit tests to ensure your environment is setup 
     
    python tests/test_simple_unit.py

Use `tox` to run the full test suite on all supported Python versions

    # run a specific test environment
    tox -e py312

    # run all test environments
    tox

    # run all test environments in parallel
    tox -p

To run `mypy` standalone

    tox -e mypy-check
