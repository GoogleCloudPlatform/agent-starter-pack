from __future__ import annotations

import argparse
from glob import glob
from os import sep
from os.path import isdir
from sys import argv

from charset_normalizer import __version__, from_path
from charset_normalizer.utils import iana_name


def calc_equivalence(content: bytes, cp_a: str, cp_b: str):
    str_a = content.decode(cp_a)
    str_b = content.decode(cp_b)

    character_count = len(str_a)
    diff_character_count = sum(chr_a != chr_b for chr_a, chr_b in zip(str_a, str_b))

    return 1.0 - (diff_character_count / character_count)


def cli_coverage(arguments: list[str]):
    parser = argparse.ArgumentParser(
        description="Embedded detection success coverage script checker for Charset-Normalizer"
    )

    parser.add_argument(
        "-p",
        "--with-preemptive",
        action="store_true",
        default=False,
        dest="preemptive",
        help="Enable the preemptive scan behaviour during coverage check",
    )
    parser.add_argument(
        "-c",
        "--coverage",
        action="store",
        default=90,
        type=int,
        dest="coverage",
        help="Define the minimum acceptable coverage to succeed",
    )

    args = parser.parse_args(arguments)

    if not isdir("./char-dataset"):
        print(
            "This script require https://github.com/Ousret/char-dataset to be cloned on package root directory"
        )
        exit(1)

    print(f"> using charset-normalizer {__version__}")

    success_count = 0
    total_count = 0

    for tbt_path in sorted(glob("./char-dataset/**/*.*")):
        expected_encoding = tbt_path.split(sep)[-2]
        total_count += 1

        results = from_path(tbt_path, preemptive_behaviour=args.preemptive)

        if expected_encoding == "None" and len(results) == 0:
            print(f"✅✅ '{tbt_path}'")
            success_count += 1
            continue

        if len(results) == 0:
            print(f"⚡⚡ '{tbt_path}' (nothing)")
            continue

        result = results.best()

        if (
            expected_encoding in result.could_be_from_charset
            or iana_name(expected_encoding) in result.could_be_from_charset
        ):
            print(f"✅✅ '{tbt_path}'")
            success_count += 1
            continue

        calc_eq = calc_equivalence(result.raw, expected_encoding, result.encoding)

        if calc_eq >= 0.98:
            success_count += 1
            print(
                f"️✅ ️'{tbt_path}' (got '{result.encoding}' but equivalence {round(calc_eq * 100.0, 3)} %)"
            )
            continue

        print(f"⚡ '{tbt_path}' (got '{result.encoding}')")

    success_ratio = round(success_count / total_count, 2) * 100.0

    print(
        f"Total EST coverage = {success_ratio} % ({success_count} / {total_count} files)"
    )

    return 0 if success_ratio >= args.coverage else 1


if __name__ == "__main__":
    exit(cli_coverage(argv[1:]))
