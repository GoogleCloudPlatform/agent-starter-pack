#!/usr/bin/env python
"""BQ CLI library for wait printers."""

import logging
import sys
import time
from typing import Optional

import googleapiclient
import httplib2

from clients import utils as bq_client_utils


def _overwrite_current_line(
    s: str, previous_token: Optional[int] = None
) -> int:
  """Print string over the current terminal line, and stay on that line.

  The full width of any previous output (by the token) will be wiped clean.
  If multiple callers call this at the same time, it would be bad.

  Args:
    s: string to print.  May not contain newlines.
    previous_token: token returned from previous call, or None on first call.

  Returns:
    a token to pass into your next call to this function.
  """
  # Tricks in use:
  # carriage return \r brings the printhead back to the start of the line.
  # sys.stdout.write() does not add a newline.

  # Erase any previous, in case new string is shorter.
  if previous_token is not None:
    sys.stderr.write('\r' + (' ' * previous_token))
  # Put new string.
  sys.stderr.write('\r' + s)
  # Display.
  sys.stderr.flush()
  return len(s)


def execute_in_chunks_with_progress(request) -> None:
  """Run an apiclient request with a resumable upload, showing progress.

  Args:
    request: an apiclient request having a media_body that is a
      MediaFileUpload(resumable=True).

  Returns:
    The result of executing the request, if it succeeds.

  Raises:
    BigQueryError: on a non-retriable error or too many retriable errors.
  """
  result = None
  retriable_errors = 0
  output_token = None
  status = None
  while result is None:
    try:
      status, result = request.next_chunk()
    except googleapiclient.errors.HttpError as e:
      logging.error(
          'HTTP Error %d during resumable media upload', e.resp.status
      )
      # Log response headers, which contain debug info for GFEs.
      for key, value in e.resp.items():
        logging.info('  %s: %s', key, value)
      if e.resp.status in [502, 503, 504]:
        sleep_sec = 2**retriable_errors
        retriable_errors += 1
        if retriable_errors > 3:
          raise
        print('Error %d, retry #%d' % (e.resp.status, retriable_errors))
        time.sleep(sleep_sec)
        # Go around and try again.
      else:
        bq_client_utils.RaiseErrorFromHttpError(e)
    except (httplib2.HttpLib2Error, IOError) as e:
      bq_client_utils.RaiseErrorFromNonHttpError(e)
    if status:
      output_token = _overwrite_current_line(
          'Uploaded %d%%... ' % int(status.progress() * 100), output_token
      )
  _overwrite_current_line('Upload complete.', output_token)
  sys.stderr.write('\n')
  return result


class WaitPrinter:
  """Base class that defines the WaitPrinter interface."""

  def print(self, job_id: str, wait_time: float, status: str) -> None:
    """Prints status for the current job we are waiting on.

    Args:
      job_id: the identifier for this job.
      wait_time: the number of seconds we have been waiting so far.
      status: the status of the job we are waiting for.
    """
    raise NotImplementedError('Subclass must implement Print')

  def done(self) -> None:
    """Waiting is done and no more Print calls will be made.

    This function should handle the case of Print not being called.
    """
    raise NotImplementedError('Subclass must implement Done')


class WaitPrinterHelper(WaitPrinter):
  """A Done implementation that prints based off a property."""

  print_on_done = False

  def done(self) -> None:
    if self.print_on_done:
      sys.stderr.write('\n')


class QuietWaitPrinter(WaitPrinterHelper):
  """A WaitPrinter that prints nothing."""

  def print(
      self, unused_job_id: str, unused_wait_time: float, unused_status: str
  ):
    pass


class VerboseWaitPrinter(WaitPrinterHelper):
  """A WaitPrinter that prints every update."""

  def __init__(self):
    self.output_token = None

  def print(self, job_id: str, wait_time: float, status: str) -> None:
    self.print_on_done = True
    self.output_token = _overwrite_current_line(
        'Waiting on %s ... (%ds) Current status: %-7s'
        % (job_id, wait_time, status),
        self.output_token,
    )


class TransitionWaitPrinter(VerboseWaitPrinter):
  """A WaitPrinter that only prints status change updates."""

  _previous_status = None

  def print(self, job_id: str, wait_time: float, status: str) -> None:
    if status != self._previous_status:
      self._previous_status = status
      super(TransitionWaitPrinter, self).print(job_id, wait_time, status)
