#!/usr/bin/env python
"""The BigQuery CLI query command."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import json
import logging
import sys
from typing import Optional

from absl import app
from absl import flags

import bq_flags
import bq_utils
from clients import bigquery_client
from clients import bigquery_client_extended
from clients import client_data_transfer
from clients import client_job
from clients import client_table
from clients import utils as bq_client_utils
from frontend import bigquery_command
from frontend import bq_cached_client
from frontend import flags as frontend_flags
from frontend import utils as frontend_utils
from frontend import utils_data_transfer
from frontend import utils_flags
from frontend import utils_formatting
from utils import bq_error
from utils import bq_id_utils
from pyglib import stringutil

FLAGS = flags.FLAGS

# These aren't relevant for user-facing docstrings:
# pylint: disable=g-doc-return-or-yield
# pylint: disable=g-doc-args


class Query(bigquery_command.BigqueryCmd):
  usage = """query <sql>"""
  command = 'query'

  def __init__(self, name: str, fv: flags.FlagValues):
    super(Query, self).__init__(name, fv)
    flags.DEFINE_string(
        'destination_table',
        '',
        'Name of destination table for query results.',
        flag_values=fv,
    )
    flags.DEFINE_string(
        'destination_schema',
        '',
        'Schema for the destination table. Either a filename or '
        'a comma-separated list of fields in the form name[:type].',
        flag_values=fv,
    )
    flags.DEFINE_integer(
        'start_row',
        0,
        'First row to return in the result.',
        short_name='s',
        flag_values=fv,
    )
    flags.DEFINE_integer(
        'max_rows',
        100,
        'How many rows to return in the result.',
        short_name='n',
        flag_values=fv,
    )
    flags.DEFINE_boolean(
        'batch',
        None,
        'Whether to run the query in batch mode. Ignored if --priority flag is '
        'specified.',
        flag_values=fv,
    )
    flags.DEFINE_enum(
        'priority',
        None,
        [
            'HIGH',
            'INTERACTIVE',
            'BATCH',
        ],
        'Query priority. If not specified, priority is determined using the '
        '--batch flag. Options include:'
        '\n HIGH (only available for whitelisted reservations)'
        '\n INTERACTIVE'
        '\n BATCH',
        flag_values=fv,
    )
    flags.DEFINE_boolean(
        'append_table',
        False,
        'When a destination table is specified, whether or not to append.',
        flag_values=fv,
    )
    flags.DEFINE_boolean(
        'rpc',
        False,
        'If true, use rpc-style query API instead of jobs.insert().',
        flag_values=fv,
    )
    flags.DEFINE_string(
        'request_id',
        None,
        'The request_id to use for the jobs.query request. '
        'Only valid when used in combination with --rpc.',
        flag_values=fv,
    )
    flags.DEFINE_boolean(
        'replace',
        False,
        'If true, erase existing contents before loading new data.',
        flag_values=fv,
    )
    flags.DEFINE_boolean(
        'replace_data',
        False,
        'If true, erase existing contents only, other table metadata like'
        ' schema is kept.',
        flag_values=fv,
    )
    flags.DEFINE_boolean(
        'allow_large_results',
        None,
        'Enables larger destination table sizes for legacy SQL queries.',
        flag_values=fv,
    )
    flags.DEFINE_boolean(
        'dry_run',
        None,
        'Whether the query should be validated without executing.',
        flag_values=fv,
    )
    flags.DEFINE_boolean(
        'require_cache',
        None,
        'Whether to only run the query if it is already cached.',
        flag_values=fv,
    )
    flags.DEFINE_boolean(
        'use_cache',
        None,
        'Whether to use the query cache to avoid rerunning cached queries.',
        flag_values=fv,
    )
    flags.DEFINE_float(
        'min_completion_ratio',
        None,
        '[Experimental] The minimum fraction of data that must be scanned '
        'before a query returns. If not set, the default server value (1.0) '
        'will be used.',
        lower_bound=0,
        upper_bound=1.0,
        flag_values=fv,
    )
    flags.DEFINE_boolean(
        'flatten_results',
        None,
        'Whether to flatten nested and repeated fields in the result schema '
        'for legacy SQL queries. '
        'If not set, the default behavior is to flatten.',
        flag_values=fv,
    )
    flags.DEFINE_multi_string(
        'external_table_definition',
        None,
        'Specifies a table name and either an inline table definition '
        'or a path to a file containing a JSON table definition to use in the '
        'query. The format is "table_name::path_to_file_with_json_def" or '
        '"table_name::schema@format=uri@connection". '
        'For example, '
        '"--external_table_definition=Example::/tmp/example_table_def.txt" '
        'will define a table named "Example" using the URIs and schema '
        'encoded in example_table_def.txt.',
        flag_values=fv,
    )
    flags.DEFINE_multi_string(
        'udf_resource',
        None,
        'The URI or local filesystem path of a code file to load and '
        'evaluate immediately as a User-Defined Function resource.',
        flag_values=fv,
    )
    flags.DEFINE_integer(
        'maximum_billing_tier',
        None,
        'The upper limit of billing tier for the query.',
        flag_values=fv,
    )
    flags.DEFINE_integer(
        'maximum_bytes_billed',
        None,
        'The upper limit of bytes billed for the query.',
        flag_values=fv,
    )
    flags.DEFINE_boolean(
        'use_legacy_sql',
        None,
        (
            'The choice of using Legacy SQL for the query is optional. If not'
            ' specified, the server will automatically determine the dialect'
            ' based on query information, such as dialect prefixes. If no'
            ' prefixes are found, it will default to Legacy SQL.'
        ),
        flag_values=fv,
    )
    flags.DEFINE_multi_string(
        'schema_update_option',
        None,
        'Can be specified when append to a table, or replace a table partition.'
        ' When specified, the schema of the destination table will be updated '
        'with the schema of the new data. One or more of the following options '
        'can be specified:'
        '\n ALLOW_FIELD_ADDITION: allow new fields to be added'
        '\n ALLOW_FIELD_RELAXATION: allow relaxing required fields to nullable',
        flag_values=fv,
    )
    flags.DEFINE_multi_string(
        'label',
        None,
        'A label to set on a query job. The format is "key:value"',
        flag_values=fv,
    )
    flags.DEFINE_multi_string(
        'parameter',
        None,
        (
            'Either a file containing a JSON list of query parameters, or a'
            ' query parameter in the form "name:type:value". An empty name'
            ' produces a positional parameter. The type may be omitted to'
            ' assume STRING: name::value or ::value. The value "NULL" produces'
            ' a null value.'
        ),
        flag_values=fv,
    )
    flags.DEFINE_string(
        'time_partitioning_type',
        None,
        'Enables time based partitioning on the table and set the type. The '
        'default value is DAY, which will generate one partition per day. '
        'Other supported values are HOUR, MONTH, and YEAR.',
        flag_values=fv,
    )
    flags.DEFINE_integer(
        'time_partitioning_expiration',
        None,
        'Enables time based partitioning on the table and sets the number of '
        'seconds for which to keep the storage for the partitions in the table.'
        ' The storage in a partition will have an expiration time of its '
        'partition time plus this value.',
        flag_values=fv,
    )
    flags.DEFINE_string(
        'time_partitioning_field',
        None,
        'Enables time based partitioning on the table and the table will be '
        'partitioned based on the value of this field. If time based '
        'partitioning is enabled without this value, the table will be '
        'partitioned based on the loading time.',
        flag_values=fv,
    )
    flags.DEFINE_string(
        'range_partitioning',
        None,
        'Enables range partitioning on the table. The format should be '
        '"field,start,end,interval". The table will be partitioned based on the'
        ' value of the field. Field must be a top-level, non-repeated INT64 '
        'field. Start, end, and interval are INT64 values defining the ranges.',
        flag_values=fv,
    )
    flags.DEFINE_boolean(
        'require_partition_filter',
        None,
        'Whether to require partition filter for queries over this table. '
        'Only apply to partitioned table.',
        flag_values=fv,
    )
    flags.DEFINE_string(
        'clustering_fields',
        None,
        'Comma-separated list of field names that specifies the columns on '
        'which a table is clustered. To remove the clustering, set an empty '
        'value.',
        flag_values=fv,
    )
    flags.DEFINE_string(
        'destination_kms_key',
        None,
        'Cloud KMS key for encryption of the destination table data.',
        flag_values=fv,
    )
    flags.DEFINE_string(
        'script_statement_timeout_ms',
        None,
        'Maximum time to complete each statement in a script.',
        flag_values=fv,
    )
    flags.DEFINE_string(
        'script_statement_byte_budget',
        None,
        'Maximum bytes that can be billed for any statement in a script.',
        flag_values=fv,
    )
    flags.DEFINE_integer(
        'max_statement_results',
        100,
        'Maximum number of script statements to display the results for.',
        flag_values=fv,
    )
    flags.DEFINE_integer(
        'max_child_jobs',
        1000,
        'Maximum number of child jobs to fetch results from after executing a '
        'script.  If the number of child jobs exceeds this limit, only the '
        'final result will be displayed.',
        flag_values=fv,
    )
    flags.DEFINE_string(
        'job_timeout_ms',
        None,
        'Maximum time to run the entire script.',
        flag_values=fv,
    )
    flags.DEFINE_string(
        'schedule',
        None,
        'Scheduled query schedule. If non-empty, this query requests could '
        'create a scheduled query understand the customer project. See '
        'https://cloud.google.com/appengine/docs/flexible/python/scheduling-jobs-with-cron-yaml#the_schedule_format '  # pylint: disable=line-too-long
        'for the schedule format',
        flag_values=fv,
    )
    flags.DEFINE_bool(
        'no_auto_scheduling',
        False,
        'Create a scheduled query configuration with automatic scheduling '
        'disabled.',
        flag_values=fv,
    )
    flags.DEFINE_string(
        'display_name',
        '',
        'Display name for the created scheduled query configuration.',
        flag_values=fv,
    )
    flags.DEFINE_string(
        'target_dataset',
        None,
        'Target dataset used to create scheduled query.',
        flag_values=fv,
    )
    flags.DEFINE_multi_string(
        'connection_property', None, 'Connection properties', flag_values=fv
    )
    flags.DEFINE_boolean(
        'create_session',
        None,
        'Whether to create a new session and run the query in the sesson.',
        flag_values=fv,
    )
    flags.DEFINE_string(
        'session_id',
        None,
        'An existing session id where the query will be run.',
        flag_values=fv,
    )
    flags.DEFINE_bool(
        'continuous',
        False,
        'Whether to run the query as continuous query',
        flag_values=fv,
    )
    flags.DEFINE_enum_class(
        'job_creation_mode',
        None,
        bigquery_client.BigqueryClient.JobCreationMode,
        'An option on job creation. Options include:'
        '\n JOB_CREATION_REQUIRED'
        '\n JOB_CREATION_OPTIONAL'
        '\n Specifying JOB_CREATION_OPTIONAL may speed up the query if the'
        ' query engine decides to bypass job creation.',
        flag_values=fv,
    )
    flags.DEFINE_integer(
        'max_slots',
        None,
        'Cap on target rate of slot consumption by the query. Requires'
        ' --alpha=query_max_slots to be specified.',
        flag_values=fv,
    )
    self.reservation_id_for_a_job_flag = (
        frontend_flags.define_reservation_id_for_a_job(flag_values=fv)
    )
    self._ProcessCommandRc(fv)

  def RunWithArgs(self, *args) -> Optional[int]:
    # pylint: disable=g-doc-exception
    """Execute a query.

    Query should be specified on command line, or passed on stdin.

    Examples:
      bq query 'select count(*) from publicdata:samples.shakespeare'
      echo 'select count(*) from publicdata:samples.shakespeare' | bq query

    Usage:
      query [<sql_query>]

    To cancel a query job, run `bq cancel job_id`.
    """
    logging.debug('In _Query.RunWithArgs: %s', args)
    bq_utils.SetBqCliUserAgentResource('jobs', overwrite=True)
    # Set up the params that are the same for rpc-style and jobs.insert()-style
    # queries.
    kwds = {
        'dry_run': self.dry_run,
        'use_cache': self.use_cache,
        'min_completion_ratio': self.min_completion_ratio,
    }
    if self.external_table_definition:
      external_table_defs = {}
      for raw_table_def in self.external_table_definition:
        table_name_and_def = raw_table_def.split('::', 1)
        if len(table_name_and_def) < 2:
          raise app.UsageError(
              'external_table_definition parameter is invalid, expected :: as '
              'the separator.'
          )
        external_table_defs[table_name_and_def[0]] = (
            frontend_utils.GetExternalDataConfig(table_name_and_def[1])
        )
      kwds['external_table_definitions_json'] = dict(external_table_defs)
    if self.udf_resource:
      kwds['udf_resources'] = frontend_utils.ParseUdfResources(
          self.udf_resource
      )
    if self.maximum_billing_tier:
      kwds['maximum_billing_tier'] = self.maximum_billing_tier
    if self.maximum_bytes_billed:
      kwds['maximum_bytes_billed'] = self.maximum_bytes_billed
    if self.schema_update_option:
      kwds['schema_update_options'] = self.schema_update_option
    if self.label is not None:
      kwds['labels'] = frontend_utils.ParseLabels(self.label)
    if self.request_id is not None:
      kwds['request_id'] = self.request_id
    if self.parameter:
      kwds['query_parameters'] = frontend_utils.ParseParameters(self.parameter)
    query = ' '.join(args)
    if not query:
      query = sys.stdin.read()
    client = bq_cached_client.Client.Get()
    if bq_flags.LOCATION.value:
      kwds['location'] = bq_flags.LOCATION.value
    kwds['use_legacy_sql'] = self.use_legacy_sql
    time_partitioning = frontend_utils.ParseTimePartitioning(
        self.time_partitioning_type,
        self.time_partitioning_expiration,
        self.time_partitioning_field,
        None,
        self.require_partition_filter,
    )
    if time_partitioning is not None:
      kwds['time_partitioning'] = time_partitioning
    range_partitioning = frontend_utils.ParseRangePartitioning(
        self.range_partitioning
    )
    if range_partitioning:
      kwds['range_partitioning'] = range_partitioning
    clustering = frontend_utils.ParseClustering(self.clustering_fields)
    if clustering:
      kwds['clustering'] = clustering
    if self.destination_schema and not self.destination_table:
      raise app.UsageError(
          'destination_schema can only be used with destination_table.'
      )
    read_schema = None
    if self.destination_schema:
      read_schema = bq_client_utils.ReadSchema(self.destination_schema)
    if self.destination_kms_key:
      kwds['destination_encryption_configuration'] = {
          'kmsKeyName': self.destination_kms_key
      }
    if (
        (self.script_statement_timeout_ms is not None)
        or (self.script_statement_byte_budget is not None)
    ):
      script_options = {
          'statementTimeoutMs': self.script_statement_timeout_ms,
          'statementByteBudget': self.script_statement_byte_budget,
      }
      kwds['script_options'] = {
          name: value
          for name, value in script_options.items()
          if value is not None
      }

    if self.schedule or self.no_auto_scheduling:
      bq_utils.SetBqCliUserAgentResource('scheduled_queries', overwrite=True)
      transfer_client = client.GetTransferV1ApiClient()
      reference = 'projects/' + (
          bq_client_utils.GetProjectReference(id_fallbacks=client).projectId
      )
      scheduled_queries_reference = reference + '/dataSources/scheduled_query'
      try:
        transfer_client.projects().dataSources().get(
            name=scheduled_queries_reference
        ).execute()
      except Exception as e:
        raise bq_error.BigqueryAccessDeniedError(
            'Scheduled queries are not enabled on this project. Please enable '
            'them at '
            'https://console.cloud.google.com/bigquery/scheduled-queries',
            {'reason': 'notFound'},
            [],
        ) from e
      if self.use_legacy_sql is None or self.use_legacy_sql:
        raise app.UsageError(
            'Scheduled queries do not support legacy SQL. Please use standard '
            'SQL and set the --use_legacy_sql flag to false.'
        )
      credentials = utils_data_transfer.CheckValidCreds(
          reference, 'scheduled_query', transfer_client
      )
      auth_info = {}
      if not credentials:
        auth_info = utils_data_transfer.RetrieveAuthorizationInfo(
            reference, 'scheduled_query', transfer_client
        )
      schedule_args = client_data_transfer.TransferScheduleArgs(
          schedule=self.schedule,
          disable_auto_scheduling=self.no_auto_scheduling,
      )
      params = {
          'query': query,
      }
      target_dataset = self.target_dataset
      if self.destination_table:
        target_dataset = (
            bq_client_utils.GetTableReference(
                id_fallbacks=client, identifier=self.destination_table
            )
            .GetDatasetReference()
            .datasetId
        )
        destination_table = bq_client_utils.GetTableReference(
            id_fallbacks=client, identifier=self.destination_table
        ).tableId
        params['destination_table_name_template'] = destination_table
      if self.append_table:
        params['write_disposition'] = 'WRITE_APPEND'
      if self.replace:
        params['write_disposition'] = 'WRITE_TRUNCATE'
      if self.replace_data:
        params['write_disposition'] = 'WRITE_TRUNCATE_DATA'
      if self.time_partitioning_field:
        params['partitioning_field'] = self.time_partitioning_field
      if self.time_partitioning_type:
        params['partitioning_type'] = self.time_partitioning_type
      transfer_name = client_data_transfer.create_transfer_config(
          transfer_client=client.GetTransferV1ApiClient(),
          reference=reference,
          data_source='scheduled_query',
          target_dataset=target_dataset,
          display_name=self.display_name,
          params=json.dumps(params),
          auth_info=auth_info,
          destination_kms_key=self.destination_kms_key,
          schedule_args=schedule_args,
          location=bq_flags.LOCATION.value,
      )
      print("Transfer configuration '%s' successfully created." % transfer_name)
      return

    if self.connection_property:
      kwds['connection_properties'] = []
      for key_value in self.connection_property:
        key_value = key_value.split('=', 2)
        if len(key_value) != 2:
          raise app.UsageError(
              'Invalid connection_property syntax; expected key=value'
          )
        kwds['connection_properties'].append(
            {'key': key_value[0], 'value': key_value[1]}
        )
    if self.session_id:
      if 'connection_properties' not in kwds:
        kwds['connection_properties'] = []
      for connection_property in kwds['connection_properties']:
        if connection_property['key'] == 'session_id':
          raise app.UsageError(
              '--session_id should not be set if session_id is specified in '
              '--connection_properties'
          )
      kwds['connection_properties'].append(
          {'key': 'session_id', 'value': self.session_id}
      )
    if self.create_session:
      kwds['create_session'] = self.create_session
    if self.reservation_id_for_a_job_flag.present:
      kwds['reservation_id'] = self.reservation_id_for_a_job_flag.value
    if self.job_timeout_ms:
      kwds['job_timeout_ms'] = self.job_timeout_ms
    if self.max_slots is not None:
      utils_flags.fail_if_not_using_alpha_feature(
          bq_flags.AlphaFeatures.QUERY_MAX_SLOTS
      )
      kwds['max_slots'] = self.max_slots
    if self.rpc:
      if self.allow_large_results:
        raise app.UsageError(
            'allow_large_results cannot be specified in rpc mode.'
        )
      if self.destination_table:
        raise app.UsageError(
            'destination_table cannot be specified in rpc mode.'
        )
      if FLAGS.job_id or FLAGS.fingerprint_job_id:
        raise app.UsageError(
            'job_id and fingerprint_job_id cannot be specified in rpc mode.'
        )
      if self.batch:
        raise app.UsageError('batch cannot be specified in rpc mode.')
      if self.flatten_results:
        raise app.UsageError('flatten_results cannot be specified in rpc mode.')
      if self.continuous:
        raise app.UsageError('continuous cannot be specified in rpc mode.')
      kwds['job_creation_mode'] = self.job_creation_mode
      kwds['max_results'] = self.max_rows
      use_full_timestamp = False
      logging.debug('Calling client_job.RunQueryRpc(%s, %s)', query, kwds)
      fields, rows, execution = client_job.RunQueryRpc(
          client, query,
          **kwds
      )
      if self.dry_run:
        frontend_utils.PrintDryRunInfo(execution)
      else:
        bq_cached_client.Factory.ClientTablePrinter.GetTablePrinter().PrintTable(
            fields, rows, use_full_timestamp=use_full_timestamp
        )
        # If we are here, the job succeeded, but print warnings if any.
        frontend_utils.PrintJobMessages(execution)
    else:
      if self.destination_table and self.append_table:
        kwds['write_disposition'] = 'WRITE_APPEND'
      if self.destination_table and self.replace:
        kwds['write_disposition'] = 'WRITE_TRUNCATE'
      if self.destination_table and self.replace_data:
        kwds['write_disposition'] = 'WRITE_TRUNCATE_DATA'
      if self.require_cache:
        kwds['create_disposition'] = 'CREATE_NEVER'
      if (
          self.batch and self.priority is not None and self.priority != 'BATCH'
      ) or (
          self.batch is not None and not self.batch and self.priority == 'BATCH'
      ):
        raise app.UsageError('Conflicting values of --batch and --priority.')
      priority = None
      if self.batch:
        priority = 'BATCH'
      if self.priority is not None:
        priority = self.priority
      if priority is not None:
        kwds['priority'] = priority

      kwds['destination_table'] = self.destination_table
      kwds['allow_large_results'] = self.allow_large_results
      kwds['flatten_results'] = self.flatten_results
      kwds['continuous'] = self.continuous
      kwds['job_id'] = utils_flags.get_job_id_from_flags()
      kwds['job_creation_mode'] = self.job_creation_mode

      logging.debug('Calling client.Query(%s, %s)', query, kwds)
      job = client_job.Query(client, query, **kwds)

      if self.dry_run:
        frontend_utils.PrintDryRunInfo(job)
      elif not bq_flags.SYNCHRONOUS_MODE.value:
        self.PrintJobStartInfo(job)
      else:
        self._PrintQueryJobResults(client, job)
    if read_schema:
      client_table.update_table(
          apiclient=client.apiclient,
          reference=bq_client_utils.GetTableReference(
              id_fallbacks=client, identifier=self.destination_table
          ),
          schema=read_schema,
      )

  def _PrintQueryJobResults(
      self, client: bigquery_client_extended.BigqueryClientExtended, job
  ) -> None:
    """Prints the results of a successful query job.

    This function is invoked only for successful jobs.  Output is printed to
    stdout.  Depending on flags, the output is printed in either free-form or
    json style.

    Args:
      client: Bigquery client object
      job: json of the job, expressed as a dictionary
    """
    if (
        job['statistics']['query']['statementType']
        == 'SCRIPT'
        ):
      self._PrintScriptJobResults(client, job)
    else:
      self.PrintNonScriptQueryJobResults(client, job)

  def _PrintScriptJobResults(
      self, client: bigquery_client_extended.BigqueryClientExtended, job
  ) -> None:
    """Prints the results of a successful script job.

    This function is invoked only for successful script jobs.  Prints the output
    of each successful child job representing a statement to stdout.

    Child jobs representing expression evaluations are not printed, as are child
    jobs which failed, but whose error was handled elsewhere in the script.

    Depending on flags, the output is printed in either free-form or
    json style.

    Args:
      client: Bigquery client object
      job: json of the script job, expressed as a dictionary
    """
    # Fetch one more child job than the maximum, so we can tell if some of the
    # child jobs are missing.
    child_jobs = list(
        client_job.ListJobs(
            bqclient=client,
            reference=bq_id_utils.ApiClientHelper.ProjectReference.Create(
                projectId=job['jobReference']['projectId']
            ),
            max_results=self.max_child_jobs + 1,
            all_users=False,
            min_creation_time=None,
            max_creation_time=None,
            page_token=None,
            parent_job_id=job['jobReference']['jobId'],
        )
    )

    # If there is no child job, show the parent job result instead.
    if not child_jobs:
      self.PrintNonScriptQueryJobResults(client, job)
      return

    child_jobs.sort(key=lambda job: job['statistics']['creationTime'])
    if len(child_jobs) == self.max_child_jobs + 1:
      # The number of child jobs exceeds the maximum number to fetch.  There
      # is no way to tell which child jobs are missing, so just display the
      # final result of the script.
      sys.stderr.write(
          'Showing only the final result because the number of child jobs '
          'exceeds --max_child_jobs (%s).\n'
          % self.max_child_jobs
      )
      self.PrintNonScriptQueryJobResults(client, job)
      return
    # To reduce verbosity, only show the results for statements, not
    # expressions.
    statement_child_jobs = [
        job
        for job in child_jobs
        if job.get('statistics', {})
        .get('scriptStatistics', {})
        .get('evaluationKind', '')
        == 'STATEMENT'
    ]
    is_raw_json = bq_flags.FORMAT.value == 'json'
    is_json = is_raw_json or bq_flags.FORMAT.value == 'prettyjson'
    if is_json:
      sys.stdout.write('[')
    statements_printed = 0
    for i, child_job_info in enumerate(statement_child_jobs):
      if bq_client_utils.IsFailedJob(child_job_info):
        # Skip failed jobs; if the error was handled, we want to ignore it;
        # if it wasn't handled, we'll see it soon enough when we print the
        # failure for the overall script.
        continue
      if statements_printed >= self.max_statement_results:
        if not is_json:
          sys.stdout.write(
              'Maximum statement results limit reached. '
              'Specify --max_statement_results to increase this '
              'limit.\n'
          )
        break
      if is_json:
        if i > 0:
          if is_raw_json:
            sys.stdout.write(',')
          else:
            sys.stdout.write(',\n')
      else:
        stack_frames = (
            child_job_info.get('statistics', {})
            .get('scriptStatistics', {})
            .get('stackFrames', [])
        )
        if len(stack_frames) <= 0:
          break
        sys.stdout.write(
            '%s; ' % stringutil.ensure_str(stack_frames[0].get('text', ''))
        )
        if len(stack_frames) >= 2:
          sys.stdout.write('\n')
        # Print stack traces
        for stack_frame in stack_frames:
          sys.stdout.write(
              '-- at %s[%d:%d]\n'
              % (
                  stack_frame.get('procedureId', ''),
                  stack_frame['startLine'],
                  stack_frame['startColumn'],
              )
          )
      self.PrintNonScriptQueryJobResults(
          client, child_job_info, json_escape=is_json
      )
      statements_printed = statements_printed + 1
    if is_json:
      sys.stdout.write(']\n')

  def PrintNonScriptQueryJobResults(
      self,
      client: bigquery_client_extended.BigqueryClientExtended,
      job,
      json_escape: bool = False,
  ) -> None:
    printable_job_info = utils_formatting.format_job_info(job)
    is_assert_job = job['statistics']['query']['statementType'] == 'ASSERT'
    if (
        not bq_client_utils.IsFailedJob(job)
        and not frontend_utils.IsSuccessfulDmlOrDdlJob(printable_job_info)
        and not is_assert_job
    ):
      use_full_timestamp = False
      # ReadSchemaAndJobRows can handle failed jobs, but cannot handle
      # a successful DML job if the destination table is already deleted.
      # DML, DDL, and ASSERT do not have query result, so skip
      # ReadSchemaAndJobRows.
      fields, rows = client_job.ReadSchemaAndJobRows(
          client,
          job['jobReference'],
          start_row=self.start_row,
          max_rows=self.max_rows,
      )
      bq_cached_client.Factory.ClientTablePrinter.GetTablePrinter().PrintTable(
          fields, rows, use_full_timestamp=use_full_timestamp
      )
    elif json_escape:
      print(
          json.dumps(
              frontend_utils.GetJobMessagesForPrinting(printable_job_info)
          )
      )
      return
    # If JSON escaping is not enabled, always print job messages, regardless
    # of job type or succeeded/failed status. Even successful query jobs will
    # have messages in some cases, such as when run in a session.
    frontend_utils.PrintJobMessages(printable_job_info)
