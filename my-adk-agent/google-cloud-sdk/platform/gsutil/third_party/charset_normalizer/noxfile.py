from __future__ import annotations

import os
import shutil

import nox


def test_impl(
    session: nox.Session,
    use_mypyc: bool = False,
):
    # Install deps and the package itself.
    session.install("-U", "pip", "setuptools", silent=False)
    session.install("-r", "dev-requirements.txt", silent=False)

    session.install(
        ".",
        silent=False,
        env={"CHARSET_NORMALIZER_USE_MYPYC": "1" if use_mypyc else "0"},
    )

    # Show the pip version.
    session.run("pip", "--version")
    # Print the Python version and bytesize.
    session.run("python", "--version")
    # Show charset-normalizer cli info
    session.run("normalizer", "--version")

    # Inspired from https://hynek.me/articles/ditch-codecov-python/
    # We use parallel mode and then combine in a later CI step
    session.run(
        "python",
        "-m",
        "coverage",
        "run",
        "--parallel-mode",
        "-m",
        "pytest",
        "-v",
        "-ra",
        f"--color={'yes' if 'GITHUB_ACTIONS' in os.environ else 'auto'}",
        "--tb=native",
        "--durations=10",
        "--strict-config",
        "--strict-markers",
        *(session.posargs or ("tests/",)),
        env={
            "PYTHONWARNINGS": "always::DeprecationWarning",
            "COVERAGE_CORE": "sysmon",
        },
    )


@nox.session(
    python=["3.7", "3.8", "3.9", "3.10", "3.11", "3.12", "3.13", "3.14", "pypy"]
)
def test(session: nox.Session) -> None:
    test_impl(session)


@nox.session(python=["3.7", "3.8", "3.9", "3.10", "3.11", "3.12", "3.13", "3.14"])
def test_mypyc(session: nox.Session) -> None:
    test_impl(session, True)


def git_clone(session: nox.Session, git_url: str) -> None:
    """We either clone the target repository or if already exist
    simply reset the state and pull.
    """
    expected_directory = git_url.split("/")[-1]

    if expected_directory.endswith(".git"):
        expected_directory = expected_directory[:-4]

    if not os.path.isdir(expected_directory):
        session.run("git", "clone", "--depth", "1", git_url, external=True)
    else:
        session.run(
            "git", "-C", expected_directory, "reset", "--hard", "HEAD", external=True
        )
        session.run("git", "-C", expected_directory, "pull", external=True)


@nox.session()
def backward_compatibility(session: nox.Session) -> None:
    git_clone(session, "https://github.com/ousret/char-dataset")

    # Install deps and the package itself.
    session.install("-U", "pip", "setuptools", silent=False)
    session.install("-r", "dev-requirements.txt", silent=False)

    session.install(".", silent=False)
    session.install("chardet")

    session.run(
        "python",
        "bin/bc.py",
        *(session.posargs or ("--coverage=85",)),
    )


@nox.session()
def coverage(session: nox.Session) -> None:
    git_clone(session, "https://github.com/ousret/char-dataset")

    # Install deps and the package itself.
    session.install("-U", "pip", "setuptools", silent=False)
    session.install("-r", "dev-requirements.txt", silent=False)

    session.install(".", silent=False)

    # Show the pip version.
    session.run("pip", "--version")
    # Print the Python version and bytesize.
    session.run("python", "--version")
    # Show charset-normalizer cli info
    session.run("normalizer", "--version")

    session.run(
        "python",
        "-m",
        "coverage",
        "run",
        "--parallel-mode",
        "bin/coverage.py",
        *(session.posargs or ("--coverage=90", "--with-preemptive")),
    )


@nox.session()
def performance(session: nox.Session) -> None:
    git_clone(session, "https://github.com/ousret/char-dataset")

    # Install deps and the package itself.
    session.install("-U", "pip", "setuptools", silent=False)
    session.install("-r", "dev-requirements.txt", silent=False)

    session.install("chardet")
    session.install(".", silent=False, env={"CHARSET_NORMALIZER_USE_MYPYC": "1"})

    session.run(
        "python",
        "bin/performance.py",
        *(session.posargs or ()),
    )


@nox.session()
def downstream_niquests(session: nox.Session) -> None:
    root = os.getcwd()
    tmp_dir = session.create_tmp()

    session.cd(tmp_dir)
    git_clone(session, "https://github.com/jawah/niquests")
    session.chdir("niquests")

    session.run("git", "rev-parse", "HEAD", external=True)
    session.install(".[socks]", silent=False)
    session.install("-r", "requirements-dev.txt", silent=False)

    session.cd(root)
    session.install(".", silent=False)
    session.cd(f"{tmp_dir}/niquests")

    session.run(
        "python",
        "-c",
        "import charset_normalizer; print(charset_normalizer.__version__)",
    )
    session.run(
        "python",
        "-m",
        "pytest",
        "-v",
        f"--color={'yes' if 'GITHUB_ACTIONS' in os.environ else 'auto'}",
        *(session.posargs or ("tests/",)),
        env={"NIQUESTS_STRICT_OCSP": "1"},
    )


@nox.session()
def downstream_requests(session: nox.Session) -> None:
    root = os.getcwd()
    tmp_dir = session.create_tmp()

    session.cd(tmp_dir)
    git_clone(session, "https://github.com/psf/requests")
    session.chdir("requests")

    session.run("git", "rev-parse", "HEAD", external=True)
    session.install(".[socks]", silent=False)
    session.install("-r", "requirements-dev.txt", silent=False)

    session.cd(root)
    session.install(".", silent=False)
    session.cd(f"{tmp_dir}/requests")

    session.run(
        "python",
        "-c",
        "import charset_normalizer; print(charset_normalizer.__version__)",
    )
    session.run(
        "python",
        "-m",
        "pytest",
        "-v",
        f"--color={'yes' if 'GITHUB_ACTIONS' in os.environ else 'auto'}",
        *(session.posargs or ("tests/",)),
    )


@nox.session()
def format(session: nox.Session) -> None:
    """Run code formatters."""
    lint(session)


@nox.session
def lint(session: nox.Session) -> None:
    session.install("pre-commit")
    session.run("pre-commit", "run", "--all-files")


@nox.session
def docs(session: nox.Session) -> None:
    session.install("-r", "docs/requirements.txt")
    session.install(".")

    session.chdir("docs")
    if os.path.exists("_build"):
        shutil.rmtree("_build")
    session.run("sphinx-build", "-b", "html", "-W", ".", "_build/html")
