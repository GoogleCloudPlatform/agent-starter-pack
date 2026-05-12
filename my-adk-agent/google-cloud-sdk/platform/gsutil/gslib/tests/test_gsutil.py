# -*- coding: utf-8 -*-
# Copyright 2013 Google Inc. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Integration tests for top-level gsutil command."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import importlib
import os
import select
import subprocess
import sys
import unittest
from unittest import mock
from google.auth import exceptions as google_auth_exceptions
from gslib.command_runner import CommandRunner
from gslib.utils import system_util

import gslib
import gslib.tests.testcase as testcase

try:
  from gsutil import _fix_google_module  # pylint: disable=g-import-not-at-top
  FIX_GOOGLE_MODULE_FUNCTION_AVAILABLE = True
except ImportError:
  FIX_GOOGLE_MODULE_FUNCTION_AVAILABLE = False


class TestGsUtil(testcase.GsUtilIntegrationTestCase):
  """Integration tests for top-level gsutil command."""

  def test_long_version_arg(self):
    stdout = self.RunGsUtil(['--version'], return_stdout=True)
    self.assertEqual('gsutil version: %s\n' % gslib.VERSION, stdout)

  def test_version_command(self):
    stdout = self.RunGsUtil(['version'], return_stdout=True)
    self.assertEqual('gsutil version: %s\n' % gslib.VERSION, stdout)

  def test_version_long(self):
    stdout = self.RunGsUtil(['version', '-l'], return_stdout=True)
    self.assertIn('gsutil version: %s\n' % gslib.VERSION, stdout)
    self.assertIn('boto version', stdout)
    self.assertIn('checksum', stdout)
    self.assertIn('config path', stdout)
    self.assertIn('gsutil path', stdout)


class TestGsUtilBanner(testcase.GsUtilIntegrationTestCase):
  """Integration tests for the deprecation banner."""

  BANNER_TEXT = 'Google recommends using Gcloud storage CLI'

  def test_banner_displayed_forced(self):
    # Tests require forcing the banner because subprocess execution is non-interactive.
    stderr = self.RunGsUtil(['version'],
                            return_stderr=True,
                            env_vars={'GSUTIL_TEST_FORCE_BANNER': 'true'})
    self.assertIn(self.BANNER_TEXT, stderr)

  def test_banner_hidden_non_interactive_default(self):
    # Verify banner is HIDDEN by default in non-interactive (script) usage.
    stderr = self.RunGsUtil(['version'], return_stderr=True)
    self.assertNotIn(self.BANNER_TEXT, stderr)

  def test_banner_suppressed_quiet(self):
    # Even if forced, -q should suppress it.
    stderr = self.RunGsUtil(['-q', 'version'],
                            return_stderr=True,
                            env_vars={'GSUTIL_TEST_FORCE_BANNER': 'true'})
    self.assertNotIn(self.BANNER_TEXT, stderr)

  def test_banner_suppressed_env_var_true(self):
    # Even if forced for testing, GSUTIL_NO_BANNER=true takes precedence.
    stderr = self.RunGsUtil(['version'],
                            return_stderr=True,
                            env_vars={
                                'GSUTIL_TEST_FORCE_BANNER': 'true',
                                'GSUTIL_NO_BANNER': 'true'
                            })
    self.assertNotIn(self.BANNER_TEXT, stderr)

  def test_banner_suppressed_env_var_1(self):
    stderr = self.RunGsUtil(['version'],
                            return_stderr=True,
                            env_vars={
                                'GSUTIL_TEST_FORCE_BANNER': 'true',
                                'GSUTIL_NO_BANNER': '1'
                            })
    self.assertNotIn(self.BANNER_TEXT, stderr)

  def test_banner_displayed_env_var_false(self):
    # GSUTIL_NO_BANNER=false should allow banner if interactive/forced.
    stderr = self.RunGsUtil(['version'],
                            return_stderr=True,
                            env_vars={
                                'GSUTIL_TEST_FORCE_BANNER': 'true',
                                'GSUTIL_NO_BANNER': 'false'
                            })
    self.assertIn(self.BANNER_TEXT, stderr)

  def test_banner_displayed_on_failure(self):
    # Command failure (exit code 1) shouldn't prevent banner display
    # if it's forced/interactive.
    stderr = self.RunGsUtil(
        ['ls', 'gs://non-existent-bucket-failure-test-12345'],
        return_stderr=True,
        expected_status=1,
        env_vars={'GSUTIL_TEST_FORCE_BANNER': 'true'})
    self.assertIn(self.BANNER_TEXT, stderr)

  def get_terminal_output(self, master_fd, slave_fd, env, cmd):
    proc = subprocess.Popen([sys.executable] + cmd,
                              stdout=slave_fd,
                              stderr=slave_fd,
                              stdin=slave_fd,
                              env=env,
                              close_fds=True)

    output = b""
    while True:
      r, _, _ = select.select([master_fd], [], [], 2.0)
      if not r:
        if proc.poll() is not None:
          break
        continue
      try:
        chunk = os.read(master_fd, 1024)
        if not chunk:
          break
        output += chunk
      except OSError:
        break

    proc.wait()
    return output
  
  @unittest.skipIf(system_util.IS_WINDOWS, 'PTY not supported on Windows')
  def test_banner_displayed_interactive_tty(self):
    """Verifies banner is displayed when running in a real PTY."""
    import pty
    master_fd, slave_fd = pty.openpty()
    try:
      cmd = [gslib.GSUTIL_PATH, 'version']
      env = os.environ.copy()
      # Ensure BOTO_CONFIG is passed through
      # Ensure no suppression env vars are set from the test runner environment
      if 'GSUTIL_NO_BANNER' in env:
        del env['GSUTIL_NO_BANNER']
      if 'GSUTIL_TEST_FORCE_BANNER' in env:
        del env['GSUTIL_TEST_FORCE_BANNER']

      output = self.get_terminal_output(master_fd=master_fd, slave_fd=slave_fd, env=env, cmd=cmd)
      output_str = output.decode('utf-8', 'ignore')
      self.assertIn(self.BANNER_TEXT, output_str)
    finally:
      os.close(master_fd)
      os.close(slave_fd)

  @unittest.skipIf(system_util.IS_WINDOWS, 'PTY not supported on Windows')
  def test_banner_suppressed_interactive_tty_quiet(self):
    import pty
    master_fd, slave_fd = pty.openpty()
    try:
      cmd = [gslib.GSUTIL_PATH, '-q', 'version']
      env = os.environ.copy()
      if 'GSUTIL_NO_BANNER' in env:
        del env['GSUTIL_NO_BANNER']
      if 'GSUTIL_TEST_FORCE_BANNER' in env:
        del env['GSUTIL_TEST_FORCE_BANNER']

      output = self.get_terminal_output(master_fd=master_fd, slave_fd=slave_fd, env=env, cmd=cmd)
      output_str = output.decode('utf-8', 'ignore')
      self.assertNotIn(self.BANNER_TEXT, output_str)
    finally:
      os.close(master_fd)
      os.close(slave_fd)

  @unittest.skipIf(system_util.IS_WINDOWS, 'PTY not supported on Windows')
  def test_banner_suppressed_interactive_tty_env_var(self):
    import pty
    master_fd, slave_fd = pty.openpty()
    try:
      cmd = [gslib.GSUTIL_PATH, 'version']
      env = os.environ.copy()
      if 'GSUTIL_TEST_FORCE_BANNER' in env:
        del env['GSUTIL_TEST_FORCE_BANNER']
      env['GSUTIL_NO_BANNER'] = 'true'

      output = self.get_terminal_output(master_fd=master_fd, slave_fd=slave_fd, env=env, cmd=cmd)
      output_str = output.decode('utf-8', 'ignore')
      self.assertNotIn(self.BANNER_TEXT, output_str)
    finally:
      os.close(master_fd)
      os.close(slave_fd)


