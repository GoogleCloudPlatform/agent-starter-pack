#!/usr/bin/env python
"""Provides Logic for Fetching and Storing Discovery Documents from an on-disc cache."""

import hashlib
import os
import pathlib
import tempfile
from typing import Optional

from absl import logging

from pyglib import stringutil


_DISCOVERY_CACHE_FILE = 'api_discovery.json'


def _get_cache_file_name(
    cache_root: str, discovery_url: str, api_name: str, api_version: str
) -> pathlib.Path:
  """Returns the cache file name for the given api and version."""
  # Use the sha1 hash as this is not security-related, just need a stable hash.
  url_hash = hashlib.sha1(discovery_url.encode('utf-8')).hexdigest()
  return pathlib.Path(
      cache_root,
      url_hash,
      api_name,
      api_version,
      _DISCOVERY_CACHE_FILE,
  )


def get_from_cache(
    cache_root: str, discovery_url: str, api_name: str, api_version: str
) -> Optional[str]:
  """Loads a discovery document from the on-disc cache using key `api` and `version`.

  Args:
    cache_root: [str], a directory where all cache files are stored.
    discovery_url: [str], URL where the discovery document was fetched from.
    api_name: [str], Name of api `discovery_document` to be saved.
    api_version: [str], Version of document to get

  Returns:
    Discovery document as a dict.
    None if any errors occur during loading, or parsing the document
  """

  file = _get_cache_file_name(cache_root, discovery_url, api_name, api_version)

  if not os.path.isfile(file):
    logging.info('Discovery doc not in cache. %s', file)
    return None

  try:
    with open(file, 'rb') as f:
      contents = f.read()
    return contents.decode('utf-8')

  except Exception as e:  # pylint: disable=broad-except
    logging.warning('Error loading discovery document %s: %s', file, e)
    return None


def save_to_cache(
    cache_root: str,
    discovery_url: str,
    api_name: str,
    api_version: str,
    discovery_document: str,
) -> None:
  """Saves a discovery document to the on-disc cache with key `api` and `version`.

  Args:
    cache_root: [str], a directory where all cache files are stored.
    discovery_url: [str], URL where the discovery document was fetched from.
    api_name: [str], Name of api `discovery_document` to be saved.
    api_version: [str], Version of `discovery_document`.
    discovery_document: [str]. Discovery document as a json string.

  Raises:
    OSError: If an error occurs when the file is written.
  """

  file = _get_cache_file_name(cache_root, discovery_url, api_name, api_version)
  directory = file.parent

  # Return. File already cached.
  if file.exists():
    return

  directory.mkdir(parents=True, exist_ok=True)

  # Here we will write the discovery doc to a temp file and then rename that
  # temp file to our destination cache file. This is to ensure we have an
  # atomic file operation. Without this it could be possible to have a bq
  # client see the cached discovery file and load it although it is empty.
  # The temporary file needs to be in a unique path so that different
  # invocations don't conflict; both will be able to write to their temp
  # file, and the last one will move to final place.
  # TOO
  with tempfile.TemporaryDirectory(dir=directory) as tmpdir:
    temp_file_path = pathlib.Path(tmpdir) / 'tmp.json'
    with temp_file_path.open('wb') as f:
      f.write(stringutil.ensure_binary(discovery_document, 'utf8'))
      # Flush followed by fsync to ensure all data is written to temp file
      # before our rename operation.
      f.flush()
      os.fsync(f.fileno())
    # Atomically create (via rename) the 'real' cache file.
    temp_file_path.rename(file)
