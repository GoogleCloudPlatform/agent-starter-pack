"""API for accessing data files from the Google codebase.

Provide a consistent API for accessing data files from the Google
codebase, whether the program is being run from a PAR file, a
Google3 module-space, or whatever.

A "resource" is simply the contents of a named file, and can be made available
by adding a data dependency in the BUILD file, e.g.:

    data = ["//foo/bar:filename.txt"],

The name of a resource is something like
`google3/tools/includes/IMPORTMAP`.  Formally, it's a relative path
name, and it's relative to the root of the Google code base (the
directory immediately above the google, google2, google3
directories).

Path components are separated by forward slashes on all platforms
regardless of the native filesystem conventions.

Search order for resources:
 1) If this module was loaded from a parfile, look in the parfile.
 2) Look relative to this module's `__file__` attribute, outside of READONLY
    to give files that are opened in the P4 client preference.
 3) Look relative to this module's `__file__` attribute, if available
 4) Look relative to `sitecustomize.GOOGLEBASE`, if available
 5) Look relative to `os.environ["GOOGLEBASE"]`, if available
 6) Check for a READONLY symlink for srcfs

Unless otherwise noted, these functions are NOT thread-safe.
"""

# For maximum PAR file happiness, we don't want this module to import
# other Google code.

import atexit
import builtins
import errno
import functools
import importlib.abc
import importlib.resources
import io
import locale
import os
import shutil
import sys
import tempfile
import threading
import typing
from typing import Any, BinaryIO, Callable, Dict, Iterable, Iterator, List, Literal, Optional, TextIO, Tuple, Union
import zipfile  # Must import zipfile at startup because of b/135941387

# TODO(b/408451275, b/409324907): Code needs to be compatible with versions
# before 3.10 before end of 4/2025 because of dependency from the BQ CLI
# (go/bq-cli-python-versions) team, and CSDNM team.
_Path = Union[str, 'os.PathLike[str]']

# Check for the special module provided by Hermetic Python. Don't try
# importing it, so we don't pick up a different module if we're not using
# Hermetic Python.
_launcher_info = sys.modules.get('_launcher_info')
if _launcher_info is not None and _launcher_info.is_par:
  import _elfzipimport  # pylint: disable=import-error,g-import-not-at-top
else:
  _elfzipimport = None
# pylint: enable=g-import-not-at-top,invalid-name

# This controls sys.stderr debug verbosity when accessing resources.
_verbosity = (
    sys.flags.verbose
    or os.environ.get('PYTHONVERBOSE', 0)
    or os.environ.get('RESOURCESVERBOSE', 0)
)
_OCTAL_777 = 0o777

_GOOGLE3_STR = os.sep + 'google3' + os.sep

MetaPathFinder = Any  # an implementation of importlib.abc.MetaPathFinder


# TODO(user): Why can't this use pyglib logging? It'd be a lot better if this
# could just show up in the INFO logs when resources verbosity is enabled.
def _Log(msg: str) -> None:
  if _verbosity:
    sys.stderr.write('[pid:%s] %s %s\n' % (os.getpid(), sys.argv[0], msg))


@functools.lru_cache(maxsize=None)
def _Runfiles() -> 'importlib.abc.Traversable':
  # `parent` is missing from the Travserable type signature, but it's there
  # in both concrete implementations: pathlib.Path and zipfile.Path
  return importlib.resources.files('google3').parent  # pytype: disable=attribute-error


def Get(*paths: _Path) -> 'importlib.abc.Traversable':
  """Provide a pathlib-style access to files inside the google3 runfiles directory.

  This is a read-only view of data dependencies of your build rule. It is
  preferred over GetResource() or GetResourceFilename(). The functionality
  is thread-safe, and it does not trigger a .par file extraction to disk.

  Unlike other methods here, there is no filesystem resolution order: only
  one location: Either runfiles or the par file, will be observed.

  The return value of a Get('filename') call is an object that implements
  the methods of go/importlib.abc.Traversable.

  The important methods are:

    * resources.Get(path).open() -> IO[str]
    * resources.Get(path).open(mode='rb') -> IO[bytes]
    * resources.Get(path).read_bytes() -> bytes
    * resources.Get(path).read_text() -> str
    * resources.Get(path).joinpath(name) -> Traversable

  In a .par file context, the concrete class of the Traversable will be
  zipfile.Path, and in a runfiles context (such as a Python unit test) it will
  be pathlib.Path.

  Example usage:

      from pyglib import resources

      with resources.Get('google3/project/testdata/input.txt').open() as f:
        for line in f:
          process(line)

      testdata_dir = resources.Get('google3/project/testdata')
      inputs = [testdata_dir.joinpath(filename).read_text()
                for filename in filenames]

  Supported on Python 3.10 or later.

  Args:
    *paths: The path segements to join together to find the file under the
      runfiles directory. For example: ('google3/pyglib/build_data.txt') or
      ('google3/pyglib/testdata', 'gfile_test.txt')

  Returns:
    An go/importlib.abc.Traversable instance, which gives important methods
    like: is_dir(), is_file(), joinpath(child), open(mode=...), read_bytes()
    and read_text(). If the path does not exist, then no error will be raised.
  """
  return _Runfiles().joinpath(*paths)


if sys.version_info < (3, 10):
  del Get  # Unsupported on older versions of Python


@typing.overload
def GetResource(
    name: _Path,
    mode: Literal['rb'] = 'rb',
    encoding: Optional[str] = None,
    errors: Optional[str] = None,
) -> bytes:
  ...


@typing.overload
def GetResource(
    name: _Path,
    mode: Literal['r', 'rt'] = 'rt',
    encoding: Optional[str] = None,
    errors: Optional[str] = None,
) -> str:
  ...


@typing.overload
def GetResource(
    name: _Path,
    mode: str = 'rb',
    encoding: Optional[str] = None,
    errors: Optional[str] = None,
) -> Union[bytes, str]:
  ...


