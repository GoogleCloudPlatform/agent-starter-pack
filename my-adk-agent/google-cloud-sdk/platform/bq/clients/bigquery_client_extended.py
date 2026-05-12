#!/usr/bin/env python
from clients import bigquery_client


class BigqueryClientExtended(bigquery_client.BigqueryClient):
  """Class extending BigqueryClient to add resource specific functionality."""

