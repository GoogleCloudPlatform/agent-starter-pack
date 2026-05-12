#!/usr/bin/env python
"""BQ CLI frontend flag utils."""

from typing import Optional

from absl import app
from absl import flags

import table_formatter
import bq_flags
from clients import utils as bq_client_utils

FLAGS = flags.FLAGS


def using_alpha_feature(feature: bq_flags.AlphaFeatures) -> bool:
  return feature in bq_flags.ALPHA.value


def fail_if_not_using_alpha_feature(feature: bq_flags.AlphaFeatures) -> None:
  if not using_alpha_feature(feature):
    raise app.UsageError(f"Please specify '--alpha={feature.value}' and retry.")


def get_formatter_from_flags(
    secondary_format: Optional[str] = 'sparse',
) -> table_formatter.TableFormatter:
  if FLAGS['format'].present:
    return table_formatter.GetFormatter(FLAGS.format)
  else:
    return table_formatter.GetFormatter(secondary_format)


def get_job_id_from_flags() -> Optional[bq_client_utils.JobIdGenerator]:
  """Returns the job id or job generator from the flags."""
  if FLAGS.fingerprint_job_id and FLAGS.job_id:
    raise app.UsageError(
        'The fingerprint_job_id flag cannot be specified with the job_id flag.'
    )
  if FLAGS.fingerprint_job_id:
    return bq_client_utils.JobIdGeneratorFingerprint()
  elif FLAGS.job_id is None:
    return bq_client_utils.JobIdGeneratorIncrementing(
        bq_client_utils.JobIdGeneratorRandom()
    )
  elif FLAGS.job_id:
    return FLAGS.job_id
  else:
    # User specified a job id, but it was empty. Let the
    # server come up with a job id.
    return None