def GetResource(
    name: _Path,
    mode: str = 'rb',
    encoding: Optional[str] = None,
    errors: Optional[str] = None,
) -> Union[bytes, str]:
  """Get the file contents of the named resource.

  Defaults to returning bytes, if you want str, then pass 'r' or 'rt' as the
  mode argument. This function is thread-safe.

  See also: WalkResources(), for finding what resources are available. e.g.
  from a directory.

  Args:
    name: The name of the resource. Example: google3/pyglib/resources.py
    mode: The file mode. GetResource only supports text read-only ('r' or 'rt')
      and binary read-only ('rb').
    encoding: The name of the encoding that the data will be decoded with if
      necessary. Defaults to locale.getpreferredencoding.
    errors: Optional string specifying how decoding errors are to be handled.
            https://docs.python.org/3/library/codecs.html#error-handlers

  Returns:
    The contents of the named resource as a bytes object OR when text mode is
    specified (mode='r' or mode='rt') it is returned as a str.
  Raises:
    IOError: if the name is not found, or the resource cannot be opened.
    ValueError: If the mode is not supported.
  """

  if mode not in ('r', 'rb', 'rt'):
    raise ValueError('Invalid mode: %r' % mode)
  # This may throw IOError.
  (filename, data) = FindResource(name, mode, encoding, errors)
  if data is None:
    assert filename
    if 'b' not in mode and not errors:
      errors = 'strict'
    with open(filename, mode, encoding=encoding, errors=errors) as data_file:
      data = data_file.read()
  return data


@typing.overload
def GetResourceAsFile(
    name: _Path,
    mode: Literal['rb'] = 'rb',
    encoding: Optional[str] = None,
    errors: Optional[str] = None,
) -> BinaryIO:
  ...


@typing.overload
def GetResourceAsFile(
    name: _Path,
    mode: Literal['rt', 'r'] = 'rt',
    encoding: Optional[str] = None,
    errors: Optional[str] = None,
) -> TextIO:
  ...


@typing.overload
def GetResourceAsFile(
    name: _Path,
    mode: str = 'rb',
    encoding: Optional[str] = None,
    errors: Optional[str] = None,
) -> Union[BinaryIO, TextIO]:
  ...


def GetResourceAsFile(
    name: _Path,
    mode: str = 'rb',
    encoding: Optional[str] = None,
    errors: Optional[str] = None,
) -> Union[BinaryIO, TextIO]:
  """Get the open file object to the named resource.

  Defaults to returning BinaryIO, if you want TextIO, then pass 'r' or 'rt' as
  the mode argument. This function is thread-safe.

  See also: WalkResources(), for finding what resources are available. e.g.
  from a directory.

  Args:
    name: The name of the resource. Example: google3/pyglib/resources.py
    mode: The file mode. GetResource only supports text read-only ('r' or 'rt')
      and binary read-only ('rb').
    encoding: The name of the encoding that the data will be decoded with if
      necessary. Defaults to locale.getpreferredencoding.
    errors: Optional string specifying how decoding errors are to be handled.
            https://docs.python.org/3/library/codecs.html#error-handlers

  Returns:
    The open file object to the named resource.
  Raises:
    IOError: if the name is not found, or the resource cannot be opened.
    ValueError: If the mode is not supported.
  """
  if mode not in ('r', 'rb', 'rt'):
    raise ValueError('Invalid mode: %r' % mode)
  # This may throw IOError.
  (filename, data) = FindResource(name, mode, encoding, errors)
  assert (filename or data) is not None
  if filename:
    if mode != 'rb' and not errors:
      errors = 'strict'
    return open(filename, mode, encoding=encoding, errors=errors)  # pytype: disable=bad-return-type
  elif mode == 'rb':
    return io.BytesIO(data)
  else:
    return io.StringIO(data)


# Temporary files.  Map from resource name to file name.
_temporaries = {}
_temporaries_lock = threading.RLock()


def GetResourceFilename(name: _Path, mode: str = 'rb') -> str:
  """Get file name of the named resource within a par file.

  Don't use this function if you can use one of the above functions
  instead, because it's less efficient for resources in PAR files.

  It may return the name of a temporary file if the resource doesn't
  natively exist in the filesystem (i.e. part of a PAR file).

  This function is thread-safe.

  NOTE: This method might fail on diskless machines. See
  go/borg-python-howto#resources_apis_that_write.

  See also: WalkResources(), for finding what resources are available. e.g.
  from a directory.

  Args:
    name: The name of the resource. Example: google3/pyglib/resources.py. Must
      point to a file, not a directory.
    mode: Unused; only present for API compatibility.

  Returns:
    The absolute path to the temporary file.
  Raises:
    IOError if the name is not found, or the resource cannot be opened.
  """

  del mode  # unused
  with _temporaries_lock:
    filename = _temporaries.get(name)
    if filename:
      try:
        # Do utime (aka touch) instead of just stat to reduce the chances
        # tmpwatch or something similar will remove the file before the caller
        # is done with it.
        os.utime(filename, None)
        return filename
      except OSError as e:
        if e.errno != errno.ENOENT:
          raise
      # The file doesn't exist, recreate it. This can happen for example when
      # tmpwatch cleans up unused files.
      del _temporaries[name]

    # Ignore the passed-in mode, since we don't return an opened file in this
    # function. This avoids coding artifacts.
    (filename, data) = FindResource(name, 'rb')  # maybe throws IOError
    if not filename:
      assert data is not None
      filename = _CreateTemporaryFile(name, data)
      _Log(
          'Resource %s does not already exist, writing it to temp file %s\n'
          % (name, filename)
      )
      permissions = _ParGetPermissions(name)
      if permissions is not None:
        os.chmod(filename, permissions)

  return filename


_resource_directory = None
# A lock that protects _resource_directory.
_resource_directory_lock = threading.Lock()
_resource_directory_files = []


