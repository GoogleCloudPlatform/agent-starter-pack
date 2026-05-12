#!/usr/bin/env python
"""A library of functions to handle bq flags consistently."""

import json
import os
import pkgutil
import platform
import re
import ssl
import sys
import textwrap
from typing import Any, Dict, List, Literal, Optional, TextIO

from absl import app
from absl import flags
from google.auth import version as google_auth_version
import httplib2
import requests
import urllib3

from pyglib import stringutil


FLAGS = flags.FLAGS

_GDRIVE_SCOPE = 'https://www.googleapis.com/auth/drive'
_BIGQUERY_SCOPE = 'https://www.googleapis.com/auth/bigquery'
_CLOUD_PLATFORM_SCOPE = 'https://www.googleapis.com/auth/cloud-platform'
_REAUTH_SCOPE = 'https://www.googleapis.com/auth/accounts.reauth'



# Boolean flag names that correspond to resources for the user agent header.
_RESOURCE_FLAG_NAMES = frozenset([
    'capacity_commitment',
    'connection',
    'dataset',
    'datasets',
    'encryption_service_account',
    'job',
    'jobs',
    'materialized_view',
    'migration_workflow',
    'model',
    'models',
    'reservation',
    'reservation_assignment',
    'reservation_group',
    'routine',
    'routines',
    'row_access_policies',
    'row_access_policy',
    'table',
    'transfer_config',
    'transfer_run',
    'view',
])

_BQ_CLI_COMMAND: Optional[str] = None
_BQ_CLI_RESOURCE: Optional[str] = None

_VERSION_FILENAME = 'VERSION'


def _GetVersion() -> str:
  """Returns content of VERSION file found in same dir as the cli binary."""
  root = __name__
  try:
    # pylint: disable-next=unused-variable
    version_str = pkgutil.get_data(root, _VERSION_FILENAME)
  except FileNotFoundError:
    pass
  if not version_str:
    version_str = 'unknown-version'
  version_str = stringutil.ensure_str(version_str).strip()
  assert (
      '\n' not in version_str
  ), 'New lines are not allowed in the version string.'
  return version_str


VERSION_NUMBER = _GetVersion()


def _IsTpcBinary() -> bool:
  """Returns true if the current binary is targeting TPC."""
  return VERSION_NUMBER.startswith('tpc-')


IS_TPC_BINARY = _IsTpcBinary()


def GetBigqueryRcFilename() -> Optional[str]:
  """Return the name of the bigqueryrc file to use.

  In order, we look for a flag the user specified, an environment
  variable, and finally the default value for the flag.

  Returns:
    bigqueryrc filename as a string.
  """
  return (  # pytype: disable=bad-return-type
      (FLAGS['bigqueryrc'].present and FLAGS.bigqueryrc)
      or os.environ.get('BIGQUERYRC')
      or FLAGS.bigqueryrc
  )


def UpdateFlag(flag_values, flag: str, value) -> None:
  # This updates the .value and .present attributes.
  flag_values[flag].parse(value)
  # This updates the .using_default_value attribute in addition.
  setattr(flag_values, flag, getattr(flag_values, flag))


def ProcessBigqueryrc() -> None:
  """Updates FLAGS with values found in the bigqueryrc file."""
  ProcessBigqueryrcSection(None, FLAGS)


def _ProcessConfigSection(
    filename: str, section_name: Optional[str] = None
) -> Dict[str, str]:
  """Read a configuration file section returned as a dictionary.

  Args:
    filename: The filename of the configuration file.
    section_name: if None, read the global flag settings.

  Returns:
    A dictionary of flag names and values from that section of the file.
  """

  # TODO(b/286571605): Replace typing when python 3.5 is unsupported.
  dictionary = {}  # type: Dict[str, str]
  if not os.path.exists(filename):
    return dictionary
  try:
    with open(filename) as rcfile:
      dictionary = _ProcessSingleConfigSection(rcfile, section_name)
  except IOError:
    pass
  return dictionary


