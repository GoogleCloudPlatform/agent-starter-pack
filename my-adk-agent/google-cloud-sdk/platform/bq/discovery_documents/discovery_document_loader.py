#!/usr/bin/env python
"""Methods for loading discovery documents for Google Cloud APIs.

Discovery Documents are used to create API Clients.
"""

import pkgutil
from typing import Optional, Union

from absl import logging

from utils import bq_consts

PKG_NAME = 'bigquery_client'

# Latest version of the BigQuery API discovery_document from discovery_next.
DISCOVERY_NEXT_BIGQUERY = 'discovery_next/bigquery.json'
# Latest version of the IAM Policy API discovery_document from discovery_next.
DISCOVERY_NEXT_IAM_POLICY = 'discovery_next/iam-policy.json'
# Latest version of the Reservations discovery_document from discovery_next.
DISCOVERY_NEXT_RESERVATIONS = (
    'discovery_next/bigqueryreservation_google_rest_v1.json'
)


SUPPORTED_BIGQUERY_APIS = frozenset([
    'https://www.googleapis.com',
    'https://bigquery.googleapis.com',
    'https://bigqueryreservation.googleapis.com',
])


SERVICES_TO_LOCAL_DISCOVERY_DOC_MAP = {
    bq_consts.Service.BIGQUERY: DISCOVERY_NEXT_BIGQUERY,
    bq_consts.Service.CONNECTIONS: DISCOVERY_NEXT_BIGQUERY,
    bq_consts.Service.RESERVATIONS: DISCOVERY_NEXT_RESERVATIONS,
    bq_consts.Service.BQ_IAM: DISCOVERY_NEXT_IAM_POLICY,
}


# TODO(b/318711380): Local discovery load for different APIs.
def load_local_discovery_doc_from_service(
    service: bq_consts.Service,
    api: str,
    api_version: str,
) -> Union[None, bytes]:
  """Loads the discovery document for a service."""
  if service not in SERVICES_TO_LOCAL_DISCOVERY_DOC_MAP:
    logging.info(
        'Skipping local %s discovery document load since the service is not yet'
        ' supported',
        service,
    )
    return
  if service == bq_consts.Service.BIGQUERY and (
      api not in SUPPORTED_BIGQUERY_APIS or api_version != 'v2'
  ):
    # For now, align this strictly with the default flag values. We can loosen
    # this but for a first pass I'm keeping the current code flow.
    logging.info(
        'Loading the "%s" discovery doc from the server since this is not'
        ' v2 (%s) and the API endpoint (%s) is not one of (%s).',
        service,
        api_version,
        api,
        ', '.join(SUPPORTED_BIGQUERY_APIS),
    )
    return
  if service != bq_consts.Service.BQ_IAM and api not in SUPPORTED_BIGQUERY_APIS:
    # For non-IAM APIs, we only support local discovery docs for selected API
    # endpoints.
    logging.info(
        'Loading the "%s" discovery doc from the server since the API endpoint'
        ' (%s) is not one of (%s).',
        service,
        api,
        ', '.join(SUPPORTED_BIGQUERY_APIS),
    )
    return
  return load_local_discovery_doc(SERVICES_TO_LOCAL_DISCOVERY_DOC_MAP[service])


def load_local_discovery_doc(doc_filename: str) -> bytes:
  """Loads the discovery document for `doc_filename` with `version` from package files.

  Example:
    bq_disc_doc = discovery_document_loader
      .load_local_discovery_doc('discovery_next/bigquery.json')

  Args:
    doc_filename: [str], The filename of the discovery document to be loaded.

  Raises:
    FileNotFoundError: If no discovery doc could be loaded.

  Returns:
    `bytes`, On success, A json object with the contents of the
    discovery document. On failure, None.
  """
  doc = _fetch_discovery_doc_from_pkg(PKG_NAME, doc_filename)

  if not doc:
    raise FileNotFoundError(
        'Failed to load discovery doc from resource path: %s.%s'
        % (PKG_NAME, doc_filename)
    )

  return doc


def _fetch_discovery_doc_from_pkg(
    package: str, resource: str
) -> Optional[bytes]:
  """Loads a discovery doc as `bytes` specified by `package` and `resource` returning None on error."""
  try:
    raw_doc = pkgutil.get_data(package, resource)
  # TODO(b/286571605) Ideally this would be ModuleNotFoundError but it's not
  # supported before python3.6 so we need to be less specific for now.
  except ImportError:
    raw_doc = None
  if not raw_doc:
    logging.warning(
        'Failed to load discovery doc from (package, resource): %s, %s',
        package,
        resource,
    )
  else:
    logging.info(
        'Successfully loaded discovery doc from (package, resource): %s, %s',
        package,
        resource,
    )
  return raw_doc