def GetResourceDirectory() -> str:
  """Get the base temp directory used by GetResourceFilenameInDirectoryTree.

  All files from a par file extract their files to a temporary directory,
  depending on how you access a resource, the temp directory it ends up in
  will differ.

  GetResourceFilename files are extracted individually
  GetARootDirWithAllResources are extracted to a different temp directory

  This function is thread-safe.

  NOTE: This method might fail on diskless machines. See
  go/borg-python-howto#resources_apis_that_write.

  Returns:
    The absolute path to the base temporary directory.
  """
  global _resource_directory
  _resource_directory_lock.acquire()
  try:
    if _resource_directory:
      return _resource_directory

    _resource_directory = tempfile.mkdtemp()
  finally:
    _resource_directory_lock.release()

  # Delete file at program exit.
  # Alias external symbols because other modules might have been cleaned up by
  # the time we get called.

  # Originally this code used os.removedirs() on _resource_directory and the
  # directories mentioned in _resource_directory_files. Unfortunately
  # os.removedirs keeps walking up the filesystem hierarchy, and it could
  # end up deleting the directory *containing* _resource_directory
  # (http://b/25613255). It would have probably made more sense to use
  # shutil.rmtree, but the code as it is takes care to only delete files it
  # knows about, presumably on purpose. The best we can do is what
  # os.removedirs() does but preventing it from "leaving"
  # _resource_directory.
  def SafeRemovedirs(
      path: str,
      dirname: str,
      rmdir: Callable[[str], None] = os.rmdir,
      split: Callable[[str], Tuple[str, str]] = os.path.split,
  ):
    rmdir(path)
    if not path.startswith(dirname + '/'):
      # if path does not appear to be in _resource_directory, something went
      # wrong; avoid walking up the filesystem.
      return
    while True:
      path, unused_subdir = split(path.rstrip('/'))
      if not path or not path.startswith(dirname):
        break
      try:
        rmdir(path)
      except OSError:
        break

  def DeleteResourceDirectoryresourceDir(
      unlink: Callable[[str], None],
      dirname: Callable[[str], str],
      removedirs: Callable[[str, str], None],
      enoent_error: Exception,
      directory: str,
      files: List[str],
  ):
    """Deleted the directory from resource directory."""
    for filename in files:
      try:
        unlink(filename)
        _Log('# deleted resource tmpfile %s\n' % filename)
      except EnvironmentError as e:
        _Log('# error deleting tmpfile %s: %s\n' % (filename, e))
    for path in sorted(set([dirname(f) for f in files]), reverse=True):
      try:
        removedirs(path, directory)
      except EnvironmentError as e:
        if e != enoent_error:
          _Log('# error deleting tmpfile path %s: %s\n' % (path, e))
    try:
      removedirs(directory, directory)
      _Log('# deleted resource tmpdirectory %s\n' % directory)
    except EnvironmentError as e:
      _Log('# error deleting tmpfile %s: %s\n' % (directory, e))

  atexit.register(
      DeleteResourceDirectoryresourceDir,
      unlink=os.unlink,
      dirname=os.path.dirname,
      removedirs=SafeRemovedirs,
      enoent_error=errno.ENOENT,
      directory=_resource_directory,
      files=_resource_directory_files,
  )
  return _resource_directory


def GetResourceFilenameInDirectoryTree(name: _Path, mode: str = 'rb') -> str:
  """Get the name of a file that contains the named resource.

  The file is guaranteed to have the same name as the resource and be in the
  same directory tree as the resource requested.

  All files will be created under the directory returned by
  GetResourceDirectory().

  This function is thread-safe.

  NOTE: This method might fail on diskless machines. See
  go/borg-python-howto#resources_apis_that_write.

  Args:
    name: The name of the resource. Example: google3/pyglib/resources.py
    mode: Unused; only present for API compatibility.

  Returns:
    The absolute path to a file that contains the named resource.
  Raises:
    IOError: If the name is not found, or the resource cannot be opened.
  """

  del mode  # unused
  filename = os.path.join(GetResourceDirectory(), name)
  if os.path.exists(filename):
    return filename

  directory = os.path.dirname(filename)

  if not os.path.exists(directory):
    # os.makedirs raises an exception if a directory already exists. This is bad
    # if you have multiple threads attempting to create a directory tree at the
    # same time. See http://go/comp-lang-python-os-makedirs for the discussion.
    try:
      os.makedirs(directory)
    except OSError as e:
      if e.errno != errno.EEXIST or not os.path.isdir(directory):
        raise

  # Ignore the passed-in mode, since we don't return an opened file in this
  # function. This avoids coding artifacts.
  (resourcefilename, data) = FindResource(name, 'rb')  # maybe throws IOError

  if data is None:
    assert resourcefilename
    with open(resourcefilename, 'rb') as f:  # maybe throws IOError
      data = f.read()
    try:
      permissions = os.stat(resourcefilename).st_mode
    except OSError:
      permissions = None
  else:
    permissions = _ParGetPermissions(name)

  # Write the file to a temporary path and atomically rename it when done.
  (fd, tmp_path) = tempfile.mkstemp(suffix=os.path.basename(filename))
  tmp_file = os.fdopen(fd, 'wb')
  try:
    tmp_file.write(data)
    tmp_file.close()

    if permissions is not None:
      os.chmod(tmp_path, permissions)
  except (IOError, OSError):
    os.remove(tmp_path)
    raise

  try:
    if os.path.exists(filename):
      # Another thread already wrote the file.
      os.remove(tmp_path)
    else:
      os.rename(tmp_path, filename)
      # If another thread performed this rename after the call to os.path.exists
      # this append will insert a duplicate entry.  If so, an extraneous error
      # message may be logged at exit.
      _resource_directory_files.append(filename)
  except OSError:
    if os.path.exists(tmp_path):
      os.remove(tmp_path)
    if not os.path.exists(filename):
      raise

  return filename


def _CreateTemporaryFile(name: _Path, data: Union[bytes, str]) -> str:
  """Create a temporary file with the specified contents.

  The temporary file will be deleted at program finish.
  This function is thread-safe.

  Args:
    name: A name string to base the temporary file's name on.
    data: Bytes to be written to the temporary file.

  Returns:
    An absolute filename.
  """

  with _temporaries_lock:
    assert name not in _temporaries

    file_name, suffix = os.path.splitext(os.path.basename(name))
    py_binary_name = os.path.splitext(os.path.basename(sys.argv[0]))[0]
    prefix = '{}__py_binary_resource_{}__'.format(file_name, py_binary_name)
    mode = 'wb' if isinstance(data, bytes) else 'w'
    with tempfile.NamedTemporaryFile(
        prefix=prefix, suffix=suffix, delete=False, mode=mode
    ) as f:
      try:
        f.write(data)
        filename = f.name
      except EnvironmentError as e:
        e.add_note(
            f'Failed to write {len(data):,} bytes to temporary file {f.name}'
        )
        os.remove(f.name)
        raise
    _temporaries[name] = filename

  # Save os.unlink because os might be None when we get called.
  def Delete(unlink=os.unlink, filename=filename):
    """Delete file at program exit."""
    try:
      unlink(filename)
      _Log('# deleted resource tmpfile %s\n' % filename)
    except EnvironmentError as e:
      _Log('# error deleting tmpfile %s: %s\n' % (filename, e))

  atexit.register(Delete)

  return filename


def _AttributeIsInUse(scope: str, attribute: str) -> bool:
  """Checks that a given attribute exists and is initialized properly."""
  return getattr(scope, attribute, None) is not None


def _GetLoader() -> MetaPathFinder:
  """Returns the python module __loader__ active for this scope."""
  return globals().get('__loader__', None)


