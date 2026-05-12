=============================
What's New in Pyparsing 3.2.0
=============================

:author: Paul McGuire

:date: October, 2024

:abstract: This document summarizes the changes made
    in the 3.2.x releases of pyparsing.

.. sectnum::    :depth: 4

.. contents::   :depth: 4


Supported Python versions
=========================

- Added support for Python 3.13.

- Python versions before 3.9 are no longer supported.
  Removed legacy Py2.x support and other deprecated features. Pyparsing
  now requires Python 3.9 or later. If you are using an earlier 3.x
  version of Python, use pyparsing 3.1; for Python 2.x, use Pyparsing
  2.4.7.


New Features
============

- Added type annotations to remainder of ``pyparsing`` package, and added ``mypy``
  run to ``tox.ini``, so that type annotations are now run as part of pyparsing's CI.

- Exception message format can now be customized, by overriding
  ``ParseBaseException.format_message``::

      def custom_exception_message(exc) -> str:
          found_phrase = f", found {exc.found}" if exc.found else ""
          return f"{exc.lineno}:{exc.column} {exc.msg}{found_phrase}"

      ParseBaseException.formatted_message = custom_exception_message

- ``run_tests`` now detects if an exception is raised in a parse action, and will
  report it with an enhanced error message, with the exception type, string,
  and parse action name.

- ``QuotedString`` now handles translation of escaped integer, hex, octal, and
  Unicode sequences to their corresponding characters.

- Defined a more performant regular expression used internally by ``common_html_entity``.

- ``Regex`` instances can now be created using a callable that takes no arguments
  and just returns a string or a compiled regular expression, so that creating complex
  regular expression patterns can be deferred until they are actually used for the first
  time in the parser.

- Fixed the displayed output of ``Regex`` terms to deduplicate repeated backslashes,
  for easier reading in debugging, printing, and railroad diagrams.

- Fixed railroad diagrams that get generated with a parser containing a Regex element
  defined using a verbose pattern - the pattern gets flattened and comments removed
  before creating the corresponding diagram element.


API Changes
===========

Possible breaking changes
-------------------------
- Fixed code in ``ParseElementEnhance`` subclasses that
  replaced detailed exception messages raised in contained expressions with a
  less-specific and less-informative generic exception message and location.

  If your code has conditional logic based on the message content in raised
  ``ParseExceptions``, this bugfix may require changes in your code.

- Fixed bug in ``transform_string()`` where whitespace
  in the input string was not properly preserved in the output string.

  If your code uses ``transform_string``, this bugfix may require changes in
  your code.

- Fixed bug where an ``IndexError`` raised in a parse action was
  incorrectly handled as an ``IndexError`` raised as part of the ``ParserElement``
  parsing methods, and reraised as a ``ParseException``. Now an ``IndexError``
  that raises inside a parse action will properly propagate out as an ``IndexError``.

  If your code raises ``IndexError`` in parse actions, this bugfix may require
  changes in your code.


Additional API changes
----------------------
- Added optional ``flatten`` Boolean argument to ``ParseResults.as_list()``, to
  return the parsed values in a flattened list.

- Added ``indent`` and ``base_1`` arguments to ``pyparsing.testing.with_line_numbers``. When
  using ``with_line_numbers`` inside a parse action, set ``base_1``=False, since the
  reported ``loc`` value is 0-based. ``indent`` can be a leading string (typically of
  spaces or tabs) to indent the numbered string passed to ``with_line_numbers``.


New / Enhanced Examples
=======================
- Added query syntax to ``mongodb_query_expression.py`` with:

  - better support for array fields ("contains all",
    "contains any", and "contains none")
  - "like" and "not like" operators to support SQL "%" wildcard matching
    and "=~" operator to support regex matching
  - text search using "search for"
  - dates and datetimes as query values
  - ``a[0]`` style array referencing

- Added ``lox_parser.py`` example, a parser for the Lox language used as a tutorial in
  Robert Nystrom's "Crafting Interpreters" (http://craftinginterpreters.com/).

- Added ``complex_chemical_formulas.py`` example, to add parsing capability for
  formulas such as "Ba(BrO₃)₂·H₂O".

- Updated ``tag_emitter.py`` to use new ``Tag`` class, introduced in pyparsing
  3.1.3.


Acknowledgments
===============
Again, thanks to the many contributors who submitted issues, questions, suggestions,
and PRs.
