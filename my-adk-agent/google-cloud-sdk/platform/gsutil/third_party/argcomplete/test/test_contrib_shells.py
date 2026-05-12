#!/usr/bin/env python
import os
import os.path
import unittest

import pexpect
import pexpect.replwrap

from .test import BASE_DIR, TEST_DIR, Shell, TestShellBase


@unittest.skip("tcsh is not supported. Enable this test manually if needed.")
class TestTcsh(TestShellBase, unittest.TestCase):
    expected_failures = [
        "test_unquoted_space",
        "test_quoted_space",
        "test_continuation",
        "test_parse_special_characters",
        "test_parse_special_characters_dollar",
        # Test case doesn't work under tcsh, could be fixed.
        "test_comp_point",
    ]

    def setUp(self):
        sh = Shell("tcsh")
        path = " ".join([os.path.join(BASE_DIR, "scripts"), TEST_DIR, "$path"])
        sh.run_command("set path = ({0})".format(path))
        sh.run_command("setenv PYTHONPATH {0}".format(BASE_DIR))
        # 'dummy' argument unused; checks multi-command registration works
        # by passing 'prog' as the second argument.
        output = sh.run_command("eval `register-python-argcomplete --shell tcsh dummy prog`")
        self.assertEqual(output, "")
        # Register a dummy completion with an external argcomplete script
        # to ensure this doesn't overwrite our previous registration.
        output = sh.run_command(
            "eval `register-python-argcomplete --shell tcsh dummy --external-argcomplete-script dummy`"
        )
        self.assertEqual(output, "")
        self.sh = sh

    def tearDown(self):
        # The shell wrapper is fragile; exactly which exception is raised
        # differs depending on environment.
        with self.assertRaises((pexpect.EOF, OSError)):
            self.sh.run_command("exit")
            self.sh.run_command("")


@unittest.skip("fish is not supported. Enable this test manually if needed.")
class TestFish(TestShellBase, unittest.TestCase):
    expected_failures = [
        "test_parse_special_characters",
        "test_comp_point",
    ]

    skipped = ["test_single_quotes_in_single_quotes", "test_parse_special_characters_dollar"]

    def setUp(self):
        sh = Shell("fish")
        path = " ".join([os.path.join(BASE_DIR, "scripts"), TEST_DIR, "$PATH"])
        sh.run_command("set -x PATH {0}".format(path))
        sh.run_command("set -x PYTHONPATH {0}".format(BASE_DIR))
        # 'dummy' argument unused; checks multi-command registration works
        # by passing 'prog' as the second argument.
        output = sh.run_command("register-python-argcomplete --shell fish dummy prog | source")
        self.assertEqual(output, "")
        # Register a dummy completion with an external argcomplete script
        # to ensure this doesn't overwrite our previous registration.
        output = sh.run_command(
            "register-python-argcomplete --shell fish dummy --external-argcomplete-script dummy | source"
        )
        self.assertEqual(output, "")
        self.sh = sh

    def tearDown(self):
        # The shell wrapper is fragile; exactly which exception is raised
        # differs depending on environment.
        with self.assertRaises((pexpect.EOF, OSError)):
            self.sh.run_command("exit")
            self.sh.run_command("")