def _ProcessSingleConfigSection(
    file: TextIO, section_name: str
) -> Dict[str, str]:
  """Read a configuration file section returned as a dictionary.

  Args:
    file: The opened configuration file object.
    section_name: Name of the section to read.

  Returns:
    A dictionary of flag names and values from that section of the file.
  """
  dictionary = {}
  in_section = not section_name
  for line in file:
    if line.lstrip().startswith('[') and line.rstrip().endswith(']'):
      next_section = line.strip()[1:-1]
      in_section = section_name == next_section
      continue
    elif not in_section:
      continue
    elif line.lstrip().startswith('#') or not line.strip():
      continue
    flag, equalsign, value = line.partition('=')
    # if no value given, assume stringified boolean true
    if not equalsign:
      value = 'true'
    flag = flag.strip()
    value = value.strip()
    while flag.startswith('-'):
      flag = flag[1:]
    dictionary[flag] = value
  return dictionary


def ProcessBigqueryrcSection(section_name: Optional[str], flag_values) -> None:
  """Read the bigqueryrc file into flag_values for section section_name.

  Args:
    section_name: if None, read the global flag settings.
    flag_values: FLAGS instance.

  Raises:
    UsageError: Unknown flag found.
  """

  bigqueryrc = GetBigqueryRcFilename()
  dictionary = _ProcessConfigSection(
      filename=bigqueryrc, section_name=section_name
  )
  for flag, value in dictionary.items():
    # We want flags specified at the command line to override
    # those in the flagfile.
    if flag not in flag_values:
      raise app.UsageError(
          'Unknown flag %s found in bigqueryrc file in section %s'
          % (flag, section_name if section_name else 'global')
      )
    if not flag_values[flag].present:
      UpdateFlag(flag_values, flag, value)
    else:
      flag_type = flag_values[flag].flag_type()
      if flag_type.startswith('multi'):
        old_value = getattr(flag_values, flag)
        flag_values[flag].parse(value)
        setattr(flag_values, flag, old_value + getattr(flag_values, flag))


def GetResolvedQuotaProjectID(
    quota_project_id: Optional[str],
    fallback_project_id: Optional[str],
) -> Optional[str]:
  """Returns the final resolved quota project ID.

  This function cross-references gcloud properties to determine the effective
  quota project ID.

  Args:
    quota_project_id: The quota project ID provided by the user.
    fallback_project_id: The project ID to use as a fallback.
  """
  if not quota_project_id and fallback_project_id:
    return fallback_project_id
  return _GetResolvedGcloudQuotaProjectID(
      quota_project_id=quota_project_id,
      fallback_project_id=fallback_project_id,
  )


def _GetResolvedGcloudQuotaProjectID(
    quota_project_id: Optional[str],
    fallback_project_id: Optional[str],
) -> Optional[str]:
  """Resolves the quota project ID using gcloud properties.

  Args:
    quota_project_id: The quota project ID to resolve.
    fallback_project_id: The fallback project ID to use.

  Returns:
    The resolved quota project ID, or None if no quota project is applicable.
  """
  if quota_project_id and quota_project_id in (
      'CURRENT_PROJECT',
      'CURRENT_PROJECT_WITH_FALLBACK',
  ):
    return fallback_project_id
  if 'LEGACY' == quota_project_id:
    return None
  return quota_project_id


def GetFallbackQuotaProject(
    is_service_account: bool,
    fallback_project_id: Optional[str],
) -> Optional[str]:
  """Return the fallback quota project ID.

  Args:
    is_service_account: True if the credentials belong to a service account.
    fallback_project_id: The project ID to use as a fallback.

  Returns:
    The fallback quota project ID, or None if not applicable.
  """

  if is_service_account:
    return None
  return fallback_project_id


def IsCredentialServiceAccount(credentials: Any) -> bool:
  """Returns if the oauth2client credentials belong to a service account."""
  class_name = credentials.__class__.__name__

  if class_name == 'WrappedCredentials':
    base = getattr(credentials, '_base', None)
    if base:
      # google-auth external account credentials have an is_user property.
      # Workload identities (machine) have is_user=False.
      # Workforce identities (human) have is_user=True.
      return not getattr(base, 'is_user', True)

  if class_name in (
      'ServiceAccountCredentials',
      'AppAssertionCredentials',  # for GCE service accounts
      'RobotCredentials',
      'OwnedTestingAccountCredentials',
      'ServiceAccountImpersonationCredential',
  ):
    return True

  # Use full class name for 'Credential' as it is too generic and avoid
  # collisions with other 'Credential' classes.
  if class_name == 'Credential' and credentials.__class__.__module__.endswith(
      'service_account_impersonation'
  ):
    return True

  if getattr(credentials, 'type', None) in (
      'service_account',
      'external_account',
  ):
    return True

  # Check for explicit service_account_email attribute
  service_account_email = getattr(credentials, 'service_account_email', None)
  if service_account_email:
    return True
  # Check for signer_email (sometimes used in service account credentials)
  signer_email = getattr(credentials, 'signer_email', None)
  if signer_email:
    return True

  account = getattr(credentials, 'account', None)
  if account and IsServiceAccount(account):
    return True

  return False


