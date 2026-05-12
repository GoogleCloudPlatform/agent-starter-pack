#!/usr/bin/env python
"""The BigQuery CLI wait command."""

import sys
from typing import Optional

from absl import app
from absl import flags

import bq_flags
from clients import client_job
from clients import utils as bq_client_utils
from frontend import bigquery_command
from frontend import bq_cached_client
from frontend import utils as frontend_utils
from utils import bq_error
from utils import bq_id_utils

# These aren't relevant for user-facing docstrings:
# pylint: disable=g-doc-return-or-yield
# pylint: disable=g-doc-args


class Wait(bigquery_command.BigqueryCmd):  # pylint: disable=missing-docstring
  usage = """wait [<job_id>] [<secs>]"""
  command = 'wait'

  def __init__(self, name: str, fv: flags.FlagValues):
    super(Wait, self).__init__(name, fv)
    flags.DEFINE_boolean(
        'fail_on_error',
        True,
        'When done waiting for the job, exit the process with an error '
        'if the job is still running, or ended with a failure.',
        flag_values=fv,
    )
    flags.DEFINE_string(
        'wait_for_status',
        'DONE',
        'Wait for the job to have a certain status. Default is DONE.',
        flag_values=fv,
    )
    self._ProcessCommandRc(fv)

  def RunWithArgs(self, job_id='', secs=sys.maxsize) -> Optional[int]:
    # pylint: disable=g-doc-exception
    """Wait some number of seconds for a job to finish.

    Poll job_id until either (1) the job is DONE or (2) the
    specified number of seconds have elapsed. Waits forever
    if unspecified. If no job_id is specified, and there is
    only one running job, we poll that job.

    Examples:
      bq wait # Waits forever for the currently running job.
      bq wait job_id  # Waits forever
      bq wait job_id 100  # Waits 100 seconds
      bq wait job_id 0  # Polls if a job is done, then returns immediately.
      # These may exit with a non-zero status code to indicate "failure":
      bq wait --fail_on_error job_id  # Succeeds if job succeeds.
      bq wait --fail_on_error job_id 100  # Succeeds if job succeeds in 100 sec.

    Arguments:
      job_id: Job ID to wait on.
      secs: Number of seconds to wait (must be >= 0).
    """
    try:
      secs = bq_client_utils.NormalizeWait(secs)
    except ValueError:
      raise app.UsageError('Invalid wait time: %s' % (secs,))

    client = bq_cached_client.Client.Get()
    if not job_id:
      running_jobs = client_job.ListJobRefs(
          bqclient=client, state_filter=['PENDING', 'RUNNING']
      )
      if len(running_jobs) != 1:
        raise bq_error.BigqueryError(
            'No job_id provided, found %d running jobs' % (len(running_jobs),)
        )
      job_reference = running_jobs.pop()
    else:
      job_reference = bq_client_utils.GetJobReference(
          id_fallbacks=client,
          identifier=job_id,
          default_location=bq_flags.LOCATION.value,
      )
    try:
      job = client_job.WaitJob(
          bqclient=client,
          job_reference=job_reference,
          wait=secs,
          status=self.wait_for_status,
      )
      frontend_utils.PrintObjectInfo(
          job,
          bq_id_utils.ApiClientHelper.JobReference.Create(
              **job['jobReference']
          ),
          custom_format='show',
      )
      return 1 if self.fail_on_error and bq_client_utils.IsFailedJob(job) else 0
    except StopIteration as e:
      print()
      print(e)
    # If we reach this point, we have not seen the job succeed.
    return 1 if self.fail_on_error else 0
