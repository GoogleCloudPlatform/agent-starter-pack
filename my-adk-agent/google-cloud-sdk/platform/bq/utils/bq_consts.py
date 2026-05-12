#!/usr/bin/env python
"""Constants for the BQ CLI."""

import enum
from typing import Literal


class Service(enum.Enum):
  """Enum for the different BigQuery APIs supported."""

  ANALYTICS_HUB = 1
  BIGLAKE = 2
  BIGQUERY = 3
  CONNECTIONS = 4
  RESERVATIONS = 5
  DTS = 6
  # This is the BQ core discovery doc with some IAM additions. See cl/600781292
  # for exactly what is added. There is some context in b/296612193 but IAM
  # needs to be a separate enum option until Dataset IAM is launched
  # (b/284146366).
  BQ_IAM = 7


FormatType = Literal['json', 'prettyjson', 'csv', 'sparse', 'pretty']

CustomPrintFormat = Literal[
    # Commands
    'list',
    'make',
    'show',
    # Resources
    'materialized_view',
    'schema',
    'table_replica',
    'view',
]