def GetEffectiveQuotaProjectIDForHTTPHeader(
    quota_project_id: str,
    project_id: str,
    use_google_auth: bool,
    credentials: Any,
) -> Optional[str]:
  """Return the effective quota project ID to be set in the API HTTP header."""
  if use_google_auth and hasattr(credentials, '_quota_project_id'):
    return credentials._quota_project_id  # pylint: disable=protected-access

  is_service_account = IsCredentialServiceAccount(credentials)
  fallback_project_id = GetFallbackQuotaProject(
      is_service_account=is_service_account,
      fallback_project_id=project_id,
  )

  return GetResolvedQuotaProjectID(
      quota_project_id=quota_project_id, fallback_project_id=fallback_project_id
  )


def GetPlatformString() -> str:
  return ':'.join([
      platform.python_implementation(),
      platform.python_version(),
      platform.platform(),
  ])


def GetInfoString() -> str:
  """Gets the info string for the current execution."""
  platform_str = GetPlatformString()
  try:
    httplib2_version = httplib2.__version__
  except AttributeError:
    # Handle an unexpected version being loaded
    # pytype: disable=module-attr
    httplib2_version = httplib2.python3.__version__
    # pytype: enable=module-attr
  try:
    shell_path = os.environ['PATH']
  except KeyError:
    shell_path = None
  try:
    python_path = os.environ['PYTHONPATH']
  except KeyError:
    python_path = None
  return textwrap.dedent(
      """\
      BigQuery CLI [{version}]

      Platform: [{platform_str}] {uname}
      Python Version: [{python_version}]

      OpenSSL Version: [{openssl_version}]
      Requests Version: [{requests_version}]
      Urllib3 Version: [{urllib3_version}]
      Httplib2: [{httplib2_version}]
      Google Auth Version: [{google_auth_version}]

      System PATH: [{sys_path}]
      Shell PATH: [{shell_path}]
      Python PATH: [{python_path}]

      """.format(
          version=VERSION_NUMBER,
          platform_str=platform_str,
          uname=platform.uname(),
          python_version=sys.version.replace('\n', ' '),
          openssl_version=ssl.OPENSSL_VERSION,
          httplib2_version=httplib2_version,
          google_auth_version=google_auth_version.__version__,
          requests_version=requests.__version__,
          urllib3_version=urllib3.__version__,
          sys_path=os.pathsep.join(sys.path),
          shell_path=shell_path,
          python_path=python_path,
      )
  )


def PrintFormattedJsonObject(
    obj: object, default_format: Literal['json', 'prettyjson'] = 'json'
):
  """Prints obj in a JSON format according to the "--format" flag.

  Args:
    obj: The object to print.
    default_format: The format to use if the "--format" flag does not specify a
      valid json format: 'json' or 'prettyjson'.
  """
  json_formats = ['json', 'prettyjson']
  if FLAGS.format in json_formats:
    use_format = FLAGS.format
  else:
    use_format = default_format

  if use_format == 'json':
    print(json.dumps(obj, separators=(',', ':')))
  elif use_format == 'prettyjson':
    print(json.dumps(obj, sort_keys=True, indent=2))
  else:
    raise ValueError(
        "Invalid json format for printing: '%s', expected one of: %s"
        % (use_format, json_formats)
    )


def GetClientScopesFromFlags() -> List[str]:
  """Returns auth scopes based on user supplied flags."""
  client_scope = [_BIGQUERY_SCOPE, _CLOUD_PLATFORM_SCOPE]
  if FLAGS.enable_gdrive:
    client_scope.append(_GDRIVE_SCOPE)
  client_scope.append(_REAUTH_SCOPE)
  return client_scope


