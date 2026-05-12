#!/usr/bin/env python
"""BQ CLI helper functions for gcloud interactions."""

import json
import logging
import subprocess
from typing import Any, Dict, Optional

from absl import flags

import bq_utils
from gcloud_wrapper import gcloud_runner


# Cache of `gcloud config config-helper` to be used in load_full_config().
_config_cache = None


def _use_gcloud_value_if_exists_and_flag_is_default_value(
    flag_values: flags._flagvalues.FlagValues,
    flag_name: str,
    gcloud_config_section: Dict[str, str],
    gcloud_property_name: str,
):
  """Updates flag if it's using the default and the gcloud value exists."""
  if not gcloud_config_section:
    return
  if gcloud_property_name not in gcloud_config_section:
    return
  flag = flag_values[flag_name]
  gcloud_value = gcloud_config_section[gcloud_property_name]
  logging.debug('Gcloud config exists for %s', gcloud_property_name)
  if flag.using_default_value:
    logging.info(
        'The `%s` flag is using a default value and a value is set in gcloud,'
        ' using that: %s',
        flag_name,
        gcloud_value,
    )
    bq_utils.UpdateFlag(flag_values, flag_name, gcloud_value)
  elif flag.value != gcloud_value:
    logging.warning(
        'Executing with different configuration than in gcloud.'
        'The flag "%s" has become set to "%s" but gcloud sets "%s" as "%s".'
        'To update the gcloud value, start from `gcloud config list`.',
        flag_name,
        flag.value,
        gcloud_property_name,
        gcloud_value,
    )


def process_config(flag_values: flags._flagvalues.FlagValues) -> None:
  """Processes the user configs from gcloud and sets flag values accordingly."""
  if not flag_values.use_gcloud_config:
    logging.info(
        "'use_gcloud_config' is false, skipping gcloud config processing."
    )
    return

  configs = load_config()

  core_config = configs.get('core', {})
  billing_config = configs.get('billing', {})
  context_aware = configs.get('context_aware', {})
  auth_config = configs.get('auth', {})
  api_endpoint_overrides = configs.get('api_endpoint_overrides', {})

  _use_gcloud_value_if_exists_and_flag_is_default_value(
      flag_values=flag_values,
      flag_name='project_id',
      gcloud_config_section=core_config,
      gcloud_property_name='project',
  )

  _use_gcloud_value_if_exists_and_flag_is_default_value(
      flag_values=flag_values,
      flag_name='quota_project_id',
      gcloud_config_section=billing_config,
      gcloud_property_name='quota_project',
  )

  _use_gcloud_value_if_exists_and_flag_is_default_value(
      flag_values=flag_values,
      flag_name='universe_domain',
      gcloud_config_section=core_config,
      gcloud_property_name='universe_domain',
  )

  _use_gcloud_value_if_exists_and_flag_is_default_value(
      flag_values=flag_values,
      flag_name='request_reason',
      gcloud_config_section=core_config,
      gcloud_property_name='request_reason',
  )

  _use_gcloud_value_if_exists_and_flag_is_default_value(
      flag_values=flag_values,
      flag_name='api',
      gcloud_config_section=api_endpoint_overrides,
      gcloud_property_name='bigquery',
  )

  _use_gcloud_value_if_exists_and_flag_is_default_value(
      flag_values=flag_values,
      flag_name='bigquery_discovery_api_key',
      gcloud_config_section=core_config,
      gcloud_property_name='api_key',
  )

  _use_gcloud_value_if_exists_and_flag_is_default_value(
      flag_values=flag_values,
      flag_name='mtls',
      gcloud_config_section=context_aware,
      gcloud_property_name='use_client_certificate',
  )

  if not auth_config or not core_config:
    return
  try:
    access_token_file = auth_config['access_token_file']
    universe_domain = core_config['universe_domain']
  except KeyError:
    # This is expected if these attributes aren't in the config file.
    return
  if access_token_file and universe_domain:
    if (
        not flag_values['oauth_access_token'].using_default_value
        or not flag_values['use_google_auth'].using_default_value
    ):
      logging.warning(
          'Users gcloud config file and bigqueryrc file have incompatible'
          ' configurations. Defaulting to the bigqueryrc file'
      )
      return

    logging.info(
        'Using the gcloud configuration to get TPC authorisation from'
        ' access_token_file'
    )
    try:
      with open(access_token_file) as token_file:
        token = token_file.read().strip()
    except IOError:
      logging.warning(
          'Could not open `access_token_file` file, ignoring gcloud settings'
      )
    else:
      bq_utils.UpdateFlag(flag_values, 'oauth_access_token', token)
      bq_utils.UpdateFlag(flag_values, 'use_google_auth', True)


def load_full_config() -> Dict[str, Any]:
  """Loads the user full configs from gcloud.

  The result is cached to avoid multiple calls to gcloud.

  Returns:
    A dictionary containing the full gcloud configuration.
  """
  global _config_cache
  if _config_cache is not None:
    logging.info('Using cached gcloud config')
    return _config_cache

  _config_cache = {}

  try:
    process = gcloud_runner.run_gcloud_command(
        ['config', 'config-helper', '--format=json'], stderr=subprocess.PIPE
    )
    out, err = process.communicate()

    if process.returncode != 0:
      # Retry interactively to allow reauthentication prompts if needed.
      retry_process = gcloud_runner.run_gcloud_command(
          ['config', 'config-helper', '--format=json'], stderr=None
      )
      retry_out, retry_err = retry_process.communicate()
      if retry_process.returncode == 0:
        process = retry_process
        out = retry_out
        err = retry_err
  except FileNotFoundError as e:
    # TODO: b/365836272 - Catch gcloud-not-found error in gcloud_runner.
    logging.warning(
        'Continuing with empty gcloud config data due to error: %s', str(e)
    )
    return _config_cache

  if err:
    logging.warning('Stderr message from gcloud config config-helper: %s', err)

  if process.returncode != 0:
    logging.warning(
        'Continuing with empty gcloud config data due to returncode %s. Stdout:'
        ' %s, Stderr: %s',
        process.returncode,
        out.strip() if out else '',
        err.strip() if err else '',
    )
    return _config_cache

  try:
    full_config = json.loads(out)
    _config_cache = full_config
  except json.JSONDecodeError as e:
    logging.warning(
        'Continuing with empty gcloud config data due to invalid config'
        ' format: %s',
        e,
    )
  return _config_cache


def load_config() -> Dict[str, Dict[str, str]]:
  """Loads the user configs from gcloud and returns them as a dictionary."""
  full_config = load_full_config()
  return full_config.get('configuration', {}).get('properties', {})


def load_access_token() -> Optional[str]:
  """Loads the access token from gcloud."""
  full_config = load_full_config()
  return full_config.get('credential', {}).get('access_token')
