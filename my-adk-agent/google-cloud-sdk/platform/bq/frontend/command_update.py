#!/usr/bin/env python
"""The BigQuery CLI update command."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import json
import time
from typing import Any, Dict, List, Optional

from absl import app
from absl import flags

import bq_flags
import bq_utils
from clients import bigquery_client_extended
from clients import client_connection
from clients import client_data_transfer
from clients import client_dataset
from clients import client_job
from clients import client_model
from clients import client_reservation
from clients import client_row_access_policy
from clients import client_table
from clients import utils as bq_client_utils
from frontend import bigquery_command
from frontend import bq_cached_client
from frontend import flags as frontend_flags
from frontend import utils as frontend_utils
from frontend import utils_data_transfer
from frontend import utils_flags
from frontend import utils_formatting
from frontend import utils_id as frontend_id_utils
from utils import bq_error
from utils import bq_id_utils
from utils import bq_processor_utils

# These aren't relevant for user-facing docstrings:
# pylint: disable=g-doc-return-or-yield
# pylint: disable=g-doc-args


class Update(bigquery_command.BigqueryCmd):
  """The BigQuery CLI update command."""

  usage = """update [-d] [-t] <identifier> [<schema>]"""
  command = 'update'

  # May be extended to more resource types and commands.
  INCOMPATIBLE_FLAGS = {
      bq_id_utils.ApiClientHelper.DatasetReference: {
          'schema',
          'expiration',
          'external_catalog_table_options',
          'external_table_definition',
          'time_partitioning_type',
          'time_partitioning_expiration',
          'time_partitioning_field',
          'clustering_fields',
          'require_partition_filter',
          'range_partitioning',
          'autodetect_schema',
      },
      bq_id_utils.ApiClientHelper.TableReference: {
          'default_table_expiration',
          'default_partition_expiration',
          'default_kms_key',
          'external_catalog_dataset_options',
          'max_time_travel_hours',
          'source',
      },
  }

  def __init__(self, name: str, fv: flags.FlagValues):
    super(Update, self).__init__(name, fv)
    self.fv = fv
    flags.DEFINE_boolean(
        'dataset',
        False,
        'Updates a dataset with this name.',
        short_name='d',
        flag_values=fv,
    )
    flags.DEFINE_boolean(
        'table',
        False,
        'Updates a table with this name.',
        short_name='t',
        flag_values=fv,
    )
    flags.DEFINE_boolean(
        'model',
        False,
        'Updates a model with this model ID.',
        short_name='m',
        flag_values=fv,
    )
    flags.DEFINE_boolean(
        'row_access_policy',
        None,
        'Updates a row access policy.',
        flag_values=fv,
    )
    flags.DEFINE_string(
        'policy_id',
        None,
        'Policy ID used to update row access policy for.',
        flag_values=fv,
    )
    flags.DEFINE_string(
        'target_table',
        None,
        'The table to update the row access policy for.',
        flag_values=fv,
    )
    flags.DEFINE_string(
        'grantees',
        None,
        'Comma separated list of iam_member users or groups that specifies the'
        ' initial members that the row-level access policy should be created'
        ' with.',
        flag_values=fv,
    )
    flags.DEFINE_string(
        'filter_predicate',
        None,
        'A SQL boolean expression that represents the rows defined by this row'
        ' access policy.',
        flag_values=fv,
    )
    flags.DEFINE_boolean(
        'reservation',
        None,
        'Updates a reservation described by this identifier.',
        flag_values=fv,
    )
    flags.DEFINE_integer(
        'slots',
        None,
        'The number of baseline slots associated with the reservation.',
        flag_values=fv,
    )
    flags.DEFINE_boolean(
        'capacity_commitment',
        None,
        'Updates a capacity commitment described by this identifier.',
        flag_values=fv,
    )
    flags.DEFINE_enum(
        'plan',
        None,
        ['MONTHLY', 'ANNUAL', 'THREE_YEAR'],
        'Commitment plan for this capacity commitment. Plan can only be '
        'updated to the one with longer committed period. Options include:'
        '\n MONTHLY'
        '\n ANNUAL'
        '\n THREE_YEAR',
        flag_values=fv,
    )
    flags.DEFINE_enum(
        'renewal_plan',
        None,
        [
            'FLEX',
            'MONTHLY',
            'ANNUAL',
            'THREE_YEAR',
            'NONE',
        ],
        'The plan this capacity commitment is converted to after committed '
        'period ends. Options include:'
        '\n NONE'
        '\n FLEX'
        '\n MONTHLY'
        '\n ANNUAL'
        '\n THREE_YEAR'
        '\n NONE can only be used in conjunction with --edition, '
        '\n while FLEX and MONTHLY cannot be used together with --edition.',
        flag_values=fv,
    )
    flags.DEFINE_boolean(
        'split',
        None,
        'If true, splits capacity commitment into two. Split parts are defined '
        'by the --slots param.',
        flag_values=fv,
    )
    flags.DEFINE_boolean(
        'merge',
        None,
        'If true, merges capacity commitments into one. At least two comma '
        'separated capacity commitment ids must be specified.',
        flag_values=fv,
    )
    flags.DEFINE_boolean(
        'reservation_assignment',
        None,
        'Updates a reservation assignment and so that the assignee will use a '
        'new reservation. '
        'Used in conjunction with --destination_reservation_id',
        flag_values=fv,
    )
    flags.DEFINE_string(
        'destination_reservation_id',
        None,
        'Destination reservation ID. '
        'Used in conjunction with --reservation_assignment.',
        flag_values=fv,
    )
    flags.DEFINE_enum(
        'priority',
        None,
        [
            'HIGH',
            'INTERACTIVE',
            'BATCH',
            '',
        ],
        'Reservation assignment default job priority. Only available for '
        'whitelisted reservations. Options include:'
        '\n HIGH'
        '\n INTERACTIVE'
        '\n BATCH'
        '\n empty string to unset priority',
        flag_values=fv,
    )
    flags.DEFINE_string(
        'reservation_size',
        None,
        'DEPRECATED, Please use bi_reservation_size instead.',
        flag_values=fv,
    )
    flags.DEFINE_string(
        'bi_reservation_size',
        None,
        'BI reservation size. Can be specified in bytes '
        '(--bi_reservation_size=2147483648) or in GB '
        '(--bi_reservation_size=1G). Minimum 1GB. Use 0 to remove reservation.',
        flag_values=fv,
    )
    flags.DEFINE_boolean(
        'use_idle_slots',
        None,
        'If true, any query running in this reservation will be able to use '
        'idle slots from other reservations. Used if ignore_idle_slots is '
        'None.',
        flag_values=fv,
    )
    flags.DEFINE_boolean(
        'ignore_idle_slots',
        None,
        'If false, any query running in this reservation will be able to use '
        'idle slots from other reservations.',
        flag_values=fv,
    )
    flags.DEFINE_integer(
        'max_concurrency',
        None,
        'Deprecated, please use target_job_concurrency instead.',
        flag_values=fv,
    )
    flags.DEFINE_integer(
        'concurrency',
        None,
        'Deprecated, please use target_job_concurrency instead.',
        flag_values=fv,
    )
    flags.DEFINE_integer(
        'target_job_concurrency',
        None,
        'Sets a soft upper bound on the number of jobs that can run '
        'concurrently in the reservation. Default value is 0 which means that '
        'concurrency target will be automatically computed by the system.',
        flag_values=fv,
    )
    flags.DEFINE_integer(
        'autoscale_max_slots',
        None,
        'Number of slots to be scaled when needed. Autoscale will be enabled '
        'when setting this.',
        flag_values=fv,
    )
    flags.DEFINE_integer(
        'max_slots',
        None,
        'The overall max slots for the reservation. It needs to be specified '
        'together with --scaling_mode. It cannot be used together '
        'with --autoscale_max_slots. It is a private preview feature.',
        flag_values=fv,
    )
    flags.DEFINE_enum(
        'scaling_mode',
        None,
        [
            'SCALING_MODE_UNSPECIFIED',
            'AUTOSCALE_ONLY',
            'IDLE_SLOTS_ONLY',
            'ALL_SLOTS',
        ],
        'The scaling mode for the reservation. Available only for reservations '
        'enrolled in the Max Slots Preview. It needs to be specified together '
        'with --max_slots. It cannot be used together with '
        '--autoscale_max_slots. Options include:'
        '\n SCALING_MODE_UNSPECIFIED'
        '\n AUTOSCALE_ONLY'
        '\n IDLE_SLOTS_ONLY'
        '\n ALL_SLOTS',
        flag_values=fv,
    )
    flags.DEFINE_string(
        'reservation_group_name',
        None,
        'Reservation group name used to create reservation for, it can be full'
        ' path or just the reservation group name. Used in conjunction with'
        ' --reservation.',
        flag_values=fv,
    )
    flags.DEFINE_integer(
        'scheduling_policy_concurrency',
        None,
        'Cap on target per-project concurrency of jobs running within the'
        ' reservation.',
        flag_values=fv,
    )
    flags.DEFINE_integer(
        'scheduling_policy_max_slots',
        None,
        'Cap on target rate of slot consumption per-project within the'
        ' reservation.',
        flag_values=fv,
    )
    flags.DEFINE_boolean(
        'transfer_config',
        False,
        'Updates a transfer configuration for a configuration resource name.',
        flag_values=fv,
    )
    flags.DEFINE_string(
        'target_dataset',
        '',
        'Updated dataset ID for the transfer configuration.',
        flag_values=fv,
    )
    flags.DEFINE_string(
        'display_name',
        '',
        'Updated display name for the transfer configuration or connection.',
        flag_values=fv,
    )
    flags.DEFINE_integer(
        'refresh_window_days',
        None,
        'Updated refresh window days for the updated transfer configuration.',
        flag_values=fv,
    )
    flags.DEFINE_string(
        'params',
        None,
        'Updated parameters for the updated transfer configuration '
        'in JSON format.'
        'For example: --params=\'{"param":"param_value"}\'',
        short_name='p',
        flag_values=fv,
    )
    flags.DEFINE_boolean(
        'update_credentials',
        False,
        'Update the transfer configuration credentials.',
        flag_values=fv,
    )
    flags.DEFINE_string(
        'schedule_start_time',
        None,
        'Time to start scheduling transfer runs for the given '
        'transfer configuration. If empty, the default value for '
        'the start time will be used to start runs immediately.'
        'The format for the time stamp is RFC3339 UTC "Zulu". '
        'Read more: '
        'https://developers.google.com/protocol-buffers/docs/'
        'reference/google.protobuf#google.protobuf.Timestamp',
        flag_values=fv,
    )
    flags.DEFINE_string(
        'schedule_end_time',
        None,
        'Time to stop scheduling transfer runs for the given '
        'transfer configuration. If empty, the default value for '
        'the end time will be used to schedule runs indefinitely.'
        'The format for the time stamp is RFC3339 UTC "Zulu". '
        'Read more: '
        'https://developers.google.com/protocol-buffers/docs/'
        'reference/google.protobuf#google.protobuf.Timestamp',
        flag_values=fv,
    )
    flags.DEFINE_string(
        'schedule',
        None,
        'Data transfer schedule. If the data source does not support a custom schedule, this should be empty. If empty, the default value for the data source will be used. The specified times are in UTC. Examples of valid format: 1st,3rd monday of month 15:30, every wed,fri of jan,jun 13:15, and first sunday of quarter 00:00. See more explanation about the format here: https://cloud.google.com/appengine/docs/flexible/python/scheduling-jobs-with-cron-yaml#the_schedule_format',  # pylint: disable=line-too-long
        flag_values=fv,
    )
    flags.DEFINE_bool(
        'no_auto_scheduling',
        False,
        'Disables automatic scheduling of data transfer runs for this '
        'configuration.',
        flag_values=fv,
    )
    self.event_driven_schedule_flag = (
        frontend_flags.define_event_driven_schedule(flag_values=fv)
    )
    flags.DEFINE_string(
        'service_account_name',
        '',
        'Service account used as the credential on the transfer config.',
        flag_values=fv,
    )
    flags.DEFINE_string(
        'notification_pubsub_topic',
        '',
        'Pub/Sub topic used for notification after transfer run completed or '
        'failed.',
        flag_values=fv,
    )
    flags.DEFINE_string(
        'schema',
        '',
        'Either a filename or a comma-separated list of fields in the form '
        'name[:type].',
        flag_values=fv,
    )
    flags.DEFINE_string(
        'description',
        None,
        'Description of the dataset, table, view or connection.',
        flag_values=fv,
    )
    flags.DEFINE_multi_string(
        'set_label',
        None,
        'A label to set on a dataset or a table. The format is "key:value"',
        flag_values=fv,
    )
    flags.DEFINE_multi_string(
        'clear_label',
        None,
        'A label key to remove from a dataset or a table.',
        flag_values=fv,
    )
    flags.DEFINE_integer(
        'expiration',
        None,
        'Expiration time, in seconds from now, of a table or view. '
        'Specifying 0 removes expiration time.',
        flag_values=fv,
    )
    flags.DEFINE_integer(
        'default_table_expiration',
        None,
        'Default lifetime, in seconds, for newly-created tables in a '
        'dataset. Newly-created tables will have an expiration time of '
        'the current time plus this value. Specify "0" to remove existing '
        'expiration.',
        flag_values=fv,
    )
    flags.DEFINE_integer(
        'default_partition_expiration',
        None,
        'Default partition expiration for all partitioned tables in the dataset'
        ', in seconds. The storage in a partition will have an expiration time '
        'of its partition time plus this value. If this property is set, '
        'partitioned tables created in the dataset will use this instead of '
        'default_table_expiration. Specify "0" to remove existing expiration.',
        flag_values=fv,
    )
    flags.DEFINE_string(
        'source',
        None,
        'Path to file with JSON payload for an update',
        flag_values=fv,
    )
    flags.DEFINE_string('view', '', 'SQL query of a view.', flag_values=fv)
    flags.DEFINE_string(
        'materialized_view',
        None,
        'Standard SQL query of a materialized view.',
        flag_values=fv,
    )
    flags.DEFINE_boolean(
        'enable_refresh',
        None,
        'Whether to enable automatic refresh of the materialized views when '
        'the base table is updated. If not set, the default is true.',
        flag_values=fv,
    )
    flags.DEFINE_integer(
        'refresh_interval_ms',
        None,
        'Milliseconds that must have elapsed since last refresh until the '
        'materialized view can be automatically refreshed again. If not set, '
        'the default value is "1800000" (30 minutes).',
        flag_values=fv,
    )
    flags.DEFINE_string(
        'max_staleness',
        None,
        'INTERVAL value that determines the maximum staleness allowed when '
        'querying a materialized view or an external table. By default no '
        'staleness is allowed. Examples of valid max_staleness values: '
        '1 day: "0-0 1 0:0:0"; 1 hour: "0-0 0 1:0:0".'
        'See more explanation about the INTERVAL values: '
        'https://cloud.google.com/bigquery/docs/reference/standard-sql/data-types#interval_type. '  # pylint: disable=line-too-long
        'To use this flag, the external_table_definition flag must be set.',
        flag_values=fv,
    )
    flags.DEFINE_string(
        'external_table_definition',
        None,
        'Specifies a table definition to use to update an external table. '
        'The value can be either an inline table definition or a path to a '
        'file containing a JSON table definition.'
        'The format of inline definition is "schema@format=uri@connection". ',
        flag_values=fv,
    )
    flags.DEFINE_string(
        'external_catalog_dataset_options',
        None,
        'Options defining open source compatible datasets living in the'
        ' BigQuery catalog. Contains metadata of open source database or'
        ' default storage location represented by the current dataset. The'
        ' value can be either an inline JSON definition or a path to a file'
        ' containing a JSON definition.',
        flag_values=fv,
    )
    flags.DEFINE_string(
        'external_catalog_table_options',
        None,
        'Options defining the metadata of an open source compatible table'
        ' living in the BigQuery catalog. Contains metadata of open source'
        ' table including serializer/deserializer information, table schema,'
        ' etc. The value can be either an inline JSON or a path to a file'
        ' containing a JSON definition.',
        flag_values=fv,
    )
    flags.DEFINE_enum(
        'metadata_cache_mode',
        None,
        ['AUTOMATIC', 'MANUAL'],
        'Enables metadata cache for an external table with a connection.'
        ' Specify AUTOMATIC to automatically refresh the cached metadata.'
        ' Specify MANUAL to stop the automatic refresh. To use this flag, the'
        ' external_table_definition flag must be set.',
        flag_values=fv,
    )
    flags.DEFINE_enum(
        'object_metadata',
        None,
        ['DIRECTORY', 'SIMPLE'],
        'Object Metadata Type used to create Object Tables. SIMPLE is the '
        'only supported value to create an Object Table containing a directory '
        'listing of objects found at the uri in external_data_definition.',
        flag_values=fv,
    )
    flags.DEFINE_multi_string(
        'view_udf_resource',
        None,
        'The URI or local filesystem path of a code file to load and '
        'evaluate immediately as a User-Defined Function resource used '
        'by the view.',
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
        'partition time plus this value. A negative number means no '
        'expiration.',
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
        'clustering_fields',
        None,
        'Comma-separated list of field names that specifies the columns on '
        'which a table is clustered. To remove the clustering, set an empty '
        'value.',
        flag_values=fv,
    )
    flags.DEFINE_string(
        'etag', None, 'Only update if etag matches.', flag_values=fv
    )
    flags.DEFINE_string(
        'destination_kms_key',
        None,
        'Cloud KMS key for encryption of the destination table data.',
        flag_values=fv,
    )
    flags.DEFINE_boolean(
        'require_partition_filter',
        None,
        'Whether to require partition filter for queries over this table. '
        'Only apply to partitioned table.',
        flag_values=fv,
    )
    flags.DEFINE_boolean(
        'connection', None, 'Update connection.', flag_values=fv
    )
    flags.DEFINE_enum(
        'connection_type',
        None,
        bq_processor_utils.CONNECTION_TYPES,
        'Connection type. Valid values:\n '
        + '\n '.join(bq_processor_utils.CONNECTION_TYPES),
        flag_values=fv,
    )
    flags.DEFINE_string(
        'properties',
        None,
        'Connection properties in JSON format.',
        flag_values=fv,
    )
    flags.DEFINE_string(
        'connection_credential',
        None,
        'Connection credential in JSON format.',
        flag_values=fv,
    )
    flags.DEFINE_string(
        'iam_role_id', None, '[Experimental] IAM role id.', flag_values=fv
    )
    # TODO(b/231712311): look into cleaning up this flag now that only federated
    # aws connections are supported.
    flags.DEFINE_boolean(
        'federated_aws',
        True,
        '[Experimental] Federated identity.',
        flag_values=fv,
    )
    flags.DEFINE_string(
        'tenant_id', None, '[Experimental] Tenant id.', flag_values=fv
    )
    flags.DEFINE_string(
        'federated_app_client_id',
        None,
        '[Experimental] The application (client) id of the Active Directory '
        'application to use with Azure federated identity.',
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
    flags.DEFINE_string(
        'default_kms_key',
        None,
        'Defines default KMS key name for all newly objects created in the '
        'dataset. Table/Model creation request can override this default.',
        flag_values=fv,
    )
    flags.DEFINE_integer(
        'max_time_travel_hours',
        None,
        'Optional. Define the max time travel in hours. The value can be from '
        '48 to 168 hours (2 to 7 days). The default value is 168 hours if this '
        'is not set.',
        flag_values=fv,
    )
    flags.DEFINE_enum(
        'storage_billing_model',
        None,
        ['LOGICAL', 'PHYSICAL'],
        'Optional. Sets the storage billing model for the dataset. \n'
        'LOGICAL - switches to logical billing model \n'
        'PHYSICAL - switches to physical billing model.',
        flag_values=fv,
    )
    flags.DEFINE_boolean(
        'autodetect_schema',
        False,
        'Optional. If true, schema is autodetected; else schema is unchanged.',
        flag_values=fv,
    )
    flags.DEFINE_string(
        'vertex_ai_model_id',
        None,
        'Optional. Define the Vertex AI model ID to register to Vertex AI for '
        'BigQuery ML models.',
        flag_values=fv,
    )
    flags.DEFINE_string(
        'kms_key_name',
        None,
        'Cloud KMS key name used for encryption.',
        flag_values=fv,
    )
    flags.DEFINE_string(
        'connector_configuration',
        None,
        'Connection configuration for connector in JSON format.',
        flag_values=fv,
    )
    flags.DEFINE_string(
        'add_tags',
        None,
        'Tags to attach to the dataset or table.The format is namespaced key:value pair like "1234567/my_tag_key:my_tag_value,test-project123/environment:production"',  # pylint: disable=line-too-long
        flag_values=fv,
    )
    flags.DEFINE_string(
        'remove_tags',
        None,
        'Tags to remove from the dataset or table'
        'The format is namespaced keys like'
        ' "1234567/my_tag_key,test-project123/environment"',
        flag_values=fv,
    )
    flags.DEFINE_boolean(
        'clear_all_tags',
        False,
        'Clear all tags attached to the dataset or table',
        flag_values=fv,
    )
    flags.DEFINE_enum_class(
        'update_mode',
        None,
        bq_client_utils.UpdateMode,
        ''.join([
            'Specifies which dataset fields are updated. By default, both ',
            'metadata and ACL information are updated. ',
            'Options include:\n ',
            '\n '.join([e.value for e in bq_client_utils.UpdateMode]),
            '\n If not set, defaults as UPDATE_FULL',
        ]),
        flag_values=fv,
    )

    self._ProcessCommandRc(fv)

  def printSuccessMessage(self, object_name: str, reference: Any):
    print(
        "%s '%s' successfully updated."
        % (
            object_name,
            reference,
        )
    )

  def RunWithArgs(
      self, identifier: str = '', schema: str = ''
  ) -> Optional[int]:
    # pylint: disable=g-doc-exception
    """Updates a dataset, table, view or transfer configuration with this name.

    See 'bq help update' for more information.

    Examples:
      bq update --description "Dataset description" existing_dataset
      bq update --description "My table" existing_dataset.existing_table
      bq update --description "My model" -m existing_dataset.existing_model
      bq update -t existing_dataset.existing_table name:integer,value:string
      bq update --destination_kms_key
          projects/p/locations/l/keyRings/r/cryptoKeys/k
          existing_dataset.existing_table
      bq update --view='select 1 as num' existing_dataset.existing_view
         (--view_udf_resource=path/to/file.js)
      bq update --transfer_config --display_name=name -p='{"param":"value"}'
          projects/p/locations/l/transferConfigs/c
      bq update --transfer_config --target_dataset=dataset
          --refresh_window_days=5 --update_credentials
          projects/p/locations/l/transferConfigs/c
      bq update --reservation --location=US --project_id=my-project
          --bi_reservation_size=2G
      bq update --capacity_commitment --location=US --project_id=my-project
          --plan=MONTHLY --renewal_plan=FLEX commitment_id
      bq update --capacity_commitment --location=US --project_id=my-project
        --split --slots=500 commitment_id
      bq update --capacity_commitment --location=US --project_id=my-project
        --merge commitment_id1,commitment_id2
      bq update --reservation_assignment
          --destination_reservation_id=proj:US.new_reservation
          proj:US.old_reservation.assignment_id
      bq update --connection_credential='{"username":"u", "password":"p"}'
        --location=US --project_id=my-project existing_connection
      bq update --row_access_policy --policy_id=existing_policy
      --target_table='existing_dataset.existing_table'
      --grantees='user:user1@google.com,group:group1@google.com'
      --filter_predicate='Region="US"'
    """
    client = bq_cached_client.Client.Get()
    if self.d and self.t:
      raise app.UsageError('Cannot specify both -d and -t.')
    if frontend_utils.ValidateAtMostOneSelected(
        self.schema, self.view, self.materialized_view
    ):
      raise app.UsageError(
          'Cannot specify more than one of'
          ' --schema or --view or --materialized_view.'
      )
    if self.t:
      reference = bq_client_utils.GetTableReference(
          id_fallbacks=client, identifier=identifier
      )
    elif self.view:
      reference = bq_client_utils.GetTableReference(
          id_fallbacks=client, identifier=identifier
      )
    elif self.materialized_view:
      reference = bq_client_utils.GetTableReference(
          id_fallbacks=client, identifier=identifier
      )
    elif self.row_access_policy:
      reference = bq_client_utils.GetRowAccessPolicyReference(
          id_fallbacks=client,
          table_identifier=self.target_table,
          policy_id=self.policy_id,
      )
      try:
        client_row_access_policy.update_row_access_policy(
            bqclient=client,
            policy_reference=reference,
            grantees=self.grantees.split(','),
            filter_predicate=self.filter_predicate,
        )
      except BaseException as e:
        raise bq_error.BigqueryError(
            "Failed to update row access policy '%s' on '%s': %s"
            % (self.policy_id, self.target_table, e)
        )
      self.printSuccessMessage('Row access policy', self.policy_id)
    elif self.reservation:
      label_keys_to_remove = None
      labels_to_set = None
      if self.set_label is not None:
        labels_to_set = frontend_utils.ParseLabels(self.set_label)
      if self.clear_label is not None:
        label_keys_to_remove = set(self.clear_label)
      try:
        if (
            self.reservation_size is not None
            or self.bi_reservation_size is not None
        ):
          size = self.bi_reservation_size
          if size is None:
            size = self.reservation_size
          reference = bq_client_utils.GetBiReservationReference(
              id_fallbacks=client, default_location=bq_flags.LOCATION.value
          )
          object_info = client_reservation.UpdateBiReservation(
              client=client.GetReservationApiClient(),
              reference=reference,
              reservation_size=size,
          )
          print(object_info)
        else:
          reference = bq_client_utils.GetReservationReference(
              id_fallbacks=client,
              identifier=identifier,
              default_location=bq_flags.LOCATION.value,
          )
          ignore_idle_arg = self.ignore_idle_slots
          if ignore_idle_arg is None and self.use_idle_slots is not None:
            ignore_idle_arg = not self.use_idle_slots
          concurrency = self.target_job_concurrency
          if concurrency is None:
            concurrency = (
                self.concurrency
                if self.concurrency is not None
                else self.max_concurrency
            )
          object_info = client_reservation.UpdateReservation(
              client=client.GetReservationApiClient(),
              api_version=bq_flags.API_VERSION.value,
              reference=reference,
              slots=self.slots,
              ignore_idle_slots=ignore_idle_arg,
              target_job_concurrency=concurrency,
              autoscale_max_slots=self.autoscale_max_slots,
              max_slots=self.max_slots,
              scaling_mode=self.scaling_mode,
              labels_to_set=labels_to_set,
              label_keys_to_remove=label_keys_to_remove,
              reservation_group_name=self.reservation_group_name,
              scheduling_policy_concurrency=self.scheduling_policy_concurrency,
              scheduling_policy_max_slots=self.scheduling_policy_max_slots,
          )
          frontend_utils.PrintObjectInfo(
              object_info, reference, custom_format='show'
          )
      except BaseException as e:
        raise bq_error.BigqueryError(
            "Failed to update reservation '%s': %s" % (identifier, e)
        )
    elif self.capacity_commitment:
      try:
        if self.split and self.merge:
          raise bq_error.BigqueryError(
              'Cannot specify both --split and --merge.'
          )
        reference = bq_client_utils.GetCapacityCommitmentReference(
            id_fallbacks=client,
            identifier=identifier,
            default_location=bq_flags.LOCATION.value,
            allow_commas=self.merge,
        )
        if self.split:
          response = client_reservation.SplitCapacityCommitment(
              client=client.GetReservationApiClient(),
              reference=reference,
              slots=self.slots,
          )
          frontend_utils.PrintObjectsArray(
              response,
              objects_type=bq_id_utils.ApiClientHelper.CapacityCommitmentReference,
          )
        elif self.merge:
          object_info = client_reservation.MergeCapacityCommitments(
              client=client.GetReservationApiClient(),
              project_id=reference.projectId,
              location=reference.location,
              capacity_commitment_ids=reference.capacityCommitmentId.split(','),
          )
          if not isinstance(object_info['name'], str):
            raise ValueError('Parsed object does not have a name of type str.')
          reference = bq_client_utils.GetCapacityCommitmentReference(
              id_fallbacks=client, path=object_info['name']
          )
          frontend_utils.PrintObjectInfo(
              object_info, reference, custom_format='show'
          )
        else:
          object_info = client_reservation.UpdateCapacityCommitment(
              client=client.GetReservationApiClient(),
              reference=reference,
              plan=self.plan,
              renewal_plan=self.renewal_plan,
          )
          frontend_utils.PrintObjectInfo(
              object_info, reference, custom_format='show'
          )
      except BaseException as e:
        err = ''
        # Merge error is not specific to identifier, so making it more generic.
        if self.merge:
          err = 'Capacity commitments merge failed: %s' % (e)
        else:
          err = "Failed to update capacity commitment '%s': %s" % (
              identifier,
              e,
          )
        raise bq_error.BigqueryError(err)
    elif self.reservation_assignment:
      try:
        reference = bq_client_utils.GetReservationAssignmentReference(
            id_fallbacks=client,
            identifier=identifier,
            default_location=bq_flags.LOCATION.value,
        )
        if self.destination_reservation_id and self.priority is not None:
          raise bq_error.BigqueryError(
              'Cannot specify both --destination_reservation_id and --priority.'
          )
        if self.destination_reservation_id:
          if (
              self.scheduling_policy_max_slots is not None
              or self.scheduling_policy_concurrency is not None
          ):
            raise bq_error.BigqueryError(
                'Cannot specify scheduling_policy flags if'
                ' --destination_reservation_id is specified.'
            )
          object_info = client_reservation.MoveReservationAssignment(
              client=client.GetReservationApiClient(),
              id_fallbacks=client,
              reference=reference,
              destination_reservation_id=self.destination_reservation_id,
              default_location=bq_flags.LOCATION.value,
          )
          reference = bq_client_utils.GetReservationAssignmentReference(
              id_fallbacks=client, path=object_info['name']
          )
        elif self.priority is not None:
          object_info = client_reservation.UpdateReservationAssignment(
              client=client.GetReservationApiClient(),
              reference=reference,
              priority=self.priority,
              scheduling_policy_max_slots=self.scheduling_policy_max_slots,
              scheduling_policy_concurrency=self.scheduling_policy_concurrency,
          )
        elif (
            self.scheduling_policy_max_slots is not None
            or self.scheduling_policy_concurrency is not None
        ):
          object_info = client_reservation.UpdateReservationAssignment(
              client=client.GetReservationApiClient(),
              reference=reference,
              priority=self.priority,
              scheduling_policy_max_slots=self.scheduling_policy_max_slots,
              scheduling_policy_concurrency=self.scheduling_policy_concurrency,
          )
        else:
          raise bq_error.BigqueryError(
              'Either --destination_reservation_id or --priority must be '
              'specified.'
          )

        frontend_utils.PrintObjectInfo(
            object_info, reference, custom_format='show', print_reference=False
        )
      except BaseException as e:
        raise bq_error.BigqueryError(
            "Failed to update reservation assignment '%s': %s" % (identifier, e)
        )
    elif self.d or not identifier:
      reference = bq_client_utils.GetDatasetReference(
          id_fallbacks=client, identifier=identifier
      )
    elif self.m:
      reference = bq_client_utils.GetModelReference(
          id_fallbacks=client, identifier=identifier
      )
    elif self.transfer_config:
      formatted_identifier = frontend_id_utils.FormatDataTransferIdentifiers(
          client, identifier
      )
      reference = bq_id_utils.ApiClientHelper.TransferConfigReference(
          transferConfigName=formatted_identifier
      )
    elif self.connection or self.connection_credential:
      reference = bq_client_utils.GetConnectionReference(
          id_fallbacks=client,
          identifier=identifier,
          default_location=bq_flags.LOCATION.value,
      )
      if self.connection_type == 'AWS' and self.iam_role_id:
        self.properties = bq_processor_utils.MakeAccessRolePropertiesJson(
            self.iam_role_id
        )
      if self.connection_type == 'Azure':
        if self.tenant_id and self.federated_app_client_id:
          self.properties = bq_processor_utils.MakeAzureFederatedAppClientAndTenantIdPropertiesJson(
              self.tenant_id, self.federated_app_client_id
          )
        elif self.federated_app_client_id:
          self.properties = (
              bq_processor_utils.MakeAzureFederatedAppClientIdPropertiesJson(
                  self.federated_app_client_id
              )
          )
        elif self.tenant_id:
          self.properties = bq_processor_utils.MakeTenantIdPropertiesJson(
              self.tenant_id
          )
      if (
          self.properties
          or self.display_name
          or self.description
          or self.connection_credential
          or self.connector_configuration
          or self.kms_key_name is not None
      ):
        updated_connection = client_connection.UpdateConnection(
            client=client.GetConnectionV1ApiClient(),
            reference=reference,
            display_name=self.display_name,
            description=self.description,
            connection_type=self.connection_type,
            properties=self.properties,
            connection_credential=self.connection_credential,
            kms_key_name=self.kms_key_name,
            connector_configuration=self.connector_configuration,
        )
        utils_formatting.maybe_print_manual_instructions_for_connection(
            updated_connection
        )
    else:
      reference = bq_client_utils.GetReference(
          id_fallbacks=client, identifier=identifier
      )
      bq_id_utils.typecheck(
          reference,
          (
              bq_id_utils.ApiClientHelper.DatasetReference,
              bq_id_utils.ApiClientHelper.TableReference,
          ),
          "Invalid identifier '%s' for update." % (identifier,),
          is_usage_error=True,
      )

    label_keys_to_remove = None
    labels_to_set = None
    if self.set_label is not None:
      labels_to_set = frontend_utils.ParseLabels(self.set_label)
    if self.clear_label is not None:
      label_keys_to_remove = set(self.clear_label)

    # Check for incompatible flags.
    reference_type = type(reference)
    for flag_name in self.INCOMPATIBLE_FLAGS.get(reference_type, []):
      if self.fv[flag_name].present:
        raise app.UsageError(
            'Cannot specify --%s with a %s.'
            % (
                flag_name,
                reference_type.typename.lower(),
            )
        )

    if isinstance(reference, bq_id_utils.ApiClientHelper.DatasetReference):
      if self.source and self.description:
        raise app.UsageError('Cannot specify description with a source.')
      default_table_exp_ms = None
      if self.default_table_expiration is not None:
        default_table_exp_ms = self.default_table_expiration * 1000
      default_partition_exp_ms = None
      if self.default_partition_expiration is not None:
        default_partition_exp_ms = self.default_partition_expiration * 1000
      tags_to_attach = None
      if self.add_tags:
        tags_to_attach = bq_utils.ParseTags(self.add_tags)
      tags_to_remove = None
      if self.remove_tags:
        tags_to_remove = bq_utils.ParseTagKeys(self.remove_tags)
      _UpdateDataset(
          client,
          reference,
          description=self.description,
          source=self.source,
          default_table_expiration_ms=default_table_exp_ms,
          default_partition_expiration_ms=default_partition_exp_ms,
          labels_to_set=labels_to_set,
          label_keys_to_remove=label_keys_to_remove,
          default_kms_key=self.default_kms_key,
          etag=self.etag,
          max_time_travel_hours=self.max_time_travel_hours,
          storage_billing_model=self.storage_billing_model,
          tags_to_attach=tags_to_attach,
          tags_to_remove=tags_to_remove,
          clear_all_tags=self.clear_all_tags,
          external_catalog_dataset_options=self.external_catalog_dataset_options,
          update_mode=self.update_mode,
      )
      self.printSuccessMessage('Dataset', reference)
    elif isinstance(reference, bq_id_utils.ApiClientHelper.TableReference):
      object_name = 'Table'
      if self.view:
        object_name = 'View'
      if self.materialized_view:
        object_name = 'Materialized View'
      if schema:
        schema = bq_client_utils.ReadSchema(schema)
      else:
        schema = None
      expiration = None
      if self.expiration is not None:
        if self.expiration == 0:
          expiration = 0
        else:
          expiration = int(self.expiration + time.time()) * 1000
      external_data_config = None
      if self.external_table_definition is not None:
        external_data_config = frontend_utils.GetExternalDataConfig(
            self.external_table_definition,
            metadata_cache_mode=self.metadata_cache_mode,
            object_metadata=self.object_metadata,
        )
        # When updating, move the schema out of the external_data_config.
        # If schema is set explicitly on this update, prefer it over the
        # external_data_config schema.
        # Note: binary formats and text formats with autodetect enabled may not
        # have a schema set.
        # Hive partitioning requires that the schema be set on the external data
        # config.
        if ('schema' in external_data_config) and (
            'hivePartitioningOptions' not in external_data_config
        ):
          if schema is None:
            schema = external_data_config['schema']['fields']
          # Regardless delete schema from the external data config.
          del external_data_config['schema']
      view_query_arg = self.view or None
      materialized_view_query_arg = self.materialized_view or None
      view_udf_resources = None
      if self.view_udf_resource:
        view_udf_resources = frontend_utils.ParseUdfResources(
            self.view_udf_resource
        )
      time_partitioning = frontend_utils.ParseTimePartitioning(
          self.time_partitioning_type,
          self.time_partitioning_expiration,
          self.time_partitioning_field,
          None,
          self.require_partition_filter,
      )
      range_partitioning = frontend_utils.ParseRangePartitioning(
          self.range_partitioning
      )
      clustering = frontend_utils.ParseClustering(self.clustering_fields)
      encryption_configuration = None
      if self.destination_kms_key:
        encryption_configuration = {'kmsKeyName': self.destination_kms_key}
      table_constraints = None
      tags_to_attach = None
      if self.add_tags:
        tags_to_attach = bq_utils.ParseTags(self.add_tags)
      tags_to_remove = None
      if self.remove_tags:
        tags_to_remove = bq_utils.ParseTagKeys(self.remove_tags)

      client_table.update_table(
          apiclient=client.apiclient,
          reference=reference,
          schema=schema,
          description=self.description,
          expiration=expiration,
          view_query=view_query_arg,
          materialized_view_query=materialized_view_query_arg,
          enable_refresh=self.enable_refresh,
          refresh_interval_ms=self.refresh_interval_ms,
          max_staleness=self.max_staleness,
          view_udf_resources=view_udf_resources,
          use_legacy_sql=self.use_legacy_sql,
          external_data_config=external_data_config,
          external_catalog_table_options=self.external_catalog_table_options,
          labels_to_set=labels_to_set,
          label_keys_to_remove=label_keys_to_remove,
          time_partitioning=time_partitioning,
          range_partitioning=range_partitioning,
          clustering=clustering,
          require_partition_filter=self.require_partition_filter,
          etag=self.etag,
          encryption_configuration=encryption_configuration,
          autodetect_schema=self.autodetect_schema,
          table_constraints=table_constraints,
          tags_to_attach=tags_to_attach,
          tags_to_remove=tags_to_remove,
          clear_all_tags=self.clear_all_tags,
      )

      self.printSuccessMessage(object_name, reference)
    elif isinstance(
        reference, bq_id_utils.ApiClientHelper.TransferConfigReference
    ):
      if client_data_transfer.transfer_exists(
          client.GetTransferV1ApiClient(), reference
      ):
        auth_info = {}
        service_account_name = ''
        if self.update_credentials:
          if self.service_account_name:
            service_account_name = self.service_account_name
          else:
            transfer_config_name = (
                frontend_id_utils.FormatDataTransferIdentifiers(
                    client, reference.transferConfigName
                )
            )
            current_config = client_data_transfer.get_transfer_config(
                client.GetTransferV1ApiClient(), transfer_config_name
            )
            auth_info = utils_data_transfer.RetrieveAuthorizationInfo(
                'projects/'
                + bq_client_utils.GetProjectReference(
                    id_fallbacks=client
                ).projectId,
                current_config['dataSourceId'],
                client.GetTransferV1ApiClient(),
            )
        self.event_driven_schedule = (
            self.event_driven_schedule_flag.value
            if self.event_driven_schedule_flag.present
            else None
        )
        schedule_args = client_data_transfer.TransferScheduleArgs(
            schedule=self.schedule,
            start_time=self.schedule_start_time,
            end_time=self.schedule_end_time,
            disable_auto_scheduling=self.no_auto_scheduling,
            event_driven_schedule=self.event_driven_schedule,
        )
        client_data_transfer.update_transfer_config(
            transfer_client=client.GetTransferV1ApiClient(),
            id_fallbacks=client,
            reference=reference,
            target_dataset=self.target_dataset,
            display_name=self.display_name,
            refresh_window_days=self.refresh_window_days,
            params=self.params,
            auth_info=auth_info,
            service_account_name=service_account_name,
            destination_kms_key=self.destination_kms_key,
            notification_pubsub_topic=self.notification_pubsub_topic,
            schedule_args=schedule_args,
        )
        self.printSuccessMessage('Transfer configuration', reference)
      else:
        raise bq_error.BigqueryNotFoundError(
            'Not found: %r' % (reference,), {'reason': 'notFound'}, []
        )
    elif isinstance(reference, bq_id_utils.ApiClientHelper.ModelReference):
      expiration = None
      if self.expiration:
        expiration = int(self.expiration + time.time()) * 1000
      else:
        expiration = self.expiration  # None or 0
      client_model.update_model(
          model_client=client.GetModelsApiClient(),
          reference=reference,
          description=self.description,
          expiration=expiration,
          labels_to_set=labels_to_set,
          label_keys_to_remove=label_keys_to_remove,
          vertex_ai_model_id=self.vertex_ai_model_id,
          etag=self.etag,
      )
      self.printSuccessMessage('Model', reference)


def _UpdateDataset(
    client: bigquery_client_extended.BigqueryClientExtended,
    reference: bq_id_utils.ApiClientHelper.DatasetReference,
    description: Optional[str] = None,
    source=None,
    default_table_expiration_ms=None,
    default_partition_expiration_ms=None,
    labels_to_set=None,
    label_keys_to_remove=None,
    etag=None,
    default_kms_key=None,
    max_time_travel_hours=None,
    storage_billing_model=None,
    tags_to_attach: Optional[Dict[str, str]] = None,
    tags_to_remove: Optional[List[str]] = None,
    clear_all_tags: Optional[bool] = None,
    external_catalog_dataset_options: Optional[str] = None,
    update_mode: Optional[bq_client_utils.UpdateMode] = None,
):
  """Updates a dataset.

  Reads JSON file if specified and loads updated values, before calling bigquery
  dataset update.

  Args:
    client: The BigQuery client.
    reference: The DatasetReference to update.
    description: An optional dataset description.
    source: An optional filename containing the JSON payload.
    default_table_expiration_ms: An optional number of milliseconds for the
      default expiration duration for new tables created in this dataset.
    default_partition_expiration_ms: An optional number of milliseconds for the
      default partition expiration duration for new partitioned tables created
      in this dataset.
    labels_to_set: An optional dict of labels to set on this dataset.
    label_keys_to_remove: an optional list of label keys to remove from this
      dataset.
    default_kms_key: An optional CMEK encryption key for all new tables in the
      dataset.
    max_time_travel_hours: Optional. Define the max time travel in hours. The
      value can be from 48 to 168 hours (2 to 7 days). The default value is 168
      hours if this is not set.
    storage_billing_model: Optional. Sets the storage billing model for the
      dataset.
    tags_to_attach: An optional dict of tags to attach to the dataset.
    tags_to_remove: An optional list of tag keys to remove from the dataset.
    clear_all_tags: If set, clears all the tags attached to the dataset.
    external_catalog_dataset_options: An optional JSON string or file path
      containing the external catalog dataset options to update.

  Raises:
    UsageError: when incorrect usage or invalid args are used.
  """
  description, acl = frontend_utils.ProcessSource(description, source)
  client_dataset.UpdateDataset(
      apiclient=client.apiclient,
      reference=reference,
      description=description,
      acl=acl,
      default_table_expiration_ms=default_table_expiration_ms,
      default_partition_expiration_ms=default_partition_expiration_ms,
      labels_to_set=labels_to_set,
      label_keys_to_remove=label_keys_to_remove,
      etag=etag,
      default_kms_key=default_kms_key,
      max_time_travel_hours=max_time_travel_hours,
      storage_billing_model=storage_billing_model,
      tags_to_attach=tags_to_attach,
      tags_to_remove=tags_to_remove,
      clear_all_tags=clear_all_tags,
      external_catalog_dataset_options=external_catalog_dataset_options,
      update_mode=update_mode,
  )