class TestGsUtilUnit(testcase.GsUtilUnitTestCase):
  """Unit tests for top-level gsutil command."""

  @unittest.skipUnless(
      FIX_GOOGLE_MODULE_FUNCTION_AVAILABLE,
      'The gsutil.py file is not available for certain installations like pip.')
  @mock.patch.object(importlib, 'reload', autospec=True)
  def test_fix_google_module(self, mock_reload):
    with mock.patch.dict('sys.modules', {'google': 'google'}):
      _fix_google_module()
      mock_reload.assert_called_once_with('google')

  @unittest.skipUnless(
      FIX_GOOGLE_MODULE_FUNCTION_AVAILABLE,
      'The gsutil.py file is not available for certain installations like pip.')
  @mock.patch.object(importlib, 'reload', autospec=True)
  def test_fix_google_module_does_not_reload_if_module_missing(
      self, mock_reload):
    with mock.patch.dict('sys.modules', {}, clear=True):
      _fix_google_module()
      self.assertFalse(mock_reload.called)

  @mock.patch.object(system_util, 'InvokedViaCloudSdk', autospec=True)
  @mock.patch.object(gslib.__main__, '_OutputAndExit', autospec=True)
  def test_translates_oauth_error_cloudsdk(self, mock_output_and_exit,
                                           mock_invoke_via_cloud_sdk):
    mock_invoke_via_cloud_sdk.return_value = True
    command_runner = CommandRunner()
    with mock.patch.object(command_runner, 'RunNamedCommand') as mock_run:
      fake_error = google_auth_exceptions.OAuthError('fake error message')
      mock_run.side_effect = fake_error
      gslib.__main__._RunNamedCommandAndHandleExceptions(command_runner,
                                                         command_name='fake')
      mock_output_and_exit.assert_called_once_with(
          'Your credentials are invalid. Please run\n$ gcloud auth login',
          fake_error)

  @mock.patch.object(system_util, 'InvokedViaCloudSdk', autospec=True)
  @mock.patch.object(gslib.__main__, '_OutputAndExit', autospec=True)
  def test_translates_oauth_error_standalone(self, mock_output_and_exit,
                                             mock_invoke_via_cloud_sdk):
    mock_invoke_via_cloud_sdk.return_value = False
    command_runner = CommandRunner()
    with mock.patch.object(command_runner, 'RunNamedCommand') as mock_run:
      fake_error = google_auth_exceptions.OAuthError('fake error message')
      mock_run.side_effect = fake_error
      gslib.__main__._RunNamedCommandAndHandleExceptions(command_runner,
                                                         command_name='fake')
      mock_output_and_exit.assert_called_once_with(
          'Your credentials are invalid. For more help, see '
          '"gsutil help creds", or re-run the gsutil config command (see '
          '"gsutil help config").', fake_error)
