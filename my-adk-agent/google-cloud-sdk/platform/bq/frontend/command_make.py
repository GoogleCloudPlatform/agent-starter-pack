#!/usr/bin/env python
"""The BigQuery CLI make command."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import time
from typing import Optional

from absl import app
from absl import flags

import bq_flags
import bq_utils
from clients import client_connection
from clients import client_data_transfer
from clients import client_dataset
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


class Make(bigquery_command.BigqueryCmd):
  """Creates a dataset or a table."""

  usage = """mk [-d] <identifier>  OR  mk [-t] <identifier> [<schema>]"""
  command = 'mk'

  def __init__(self, name: str, fv: flags.FlagValues):
    super(Make, self).__init__(name, fv)
    flags.DEFINE_boolean(
        'force',
        False,
        'Bypass existence checks and ignore errors that the object already '
        'exists.',
        short_name='f',
        flag_values=fv,
    )
    flags.DEFINE_boolean(
        'dataset',
        False,
        'Create dataset with this name.',
        short_name='d',
        flag_values=fv,
    )
    flags.DEFINE_boolean(
        'table',
        False,
        'Create table with this name.',
        short_name='t',
        flag_values=fv,
    )
    flags.DEFINE_boolean(
        'transfer_config', None, 'Create transfer config.', flag_values=fv
    )
    flags.DEFINE_string(
        'target_dataset',
        '',
        'Target dataset for the created transfer configuration.',
        flag_values=fv,
    )
    flags.DEFINE_string(
        'display_name',
        '',
        'Display name for the created transfer configuration or connection.',
        flag_values=fv,
    )
    flags.DEFINE_enum(
        'managed_table_type',
        None,
        [
            'NATIVE',
            'BIGLAKE',
        ],
        'Destination table type for the created transfer configuration.',
        flag_values=fv,
    )
    flags.DEFINE_string(
        'data_source',
        '',
        'Data source for the created transfer configuration.',
        flag_values=fv,
    )
    flags.DEFINE_integer(
        'refresh_window_days',
        0,
        'Refresh window days for the created transfer configuration.',
        flag_values=fv,
    )
    flags.DEFINE_string(
        'params',
        None,
        'Parameters for the created transfer configuration in JSON format. '
        'For example: --params=\'{"param":"param_value"}\'',
        short_name='p',
        flag_values=fv,
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
    flags.DEFINE_bool(
        'transfer_run',
        False,
        'Creates transfer runs for a time range.',
        flag_values=fv,
    )
    flags.DEFINE_string(
        'start_time',
        None,
        'Start time of the range of transfer runs. '
        'The format for the time stamp is RFC3339 UTC "Zulu". '
        'Example: 2019-01-20T06:50:0Z. Read more: '
        'https://developers.google.com/protocol-buffers/docs/'
        'reference/google.protobuf#google.protobuf.Timestamp ',
        flag_values=fv,
    )
    flags.DEFINE_string(
        'end_time',
        None,
        'Exclusive end time of the range of transfer runs. '
        'The format for the time stamp is RFC3339 UTC "Zulu". '
        'Example: 2019-01-20T06:50:0Z. Read more: '
        'https://developers.google.com/protocol-buffers/docs/'
        'reference/google.protobuf#google.protobuf.Timestamp ',
        flag_values=fv,
    )
    flags.DEFINE_string(
        'run_time',
        None,
        'Specific time for a transfer run. '
        'The format for the time stamp is RFC3339 UTC "Zulu". '
        'Example: 2019-01-20T06:50:0Z. Read more: '
        'https://developers.google.com/protocol-buffers/docs/'
        'reference/google.protobuf#google.protobuf.Timestamp ',
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
        'schema',
        '',
        'Either a filename or a comma-separated list of fields in the form '
        'name[:type].',
        flag_values=fv,
    )
    flags.DEFINE_string(
        'description',
        None,
        'Description of the dataset, table or connection.',
        flag_values=fv,
    )
    flags.DEFINE_string(
        'data_location',
        None,
        'Geographic location of the data. See details at '
        'https://cloud.google.com/bigquery/docs/locations.',
        flag_values=fv,
    )
    flags.DEFINE_integer(
        'expiration',
        None,
        'Expiration time, in seconds from now, of a table.',
        flag_values=fv,
    )
    flags.DEFINE_integer(
        'default_table_expiration',
        None,
        'Default lifetime, in seconds, for newly-created tables in a '
        'dataset. Newly-created tables will have an expiration time of '
        'the current time plus this value.',
        flag_values=fv,
    )
    flags.DEFINE_integer(
        'default_partition_expiration',
        None,
        'Default partition expiration for all partitioned tables in the dataset'
        ', in seconds. The storage in a partition will have an expiration time '
        'of its partition time plus this value. If this property is set, '
        'partitioned tables created in the dataset will use this instead of '
        'default_table_expiration.',
        flag_values=fv,
    )
    flags.DEFINE_string(
        'external_table_definition',
        None,
        'Specifies a table definition to use to create an external table. '
        'The value can be either an inline table definition or a path to a '
        'file containing a JSON table definition. '
        'The format of inline definition is "schema@format=uri@connection", '
        'where "schema@", "format=", and "connection" are optional and "format"'
        'has the default value of "CSV" if not specified. ',
        flag_values=fv,
    )
    flags.DEFINE_string(
        'connection_id',
        None,
        'The connection specifying the credentials to be used to read external storage. The connection_id can have the form "<project_id>.<location_id>.<connection_id>" or "projects/<project_id>/locations/<location_id>/connections/<connection_id>". ',  # pylint: disable=line-too-long
        flag_values=fv,
    )
    flags.DEFINE_string(
        'storage_uri',
        None,
        (
            'The fully qualified location prefix of the external folder where'
            ' the table data of a BigLake table is stored. The "*" wildcard'
            ' character is not allowed. The URI should be in the format'
            ' "gs://bucket/path_to_table/". '
        ),
        flag_values=fv,
    )
    flags.DEFINE_enum(
        'file_format',
        None,
        ['PARQUET'],
        'The file format the table data of a BigLake table is stored in. ',
        flag_values=fv,
    )
    flags.DEFINE_enum(
        'table_format',
        None,
        ['ICEBERG'],
        (
            'The table format the metadata only snapshots of a BigLake table'
            ' are stored in. '
        ),
        flag_values=fv,
    )
    flags.DEFINE_string(
        'view', '', 'Create view with this SQL query.', flag_values=fv
    )
    flags.DEFINE_multi_string(
        'view_udf_resource',
        None,
        'The URI or local filesystem path of a code file to load and '
        'evaluate immediately as a User-Defined Function resource used '
        'by the view.',
        flag_values=fv,
    )
    flags.DEFINE_string(
        'materialized_view',
        None,
        '[Experimental] Create materialized view with this Standard SQL query.',
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
        'INTERVAL value that determines the maximum staleness allowed when querying a materialized view or an external table. By default no staleness is allowed. Examples of valid max_staleness values: 1 day: "0-0 1 0:0:0"; 1 hour: "0-0 0 1:0:0".See more explanation about the INTERVAL values: https://cloud.google.com/bigquery/docs/reference/standard-sql/data-types#interval_type',  # pylint: disable=line-too-long
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
        'destination_kms_key',
        None,
        'Cloud KMS key for encryption of the destination table data.',
        flag_values=fv,
    )
    flags.DEFINE_multi_string(
        'label',
        None,
        'A label to set on the table or dataset. The format is "key:value"',
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
        'which a table is clustered.',
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
        'row_access_policy',
        None,
        'Creates a row access policy.',
        flag_values=fv,
    )
    flags.DEFINE_string(
        'policy_id',
        None,
        'Policy ID used to create row access policy for.',
        flag_values=fv,
    )
    flags.DEFINE_string(
        'target_table',
        None,
        'The table to create the row access policy for.',
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
        'Creates a reservation described by this identifier. ',
        flag_values=fv,
    )
    flags.DEFINE_boolean(
        'capacity_commitment',
        None,
        'Creates a capacity commitment. You do not need to specify a capacity '
        'commitment id, this will be assigned automatically.',
        flag_values=fv,
    )
    flags.DEFINE_enum(
        'plan',
        None,
        [
            'FLEX',
            'MONTHLY',
            'ANNUAL',
            'THREE_YEAR',
        ],
        'Commitment plan for this capacity commitment. Plans cannot be deleted '
        'before their commitment period is over. Options include:'
        '\n FLEX\n MONTHLY\n ANNUAL\n THREE_YEAR',
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
    flags.DEFINE_integer(
        'slots',
        0,
        'The number of baseline slots associated with the reservation.',
        flag_values=fv,
    )
    flags.DEFINE_boolean(
        'multi_region_auxiliary',
        False,
        'If true, capacity commitment or reservation is placed in the '
        'organization'
        's auxiliary region which is designated for disaster '
        'recovery purposes. Applicable only for US and EU locations. Available '
        'only for allow-listed projects.',
        flag_values=fv,
    )
    flags.DEFINE_boolean(
        'use_idle_slots',
        True,
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
    flags.DEFINE_enum(
        'job_type',
        None,
        [
            'QUERY',
            'PIPELINE',
            'ML_EXTERNAL',
            'BACKGROUND',
            'SPARK',
            'CONTINUOUS',
            'BACKGROUND_CHANGE_DATA_CAPTURE',
            'BACKGROUND_COLUMN_METADATA_INDEX',
            'BACKGROUND_SEARCH_INDEX_REFRESH',
        ],
        (
            'Type of jobs to create reservation assignment for.'
            ' Options include:'
            '\n QUERY'
            '\n PIPELINE'
            '\n Note if PIPELINE reservations are'
            ' created, then load jobs will just use the slots from this'
            " reservation and slots from shared pool won't be used."
            '\n ML_EXTERNAL'
            '\n BigQuery ML jobs that use services external to BQ'
            ' for model training will use slots from this reservation. Slots'
            ' used by these jobs are not preemptible, i.e., they are not'
            ' available for other jobs running in the reservation. These jobs'
            ' will not utilize idle slots from other reservations.'
            '\n BACKGROUND'
            '\n BACKGROUND_CHANGE_DATA_CAPTURE'
            '\n BigQuery CDC background merge will use'
            ' BACKGROUND_CHANGE_DATA_CAPTURE'
            ' reservations to execute if created, but will fall back to using'
            ' BACKGROUND reservations if one does not exist.'
            '\n BACKGROUND_COLUMN_METADATA_INDEX'
            '\n BACKGROUND_SEARCH_INDEX_REFRESH'
            '\n SPARK'
            '\n BigQuery Spark jobs'
            ' that use services external to BQ for executing SPARK procedure'
            ' job. Slots used by these jobs are not preemptible, i.e., they are'
            ' not available for other jobs running in the reservation. These'
            ' jobs will not utilize idle slots from other reservations.'
        ),
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
        'Reservation assignment default job priority. Only available for '
        'whitelisted reservations. Options include:'
        '\n HIGH'
        '\n INTERACTIVE'
        '\n BATCH',
        flag_values=fv,
    )
    flags.DEFINE_string(
        'reservation_id',
        None,
        'Reservation ID used to create reservation assignment for. '
        'Used in conjunction with --reservation_assignment.',
        flag_values=fv,
    )
    flags.DEFINE_boolean(
        'reservation_assignment',
        None,
        'Create a reservation assignment.',
        flag_values=fv,
    )
    flags.DEFINE_enum(
        'assignee_type',
        None,
        ['PROJECT', 'FOLDER', 'ORGANIZATION'],
        'Type of assignees for the reservation assignment. Options include:'
        '\n PROJECT'
        '\n FOLDER'
        '\n ORGANIZATION'
        '\n Used in conjunction with --reservation_assignment.',
        flag_values=fv,
    )
    flags.DEFINE_string(
        'assignee_id',
        None,
        'Project/folder/organization ID, to which the reservation is assigned. '
        'Used in conjunction with --reservation_assignment.',
        flag_values=fv,
    )
    flags.DEFINE_enum(
        'edition',
        None,
        ['STANDARD', 'ENTERPRISE', 'ENTERPRISE_PLUS'],
        'Type of editions for the reservation or capacity commitment. '
        'Options include:'
        '\n STANDARD'
        '\n ENTERPRISE'
        '\n ENTERPRISE_PLUS'
        '\n Used in conjunction with --reservation or --capacity_commitment.'
        '\n STANDARD cannot be used together with --capacity_commitment.',
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
            'AUTOSCALE_ONLY',
            'IDLE_SLOTS_ONLY',
            'ALL_SLOTS',
        ],
        'The scaling mode for the reservation. Available only for reservations '
        'enrolled in the Max Slots Preview. It needs to be specified together '
        'with --max_slots. It cannot be used together with '
        '--autoscale_max_slots. Options include:'
        '\n AUTOSCALE_ONLY'
        '\n IDLE_SLOTS_ONLY'
        '\n ALL_SLOTS',
        flag_values=fv,
    )
    flags.DEFINE_boolean(
        'reservation_group',
        None,
        'Creates a reservation group described by this identifier. ',
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
    flags.DEFINE_boolean(
        'connection', None, 'Create a connection.', flag_values=fv
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
        'connector_configuration',
        None,
        'Connection configuration for connector in JSON format.',
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
    flags.DEFINE_boolean(
        'federated_azure',
        None,
        '[Experimental] Federated identity for Azure.',
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
        'default_kms_key',
        None,
        'Defines default KMS key name for all newly objects created in the '
        'dataset. Table/Model creation request can override this default.',
        flag_values=fv,
    )
    flags.DEFINE_boolean(
        'use_avro_logical_types',
        True,
        'If sourceFormat is set to "AVRO", indicates whether to enable '
        'interpreting logical types into their corresponding types '
        '(ie. TIMESTAMP), instead of only using their raw types (ie. INTEGER).',
        flag_values=fv,
    )
    flags.DEFINE_string(
        'source_dataset',
        None,
        'When set to a dataset reference, creates a Linked Dataset pointing to '
        'the source dataset.',
        flag_values=fv,
    )
    flags.DEFINE_string(
        'external_source',
        None,
        (
            'External source that backs this dataset. Currently only AWS Glue'
            ' databases are supported (format'
            ' aws-glue://<AWS_ARN_OF_GLUE_DATABASE>)'
        ),
        flag_values=fv,
    )
    flags.DEFINE_string(
        'external_catalog_dataset_options',
        None,
        'Options defining open source compatible datasets living in the'
        ' BigQuery catalog. Contains metadata of open source database or'
        ' default storage location represented by the current dataset. The'
        ' value can be either an inline JSON or a path to a file containing a'
        ' JSON definition.',
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
    flags.DEFINE_boolean(
        'parquet_enum_as_string',
        False,
        'Infer Parquet ENUM logical type as STRING '
        '(instead of BYTES by default).',
        flag_values=fv,
    )
    flags.DEFINE_boolean(
        'parquet_enable_list_inference',
        False,
        frontend_utils.PARQUET_LIST_INFERENCE_DESCRIPTION,
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
    flags.DEFINE_enum(
        'metadata_cache_mode',
        None,
        ['AUTOMATIC', 'MANUAL'],
        'Enables metadata cache for an external table with a connection. '
        'Specify AUTOMATIC to automatically refresh the cached metadata. '
        'Specify MANUAL to stop the automatic refresh.',
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
    flags.DEFINE_boolean(
        'preserve_ascii_control_characters',
        False,
        'Whether to preserve embedded Ascii Control characters in CSV External '
        'table ',
        flag_values=fv,
    )
    flags.DEFINE_string(
        'reference_file_schema_uri',
        None,
        'provide a reference file with the table schema, currently '
        'enabled for the formats: AVRO, PARQUET, ORC.',
        flag_values=fv,
    )
    flags.DEFINE_enum(
        'file_set_spec_type',
        None,
        ['FILE_SYSTEM_MATCH', 'NEW_LINE_DELIMITED_MANIFEST'],
        'Specifies how to discover files given source URIs. '
        'Options include: '
        '\n FILE_SYSTEM_MATCH: expand source URIs by listing files from the '
        'underlying object store. This is the default behavior.'
        '\n NEW_LINE_DELIMITED_MANIFEST: indicate the source URIs provided are '
        'new line delimited manifest files, where each line contains a URI '
        'with no wild-card.',
        flag_values=fv,
    )
    flags.DEFINE_string(
        'kms_key_name',
        None,
        'Cloud KMS key name used for encryption.',
        flag_values=fv,
    )
    flags.DEFINE_string(
        'add_tags',
        None,
        'Tags to attach to the dataset or table. The format is namespaced key:value pair like "1234567/my_tag_key:my_tag_value,test-project123/environment:production" ',  # pylint: disable=line-too-long
        flag_values=fv,
    )
    flags.DEFINE_string(
        'source',
        None,
        'Path to file with JSON payload for an update',
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
    self.null_marker_flag = frontend_flags.define_null_marker(flag_values=fv)
    self.null_markers_flag = frontend_flags.define_null_markers(flag_values=fv)
    self.time_zone_flag = frontend_flags.define_time_zone(flag_values=fv)
    self.date_format_flag = frontend_flags.define_date_format(flag_values=fv)
    self.datetime_format_flag = frontend_flags.define_datetime_format(
        flag_values=fv
    )
    self.time_format_flag = frontend_flags.define_time_format(flag_values=fv)
    self.timestamp_format_flag = frontend_flags.define_timestamp_format(
        flag_values=fv
    )
    self.timestamp_target_precision_flag = (
        frontend_flags.define_timestamp_target_precision(flag_values=fv)
    )
    self.source_column_match_flag = frontend_flags.define_source_column_match(
        flag_values=fv
    )
    self.parquet_map_target_type_flag = (
        frontend_flags.define_parquet_map_target_type(flag_values=fv)
    )
    flags.DEFINE_boolean(
        'migration_workflow',
        None,
        'Create a migration workflow.',
        flag_values=fv,
    )
    flags.DEFINE_string(
        'config_file',
        None,
        'The file containing the JSON of the migration workflow to create.',
        flag_values=fv,
    )
    self._ProcessCommandRc(fv)

  def printSuccessMessage(self, object_name: str, reference: str):
    print(
        "%s '%s' successfully created."
        % (
            object_name,
            reference,
        )
    )

  def RunWithArgs(
      self, identifier: str = '', schema: str = ''
  ) -> Optional[int]:
    # pylint: disable=g-doc-exception
    """Create a dataset, table, view, or transfer configuration with this name.

    See 'bq help mk' for more information.

    Examples:
      bq mk new_dataset
      bq mk new_dataset.new_table
      bq --dataset_id=new_dataset mk table
      bq mk -t new_dataset.newtable name:integer,value:string
      bq mk --view='select 1 as num' new_dataset.newview
         (--view_udf_resource=path/to/file.js)
      bq mk --materialized_view='select sum(x) as sum_x from dataset.table'
          new_dataset.newview
      bq mk -d --data_location=EU new_dataset
      bq mk -d --source_dataset=src_dataset new_dataset (requires allowlisting)
      bq mk -d
        --external_source=aws-glue://<aws_arn_of_glue_database>
        --connection_id=<connection>
        new_dataset
      bq mk --transfer_config --target_dataset=dataset --display_name=name
          -p='{"param":"value"}' --data_source=source
          --schedule_start_time={schedule_start_time}
          --schedule_end_time={schedule_end_time}
      bq mk --transfer_run --start_time={start_time} --end_time={end_time}
          projects/p/locations/l/transferConfigs/c
      bq mk --transfer_run --run_time={run_time}
          projects/p/locations/l/transferConfigs/c
      bq mk --reservation --project_id=project --location=us reservation_name
      bq mk --reservation_assignment --reservation_id=project:us.dev
          --job_type=QUERY --assignee_type=PROJECT --assignee_id=myproject
      bq mk --reservation_assignment --reservation_id=project:us.dev
          --job_type=QUERY --assignee_type=FOLDER --assignee_id=123
      bq mk --reservation_assignment --reservation_id=project:us.dev
          --job_type=QUERY --assignee_type=ORGANIZATION --assignee_id=456
      bq mk --reservation_group --project_id=project --location=us
          reservation_group_name
      bq mk --connection --connection_type='CLOUD_SQL'
        --properties='{"instanceId" : "instance",
        "database" : "db", "type" : "MYSQL" }'
        --connection_credential='{"username":"u", "password":"p"}'
        --project_id=proj --location=us --display_name=name new_connection
      bq mk --row_access_policy --policy_id=new_policy
      --target_table='existing_dataset.existing_table'
      --grantees='user:user1@google.com,group:group1@google.com'
      --filter_predicate='Region="US"'
      bq mk --source=file.json
      bq mk --migration_workflow --location=us --config_file=file.json
    """

    client = bq_cached_client.Client.Get()
    reference = None

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
        client_row_access_policy.create_row_access_policy(
            bqclient=client,
            policy_reference=reference,
            grantees=self.grantees.split(','),
            filter_predicate=self.filter_predicate,
        )
      except BaseException as e:
        raise bq_error.BigqueryError(
            "Failed to create row access policy '%s' on '%s': %s"
            % (self.policy_id, self.target_table, e)
        )
      self.printSuccessMessage('Row access policy', self.policy_id)
    elif self.reservation:
      object_info = None
      reference = bq_client_utils.GetReservationReference(
          id_fallbacks=client,
          identifier=identifier,
          default_location=bq_flags.LOCATION.value,
      )
      try:
        ignore_idle_arg = self.ignore_idle_slots
        if ignore_idle_arg is None:
          ignore_idle_arg = not self.use_idle_slots
        concurrency = self.target_job_concurrency
        if concurrency is None:
          concurrency = (
              self.concurrency
              if self.concurrency is not None
              else self.max_concurrency
          )
        object_info = client_reservation.CreateReservation(
            client=client.GetReservationApiClient(),
            api_version=bq_flags.API_VERSION.value,
            reference=reference,
            slots=self.slots,
            ignore_idle_slots=ignore_idle_arg,
            edition=self.edition,
            target_job_concurrency=concurrency,
            multi_region_auxiliary=self.multi_region_auxiliary,
            autoscale_max_slots=self.autoscale_max_slots,
            max_slots=self.max_slots,
            scaling_mode=self.scaling_mode,
            reservation_group_name=self.reservation_group_name,
            scheduling_policy_concurrency=self.scheduling_policy_concurrency,
            scheduling_policy_max_slots=self.scheduling_policy_max_slots,
        )
      except BaseException as e:
        raise bq_error.BigqueryError(
            "Failed to create reservation '%s': %s" % (identifier, e)
        )
      if object_info is not None:
        frontend_utils.PrintObjectInfo(
            object_info, reference, custom_format='show'
        )
    elif self.capacity_commitment:
      reference = bq_client_utils.GetCapacityCommitmentReference(
          id_fallbacks=client,
          identifier=identifier,
          default_location=bq_flags.LOCATION.value,
          default_capacity_commitment_id=' ',
      )
      try:
        object_info = client_reservation.CreateCapacityCommitment(
            client=client.GetReservationApiClient(),
            reference=reference,
            edition=self.edition,
            slots=self.slots,
            plan=self.plan,
            renewal_plan=self.renewal_plan,
            multi_region_auxiliary=self.multi_region_auxiliary,
        )
      except BaseException as e:
        raise bq_error.BigqueryError(
            "Failed to create capacity commitment in '%s': %s" % (identifier, e)
        )
      if object_info is not None:
        frontend_utils.PrintObjectInfo(
            object_info, reference, custom_format='show'
        )
    elif self.reservation_assignment:
      try:
        reference = bq_client_utils.GetReservationReference(
            id_fallbacks=client,
            default_location=bq_flags.LOCATION.value,
            identifier=self.reservation_id,
        )
        object_info = client_reservation.CreateReservationAssignment(
            client=client.GetReservationApiClient(),
            reference=reference,
            job_type=self.job_type,
            priority=self.priority,
            assignee_type=self.assignee_type,
            assignee_id=self.assignee_id,
            scheduling_policy_max_slots=self.scheduling_policy_max_slots,
            scheduling_policy_concurrency=self.scheduling_policy_concurrency,
        )
        reference = bq_client_utils.GetReservationAssignmentReference(
            id_fallbacks=client, path=object_info['name']
        )
        frontend_utils.PrintObjectInfo(
            object_info, reference, custom_format='show'
        )
      except BaseException as e:
        raise bq_error.BigqueryError(
            "Failed to create reservation assignment '%s': %s" % (identifier, e)
        )
    elif self.reservation_group:
      try:
        reference = bq_client_utils.GetReservationGroupReference(
            id_fallbacks=client,
            identifier=identifier,
            default_location=bq_flags.LOCATION.value,
        )
        object_info = client_reservation.CreateReservationGroup(
            reservation_group_client=client.GetReservationApiClient(),
            reference=reference,
        )
        frontend_utils.PrintObjectInfo(
            object_info, reference, custom_format='show'
        )
      except BaseException as e:
        raise bq_error.BigqueryError(
            "Failed to create reservation group '%s': %s" % (identifier, e)
        )
    elif self.transfer_config:
      transfer_client = client.GetTransferV1ApiClient()
      reference = 'projects/' + (
          bq_client_utils.GetProjectReference(id_fallbacks=client).projectId
      )
      credentials = False
      if self.data_source:
        credentials = utils_data_transfer.CheckValidCreds(
            reference, self.data_source, transfer_client
        )
      else:
        raise bq_error.BigqueryError('A data source must be provided.')
      auth_info = {}
      if (
          not credentials
          and self.data_source != 'loadtesting'
          and not self.service_account_name
      ):
        auth_info = utils_data_transfer.RetrieveAuthorizationInfo(
            reference, self.data_source, transfer_client
        )
      location = self.data_location or bq_flags.LOCATION.value
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
      transfer_name = client_data_transfer.create_transfer_config(
          transfer_client=client.GetTransferV1ApiClient(),
          reference=reference,
          data_source=self.data_source,
          target_dataset=self.target_dataset,
          display_name=self.display_name,
          refresh_window_days=self.refresh_window_days,
          params=self.params,
          auth_info=auth_info,
          service_account_name=self.service_account_name,
          destination_kms_key=self.destination_kms_key,
          managed_table_type=self.managed_table_type,
          notification_pubsub_topic=self.notification_pubsub_topic,
          schedule_args=schedule_args,
          location=location,
      )
      self.printSuccessMessage('Transfer configuration', transfer_name)
    elif self.transfer_run:
      formatter = utils_flags.get_formatter_from_flags()
      formatted_identifier = frontend_id_utils.FormatDataTransferIdentifiers(
          client, identifier
      )
      reference = bq_id_utils.ApiClientHelper.TransferConfigReference(
          transferConfigName=formatted_identifier
      )
      incompatible_options = (
          self.start_time or self.end_time
      ) and self.run_time
      incomplete_options = (
          not self.start_time or not self.end_time
      ) and not self.run_time
      if incompatible_options or incomplete_options:
        raise app.UsageError(
            'Need to specify either both --start_time and --end_time '
            'or only --run_time.'
        )
      results = list(
          map(
              utils_formatting.format_transfer_run_info,
              client_data_transfer.start_manual_transfer_runs(
                  transfer_client=client.GetTransferV1ApiClient(),
                  reference=reference,
                  start_time=self.start_time,
                  end_time=self.end_time,
                  run_time=self.run_time,
              ),
          )
      )
      utils_formatting.configure_formatter(
          formatter,
          bq_id_utils.ApiClientHelper.TransferRunReference,
          print_format='make',
          object_info=results[0],
      )
      for result in results:
        formatter.AddDict(result)
      formatter.Print()
    elif self.connection:
      # Create a new connection.
      connection_type_defined = self.connection_type
      connection_type_defined = (
          connection_type_defined or self.connector_configuration
      )
      if not connection_type_defined:
        error = (
            'Need to specify --connection_type or --connector_configuration.'
        )
        raise app.UsageError(error)

      if self.connection_type == 'AWS' and self.iam_role_id:
        self.properties = bq_processor_utils.MakeAccessRolePropertiesJson(
            self.iam_role_id
        )
        if not self.federated_aws:
          raise app.UsageError('Non-federated AWS connections are deprecated.')
      if self.connection_type == 'Azure' and self.tenant_id:
        if self.federated_azure:
          if not self.federated_app_client_id:
            raise app.UsageError(
                'Must specify --federated_app_client_id for federated Azure '
                'connections.'
            )
          self.properties = bq_processor_utils.MakeAzureFederatedAppClientAndTenantIdPropertiesJson(
              self.tenant_id, self.federated_app_client_id
          )
        else:
          self.properties = bq_processor_utils.MakeTenantIdPropertiesJson(
              self.tenant_id
          )

      param_properties = self.properties
      # All connection types require properties, except CLOUD_RESOURCE as
      # it serves as a container for a service account that is generated
      # by the connection service.
      if not param_properties and self.connection_type == 'CLOUD_RESOURCE':
        param_properties = '{}'
      # SPARK connections does not require properties since all the fields in
      # the properties are optional.
      if not param_properties and self.connection_type == 'SPARK':
        param_properties = '{}'
      properties_defined = param_properties
      properties_defined = properties_defined or self.connector_configuration
      if not properties_defined:
        error = 'Need to specify --properties or --connector_configuration'
        raise app.UsageError(error)
      created_connection = client_connection.CreateConnection(
          client=client.GetConnectionV1ApiClient(),
          project_id=bq_flags.PROJECT_ID.value,
          location=bq_flags.LOCATION.value,
          connection_type=self.connection_type,
          properties=param_properties,
          connection_credential=self.connection_credential,
          display_name=self.display_name,
          description=self.description,
          connection_id=identifier,
          kms_key_name=self.kms_key_name,
          connector_configuration=self.connector_configuration,
      )
      if created_connection:
        reference = bq_client_utils.GetConnectionReference(
            id_fallbacks=client, path=created_connection['name']
        )
        print('Connection %s successfully created' % reference)
        utils_formatting.maybe_print_manual_instructions_for_connection(
            created_connection, flag_format=bq_flags.FORMAT.value
        )
    elif self.migration_workflow:
      if not bq_flags.LOCATION.value:
        raise app.UsageError(
            'Need to specify location for creating migration workflows.'
        )
      if not self.config_file:
        raise app.UsageError(
            'Need to specify config file for creating migration workflows.'
        )
      reference = None
      self.DelegateToGcloudAndExit(
          'migration_workflows',
          'mk',
          identifier,
          command_flags_for_this_resource={
              'location': bq_flags.LOCATION.value,
              'config_file': self.config_file,
              'sync': bq_flags.SYNCHRONOUS_MODE.value,
              'synchronous_mode': bq_flags.SYNCHRONOUS_MODE.value,
          },
      )
    elif self.d or not identifier:
      reference = bq_client_utils.GetDatasetReference(
          id_fallbacks=client, identifier=identifier
      )
      if reference.datasetId and identifier:
        frontend_utils.ValidateDatasetName(reference.datasetId)
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
          "Invalid identifier '%s' for mk." % (identifier,),
          is_usage_error=True,
      )
    if isinstance(reference, bq_id_utils.ApiClientHelper.DatasetReference):
      if self.schema:
        raise app.UsageError('Cannot specify schema with a dataset.')
      if self.source and self.description:
        raise app.UsageError('Cannot specify description with a source.')
      if self.expiration:
        raise app.UsageError('Cannot specify an expiration for a dataset.')
      if self.external_table_definition is not None:
        raise app.UsageError(
            'Cannot specify an external_table_definition for a dataset.'
        )
      if (not self.force) and client_dataset.DatasetExists(
          apiclient=client.apiclient,
          reference=reference,
      ):
        message = "Dataset '%s' already exists." % (reference,)
        if not self.f:
          raise bq_error.BigqueryError(message)
        else:
          print(message)
          return
      default_table_exp_ms = None
      if self.default_table_expiration is not None:
        default_table_exp_ms = self.default_table_expiration * 1000
      default_partition_exp_ms = None
      if self.default_partition_expiration is not None:
        default_partition_exp_ms = self.default_partition_expiration * 1000

      location = self.data_location or bq_flags.LOCATION.value
      labels = None
      if self.label is not None:
        labels = frontend_utils.ParseLabels(self.label)

      if self.source_dataset:
        source_dataset_reference = bq_client_utils.GetDatasetReference(
            id_fallbacks=client, identifier=self.source_dataset
        )
      else:
        source_dataset_reference = None

      if self.external_source and self.source_dataset:
        raise app.UsageError(
            'Cannot specify both external_source and linked dataset.'
        )
      if self.external_catalog_table_options is not None:
        raise app.UsageError(
            'Cannot specify external_catalog_table_options for a dataset.'
        )
      if self.external_source:
        if not self.connection_id:
          if not self.external_source.startswith('google-cloudspanner:/'):
            raise app.UsageError(
                'connection_id is required when external_source is specified.'
            )
      resource_tags = None
      if self.add_tags is not None:
        resource_tags = bq_utils.ParseTags(self.add_tags)
      self.description, acl = frontend_utils.ProcessSource(
          self.description, self.source
      )
      command_flags_for_this_resource = {
          'description': self.description,
          'force': self.force,
      }
      # TODO(b/355324165): Add genralised code to handle defaults.
      if location and (location != 'us' or location != 'US'):
        command_flags_for_this_resource['location'] = location
      # The DatasetExists check has already happened.
      self.PossiblyDelegateToGcloudAndExit(
          resource='datasets',
          bq_command='mk',
          identifier=identifier,
          command_flags_for_this_resource=command_flags_for_this_resource,
      )
      client_dataset.CreateDataset(
          apiclient=client.apiclient,
          reference=reference,
          ignore_existing=self.force,
          description=self.description,
          acl=acl,
          default_table_expiration_ms=default_table_exp_ms,
          default_partition_expiration_ms=default_partition_exp_ms,
          data_location=location,
          default_kms_key=self.default_kms_key,
          labels=labels,
          source_dataset_reference=source_dataset_reference,
          external_source=self.external_source,
          connection_id=self.connection_id,
          external_catalog_dataset_options=self.external_catalog_dataset_options,
          max_time_travel_hours=self.max_time_travel_hours,
          storage_billing_model=self.storage_billing_model,
          resource_tags=resource_tags,
      )
      self.printSuccessMessage('Dataset', reference)
    elif isinstance(reference, bq_id_utils.ApiClientHelper.TableReference):
      if self.source_dataset:
        raise app.UsageError('Cannot specify --source_dataset for a table.')
      object_name = 'Table'
      if self.view:
        object_name = 'View'
      if self.materialized_view:
        object_name = 'Materialized View'
      if (not self.force) and client_table.table_exists(
          apiclient=client.apiclient, reference=reference
      ):
        message = (
            "%s '%s' could not be created; a table with this name "
            'already exists.'
        ) % (
            object_name,
            reference,
        )
        if not self.f:
          raise bq_error.BigqueryError(message)
        else:
          print(message)
          return
      if schema:
        schema = bq_client_utils.ReadSchema(schema)
      else:
        schema = None
      expiration = None
      labels = None
      if self.label is not None:
        labels = frontend_utils.ParseLabels(self.label)
      if self.data_location:
        raise app.UsageError('Cannot specify data location for a table.')
      if self.default_table_expiration:
        raise app.UsageError('Cannot specify default expiration for a table.')
      if self.external_catalog_dataset_options is not None:
        raise app.UsageError(
            'Cannot specify external_catalog_dataset_options for a table.'
        )
      if self.expiration:
        expiration = int(self.expiration + time.time()) * 1000
      view_query_arg = self.view or None
      materialized_view_query_arg = self.materialized_view or None

      external_data_config = None
      if self.external_table_definition is not None:
        external_data_config = frontend_utils.GetExternalDataConfig(
            self.external_table_definition,
            self.use_avro_logical_types,
            self.parquet_enum_as_string,
            self.parquet_enable_list_inference,
            self.metadata_cache_mode,
            self.object_metadata,
            self.preserve_ascii_control_characters,
            self.reference_file_schema_uri,
            self.file_set_spec_type,
            self.null_marker_flag.value,
            self.null_markers_flag.value,
            self.time_zone_flag.value,
            self.date_format_flag.value,
            self.datetime_format_flag.value,
            self.time_format_flag.value,
            self.timestamp_format_flag.value,
            self.source_column_match_flag.value,
            parquet_map_target_type=self.parquet_map_target_type_flag.value,
            timestamp_target_precision=self.timestamp_target_precision_flag.value,
        )
        if (self.require_partition_filter is not None) and (
            'hivePartitioningOptions' in external_data_config
        ):
          raise app.UsageError(
              'Cannot specify require_partition_filter for hive partition'
              ' tables.'
          )
        if 'fileSetSpecType' in external_data_config:
          external_data_config['fileSetSpecType'] = (
              frontend_utils.ParseFileSetSpecType(
                  external_data_config['fileSetSpecType']
              )
          )

      biglake_config = None
      has_all_required_biglake_config = (
          self.connection_id
          and self.storage_uri  and self.table_format
      )
      has_some_required_biglake_config = (
          self.connection_id
          or self.storage_uri
          or self.file_format
          or self.table_format
      )
      if has_all_required_biglake_config:
        biglake_config = {
            'connection_id': self.connection_id,
            'storage_uri': self.storage_uri,
            'file_format': self.file_format,
            'table_format': self.table_format,
        }
      elif has_some_required_biglake_config:
        missing_fields = []
        if not self.connection_id:
          missing_fields.append('connection_id')
        if not self.storage_uri:
          missing_fields.append('storage_uri')
        if not self.table_format:
         missing_fields.append('table_format')
        missing_fields = ', '.join(missing_fields)
        raise app.UsageError(
            f'BigLake tables require {missing_fields} to be specified'
        )

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
      clustering = frontend_utils.ParseClustering(self.clustering_fields)
      range_partitioning = frontend_utils.ParseRangePartitioning(
          self.range_partitioning
      )
      table_constraints = None
      resource_tags = None
      if self.add_tags is not None:
        resource_tags = bq_utils.ParseTags(self.add_tags)
      client_table.create_table(
          apiclient=client.apiclient,
          reference=reference,
          ignore_existing=True,
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
          biglake_config=biglake_config,
          external_catalog_table_options=self.external_catalog_table_options,
          labels=labels,
          time_partitioning=time_partitioning,
          clustering=clustering,
          range_partitioning=range_partitioning,
          require_partition_filter=self.require_partition_filter,
          destination_kms_key=(self.destination_kms_key),
          table_constraints=table_constraints,
          resource_tags=resource_tags,
      )
      self.printSuccessMessage(object_name, reference)
