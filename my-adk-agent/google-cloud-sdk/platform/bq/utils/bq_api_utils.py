#!/usr/bin/env python
"""API utils for the BQ CLI."""

import json
import logging
import re
from typing import Dict, NamedTuple, Optional, Union
import urllib
from absl import flags
from utils import bq_consts
from utils import bq_error

Service = bq_consts.Service

# TODO(b/151445175) Remove Apiary formats.
STATIC_HTTP_ENDPOINT_RE_PREFIX = (
    'https?://(www|(staging-www|test-bigquery).sandbox|bigquery-sq|bigquery)'
    '.(google|googleapis).com'
)

_GDU_DOMAIN = 'googleapis.com'


def _get_service_name_from_enum(service: Service) -> str:
  """Returns the service name for the given service enum."""
  if service is Service.BIGQUERY:
    return 'bigquery'
  elif service is Service.CONNECTIONS:
    return 'bigqueryconnection'
  elif service is Service.RESERVATIONS:
    return 'bigqueryreservation'
  elif service is Service.DTS:
    return 'bigquerydatatransfer'
  elif service is Service.ANALYTICS_HUB:
    return 'analyticshub'
  elif service is Service.BIGLAKE:
    return 'biglake'
  elif service is Service.BQ_IAM:
    return 'bigquery'
  else:
    raise ValueError(f'Unsupported service: {service}')


def _get_tpc_service_endpoint_hostname(
    service_enum: Service = Service.BIGQUERY,
    universe_domain: str = _GDU_DOMAIN,
    region: Optional[str] = None,
    is_mtls: bool = False,
    is_rep: bool = False,
    is_lep: bool = False,
) -> str:
  """Returns the TPC service endpoint hostname."""

  logging.info(
      'Building a root URL for the %s service in the "%s" universe for region'
      ' "%s" %s mTLS, %s REP, and %s LEP',
      service_enum,
      universe_domain,
      region,
      'with' if is_mtls else 'without',
      'with' if is_rep else 'without',
      'with' if is_lep else 'without',
  )

  service = _get_service_name_from_enum(service_enum)

  # These are taken from here:
  # https://docs.google.com/document/d/1c0l65oyQ_iUvhOSHXKF9SWPS7WIu4VZYuXiPFn3zDx8

  # Fully qualified, MTLS, REP:
  if is_mtls and is_rep and region:
    return f'{service}.{region}.rep.mtls.{universe_domain}'
  # Fully qualified, non-MTLS, REP:
  if not is_mtls and is_rep and region:
    return f'{service}.{region}.rep.{universe_domain}'
  # MTLS, non-regional:
  if is_mtls and not region:
    return f'{service}.mtls.{universe_domain}'
  # MTLS omitted, LEP
  if not is_mtls and is_lep and region:
    return f'{region}-{service}.{universe_domain}'
  # Purpose, region, and MTLS omitted (default):
  return f'{service}.{universe_domain}'


def add_trailing_slash_if_missing(url: str) -> str:
  if not url.endswith('/'):
    return url + '/'
  return url


def get_tpc_root_url_from_flags(
    service: Service,
    inputted_flags: NamedTuple(
        'InputtedFlags',
        [
            ('API', flags.FlagHolder[Optional[str]]),
            ('UNIVERSE_DOMAIN', flags.FlagHolder[Optional[str]]),
            ('LOCATION', flags.FlagHolder[Optional[str]]),
            ('USE_LEP', flags.FlagHolder[bool]),
            ('USE_REP', flags.FlagHolder[bool]),
            ('USE_REGIONAL_ENDPOINTS', flags.FlagHolder[bool]),
            ('MTLS', flags.FlagHolder[bool]),
        ],
    ),
) -> str:
  """Takes BQ CLI flags to build a root URL to make requests to.

  If the `api` flag is set, and is a http/https URL then it will be used
  otherwise the result is built up from the different options for a TPC service
  endpoint.

  Args:
    service: The service that this request will be made to. Usually the API that
      is being hit.
    inputted_flags: The flags set, usually straight from bq_flags.

  Returns:
    The root URL to be used for BQ requests. This is built from the service
    being targeted and a number of flags as arguments. It's intended to be used
    both for building the URL to request the discovery doc from, and to override
    the rootUrl and servicePath values of the discovery doc when they're
    incorrect. It always ends with a trailing slash.

  Raises:
    BigqueryClientError: If the flags are used incorrectly.
  """

  number_of_flags_requesting_a_regional_api = [
      inputted_flags.USE_LEP.value,
      inputted_flags.USE_REP.value,
      inputted_flags.USE_REGIONAL_ENDPOINTS.value,
  ].count(True)

  if number_of_flags_requesting_a_regional_api > 1:
    raise bq_error.BigqueryClientError(
        'Only one of use_lep, use_rep or use_regional_endpoints can be used at'
        ' a time'
    )

  if (
      number_of_flags_requesting_a_regional_api == 1
      and not inputted_flags.LOCATION.value
  ):
    raise bq_error.BigqueryClientError(
        'A region is needed when the use_lep, use_rep or use_regional_endpoints'
        ' flags are used.'
    )

  if (
      inputted_flags.API.present
  ):
    logging.info(
        'Looking for a root URL and an `api` value was found, using that: %s',
        inputted_flags.API.value,
    )
    return add_trailing_slash_if_missing(inputted_flags.API.value)


  # The BQ CLI tool has historically interpreted the location flag to mean
  # a resource from a specific region will be requested from a global API.
  # For our initial implementation, this code maintains this behaviour.
  if (
      number_of_flags_requesting_a_regional_api == 0
      and inputted_flags.LOCATION.value
  ):
    region = None
  else:
    region = inputted_flags.LOCATION.value

  # Re-evaluate the usage of LEP requests for `use_regional_endpoints`. It was
  # originally implemented this way as part of b/211695055 but now that LEP is
  # being replace by REP, and there is varied support across the different BQ
  # service APIs, then this should be revisited.
  if inputted_flags.USE_REGIONAL_ENDPOINTS.value:
    logging.info(
        'Building a root URL and `use_regional_endpoints` is present,'
        ' forcing LEP'
    )
    is_lep = True
  else:
    is_lep = inputted_flags.USE_LEP.value

  # Use the default `universe_domain` value if it's not set, so long as there
  # was no `api` flag specified (handled above). The initial implementation is
  # done this way since historically the `api` flag defined a default value, and
  # that had to be handled or migrated. Since there is already enough risk with
  # this change the behaviour was kept. Precedence for their values does mean it
  # makes sense for the `api` default to eventually become the `None` value.
  if inputted_flags.UNIVERSE_DOMAIN.value:
    universe_domain = inputted_flags.UNIVERSE_DOMAIN.value
  else:
    universe_domain = _GDU_DOMAIN

  hostname = _get_tpc_service_endpoint_hostname(
      service_enum=service,
      universe_domain=universe_domain,
      region=region,
      is_mtls=inputted_flags.MTLS.value,
      is_rep=inputted_flags.USE_REP.value,
      is_lep=is_lep,
  )

  root_url = add_trailing_slash_if_missing(
      urllib.parse.urlunsplit(
          urllib.parse.SplitResult(
              scheme='https', netloc=hostname, path='', query='', fragment=''
          )
      )
  )
  logging.info('Final root URL built as: %s', root_url)
  return root_url


