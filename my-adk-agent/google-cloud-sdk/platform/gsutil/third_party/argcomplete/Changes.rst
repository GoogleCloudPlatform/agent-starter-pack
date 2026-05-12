Changes for v3.6.2 (2025-04-02)
===============================

- Revert “zsh: skip repeat Python runs in the same completion run” This
  reverts a regression introduced in zsh tab completion configurations
  utilizing multiple matchers.

Changes for v3.6.1 (2025-03-22)
===============================

- zsh: add global completion system install dir to user fpath if not
  present

- Update shell_integration.py to support spaces in script file path.
  (#525)

- Fix completion when wordbreak is first character (#526)

Changes for v3.6.0 (2025-03-05)
===============================

- Support namespace package traversal when completing Python entry
  points

- zsh: skip repeat Python runs in the same completion run

- Make \_parse_known_args signature more general for future API changes

Changes for v3.5.3 (2024-12-31)
===============================

-  Use interactive shells and bind to make environment variable name
   completions work in older Bash versions (#506)

Changes for v3.5.2 (2024-12-06)
===============================

-  Fix \_parse_known_args monkeypatching

   - Note: This fix is required to restore compatibility with Python 3.12.8 and 3.13.1.

-  CI improvements

Changes for v3.5.1 (2024-10-06)
===============================

-  Restore compatibility with argparse in Python 3.12.7+ (#508)

Changes for v3.5.0 (2024-08-06)
===============================

-  Use project.scripts instead of setuptools scripts (#498)

-  Test infrastructure improvements

Changes for v3.4.0 (2024-06-16)
===============================

-  No stdin for python calls from bash completion functions (#488)

   Prevents usage of stdin by (python) executables that are called
   during completion generation. This prevents the completion locking up
   the entire shell when the python script is broken i.e. it enters an
   interactive mode (REPL) instead of generating the completions, as
   expected.

-  Localize shell variable REPLY to avoid overwriting users’ value
   (#489)

   The variable REPLY is used by default by the ``read`` shell builtin
   to store the return value, and like all bash/zsh variables, is scoped
   globally. This change allows this variable to be used for other needs
   by appropriately scoping its internal use by an argcomplete utility
   function that uses ``read``.

Changes for v3.3.0 (2024-04-14)
===============================

-  Preserve compatibility with argparse option tuples of length 4. This
   update is required to use argcomplete on Python 3.11.9+ or 3.12.3+.

Changes for v3.2.3 (2024-03-07)
===============================

-  Allow register-python-argcomplete output to be used as lazy-loaded
   zsh completion module (#475)

-  Move debug_stream initialization to helper method to allow fd 9
   behavior to be overridden in subclasses (#471)

Changes for v3.2.2 (2024-01-23)
===============================

Expand tilde in zsh

Changes for v3.2.1 (2023-12-10)
===============================

-  Allow explicit zsh global completion activation (#467)

Changes for v3.2.0 (2023-12-09)
===============================

-  Fix and test global completion in zsh (#463, #466)

-  Add –yes option to activate-global-python-argcomplete (#461)

-  Test suite improvements

Changes for v3.1.6 (2023-11-12)
===============================

-  Respect user choice in activate-global-python-argcomplete

Changes for v3.1.5 (2023-11-12)
===============================

-  Escape colon in zsh completions. Fixes #456

Changes for v3.1.4 (2023-11-01)
===============================

-  Call \_default as a fallback in zsh global completion

Changes for v3.1.3 (2023-11-01)
===============================

-  Use homebrew prefix by default

-  zsh: Allow to use external script (#453)

-  Add support for Python 3.12 and drop EOL 3.6 and 3.7 (#449)

Changes for v3.1.3 (2023-11-01)
===============================

-  Use homebrew prefix by default

-  zsh: Allow to use external script (#453)

-  Add support for Python 3.12 and drop EOL 3.6 and 3.7 (#449)

Changes for v3.1.2 (2023-09-16)
===============================

-  Ensure Python 3.12+ compatibility in check_console_script (#448)

Changes for v3.1.1 (2023-06-11)
===============================

-  Search through asdf shims

-  Use \` as escape character in PowerShell (#434)

Changes for v3.1.0 (2023-06-10)
===============================

-  setup.py -> pyproject.toml migration start (#427)

-  Improve user install logic in activate-global-python-argcomplete
   (#437)

-  Ensure Python 3.7 compatibility in check_console_script (#436)

-  ZSH implementation fixes (#431, #433)

-  Documentation improvements

Changes for v3.0.8 (2023-04-23)
===============================

-  Test suite shell wrapper: Accept OSError on exit

Changes for v3.0.7 (2023-04-23)
===============================

-  Test suite: Use general regex to cut zsh reset ANSI sequences (#425)

Changes for v3.0.6 (2023-04-22)
===============================

-  Allow importlib-metadata 6.x; skip test failures on Python 3.7 (#420,
   #424)

-  Note completers can return iterables of strings, not just lists
   (#422)

-  Documentation and test improvements

Changes for v3.0.5 (2023-03-25)
===============================

-  Call \_default as fallback in zsh global completion hook

-  Begin support for mapping-emitting completers

Changes for v3.0.4 (2023-03-21)
===============================

-  activate-global-python-argcomplete: do not overwrite existing dotfile
   in user directory

-  Add NOTICE file

-  Establish long term name for split_line as
   argcomplete.lexers.split_line

Changes for v3.0.3 (2023-03-20)
===============================

-  Re-add split_line to API (#419)

Changes for v3.0.2 (2023-03-19)
===============================

Fix zsh default completion issues

Changes for v3.0.1 (2023-03-19)
===============================

-  Fix zsh autoload issues

Changes for v3.0.0 (2023-03-19)
===============================

-  Fully support zsh. Argcomplete now supports completion descriptions
   and global completion in zsh.

-  Clean up top level namespace.

-  Documentation and test improvements.

Changes for v2.1.2 (2023-03-17)
===============================

-  Test infrastructure improvements

-  Indicate that there is no support commitment for fish and tcsh shells

Changes for v2.1.1 (2023-03-06)
===============================

-  Documentation and test improvements

Changes for v2.1.0 (2023-03-06)
===============================

-  Remove scripts for contrib-supported shells from global namespace

Changes for v2.0.6 (2023-03-06)
===============================

-  setup.py: exclude test.\* subpackages from find_packages (#406)

-  Support PowerShell (#405)

-  CI updates

Changes for v2.0.5 (2023-03-04)
===============================

-  Revert “Support powershell (#392)”

Changes for v2.0.4 (2023-03-04)
===============================

-  Fix interrupted release (v2.0.1)

Changes for v2.0.3 (2023-03-04)
===============================

-  Fix interrupted release (v2.0.1)

Changes for v2.0.2 (2023-03-04)
===============================

-  Fix interrupted release (v2.0.1)

Changes for v2.0.1 (2023-03-04)
===============================

-  Support powershell (#392)

-  Update importlib-metadata dependency to include versions 5.x (#389)

-  Test and documentation improvements

Changes for v2.0.0 (2022-01-03)
===============================

-  Truncate input after cursor. Fixes #351 (#352)

-  Support of path completion in fish #327 (#359)

-  Drop support for Python 2.7 and 3.5 (#361)

-  Add support for Python 3.10 (#356)

-  Test, documentation, and release infrastructure improvements

Changes for v1.12.3 (2021-04-19)
================================

-  Update importlib-metadata version pin (#345)

-  Display script debug output in tcsh (#342)

-  Fish support improvements (#338, #339)

-  Print ``warn()`` message from beginning of line (#335)

-  Test infrastructure improvements

Changes for v1.12.2 (2020-11-23)
================================

-  Update importlib-metadata dependency pin (#332)

-  Add change log project URL (#312)

-  Replace Travis CI with GitHub Actions (#323)

Changes for v1.12.1 (2020-09-26)
================================

-  Update importlib-metadata dependency version range

-  Bash nounset mode fixes (#313)

Changes for v1.11.1 (2020-01-14)
================================

-  Add -o bashdefault to register-python-argcomplete’s output command
   (#284)

Changes for v1.11.0 (2019-12-23)
================================

-  Use shell builtins where possible (#280)

-  Switch from pkg_resources to importlib (#283)

-  Remove .sh extension by bash-completion convention (#281)

-  Catch exceptions in \_check_module (#269)

-  Documentation and test improvements

Changes for v1.10.3 (2019-11-26)
================================

-  Do not suggest options after – (end-of-options delimiter)

Changes for v1.10.2 (2019-11-17)
================================

-  Include all test directory contents in source distribution

Changes for v1.10.1 (2019-11-16)
================================

-  Trigger completers on –optional=PARTIAL_VALUE

-  Complete console scripts installed from wheels (#241)

Changes for v1.10.0 (2019-05-12)
================================

-  Fish support #68 (#260), thanks to @volkov

Changes for v1.9.5 (2019-04-02)
===============================

-  check_module: Don’t crash, exit with error instead (#261)

-  Register completion for multiple commands (#246)

Changes for v1.9.4 (2018-02-13)
===============================

-  Use the correct interpreter when checking wrappers (#226)

-  Provide shellcode as a module function (#237)

Changes for v1.9.3 (2017-11-16)
===============================

-  Fix handling of COMP\_POINT (#236)

-  Fix crash when writing unicode to debug\_stream in Python 2 (#230)

Changes for v1.9.2 (2017-08-23)
===============================

-  Fix release

Changes for v1.9.1 (2017-08-23)
===============================

-  Fix release

Changes for v1.9.0 (2017-08-23)
===============================

-  Add SuppressCompleter to skip completion for specific arguments while
   allowing help text (#224)

-  Redirect all output to debug stream in debug mode (#206)

-  Complete python -m module (#204)

Changes for v1.8.2 (2017-01-26)
===============================

-  Fix bug introduced in v0.7.1 where completers would not receive the
   parser keyword argument.

-  Documentation improvements.

Changes for v1.8.1 (2017-01-21)
===============================

-  Fix completion after tokens with wordbreak chars (#197)

Changes for v1.8.0 (2017-01-19)
===============================

This release contains work by @evanunderscore with numerous improvements
to the handling of special characters in completions.

-  Simplify nospace handling in global completion (#195)

-  Specially handle all characters in COMP\_WORDBREAKS (#187)

-  Use setuptools tests-require directive, fixes #186

-  Complete files using the specified interpreter (#192)

-  Fix completion for scripts run via python (#191)

-  Clarify argument to register-python-argcomplete (#190)

-  Fix handling of commas and other special chars (#172); handle more
   special characters (#189)

-  Fix handling of special characters in tcsh (#188)

-  Update my\_shlex to Python 3.6 version (#184)

-  Fix additional trailing space in exact matches (#183)

-  Adjust tests to handle development environments (#180)

-  Fix tcsh tests on OSX (#177); Update bash on OSX (#176); Check output
   of test setup command (#179)

-  Optionally disable duplicated flags (#143)

-  Add default\_completer option to CompletionFinder.\ **call** (#167)

-  Let bash add or suppress trailing space (#159)

Changes for v1.7.0 (2016-11-30)
===============================

-  Restore parser to its original state to allow reuse after completion
   (#150).

-  Expose COMP\_TYPE environment variable (#157). Thanks to Matt Clay
   (@mattclay).

-  Test infrastructure and documentation improvements.

Changes for v1.6.0 (2016-10-20)
===============================

-  Add support for tcsh (#155)

-  Fix handling of unquoted completions containing $ (#154)

-  Don't insert unnecessary leading quote char in completions (#152)

-  Fix parser reuse with positional arguments (#149)

-  Tests: Add simple pexpect tests for bash (#153); Add test case to
   verify #20 is fixed (#148)

-  Thanks to @davvid and @evanunderscore for their work on this release.

Changes for v1.5.1 (2016-10-11)
===============================

-  Packaging fix

Changes for v1.5.0 (2016-10-11)
===============================

-  Do not suggest options from mutually exclusive groups (#145).

Version 1.4.1 (2016-06-14)
==========================
- activate-global-python-argcomplete runs on Homebrew out of the box

Version 1.4.0 (2016-06-10)
==========================
- Correctly handle suggestions for positionals with variable-length nargs. Thanks to @evanunderscore (#132, #133).

Version 1.3.0 (2016-06-01)
==========================
- Correctly handle suggestions with custom nargs for optionals. Thanks to @evanunderscore (#131).

Version 1.2.0 (2016-05-25)
==========================
- Fix propagation of partially parsed subparser namespace into parent parser namespace upon subparser failure due to
  partial args. This allows completers to access partial parse results for subparser optionals in parsed_args (#114).
- The default completer can now be specified when manually instantiating CompletionFinder. Thanks to @avylove (#130).

Version 1.1.1 (2016-03-22)
==========================
- Use FilesCompleter as default completer fallback (#120).

Version 1.1.0 (2016-02-21)
==========================
- Recognize subclasses of argparse._SubParsersAction. Thanks to Stephen Koo (#118).
- Support parsed_args in custom completers with missing args. Thanks to Dan Kilman (#124).
- Non-ASCII support in FilesCompleter.
- Automatically enable FilesCompleter for argparse.FileType arguments.

Version 1.0.0 (2015-08-22)
==========================
- Don't print args with suppressed help by default; add
  ``argcomplete.autocomplete(print_suppressed=True)`` to control this
  behavior (#113).

Version 0.9.0 (2015-07-03)
==========================
- Fix always_complete_options=False support (#115).

Version 0.8.9 (2015-06-01)
==========================
- Correct doc filename in setup.cfg (fixes bdist_rpm failure, Issue 111).
- Make context managers exception-safe. Thanks to Mikołaj Siedlarek (pull request #110).

Version 0.8.8 (2015-05-01)
==========================
- Build and upload universal wheel packages in release.
- Fix issue with non-string choices for arguments. Thanks to @neizod (pull request #107).
- Improve non-ascii argparse argument support on Python 2.7.

Version 0.8.7 (2015-04-11)
==========================
- register-python-argcomplete: add option to avoid default readline completion. Thanks to @drmalex07 (pull request #99).

Version 0.8.6 (2015-04-11)
==========================
- Expand tilde in script name, allowing argcomplete to work when invoking scripts from one's home directory. Thanks to @VorpalBlade (Issue 104).

Version 0.8.5 (2015-04-07)
==========================
- Fix issues related to using argcomplete in a REPL environment.
- New helper method for custom completion display.
- Expand test suite; formatting cleanup.

Version 0.8.4 (2014-12-11)
==========================
- Fix issue related to using argcomplete in a REPL environment. Thanks to @wapiflapi (pull request #91).

Version 0.8.3 (2014-11-09)
==========================
- Fix multiple issues related to using argcomplete in a REPL environment. Thanks to @wapiflapi (pull request #90).

Version 0.8.2 (2014-11-03)
==========================
- Don't strip colon prefix in completion results if COMP_WORDBREAKS does not contain a colon. Thanks to @berezv (pull request #88).

Version 0.8.1 (2014-07-02)
==========================
- Use complete --nospace to avoid issues with directory completion.

Version 0.8.0 (2014-04-07)
==========================
- Refactor main body of code into a class to enable subclassing and overriding of functionality (Issue #78).

Version 0.7.1 (2014-03-29)
==========================
- New keyword option "argcomplete.autocomplete(validator=...)" to supply a custom validator or bypass default validation. Thanks to @thijsdezoete (Issue #77).
- Document debug options.

Version 0.7.0 (2014-01-19)
==========================
- New keyword option "argcomplete.autocomplete(exclude=[...])" to suppress options (Issue #74).
- More speedups to code path for global completion hook negative result.

Version 0.6.9 (2014-01-19)
==========================
- Fix handling of development mode script wrappers. Thanks to @jmlopez-rod and @dcosson (Issue #69).
- Speed up code path for global completion hook negative result by loading pkg_resources on demand.

Version 0.6.8 (2014-01-18)
==========================
- Begin tracking changes in changelog.
- Add completion support for PBR installed scripts (PR #71).
- Detect easy-install shims with shebang lines that contain Py instead of py (Issue #69).