def GetClientScopesFor3pi() -> List[str]:
  """Returns the scopes list for 3rd Party Identity Federation."""
  return [_CLOUD_PLATFORM_SCOPE]


def ParseTags(tags: str) -> Dict[str, str]:
  """Parses user-supplied string representing tags.

  Args:
    tags: A comma separated user-supplied string representing tags. It is
      expected to be in the format "key1:value1,key2:value2".

  Returns:
    A dictionary mapping tag keys to tag values.

  Raises:
    UsageError: Incorrect tags or no tags are supplied.
  """
  tags = tags.strip()
  if not tags:
    raise app.UsageError('No tags supplied')
  tags_dict = {}
  for key_value in tags.split(','):
    k, _, v = key_value.rpartition(':')
    k = k.strip()
    if not k:
      raise app.UsageError('Tag key cannot be None')
    v = v.strip()
    if not v:
      raise app.UsageError('Tag value cannot be None')
    if k in tags_dict:
      raise app.UsageError('Cannot specify tag key "%s" multiple times' % k)
    tags_dict[k] = v
  return tags_dict


def ParseTagKeys(tag_keys: str) -> List[str]:
  """Parses user-supplied string representing tag keys.

  Args:
    tag_keys: A comma separated user-supplied string representing tag keys.  It
      is expected to be in the format "key1,key2" or
      "tpczero-system:key1,tpczero-system:key2".

  Returns:
    A list of tag keys.

  Raises:
    UsageError: Incorrect tag_keys or no tag_keys are supplied.
  """
  tag_keys = tag_keys.strip()
  if not tag_keys:
    raise app.UsageError('No tag keys supplied')
  tags_set = set()
  for key in tag_keys.split(','):
    key = key.strip()
    if not key:
      raise app.UsageError('Tag key cannot be None')
    if key in tags_set:
      raise app.UsageError('Cannot specify tag key "%s" multiple times' % key)
    tags_set.add(key)
  return list(tags_set)


def SetBqCliUserAgentCommand(command: Optional[str]):
  """Sets the BQ CLI user agent command."""
  global _BQ_CLI_COMMAND
  _BQ_CLI_COMMAND = command


def SetBqCliUserAgentResource(resource: Optional[str], overwrite: bool = True):
  """Sets the BQ CLI user agent resource.

  Args:
    resource: The resource string.
    overwrite: If True, overwrite the existing resource. If False, only set it
      if it is currently None.
  """
  global _BQ_CLI_RESOURCE
  if overwrite or _BQ_CLI_RESOURCE is None:
    _BQ_CLI_RESOURCE = resource


def GetBqCliUserAgentComponent() -> Optional[str]:
  """Returns the BQ CLI specific part of the user agent."""
  if not _BQ_CLI_COMMAND:
    return None
  return f'bq.{_BQ_CLI_COMMAND}.{_BQ_CLI_RESOURCE or "unknown"}'


def Pluralize(name: str) -> str:
  """Get pluralized resource name from typename for the user agent string.

  Replaces spaces with underscores and applies basic pluralization rules.

  Args:
    name: The name to pluralize.

  Returns:
    The pluralized name.
  """
  if not name:
    return name
  name = name.replace(' ', '_')
  if name.endswith('s'):
    return name
  if name.endswith('y'):
    return name[:-1] + 'ies'
  return name + 's'


def GetResourceFlagNames() -> frozenset[str]:
  """Returns the set of boolean flags that correspond to resources."""
  return _RESOURCE_FLAG_NAMES


def GetUserAgent() -> str:
  """Returns the user agent for BigQuery API requests."""
  google_python_client_name = 'google-api-python-client'
  if os.environ.get('CLOUDSDK_WRAPPER') == '1':
    return (
        'google-cloud-sdk'
        + os.environ.get('CLOUDSDK_VERSION', VERSION_NUMBER)
        + ' '
        + google_python_client_name
    )
  else:
    return 'bq/' + VERSION_NUMBER + ' ' + google_python_client_name


# See go/cloud-iam-service-account-types.
def IsServiceAccount(account: str) -> bool:
  """Returns whether the account may be a service account.

  This is based on the user-created or system-created account name.

  Args:
    account: The account string to check.
  """
  return re.fullmatch(r'^.+@(.+)(\.gserviceaccount\.com)$', account) is not None