def _IsClassicBootstrap(loader: MetaPathFinder) -> bool:
  return loader and _AttributeIsInUse(loader, '_par')


def _IsModernBootstrap(loader: MetaPathFinder) -> bool:
  return loader and _AttributeIsInUse(loader, 'par')


def _IsParLoader(loader: MetaPathFinder) -> bool:
  return (
      _IsClassicBootstrap(loader)
      or _IsModernBootstrap(loader)
      or _IsHermeticParLoader(loader)
      or 'FakeLoader' in str(loader)
  )


# Hermetic Python/PAR support. This duplicates some of the code from the
# classic and modern bootstraps and zipimport implementations, but it
# probably makes more sense for it to live here.


def UsingPythonLauncher() -> bool:
  """Returns True if we are running under Hermetic Python."""
  if _launcher_info:
    return _launcher_info.is_google3_python_launcher
  return False


# Cached ZipFile instance for Hermetic PAR files. Reading data from it is
# not thread-safe, but getting file information is. Unsafe access is
# protected through the _RESOURCE_LOCK, below.
_hermetic_par_zipfile = None


def _IsHermeticParLoader(loader: MetaPathFinder) -> bool:
  if not loader:
    return False
  if not _elfzipimport:
    return False
  return isinstance(loader, _elfzipimport.ElfZipImporter)


def _GetHermeticParZipFile() -> zipfile.ZipFile:
  global _hermetic_par_zipfile
  if _hermetic_par_zipfile is None:
    loader = _GetLoader()
    assert _IsHermeticParLoader(loader)
    _hermetic_par_zipfile = loader.get_zipfile()
  return _hermetic_par_zipfile


def _NormalizeFilename(parfile: str, pathlike: _Path) -> str:
  path = os.fspath(pathlike)
  parfile += '/'
  if path.startswith(parfile):
    path = path[len(parfile) :]
  return path


def _ExtractZipFile(
    zip_file: zipfile.ZipFile, predicate: Callable[[str], bool], path: _Path
) -> None:
  """Extract predicate-defined files to the path, and set permissions right."""
  for info in zip_file.infolist():
    if not predicate(info.filename):
      continue
    filename = zip_file.extract(info, path=path)
    # zipfile.ZipFile.extract claims to extract the file's information "as
    # accurately as possible", but it doesn't actually set the file's mode
    # or timestamp. The zipfile module API sucks. For classic and modern PAR
    # bootstraps, this logic is part of the bootstrap. Hermetic PAR files
    # don't extract, as such, so it makes more sense to do it here.
    mode = info.external_attr >> 16
    if mode:
      os.chmod(filename, mode)
    # The file timestamp is trickier to restore (the ZIP format only stores
    # local time) and it's unlikely anyone will care, so don't bother.
    # TODO(user): revisit this decision later.


def _ParGetPermissions(name: _Path) -> Optional[int]:
  """Get the file permissions of the given file.

  Returns an integer containing the permissions or None if they can't be
  acquired.

  This function does not modify global state, so it is thread-safe.

  Args:
    name: The name of the resource. Example: google3/pyglib/resources.py

  Returns:
    An integer containing the permissions or None if they can't be
    acquired.
  """
  loader = _GetLoader()
  name = os.fspath(name)
  if loader:
    if _IsClassicBootstrap(loader):
      # Repeating the line below prevents a windows error where
      # loader does not have the _NormalizeFilename function.
      name = loader._NormalizeFilename(name)  # pylint: disable=protected-access
      try:
        # pylint: disable=protected-access
        return (
            loader._par._zip_file.getinfo(name).external_attr >> 16
        ) & _OCTAL_777
        # pylint: enable=protected-access
      except KeyError:
        # Can't find the metadata for the file so we don't know the permissions.
        return None
    elif _IsModernBootstrap(loader):
      name = loader._NormalizeFilename(name)  # pylint: disable=protected-access
      resource = loader.par.StoredResource(name)
      if resource is not None:
        return resource.permissions & _OCTAL_777
    elif _IsHermeticParLoader(loader):
      name = _NormalizeFilename(loader.archive, name)
      zip_file = _GetHermeticParZipFile()
      try:
        return zip_file.getinfo(name).external_attr >> 16 & _OCTAL_777
      except KeyError:
        return None

  return None


# Lock to prevent race condition in ZipFile when accessing resources
# from multiple threads simultaneously.
_RESOURCE_LOCK = threading.Lock()


def _IsSubPath(root: _Path, path: _Path) -> bool:
  """Determine whether resource path is contained within root.

  This purposefully ignores symbolic links as resources are typically
  symlinked into /build/cas/... which is outside "root".

  Args:
    root: The path in which the resource is expected to be found.
    path: A resource path.

  Returns:
    True if "path" is a relative path or if it is an absolute path
    pointing within "root".
  """
  root = os.path.abspath(root)
  if not os.path.isabs(path):
    path = os.path.join(root, path)
  path = os.path.normpath(path)
  return os.path.commonprefix([root, path]) == root


@typing.overload
def FindResource(
    name: _Path,
    mode: Literal['r', 'rt'] = 'r',
    encoding: Optional[str] = None,
    errors: Optional[str] = None,
) -> Union[Tuple[str, None], Tuple[None, str]]:
  ...


@typing.overload
def FindResource(
    name: _Path,
    mode: Literal['rb'] = 'rb',
    encoding: Optional[str] = None,
    errors: Optional[str] = None,
) -> Union[Tuple[str, None], Tuple[None, bytes]]:
  ...


@typing.overload
def FindResource(
    name: _Path,
    mode: str = 'r',
    encoding: Optional[str] = None,
    errors: Optional[str] = None,
) -> Union[Tuple[str, None], Tuple[None, bytes]]:
  ...


