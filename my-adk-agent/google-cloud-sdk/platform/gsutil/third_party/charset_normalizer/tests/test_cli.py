from __future__ import annotations

import unittest
from os import pardir, path, remove
from os.path import exists
from unittest.mock import patch

from charset_normalizer.cli import cli_detect, query_yes_no

DIR_PATH = path.join(path.dirname(path.realpath(__file__)), pardir)


class TestCommandLineInterface(unittest.TestCase):
    @patch("builtins.input", lambda *args: "y")
    def test_simple_yes_input(self):
        self.assertTrue(query_yes_no("Are u willing to chill a little bit ?"))

    @patch("builtins.input", lambda *args: "N")
    def test_simple_no_input(self):
        self.assertFalse(query_yes_no("Are u willing to chill a little bit ?"))

    def test_single_file(self):
        self.assertEqual(0, cli_detect([DIR_PATH + "/data/sample-arabic-1.txt"]))

    def test_version_output_success(self):
        with self.assertRaises(SystemExit):
            cli_detect(["--version"])

    def test_single_file_normalize(self):
        self.assertEqual(
            0, cli_detect([DIR_PATH + "/data/sample-arabic-1.txt", "--normalize"])
        )

        self.assertTrue(exists(DIR_PATH + "/data/sample-arabic-1.cp1256.txt"))

        try:
            remove(DIR_PATH + "/data/sample-arabic-1.cp1256.txt")
        except:
            pass

    def test_single_verbose_file(self):
        self.assertEqual(
            0, cli_detect([DIR_PATH + "/data/sample-arabic-1.txt", "--verbose"])
        )

    def test_multiple_file(self):
        self.assertEqual(
            0,
            cli_detect(
                [
                    DIR_PATH + "/data/sample-arabic-1.txt",
                    DIR_PATH + "/data/sample-french.txt",
                    DIR_PATH + "/data/sample-chinese.txt",
                ]
            ),
        )

    def test_with_alternative(self):
        self.assertEqual(
            0,
            cli_detect(
                [
                    "-a",
                    DIR_PATH + "/data/sample-arabic-1.txt",
                    DIR_PATH + "/data/sample-french.txt",
                    DIR_PATH + "/data/sample-chinese.txt",
                ]
            ),
        )

    def test_with_minimal_output(self):
        self.assertEqual(
            0,
            cli_detect(
                [
                    "-m",
                    DIR_PATH + "/data/sample-arabic-1.txt",
                    DIR_PATH + "/data/sample-french.txt",
                    DIR_PATH + "/data/sample-chinese.txt",
                ]
            ),
        )

    def test_with_minimal_and_alt(self):
        self.assertEqual(
            0,
            cli_detect(
                [
                    "-m",
                    "-a",
                    DIR_PATH + "/data/sample-arabic-1.txt",
                    DIR_PATH + "/data/sample-french.txt",
                    DIR_PATH + "/data/sample-chinese.txt",
                ]
            ),
        )

    def test_non_existent_file(self):
        with self.assertRaises(SystemExit) as cm:
            cli_detect([DIR_PATH + "/data/not_found_data.txt"])

        self.assertEqual(cm.exception.code, 2)

    def test_replace_without_normalize(self):
        self.assertEqual(
            cli_detect([DIR_PATH + "/data/sample-arabic-1.txt", "--replace"]), 1
        )

    def test_force_replace_without_replace(self):
        self.assertEqual(
            cli_detect([DIR_PATH + "/data/sample-arabic-1.txt", "--force"]), 1
        )


if __name__ == "__main__":
    unittest.main()
