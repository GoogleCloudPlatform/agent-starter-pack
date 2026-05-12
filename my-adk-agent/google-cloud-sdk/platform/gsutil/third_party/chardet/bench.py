"""
Run chardet on a bunch of documents and see that we get the correct encodings.

:author: Dan Blanchard
:author: Ian Cordasco
"""


import argparse
import sys
import time
from collections import defaultdict
from os import listdir
from os.path import dirname, isdir, join, realpath, relpath, splitext

import chardet

try:
    import cchardet  # pylint: disable=import-error

    HAVE_CCHARDET = True
except Exception:
    HAVE_CCHARDET = False


# TODO: Restore Hungarian encodings (iso-8859-2 and windows-1250) after we
#       retrain model.
MISSING_ENCODINGS = {
    "iso-8859-2",
    "iso-8859-6",
    "windows-1250",
    "windows-1254",
    "windows-1256",
}
EXPECTED_FAILURES = {
    "tests/iso-8859-7-greek/disabled.gr.xml",
    "tests/iso-8859-9-turkish/divxplanet.com.xml",
    "tests/iso-8859-9-turkish/subtitle.srt",
    "tests/iso-8859-9-turkish/wikitop_tr_ISO-8859-9.txt",
}


def get_py_impl():
    """Return what kind of Python this is"""
    if hasattr(sys, "pypy_version_info"):
        pyimpl = "PyPy"
    elif sys.platform.startswith("java"):
        pyimpl = "Jython"
    elif sys.platform == "cli":
        pyimpl = "IronPython"
    else:
        pyimpl = "CPython"
    return pyimpl


def get_test_files():
    """Yields filenames to use for timing chardet.detect"""
    base_path = relpath(join(dirname(realpath(__file__)), "tests"))
    for encoding in listdir(base_path):
        path = join(base_path, encoding)
        # Skip files in tests directory
        if not isdir(path):
            continue
        # Remove language suffixes from encoding if present
        encoding = encoding.lower()
        for postfix in [
            "-arabic",
            "-bulgarian",
            "-cyrillic",
            "-greek",
            "-hebrew",
            "-hungarian",
            "-turkish",
        ]:
            if encoding.endswith(postfix):
                encoding = encoding.rpartition(postfix)[0]
                break
        # Skip directories for encodings we don't handle yet.
        if encoding in MISSING_ENCODINGS:
            continue
        # Test encoding detection for each file we have of encoding for
        for file_name in listdir(path):
            ext = splitext(file_name)[1].lower()
            if ext not in [".html", ".txt", ".xml", ".srt"]:
                continue
            full_path = join(path, file_name)
            if full_path in EXPECTED_FAILURES:
                continue
            yield full_path, encoding


def benchmark(chardet_mod=chardet, verbose=False, num_iters=10):
    print(
        f"Benchmarking {chardet_mod.__name__} {chardet_mod.__version__} "
        f"on {get_py_impl()} {sys.version}"
    )
    print("-" * 80)
    total_time = 0
    num_files = 0
    encoding_times = defaultdict(float)
    encoding_num_files = defaultdict(int)
    for full_path, encoding in get_test_files():
        num_files += 1
        with open(full_path, "rb") as f:
            input_bytes = f.read()
        start = time.time()
        for _ in range(num_iters):
            chardet_mod.detect(input_bytes)
        bench_time = time.time() - start
        if verbose:
            print(f"Average time for {full_path}: {bench_time / num_iters}s")
        else:
            print(".", end="")
            sys.stdout.flush()
        total_time += bench_time
        encoding_times[encoding] += bench_time
        encoding_num_files[encoding] += 1

    print("\nCalls per second for each encoding:")
    for encoding in sorted(encoding_times.keys()):
        calls_per_sec = (
            num_iters * encoding_num_files[encoding] / encoding_times[encoding]
        )
        print(f"{encoding}: {calls_per_sec}")
    calls_per_sec = num_iters * num_files / total_time
    print(f"\nTotal time: {total_time}s ({calls_per_sec} calls per second)")


def main():
    parser = argparse.ArgumentParser(
        description="Times how long it takes to process each file in test set "
        "multiple times.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "-c",
        "--cchardet",
        action="store_true",
        help="Run benchmarks for cChardet instead of chardet, if it is installed.",
    )
    parser.add_argument(
        "-i",
        "--iterations",
        help="Number of times to process each file",
        type=int,
        default=10,
    )
    parser.add_argument(
        "-v",
        "--verbose",
        help="Prints out the timing for each individual file.",
        action="store_true",
    )
    args = parser.parse_args()

    if args.cchardet and not HAVE_CCHARDET:
        print("You must pip install cchardet if you want to benchmark it.")
        sys.exit(1)

    benchmark(
        chardet_mod=cchardet if args.cchardet else chardet,
        verbose=args.verbose,
        num_iters=args.iterations,
    )


if __name__ == "__main__":
    main()