def FindResource(
    name: _Path,
    mode: str = 'r',
    encoding: Optional[str] = None,
    errors: Optional[str] = None,
) -> Union[Tuple[str, None], Tuple[None, Union[bytes, str]]]:
  """Search for a named resource.

  Returns a tuple of (filename, file contents as string), where at
  least one element is not None, depending on the abilities of the
  entity where the resource was found.  E.g. resources from PAR files
  don't have independent filenames.

  This function is thread-safe.

  Args:
    name: The name of the resource. Example: google3/pyglib/resources.py
    mode: The mode to use for opening the file. This behaves the same way as the
      'mode' argument of __builtins__.open(), where 'b' must be supplied to get
      bytes.
    encoding: The name of the encoding that the data will be decoded with if
      necessary. Defaults to locale.getpreferredencoding.
    errors: Optional string specifying how decoding errors are to be handled.
            https://docs.python.org/3/library/codecs.html#error-handlers

  Returns:
    A tuple of (filename, file contents as string/bytes), where at
    least one element is not None, depending on the abilities of the
    entity where the resource was found.  E.g. resources from PAR files
    don't have independent filenames.
  Raises:
    IOError: If the name is not found, or the resource cannot be opened.
  """

  name = os.path.normpath(name)

  # 1 If this module was loaded from a parfile, look in the parfile.
  loader = _GetLoader()
  if sys.platform == 'win32':
    # On current Win32 Python version the attributes _par and par, tested by
    # _IsParLoader, are not defined so skip testing for them.
    is_par = True
  else:
    is_par = _IsParLoader(loader)
  if loader and _AttributeIsInUse(loader, 'get_data') and is_par:
    try:
      with _RESOURCE_LOCK:
        data = loader.get_data(name)
      if isinstance(data, bytes) and 'b' not in mode:
        data = data.decode(
            encoding or locale.getpreferredencoding(False), errors or 'strict'
        )
      _Log('# loading resource %s via __loader__\n' % name)
      return (None, data)
    except IOError as e:
      _Log('# resource %s not found by loader %s: %s' % (name, loader, e))

  root, readonly_root = _DeriveRootPathFromThisFile(__file__)

  # 2 Look relative to this module's __file__ attribute, outside of READONLY
  #   to give files that are opened in the P4 client preference.
  if root and _IsSubPath(root, name):
    filename = os.path.join(root, name)
    if os.path.isfile(filename):
      _Log(
          '# loading resource %s from %s via __file__ (non-READONLY)\n'
          % (name, filename)
      )
      return (filename, None)

  # 3 Look relative to this module's __file__ attribute, if available
  if readonly_root and _IsSubPath(readonly_root, name):
    filename = os.path.join(readonly_root, name)
    if os.path.isfile(filename):
      _Log(
          '# loading resource %s from %s via __file__ (READONLY)\n'
          % (name, filename)
      )
      return (filename, None)

  # 4 Look relative to sitecustomize.GOOGLEBASE, if available
  if 'sitecustomize' in sys.modules:
    sitecustomize = sys.modules['sitecustomize']
    root = getattr(sitecustomize, 'GOOGLEBASE', None)
    if root and _IsSubPath(root, name):
      filename = os.path.join(root, name)
      if os.path.isfile(filename):
        _Log(
            '# loading resource %s from %s via sitecustomize\n'
            % (name, filename)
        )
        return (filename, None)
      else:
        _Log('# resource %s not found via sitecustomize %s' % (name, root))

  # 5 Look relative to os.environ["GOOGLEBASE"], if available
  root = os.environ.get('GOOGLEBASE', None)
  if root and _IsSubPath(root, name):
    filename = os.path.join(root, name)
    if os.path.isfile(filename):
      _Log('# loading resource %s from %s via GOOGLEBASE\n' % (name, filename))
      return (filename, None)
    else:
      _Log('# resource %s not found in GOOGLEBASE %s' % (name, root))

  # 6 Check if the file is under a READONLY symlink for srcfs path
  # First check make-dbg or mach style relative srcfs.
  if name.startswith('../READONLY'):
    return (name, None)
  # Next check blaze style full paths.
  # Blaze input is like "/home/foo/client/google3/path/to/file.txt"
  # Find the google3 dir within the name and see if it has a READONLY
  readonly_path = None
  resource_name = None
  head = name
  # Start at the back of the path and go until google3.
  # This assumes there's no google3 anywhere else in the path.
  # Note: os.path.split('/') returns ('/', '') and
  # os.path.split('foo') return ('', 'foo').
  # Thus we know that we have run out of path components when head ends with
  #  '/' or is the empty string.  We use endswith instead of equality because
  # we can run into a case where head winds up set to something like '//',
  # which would loop forever in this loop because
  # os.path.split('//') = ('//', '')
  while readonly_path is None and not head and not head.endswith('/'):
    (head, tail) = os.path.split(head)
    if resource_name is not None:
      resource_name = os.path.join(tail, resource_name)
    else:
      resource_name = tail

    if tail == 'google3':
      readonly_path = os.path.join(head, 'READONLY')

  if readonly_path is not None and _IsSubPath(readonly_path, resource_name):
    filename = os.path.join(readonly_path, resource_name)
    if os.path.isfile(filename):
      _Log(
          '# loading resource %s from %s via srcfs READONLY\n'
          % (name, filename)
      )
      return (filename, None)

  # If all else fails, see if it's just an absolute filesystem path pointing
  # to a previously extracted resource. This is not a documented use, but there
  # are over 67,000 tests depending on it. We explicitly don't allow resolving
  # arbitrary non-resource files as to mitigate some directory traversal
  # attacks.
  if os.path.isabs(name):
    # This lookup is O(n), which could cause poor performance if
    # GetResourceFilename is called a lot and then FindResource is used in
    # this unsupported manner. We could add a dict indexed by path to speed
    # this up but instead of adding complexity in the library it seems saner
    # for the users to fix their code.
    if name in _temporaries.values():
      _Log(
          '# UNSUPPORTED LEGACY USAGE: loading resource from previously '
          'extracted file. resources.py is only expected to handle google3 '
          'resource paths. That is an absolute path you should open with '
          'gfile instead: %s\n' % name
      )
      return (name, None)
    else:
      _Log(
          '# discarding absolute path not pointing to known resource: %s\n'
          % name
      )

  raise IOError(errno.ENOENT, 'Resource not found', name)