def add_api_key_to_discovery_url(
    discovery_url: str,
    universe_domain: Optional[str],
    inputted_flags: NamedTuple(
        'InputtedFlags',
        [
            (
                'BIGQUERY_DISCOVERY_API_KEY_FLAG',
                flags.FlagHolder[Optional[str]],
            ),
        ],
    ),
    key: Optional[str] = None,
    labels: Optional[str] = None,
) -> str:
  """Adds an API key to the URL."""
  # TODO: b/361181701 - Clean up the duplicate key check logic when cleaning up
  # discovery_url_extra handling.
  if key and f'key={key}' in discovery_url:
    logging.info(
        'API key %s has already been added, presumably from'
        ' --discovery_url_extra',
        key,
    )
    return discovery_url
  if 'key=' in discovery_url:
    logging.info(
        'An API key already exists in the URL, presumably from'
        ' --discovery_url_extra, so not adding any new key'
    )
    return discovery_url

  if not key:
    key = inputted_flags.BIGQUERY_DISCOVERY_API_KEY_FLAG.value
    logging.info(
        'No API key has been set, using value from the'
        ' `bigquery_discovery_api_key` flag targeting the universe_domain'
        ' (%s)',
        universe_domain,
    )

  if key:
    if '?' in discovery_url:
      delimiter = '&'
    else:
      delimiter = '?'
    discovery_url += f'{delimiter}key={key}'
    if labels:
      discovery_url += f'&labels={labels}'
    logging.info('Discovery URL has been updated (%s)', discovery_url)
  return discovery_url


def get_discovery_url_from_root_url(
    root_url: str, api_version: str = 'v2'
) -> str:
  """Returns the discovery doc URL from a root URL."""
  parts = urllib.parse.urlsplit(root_url)
  query = urllib.parse.urlencode({'version': api_version})
  parts = parts._replace(path='/$discovery/rest', query=query)
  return urllib.parse.urlunsplit(parts)


# This typing here is minimal needed for our current use cases but doesn't
# express how complicated the returned object can be.
def parse_discovery_doc(
    discovery_document: Union[str, bytes],
) -> Dict[str, str]:
  """Takes a downloaded discovery document and parses it.

  Args:
    discovery_document: The discovery doc to parse.

  Returns:
    The parsed api doc.
  """
  if isinstance(discovery_document, str):
    return json.loads(discovery_document)
  elif isinstance(discovery_document, bytes):
    return json.loads(discovery_document.decode('utf-8'))
  raise ValueError(
      f'Unsupported discovery document type: {type(discovery_document)}'
  )


def is_gdu_universe(universe_domain: Optional[str]) -> bool:
  """Returns whether the universe domain is GDU."""
  if not universe_domain:
    return False
  return universe_domain == _GDU_DOMAIN


def is_gdu_url(url: Optional[str]) -> bool:
  """Returns whether the url is GDU."""
  if not url:
    return False
  return _GDU_DOMAIN in url or (
      re.compile(STATIC_HTTP_ENDPOINT_RE_PREFIX).match(url) is not None
  )
