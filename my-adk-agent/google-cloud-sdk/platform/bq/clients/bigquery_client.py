#!/usr/bin/env python
"""BigqueryClient class."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import enum
from http import client as http_client_lib
import json
import logging
import tempfile
import time
import traceback
from typing import Callable, List, Optional, Union
import urllib

# To configure apiclient logging.
from absl import flags
import certifi
import googleapiclient
from googleapiclient import discovery
import httplib2
from typing_extensions import TypeAlias


import bq_flags
import bq_utils
import credential_loader
from auth import main_credential_loader
from clients import bigquery_http
from clients import utils as bq_client_utils
from clients import wait_printer
from discovery_documents import discovery_document_cache
from discovery_documents import discovery_document_loader
from utils import bq_api_utils
from utils import bq_error
from utils import bq_logging

# TODO(b/388312723): Review if we can remove this try/except block.
try:
  from google.auth import credentials as google_credentials  # pylint: disable=g-import-not-at-top

  _HAS_GOOGLE_AUTH = True
except ImportError:
  _HAS_GOOGLE_AUTH = False

# TODO(b/388312723): Review if we can remove this try/except block.
try:
  import google_auth_httplib2  # pylint: disable=g-import-not-at-top

  _HAS_GOOGLE_AUTH_HTTPLIB2 = True
except ImportError:
  _HAS_GOOGLE_AUTH_HTTPLIB2 = False

# A unique non-None default, for use in kwargs that need to
# distinguish default from None.
_DEFAULT = object()

LegacyAndGoogleAuthCredentialsUnionType = Union[
    main_credential_loader.GoogleAuthCredentialsUnionType,
    credential_loader.CredentialsFromFlagsUnionType,
]

Service = bq_api_utils.Service

Http: TypeAlias = Union[
    httplib2.Http,
]

AuthorizedHttp: TypeAlias = Union[
    httplib2.Http,
    'google_auth_httplib2.AuthorizedHttp',
]


def CreateHttp(
    proxy_info: Optional[httplib2.ProxyInfo] = None,
    ca_certs: Optional[str] = None,
    disable_ssl_validation: Optional[bool] = None,
) -> httplib2.Http:
  """Returns the httplib2 Http to use."""
  if not proxy_info:
    proxy_info = httplib2.proxy_info_from_environment
    if flags.FLAGS.proxy_address and flags.FLAGS.proxy_port:
      try:
        port = int(flags.FLAGS.proxy_port)
      except ValueError as e:
        raise ValueError(
            'Invalid value for proxy_port: {}'.format(flags.FLAGS.proxy_port)
        ) from e
      proxy_info = httplib2.ProxyInfo(
          proxy_type=3,
          proxy_host=flags.FLAGS.proxy_address,
          proxy_port=port,
          proxy_user=flags.FLAGS.proxy_username or None,
          proxy_pass=flags.FLAGS.proxy_password or None,
      )

  if not ca_certs:
    ca_certs = flags.FLAGS.ca_certificates_file or certifi.where()
  if disable_ssl_validation is None:
    disable_ssl_validation = flags.FLAGS.disable_ssl_validation

  http = httplib2.Http(
      proxy_info=proxy_info,
      ca_certs=ca_certs,
      disable_ssl_certificate_validation=disable_ssl_validation,
  )

  if hasattr(http, 'redirect_codes'):
    http.redirect_codes = set(http.redirect_codes) - {308}

  return http


class BigqueryClient:
  """Class encapsulating interaction with the BigQuery service."""

  class JobCreationMode(str, enum.Enum):
    """Enum of job creation mode."""

    JOB_CREATION_REQUIRED = 'JOB_CREATION_REQUIRED'
    JOB_CREATION_OPTIONAL = 'JOB_CREATION_OPTIONAL'

  def __init__(
      self,
      *,
      api: str,
      api_version: str,
      project_id: Optional[str] = '',
      dataset_id: Optional[str] = '',
      discovery_document: Union[bytes, object, None] = _DEFAULT,
      job_property: str = '',
      trace: Optional[str] = None,
      sync: bool = True,
      wait_printer_factory: Optional[
          Callable[[], wait_printer.WaitPrinter]
      ] = wait_printer.TransitionWaitPrinter,
      job_id_generator: bq_client_utils.JobIdGenerator = bq_client_utils.JobIdGeneratorIncrementing(
          bq_client_utils.JobIdGeneratorRandom()
      ),
      max_rows_per_request: Optional[int] = None,
      quota_project_id: Optional[str] = None,
      use_google_auth: bool = False,
      credentials: Optional[LegacyAndGoogleAuthCredentialsUnionType] = None,
      enable_resumable_uploads: bool = True,
      **kwds,
  ):
    """Initializes BigqueryClient.

    Required keywords:
      api: the api to connect to, for example "bigquery".
      api_version: the version of the api to connect to, for example "v2".

    Optional keywords:
      project_id: a default project id to use. While not required for
        initialization, a project_id is required when calling any
        method that creates a job on the server. Methods that have
        this requirement pass through **kwds, and will raise
        bq_error.BigqueryClientConfigurationError if no project_id can be
        found.
      dataset_id: a default dataset id to use.
      discovery_document: the discovery document to use. If None, one
        will be retrieved from the discovery api. If not specified,
        the built-in discovery document will be used.
      job_property: a list of "key=value" strings defining properties
        to apply to all job operations.
      trace: a tracing header to include in all bigquery api requests.
      sync: boolean, when inserting jobs, whether to wait for them to
        complete before returning from the insert request.
      wait_printer_factory: a function that returns a WaitPrinter.
        This will be called for each job that we wait on. See WaitJob().

    Raises:
      ValueError: if keywords are missing or incorrectly specified.
    """
    super().__init__()
    self.api = api
    self.api_version = api_version
    self.project_id = project_id
    self.dataset_id = dataset_id
    self.discovery_document = discovery_document
    self.job_property = job_property
    self.trace = trace
    self.sync = sync
    self.wait_printer_factory = wait_printer_factory
    self.job_id_generator = job_id_generator
    self.max_rows_per_request = max_rows_per_request
    self.quota_project_id = quota_project_id
    self.use_google_auth = use_google_auth
    self.credentials = credentials
    self.enable_resumable_uploads = enable_resumable_uploads
    # TODO(b/324243535): Delete this block to make attributes explicit.
    for key, value in kwds.items():
      setattr(self, key, value)
    self._apiclient = None
    self._routines_apiclient = None
    self._row_access_policies_apiclient = None
    self._op_transfer_client = None
    self._op_reservation_client = None
    self._op_bi_reservation_client = None
    self._models_apiclient = None
    self._op_connection_service_client = None
    self._iam_policy_apiclient = None
    default_flag_values = {
        'iam_policy_discovery_document': _DEFAULT,
    }
    for flagname, default in default_flag_values.items():
      if not hasattr(self, flagname):
        setattr(self, flagname, default)

  columns_to_include_for_transfer_run = [
      'updateTime',
      'schedule',
      'runTime',
      'scheduleTime',
      'params',
      'endTime',
      'dataSourceId',
      'destinationDatasetId',
      'state',
      'startTime',
      'name',
  ]

  # These columns appear to be empty with scheduling a new transfer run
  # so there are listed as excluded from the transfer run output.
  columns_excluded_for_make_transfer_run = ['schedule', 'endTime', 'startTime']

  def GetHttp(
      self,
  ) -> AuthorizedHttp:
    """Returns the httplib2 Http to use."""

    proxy_info = None
    disable_ssl = flags.FLAGS.disable_ssl_validation
    use_ecp = False


    # Let CreateHttp handle command-line proxy flags only if ECP is NOT active.
    if not use_ecp:
      logging.info('Configured httplib2 with manual proxy')

    http = CreateHttp(proxy_info=proxy_info, disable_ssl_validation=disable_ssl)

    # Apply mTLS credentials ONLY if NOT using the ECP proxy.
    # The ECP proxy handles the mTLS handshake.
    if flags.FLAGS.mtls and not use_ecp:
      logging.info('mTLS enabled, adding mTLS credentials to Http.')
      _, self._cert_file = tempfile.mkstemp()
      _, self._key_file = tempfile.mkstemp()
      discovery.add_mtls_creds(
          http, discovery.get_client_options(), self._cert_file, self._key_file
      )
    elif flags.FLAGS.mtls and use_ecp:
      logging.info(
          'mTLS enabled, but using ECP HTTP Proxy. Skipping direct mTLS creds'
          ' in httplib2.'
      )

    return http

  def GetDiscoveryUrl(
      self,
      service: Service,
      api_version: str,
      domain_root: Optional[str] = None,
      labels: Optional[str] = None,
  ) -> str:
    """Returns the url to the discovery document for bigquery."""
    discovery_url = None  # pylint:disable=unused-variable
    if not discovery_url:
      discovery_url = bq_api_utils.get_discovery_url_from_root_url(
          domain_root
          or bq_api_utils.get_tpc_root_url_from_flags(
              service=service, inputted_flags=bq_flags
          ),
          api_version=api_version,
      )
    return discovery_url

  def GetAuthorizedHttp(
      self,
      credentials: LegacyAndGoogleAuthCredentialsUnionType,
      http: Http,
  ) -> AuthorizedHttp:
    """Returns an http client that is authorized with the given credentials."""

    if self.use_google_auth:
      if not _HAS_GOOGLE_AUTH:
        logging.error(
            'System is set to use `google.auth`, but it did not load.'
        )
      if not isinstance(credentials, google_credentials.Credentials):
        logging.error(
            'The system is using `google.auth` but the parsed credentials are'
            ' of an incorrect type: %s',
            type(credentials),
        )
    else:
      logging.debug('System is set to not use `google.auth`.')

    # LINT.IfChange(http_authorization)
    if _HAS_GOOGLE_AUTH and isinstance(
        credentials, google_credentials.Credentials
    ):
      if not _HAS_GOOGLE_AUTH_HTTPLIB2:
        raise ValueError(
            'Credentials from google.auth specified, but '
            'google-api-python-client is unable to use these credentials '
            'unless google-auth-httplib2 is installed. Please install '
            'google-auth-httplib2.'
        )
      return google_auth_httplib2.AuthorizedHttp(credentials, http=http)
    # Note: This block simplified adding typing and should be removable when
    # legacy credentials are removed.
    if hasattr(credentials, 'authorize'):
      return credentials.authorize(http)
    else:
      raise TypeError('Unsupported credential type: {type(credentials)}')
    # LINT.ThenChange(
    #     //depot/google3/cloud/helix/testing/e2e/python_api_client/api_client_lib.py:http_authorization,
    #     //depot/google3/cloud/helix/testing/e2e/python_api_client/api_client_util.py:http_authorization,
    # )


  def _LoadDiscoveryDocumentLocal(
      self,
      service: Service,
      discovery_url: Optional[str],
      api_version: str,
  ) -> Optional[Union[str, bytes, object]]:
    """Loads the local discovery document for the given service.

    Args:
      service: The BigQuery service being used.
      discovery_url: The URL to load the discovery doc from.
      api_version: The API version for the targeted discovery doc.

    Returns:
      discovery_document The loaded discovery document.
    """

    discovery_document = None
    if self.discovery_document != _DEFAULT:
      discovery_document = self.discovery_document
      logging.info(
          'Skipping local "%s" discovery document load since discovery_document'
          ' has a value: %s',
          service,
          discovery_document,
      )
      return discovery_document
    if discovery_url is not None:
      logging.info(
          'Skipping the local "%s" discovery document load since discovery_url'
          ' has a value',
          service,
      )
    elif bq_flags.BIGQUERY_DISCOVERY_API_KEY_FLAG.present:
      logging.info(
          'Skipping local "%s" discovery document load since the'
          ' bigquery_discovery_api_key flag was used',
          service,
      )
    else:
      # Load the local api description if one exists and is supported.
      try:
        discovery_document = (
            discovery_document_loader.load_local_discovery_doc_from_service(
                service=service,
                api=self.api,
                api_version=api_version,
            )
        )
        if discovery_document:
          logging.info('The "%s" discovery doc is already loaded', service)
      except FileNotFoundError as e:
        logging.warning(
            'Failed to load the "%s" discovery doc from local files: %s',
            service,
            e,
        )
    return discovery_document


  def _LoadDiscoveryDocumentUrl(
      self,
      service: Service,
      http: AuthorizedHttp,
      discovery_url: str,
  ) -> Optional[Union[str, bytes, object]]:
    """Loads the discovery document from the provided URL.

    Args:
      service: The BigQuery service being used.
      http: Http object to be used to execute request.
      discovery_url: The URL to load the discovery doc from.

    Returns:
      discovery_document The loaded discovery document.

    Raises:
      bq_error.BigqueryClientError: If the request to load the discovery
      document fails.
    """

    discovery_document = None
    # Attempt to retrieve discovery doc with retry logic for transient,
    # retry-able errors.
    max_retries = 3
    iterations = 0
    headers = (
        {'X-ESF-Use-Cloud-UberMint-If-Enabled': '1'}
        if hasattr(self, 'use_uber_mint') and self.use_uber_mint
        else None
    )
    while iterations < max_retries and discovery_document is None:
      if iterations > 0:
        # Wait briefly before retrying with exponentially increasing wait.
        time.sleep(2**iterations)
      iterations += 1
      try:
        logging.info(
            'Requesting "%s" discovery document from %s',
            service,
            discovery_url,
        )
        if headers:
          response_metadata, discovery_document = http.request(
              discovery_url, headers=headers
          )
        else:
          response_metadata, discovery_document = http.request(discovery_url)
        discovery_document = discovery_document.decode('utf-8')
        if int(response_metadata.get('status')) >= 400:
          msg = 'Got %s response from discovery url: %s' % (
              response_metadata.get('status'),
              discovery_url,
          )
          logging.error('%s:\n%s', msg, discovery_document)
          raise bq_error.BigqueryCommunicationError(msg)
      except (
          httplib2.HttpLib2Error,
          googleapiclient.errors.HttpError,
          http_client_lib.HTTPException,
      ) as e:
        # We can't find the specified server. This can be thrown for
        # multiple reasons, so inspect the error.
        if hasattr(e, 'content'):
          if iterations == max_retries:
            content = ''
            if hasattr(e, 'content'):
              content = e.content
            raise bq_error.BigqueryCommunicationError(
                'Cannot contact server. Please try again.\nError: %r'
                '\nContent: %s' % (e, content)
            )
        else:
          if iterations == max_retries:
            raise bq_error.BigqueryCommunicationError(
                'Cannot contact server. Please try again.\nTraceback: %s'
                % (traceback.format_exc(),)
            )
      except IOError as e:
        if iterations == max_retries:
          raise bq_error.BigqueryCommunicationError(
              'Cannot contact server. Please try again.\nError: %r' % (e,)
          )
      except googleapiclient.errors.UnknownApiNameOrVersion as e:
        # We can't resolve the discovery url for the given server.
        # Don't retry in this case.
        raise bq_error.BigqueryCommunicationError(
            'Invalid API name or version: %s' % (str(e),)
        )
    return discovery_document

  def BuildApiClient(
      self,
      service: Service,
      discovery_url: Optional[str] = None,
      discovery_root_url: Optional[str] = None,
      api_version: Optional[str] = None,
      domain_root: Optional[str] = None,
      labels: Optional[str] = None,
  ) -> discovery.Resource:
    """Build and return BigQuery Dynamic client from discovery document."""
    logging.info(
        'BuildApiClient discovery_url: %s, discovery_root_url: %s',
        discovery_url,
        discovery_root_url,
    )
    if api_version is None:
      api_version = self.api_version
    # If self.credentials is of type google.auth, it has to be cleared of the
    # _quota_project_id value later on in this function for discovery requests.
    # bigquery_model has to be built with the quota project retained, so in this
    # version of the implementation, it's built before discovery requests take
    # place.
    bigquery_model = bigquery_http.BigqueryModel(
        trace=self.trace,
        quota_project_id=bq_utils.GetEffectiveQuotaProjectIDForHTTPHeader(
            quota_project_id=self.quota_project_id,
            project_id=self.project_id,
            use_google_auth=self.use_google_auth,
            credentials=self.credentials,
        ),
    )
    bq_request_builder = bigquery_http.BigqueryHttp.Factory(
        bigquery_model,
    )

    # Clean up quota project ID from Google Auth credentials.
    # This is specifically needed to construct a http object used for discovery
    # requests below as quota project ID shouldn't participate in discovery
    # document retrieval, otherwise the discovery request would result in a
    # permission error seen in b/321286043.
    if self.use_google_auth and hasattr(self.credentials, '_quota_project_id'):
      self.credentials._quota_project_id = None  # pylint: disable=protected-access

    http = None
    if not http:
      http_client = self.GetHttp()
      http = self.GetAuthorizedHttp(self.credentials, http_client)

    discovery_document = None
    # First, trying to load the discovery document from the local package.
    if discovery_document is None:
      discovery_document = self._LoadDiscoveryDocumentLocal(
          service=service,
          discovery_url=discovery_url,
          api_version=api_version,
      )

    # If document was not loaded from the local package and
    # discovery_url is not provided, we will generate the url to fetch from the
    # server.
    discovery_url_not_provided = discovery_url is None
    if discovery_document is None and discovery_url is None:
      discovery_url = self.GetDiscoveryUrl(
          service=service,
          api_version=api_version,
          domain_root=domain_root,
          labels=labels,
      )


    # If discovery_document is still not loaded, fetch it from the server.
    if not discovery_document:
      discovery_document = self._LoadDiscoveryDocumentUrl(
          service=service,
          http=http,
          discovery_url=discovery_url,
      )

    discovery_document_to_build_client = self.OverrideEndpoint(
        discovery_document=discovery_document,
        service=service,
        discovery_root_url=discovery_root_url,
    )

    bq_logging.SaveStringToLogDirectoryIfAvailable(
        file_prefix='discovery_document',
        content=discovery_document_to_build_client,
        apilog=bq_flags.APILOG.value,
    )

    try:
      # If the underlying credentials object used for authentication is of type
      # google.auth, its quota project ID will have been removed earlier in this
      # function if one was provided explicitly. This specific http object
      # created from that modified credentials object must be the one used for
      # the discovery requests, otherwise they would result in a permission
      # error as seen in b/321286043.
      built_client = discovery.build_from_document(
          discovery_document_to_build_client,
          http=http,
          model=bigquery_model,
          requestBuilder=bq_request_builder,
      )
    except Exception:
      logging.error(
          'Error building from the "%s" discovery document: %s',
          service,
          discovery_document,
      )
      raise


    return built_client

  @property
  def apiclient(self) -> discovery.Resource:
    """Returns a singleton ApiClient built for the BigQuery core API."""
    if self._apiclient:
      logging.info('Using the cached BigQuery API client')
    else:
      self._apiclient = self.BuildApiClient(service=Service.BIGQUERY)
    return self._apiclient

  def GetModelsApiClient(self) -> discovery.Resource:
    """Returns the apiclient attached to self."""
    if self._models_apiclient is None:
      self._models_apiclient = self.BuildApiClient(service=Service.BIGQUERY)
    return self._models_apiclient

  def GetRoutinesApiClient(self) -> discovery.Resource:
    """Return the apiclient attached to self."""
    if self._routines_apiclient is None:
      self._routines_apiclient = self.BuildApiClient(service=Service.BIGQUERY)
    return self._routines_apiclient

  def GetRowAccessPoliciesApiClient(self) -> discovery.Resource:
    """Return the apiclient attached to self."""
    if self._row_access_policies_apiclient is None:
      self._row_access_policies_apiclient = self.BuildApiClient(
          service=Service.BIGQUERY
      )
    return self._row_access_policies_apiclient

  def GetIAMPolicyApiClient(self) -> discovery.Resource:
    """Return the apiclient attached to self."""
    if self._iam_policy_apiclient is None:
      self._iam_policy_apiclient = self.BuildApiClient(
          service=Service.BQ_IAM,
      )
    return self._iam_policy_apiclient

  def GetInsertApiClient(self) -> discovery.Resource:
    """Return the apiclient that supports insert operation."""
    discovery_url = None  # pylint: disable=unused-variable
    if discovery_url:
      return self.BuildApiClient(
          discovery_url=discovery_url, service=Service.BIGQUERY
      )
    return self.apiclient

  def GetTransferV1ApiClient(
      self, transferserver_address: Optional[str] = None
  ) -> discovery.Resource:
    """Return the apiclient that supports Transfer v1 operation."""
    logging.info(
        'GetTransferV1ApiClient transferserver_address: %s',
        transferserver_address,
    )

    if self._op_transfer_client:
      logging.info('Using the cached Transfer API client')
    else:
      path = transferserver_address or bq_api_utils.get_tpc_root_url_from_flags(
          service=Service.DTS, inputted_flags=bq_flags
      )
      self._op_transfer_client = self.BuildApiClient(
          domain_root=path,
          discovery_root_url=path,
          api_version='v1',
          service=Service.DTS,
      )
    return self._op_transfer_client

  def GetReservationApiClient(
      self, reservationserver_address: Optional[str] = None
  ) -> discovery.Resource:
    """Return the apiclient that supports reservation operations."""
    if self._op_reservation_client:
      logging.info('Using the cached Reservations API client')
    else:
      path = (
          reservationserver_address
          or bq_api_utils.get_tpc_root_url_from_flags(
              service=Service.RESERVATIONS,
              inputted_flags=bq_flags,
          )
      )
      reservation_version = 'v1'
      labels = None
      self._op_reservation_client = self.BuildApiClient(
          service=Service.RESERVATIONS,
          domain_root=path,
          discovery_root_url=path,
          api_version=reservation_version,
          labels=labels,
      )
    return self._op_reservation_client

  def GetConnectionV1ApiClient(
      self, connection_service_address: Optional[str] = None
  ) -> discovery.Resource:
    """Return the apiclient that supports connections operations."""
    if self._op_connection_service_client:
      logging.info('Using the cached Connections API client')
    else:
      path = (
          connection_service_address
          or bq_api_utils.get_tpc_root_url_from_flags(
              service=Service.CONNECTIONS,
              inputted_flags=bq_flags,
          )
      )
      discovery_url = bq_api_utils.get_discovery_url_from_root_url(
          path, api_version='v1'
      )
      discovery_url = bq_api_utils.add_api_key_to_discovery_url(
          discovery_url=discovery_url,
          universe_domain=bq_flags.UNIVERSE_DOMAIN.value,
          inputted_flags=bq_flags,
      )
      self._op_connection_service_client = self.BuildApiClient(
          discovery_url=discovery_url,
          discovery_root_url=path,
          service=Service.CONNECTIONS,
          api_version='v1',
      )
    return self._op_connection_service_client

  def OverrideEndpoint(
      self,
      discovery_document: Union[str, bytes],
      service: Service,
      discovery_root_url: Optional[str] = None,
  ) -> Optional[str]:
    """Override rootUrl for regional endpoints.

    Args:
      discovery_document: BigQuery discovery document.
      service: The BigQuery service being used.
      discovery_root_url: The root URL to use for the discovery document.

    Returns:
      discovery_document updated discovery document.

    Raises:
      bq_error.BigqueryClientError: if location is not set and
        use_regional_endpoints is.
    """
    if discovery_document is None:
      return discovery_document

    discovery_document = bq_api_utils.parse_discovery_doc(discovery_document)

    logging.info(
        'Discovery doc routing values being considered for updates: rootUrl:'
        ' (%s), basePath: (%s), baseUrl: (%s)',
        discovery_document['rootUrl'],
        discovery_document['basePath'],
        discovery_document['baseUrl'],
    )

    discovery_document['rootUrl'] = bq_api_utils.get_tpc_root_url_from_flags(
        service=service, inputted_flags=bq_flags
    )


    discovery_document['baseUrl'] = urllib.parse.urljoin(
        discovery_document['rootUrl'], discovery_document['servicePath']
    )

    logging.info(
        'Discovery doc routing values post updates: rootUrl: (%s), basePath:'
        ' (%s), baseUrl: (%s)',
        discovery_document['rootUrl'],
        discovery_document['basePath'],
        discovery_document['baseUrl'],
    )

    return json.dumps(discovery_document)