class _FileIndex:
  """A structure for holding a tree of files.

  This index is used internally by resources.py to help implement an os.walk
  style API.
  """

  def __init__(self, filenames: List[str]) -> None:
    """Creates a file index from a list of file paths.

    Args:
      filenames: A list of strings like 'dir1/dir2/somefile'. An empty directory
        can be expressed as 'dir1/dir2/'. This is the same as the output of
        ZipFile.namelist().
    """
    # A dictionary like {'dir1': {'dir2': {'somefile': None}}}. Directories will
    # be expressed as dictionaries of their contents, and files will be
    # expressed as None.
    self._dict: Dict[str, Any] = {}

    for filename in filenames:
      components = filename.lstrip('/').split('/')
      if not components:
        continue
      d: Any = self._dict
      for component in components[:-1]:
        if component not in d:
          d[component] = {}
        d = d[component]
      filename = components[-1]
      if filename:
        d[filename] = None

  def Walk(self, top: str) -> Iterable[Tuple[str, List[str], List[str]]]:
    """Walks the directory tree like os.walk."""

    def ProcessDir(
        prefix, d: Dict[str, Any]
    ) -> Iterable[Tuple[str, List[str], List[str]]]:
      """Yield 3-tuples for a directory."""
      dirnames = []
      filenames = []
      items = sorted(d.items())
      for k, v in items:
        if v is not None:
          dirnames.append(k)
        else:
          filenames.append(k)
      yield (prefix, dirnames, filenames)
      for k, v in items:
        if v is not None:
          for entry in ProcessDir(os.path.join(prefix, k), v):
            yield entry

    d = self._LookupPath(top)
    if d is not None:
      for entry in ProcessDir(top.strip('/'), d):
        yield entry

  def _LookupPath(self, path: str) -> Optional[Dict[str, Any]]:
    """Returns a directory entry from self._dict for a path."""
    components = path.split('/')

    # ignore a path that ends with '/'
    if not components[-1]:
      components = components[:-1]

    d = self._dict
    for component in components:
      if component not in d:
        return None
      d = d[component]
    return d


_par_file_index = None


def _TrimPathPrefixFromWalkIterable(
    path_prefix: str, iterable: Iterable[Tuple[str, List[str], List[str]]]
):
  for dirpath, dirnames, filenames in iterable:
    if not dirpath.startswith(path_prefix):
      raise ValueError(
          "path %r doesn't start with prefix %r" % (dirpath, path_prefix)
      )
    yield dirpath[len(path_prefix) :], dirnames, filenames


def WalkResources(path: _Path) -> Iterator[Tuple[str, List[str], List[str]]]:
  """Walks the directory tree of resources similar to os.walk.

  This can be useful for finding files within a directory when they aren't
  all known ahead of time (e.g., a glob(testdata/*) situation).

  Args:
    path: A string like 'google3/pyglib'.

  Returns:
    An iterator of 3-tuples (dirpath, dirnames, filenames). For example:
    ('google3/pyglib', ['tests'], ['resources.py']).
  """
  runfiles_dir = GetRunfilesDir()
  # Return a runfiles dir only if it's this file's runfiles dir and not from a
  # higher level, such as a test environment.
  if runfiles_dir and runfiles_dir == __file__.rpartition(_GOOGLE3_STR)[0]:
    abs_path = os.path.join(runfiles_dir, path)
    return _TrimPathPrefixFromWalkIterable(
        runfiles_dir + '/', os.walk(abs_path)
    )

  global _par_file_index
  with _RESOURCE_LOCK:
    if not _par_file_index:
      loader = globals().get('__loader__', None)
      if loader and hasattr(loader, 'get_data'):
        # pylint: disable=protected-access
        _par_file_index = _FileIndex(_ListAllFiles(loader))
        # pylint: enable=protected-access

  if _par_file_index:
    return _par_file_index.Walk(str(path))
  return iter([])


def _DeriveRootPathFromThisFile(
    this_filename: str,
) -> Tuple[Optional[str], Optional[str]]:
  """Get the root and READONLY root path of this Piper client.

  Args:
    this_filename: The complete path to this file (resources.py).

  Returns:
    A tuple of the root path and READONLY root path of this Piper client,
    assuming it is a client at all.  Callers should test their presence on the
    filesystem before using them.
  """
  readonly_root = None
  root = None
  if this_filename:
    # this_filename is like <root>/google3/pyglib/resources.py
    # where <root> is either the srcfs READONLY folder or the actual client
    # root.
    google3_dir = os.path.dirname(
        os.path.dirname(os.path.abspath(this_filename))
    )
    tentative_root = os.path.dirname(google3_dir)
    if 'google3' == os.path.basename(google3_dir):
      root = tentative_root
      if os.path.basename(root) == 'READONLY':
        readonly_root = root
        root = os.path.dirname(root)
      else:
        readonly_root = os.path.join(root, 'READONLY')
  return root, readonly_root


def GetRunfilesDir() -> Optional[str]:
  """Get the runfiles directory.

  Note: this function only looks for the runfiles dir of a google3
  program run from a google3/... subtree. It will not return the
  similarly-named <name>.runfiles directory created by the PAR
  extractor when running a PAR file. (This means that when called
  from a PAR file, it might return the runfiles from a containing
  google3 program. Please do not rely on this.)

  Returns:
    The runfiles directory for the currently-running program.
  """
  # Before Hermetic Python, this just used FindRunfilesDir() passing
  # sys.argv[0] as the starting point. This has the dubious behaviour, in
  # the case of PAR files, of sometimes returning a containing program's
  # runfiles, if that's where the PAR file is, or the working directory as
  # fallback. That's because argv[0] for a py_binary stub would be the .py
  # file (which is inside the runfiles directory), but argv[0] for a PAR
  # file is the PAR file (which, if it even has unpacked runfiles, is
  # usually outside its own runfiles.) This was probably not by design, but
  # some number of google3 tests and genrules ended up depending on it.
  # TODO(b/23267581): make GetRunfilesDir an error in PAR files and clean up
  # the breakages.
  #
  # When using Hermetic Python, argv[0] is always the launcher binary, which
  # is usually not inside the runfiles directory (although it can be.) To
  # emulate the old behaviour with Hermetic Python, use argv[0] only when
  # we're running from a PAR file, and use __file__ otherwise.
  #
  # We use __file__ also if running under Eclipse's Google PyDev launcher
  # which has sys.argv[0] set to:
  # /usr/local/google/eclipse.../plugins/org.python.pydev_.../pysrc/runfiles.py
  starting_point = sys.argv[0]
  if ('/org.python.pydev' in starting_point) or (
      UsingPythonLauncher() and not _RunningInsideParFile()
  ):
    starting_point = __file__
  return FindRunfilesDir(os.path.abspath(starting_point))


def FindRunfilesDir(program_filename: str) -> Optional[str]:
  r"""Look for a runfiles directory corresponding to the given program.

  We assume that program name is like one of:
   1) <root>/google3/<package>/<file>.<extension>
      - or -
      <root>/google3/bin/<package>/<file>.<extension>
      Runfiles :=  <root>/google3/bin/<package>/<file>.runfiles
   2) <root>/google3/linux-dbg/<package>/<file>.runfiles/google3/\
      <package2>/<file>.py
      Runfiles :=  <root>/google3/linux-dbg/<package>/<file>.runfiles

  Args:
    program_filename: absolute path to a Google3 Python program
  Returns:
    The path to the runfiles directory, or None if one wasn't found.
  """

  def _GetBinaryDirectoryFilename(filename: str) -> Tuple[str, str]:
    """Find a match for the binary filename and its path.

    If the binary directory isn't known, search the program's
    filename for a binary directory.

    Args:
      filename: The name of the binary file.

    Returns:
      A tuple of the binary directory, and the filename relative to that
      directory.
      If the binary directory isn't known, search the program's
      filename for a binary directory
    """
    # first, see if filename begins with a bin directory
    for bindir in ['bin', 'blaze-bin']:
      bindir_sep = bindir + os.sep
      if filename.startswith(bindir_sep):
        filename = filename[len(bindir_sep) :]
        return bindir, filename
    # if not, find the bin directory in the absolute programname
    for elem in os.path.abspath(sys.argv[0]).split(os.sep):
      if elem in ['bin', 'blaze-bin']:
        return elem, filename
    # shouldn't happen but will fail os.path.isdir below
    return '', filename

  google3_idx = program_filename.rfind(_GOOGLE3_STR)
  if google3_idx != -1:
    root_dir = program_filename[:google3_idx]
    rel_filename = program_filename[google3_idx + len(_GOOGLE3_STR) :]
    bindir, rel_filename = _GetBinaryDirectoryFilename(rel_filename)
    rel_filename_noext = os.path.splitext(rel_filename)[0]
    runfiles = os.path.join(
        root_dir, 'google3', bindir, rel_filename_noext + '.runfiles'
    )
    if os.path.isdir(runfiles):
      return runfiles
    return root_dir
  else:
    return None


_extracted_root_dir = None


def _RunningInsideParFile() -> bool:
  """Determine if we are executing within a par file or not.

  DO NOT USE, PLEASE.  You don't need it and you don't want to have your
  program depend on par run context. Use the other methods in this module
  to make your code work anywhere, not special modes based on this hack
  to hack your own stuff.

  Note that there is a public version of this in //pyglib:parinfo if you won't
  be dissuaded.

  Returns:
    boolean value: True if we are running inside a par file.
  """
  loader = _GetLoader()
  if not loader:
    return False
  return (
      _IsClassicBootstrap(loader)
      or _IsModernBootstrap(loader)
      or _IsHermeticParLoader(loader)
  )


def _ListAllFiles(loader) -> List[str]:
  """Attempt to get a python archive from the module loader."""
  if _IsClassicBootstrap(loader):  # Classic zipimport_tinypar.py API.
    # pylint: disable=protected-access
    # The available API is unfortunately _protected.
    return loader._par.NameList()
    # pylint: enable=protected-access
  elif _IsModernBootstrap(loader):  # zipimport_modern.py API.
    return sorted(loader.par.resources.keys())
  elif _IsHermeticParLoader(loader):
    return loader.get_zipfile().namelist()
  else:
    raise NotImplementedError('Unknown .par module loader: %r' % loader)


def GetARootDirWithAllResources(
    filename_predicate: Union[str, Callable[[str], bool]] = lambda x: 1,
    skip_previous_extraction_check: bool = False,
) -> str:
  """Get a root directory containing all the resources matching a predicate.

  Tries the following steps and returns at the first successful step
    * Returns a root dir previously found/extracted by this function and cached.
      This check can be skipped with skip_previous_extraction_check.
    * If this program is a par file, extract all files out of it into a temp
      tree and return its root. The temp tree is automatically cleaned on exit
      unless the process is terminated with an unhandled signal (i.e., SIGTERM
      or SIGKILL).
    * If this program is a google3 target built in a standard google3
      client tree, find and return the runfiles directory built with it.

  NOTE: This function returns "a" root dir with all the resources and
  not "the" root dir. It is not necessary that the directory returned
  by this function is the one that will be used by GetResource...() functions
  in this module to find resources. If the executable is a par file, the first
  call to this function may lead to an expensive extraction of files from the
  par file into a new directory.

  NOTE: This method might fail on diskless machines. See
  go/borg-python-howto#resources_apis_that_write.

  Args:
    filename_predicate: Callable predicate used to filter which files are
      extracted from the par file, or a string that should be the prefix of all
      paths.
    skip_previous_extraction_check: Performs the extraction even if it has been
      done before. This is useful when using different filename_predicates in
      successive calls.

  Returns:
    root: Path to root directory.

  Raises:
    OSError: if an error occurs, such as disk full or unable to find the correct
      directory.
    NotImplementedError: If used with unsupported .par startup code.
  """
  if isinstance(filename_predicate, str):
    path_prefix = filename_predicate
    filename_predicate = lambda path: path.startswith(path_prefix)
  elif not callable(filename_predicate):
    raise ValueError(
        'filename_predicate must be callable or str, got:'
        f' {filename_predicate!r}'
    )

  def _ExtractParFileResourcesUnconditionally() -> str:
    """Extract the par file to a local directory."""
    loader = _GetLoader()
    with _RESOURCE_LOCK:
      if _IsClassicBootstrap(loader):
        # Classic zipimport_tinypar.py API unpacks into a fresh temp separate
        # from the directory all the import files are sitting in.
        root = tempfile.mkdtemp(suffix='__unpar__.runfiles')
        try:
          # The available API is unfortunately _protected.
          loader._par._ExtractFiles(  # pylint: disable=protected-access
              filename_predicate, 'file', root
          )
        except EnvironmentError:
          shutil.rmtree(root, ignore_errors=True)
          raise
        atexit.register(shutil.rmtree, root, ignore_errors=True)
        return root

      elif _IsModernBootstrap(loader):  # zipimport_modern.py API.
        # zipimport_modern extracts into the existing bootstrap directory
        # which is not considered a "temp" as it is recycled between runs.
        return loader.par.ExtractMultipleResourcesByPredicateIfNeeded(
            extraction_predicate=filename_predicate,
            force_extract=skip_previous_extraction_check,
        )
      elif _IsHermeticParLoader(loader):
        # With Hermetic PAR files, nothing is extracted by default, and
        # there is no canonical runfiles directory. Like the classic tinypar
        # bootstrap, unpack into a fresh temporary directory instead.
        root = tempfile.mkdtemp(suffix='__unpar__.runfiles')
        try:
          _ExtractZipFile(_GetHermeticParZipFile(), filename_predicate, root)
        except EnvironmentError:
          shutil.rmtree(root, ignore_errors=True)
          raise
        atexit.register(shutil.rmtree, root, ignore_errors=True)
        return root

      else:
        raise NotImplementedError('Unknown .par module loader: %r' % loader)

  global _extracted_root_dir

  # 1 if it was already extracted, return that.
  if _extracted_root_dir and not skip_previous_extraction_check:
    return _extracted_root_dir

  # 2 Par files should always follow their own extraction logic.
  if _RunningInsideParFile():
    if not _extracted_root_dir or skip_previous_extraction_check:
      _extracted_root_dir = _ExtractParFileResourcesUnconditionally()
    return _extracted_root_dir

  # 3 Return a runfiles dir only if it's this file's runfiles dir and not from
  # a higher level, such as a test environment.
  runfiles_dir = GetRunfilesDir()
  if not runfiles_dir:
    raise OSError('The runfiles directory could not be found.')

  if runfiles_dir == __file__.rpartition(_GOOGLE3_STR)[0]:
    _extracted_root_dir = runfiles_dir
    return _extracted_root_dir

  raise OSError(
      'Could not create or find the directory containing all resources.'
  )


# We use _UNINITIALIZED as the special value for _par_extract_all_files_cache,
# because we can not choose any other value as the default.
_UNINITIALIZED = object()
_par_extract_all_files_cache = _UNINITIALIZED


def ParExtractAllFiles() -> Optional[str]:
  """Extracts all files if running as par file.

  WARNING: This function will fail with permission errors when run on Borg.
  You should probably call resources.GetARootDirWithAllResources() instead.

  This function only tries to extract files once. Subsequent calls return value
  cached from previous runs.

  NOTE: This method might fail on diskless machines. See
  go/borg-python-howto#resources_apis_that_write.

  Returns:
    a string, runfiles directory, or None if an error happened or if not
    running as par file.
  Raises:
    Will raise exceptions if zipimport implementation raises something.
  """
  global _par_extract_all_files_cache
  if _par_extract_all_files_cache is _UNINITIALIZED:
    loader = _GetLoader()
    if loader:
      if _IsClassicBootstrap(loader):
        # pylint: disable=protected-access
        # The only API available in "classic" is unfortunately _protected.
        loader._par._ExtractAllFiles()
        _par_extract_all_files_cache = loader._par._SetAndGetRunfilesRoot()
        # pylint: enable=protected-access
      elif _IsModernBootstrap(loader):
        # zipimport_modern's loader has a different API.
        _par_extract_all_files_cache = (
            loader.par.ExtractMultipleResourcesByPredicateIfNeeded()
        )
      elif _IsHermeticParLoader(loader):
        # There isn't really a runfiles directory for Hermetic PAR files,
        # so just fall back to GetARootDirWithAllResources().
        _par_extract_all_files_cache = GetARootDirWithAllResources()
      else:  # Other loader means we're not running in a .par file.
        _par_extract_all_files_cache = None
    else:  # No loader means we're not running in a .par file.
      _par_extract_all_files_cache = None
  return _par_extract_all_files_cache  # pytype: disable=bad-return-type


_PAR_PREFIX = None
_BUILTIN_OPEN = None


@typing.overload
def _ParOpen(  # pylint: disable=keyword-arg-before-vararg
    path: _Path, mode: Literal['r', 'rt'] = 'r', *args, **kwargs
) -> TextIO:
  ...


@typing.overload
def _ParOpen(  # pylint: disable=keyword-arg-before-vararg
    path: _Path, mode: Literal['rb'] = 'rb', *args, **kwargs
) -> BinaryIO:
  ...


@typing.overload
def _ParOpen(  # pylint: disable=keyword-arg-before-vararg
    path: _Path, mode: str = 'r', *args, **kwargs
) -> Union[BinaryIO, TextIO]:
  ...


def _ParOpen(  # pylint: disable=keyword-arg-before-vararg
    path: _Path, mode: str = 'r', *args, **kwargs
) -> Union[BinaryIO, TextIO]:
  """Internal method for opening a par file.

  Args:
    path: Path to the par file.
    mode: file mode for opening the file.
    *args: Other argments to apply to the Open command.
    **kwargs: Keyword arguments to apply to the open command.

  Returns:
    A file handle to the par file.
  Raises:
    IOError: If the parfile is not writable, should write mode be specified.
  """
  path = os.path.abspath(path)

  if not path.startswith(_PAR_PREFIX):
    return _BUILTIN_OPEN(path, mode, *args, **kwargs)  # pytype: disable=bad-return-type

  # We only support reading.
  if any(write_indicator in mode for write_indicator in ['w', 'a', '+']):
    raise IOError(errno.EROFS, 'Parfiles are not writable: %r' % path)

  relative_path = path[len(_PAR_PREFIX) :]
  fp = GetResourceAsFile(relative_path)
  if 'b' in mode:
    return fp  # pytype: disable=bad-return-type
  return io.TextIOWrapper(fp, newline=kwargs.get('newline', None))  # pytype: disable=bad-return-type


def InstallParOpen() -> None:
  """Install an open that also works for files inside a par.

  It is highly recommended that this only be called by the main file of a
  py_binary and not from a py_library.

  Once this method is called, you can take a path to inside your par file:

      path = os.path.join(os.path.dirname(__file__), ...)
      # path = "/path/to/my.par/google3/whatever"

  and open it like any regular file:

      fp = open(path)
  """
  # If already installed, we're good to go.
  global _PAR_PREFIX, _BUILTIN_OPEN
  if _PAR_PREFIX is not None:
    return

  loader = _GetLoader()
  if _IsModernBootstrap(loader):
    par_name = loader.par.name
  elif _IsClassicBootstrap(loader):
    # pylint: disable=protected-access
    par_name = loader._par._zip_filename
    # pylint: enable=protected-access
  elif _IsHermeticParLoader(loader):
    par_name = loader.archive
  else:
    # Not running in a parfile so the normal open is sufficient.
    return

  _PAR_PREFIX = os.path.abspath(par_name) + '/'
  _BUILTIN_OPEN = builtins.open
  builtins.open = _ParOpen


def _UninstallParOpenForTestingOnly() -> None:  # pylint: disable=unused-private-name
  global _PAR_PREFIX, _BUILTIN_OPEN
  # Just in case someone else did a further monkeypatch.
  assert builtins.open == _ParOpen  # pylint: disable=comparison-with-callable

  builtins.open = _BUILTIN_OPEN
  _BUILTIN_OPEN = None
  _PAR_PREFIX = None
