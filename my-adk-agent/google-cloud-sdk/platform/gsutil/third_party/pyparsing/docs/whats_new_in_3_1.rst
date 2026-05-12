=============================
What's New in Pyparsing 3.1.0
=============================

:author: Paul McGuire

:date: October, 2024

:abstract: This document summarizes the changes made
    in the 3.1.x releases of pyparsing.

.. sectnum::    :depth: 4

.. contents::   :depth: 4


Supported Python versions
=========================
- Added support for Python 3.12.

- All internal string expressions using '%' string interpolation and ``str.format()``
  converted to f-strings.


New Features
============
- Added new ``Tag`` ParserElement, for inserting metadata into the parsed results.
  This allows a parser to add metadata or annotations to the parsed tokens.
  The ``Tag`` element also accepts an optional ``value`` parameter, defaulting to ``True``.
  See the new ``tag_metadata.py`` example in the ``examples`` directory.

  Example::

        # add tag indicating mood
        end_punc = "." | ("!" + Tag("enthusiastic")))
        greeting = "Hello" + Word(alphas) + end_punc

        result = greeting.parse_string("Hello World.")
        print(result.dump())

        result = greeting.parse_string("Hello World!")
        print(result.dump())

  prints::

        ['Hello', 'World', '.']

        ['Hello', 'World', '!']
        - enthusiastic: True

- Extended ``expr[]`` notation for repetition of ``expr`` to accept a
  slice, where the slice's stop value indicates a ``stop_on``
  expression::

      test = "BEGIN aaa bbb ccc END"
      BEGIN, END = Keyword.using_each("BEGIN END".split())
      body_word = Word(alphas)

      # new slice syntax support
      expr = BEGIN + Group(body_word[...:END]) + END
      # equivalent to
      # expr = BEGIN + Group(ZeroOrMore(body_word, stop_on=END)) + END

      print(expr.parse_string(test))

  Prints::

      ['BEGIN', ['aaa', 'bbb', 'ccc'], 'END']

- Added new class method ``ParserElement.using_each``, to simplify code
  that creates a sequence of ``Literals``, ``Keywords``, or other ``ParserElement``
  subclasses.

  For instance, to define suppressible punctuation, you would previously
  write::

      LPAR, RPAR, LBRACE, RBRACE, SEMI = map(Suppress, "(){};")

  You can now write::

      LPAR, RPAR, LBRACE, RBRACE, SEMI = Suppress.using_each("(){};")

  ``using_each`` will also accept optional keyword args, which it will
  pass through to the class initializer. Here is an expression for
  single-letter variable names that might be used in an algebraic
  expression::

      algebra_var = MatchFirst(
          Char.using_each(string.ascii_lowercase, as_keyword=True)
      )

- Added new builtin ``python_quoted_string``, which will match any form
  of single-line or multiline quoted strings defined in Python.

- ``Word`` arguments are now validated if ``min`` and ``max`` are both
  given, that ``min`` <= ``max``; raises ``ValueError`` if values are invalid.

- Added '·' (Unicode MIDDLE DOT) to the set of ``Latin1.identbodychars``.

- Added ``ieee_float`` expression to ``pyparsing.common``, which parses float values,
  plus "NaN", "Inf", "Infinity".

- Minor performance speedup in ``trim_arity``, to benefit any parsers using parse actions.


API Changes
===========
- ``Optional(expr)`` may now be written as ``expr | ""``

  This will make this code::

      "{" + Optional(Literal("A") | Literal("a")) + "}"

  writable as::

      "{" + (Literal("A") | Literal("a") | "") + "}"

  Some related changes implemented as part of this work:
  - ``Literal("")`` now internally generates an ``Empty()`` (and no longer raises an exception)
  - ``Empty`` is now a subclass of ``Literal``

- Added new class property ``identifier`` to all Unicode set classes in ``pyparsing.unicode``,
  using the class's values for ``cls.identchars`` and ``cls.identbodychars``. Now Unicode-aware
  parsers that formerly wrote::

      ppu = pyparsing.unicode
      ident = Word(ppu.Greek.identchars, ppu.Greek.identbodychars)

  can now write::

      ident = ppu.Greek.identifier
      # or
      # ident = ppu.Ελληνικά.identifier

- Added bool ``embed`` argument to ``ParserElement.create_diagram()``.
  When passed as True, the resulting diagram will omit the ``<DOCTYPE>``,
  ``<HEAD>``, and ``<BODY>`` tags so that it can be embedded in other
  HTML source. (Useful when embedding a call to ``create_diagram()`` in
  a PyScript HTML page.)

- Added ``recurse`` argument to ``ParserElement.set_debug`` to set the
  debug flag on an expression and all of its sub-expressions.

- Reworked ``delimited_list`` function into the new ``DelimitedList`` class.
  ``DelimitedList`` has the same constructor interface as ``delimited_list``, and
  in this release, ``delimited_list`` changes from a function to a synonym for
  ``DelimitedList``. ``delimited_list`` and the older ``delimitedList`` method will be
  deprecated in a future release, in favor of ``DelimitedList``.

- ``ParseResults`` now has a new method ``deepcopy()``, in addition to the current
  ``copy()`` method. ``copy()`` only makes a shallow copy - any contained ``ParseResults``
  are copied as references - changes in the copy will be seen as changes in the original.
  In many cases, a shallow copy is sufficient, but some applications require a deep copy.
  ``deepcopy()`` makes a deeper copy: any contained ``ParseResults`` or other mappings or
  containers are built with copies from the original, and do not get changed if the
  original is later changed.

- Added named field "url" to ``pyparsing.common.url``, returning the entire
  parsed URL string.

- Added exception type to ``trace_parse_action`` exception output.

- Added ``<META>`` tag to HTML generated for railroad diagrams to force UTF-8 encoding
  with older browsers, to better display Unicode parser characters.

- To address a compatibility issue in RDFLib, added a property setter for the
  ``ParserElement.name`` property, to call ``ParserElement.set_name``.

- Modified ``ParserElement.set_name()`` to accept a None value, to clear the defined
  name and corresponding error message for a ``ParserElement``.

- Updated railroad diagram generation for ``ZeroOrMore`` and ``OneOrMore`` expressions with
  ``stop_on`` expressions.


Discontinued Features
=====================

Python 2.x no longer supported
------------------------------
Removed Py2.x support and other deprecated features. Pyparsing
now requires Python 3.6.8 or later. If you are using an earlier
version of Python, you must use a Pyparsing 2.4.x version.

Other discontinued / deprecated features
----------------------------------------
- ``ParserElement.validate()`` is deprecated. It predates the support for left-recursive
  parsers, and was prone to false positives (warning that a grammar was invalid when
  it was in fact valid).  It will be removed in a future pyparsing release. In its
  place, developers should use debugging and analytical tools, such as ``ParserElement.set_debug()``
  and ``ParserElement.create_diagram()``.


Fixed Bugs
==========
- Updated ``ci.yml`` permissions to limit default access to source.

- Updated ``create_diagram()`` code to be compatible with railroad-diagrams package
  version 3.0.

- Fixed bug in ``pyparsing.common.url``, when input URL is not alone
  on an input line.

- Fixed bug in srange, when parsing escaped '/' and '\' inside a
  range set.

- Fixed exception messages for some ``ParserElements`` with custom names,
  which instead showed their contained expression names.

- Fixed bug in ``Word`` when ``max=2``. Also added performance enhancement
  when specifying ``exact`` argument.

- Fixed bug when parse actions returned an empty string for an expression that
  had a results name, that the results name was not saved. That is::

      expr = Literal("X").add_parse_action(lambda tokens: "")("value")
      result = expr.parse_string("X")
      print(result["value"])

  would raise a ``KeyError``. Now empty strings will be saved with the associated
  results name.

- Fixed bug in ``SkipTo`` where ignore expressions were not properly handled while
  scanning for the target expression.

- Fixed bug in ``NotAny``, where parse actions on the negated expr were not being run.
  This could cause ``NotAny`` to incorrectly fail if the expr would normally match,
  but would fail to match if a condition used as a parse action returned False.

- Fixed ``create_diagram()`` to accept keyword args, to be passed through to the
  ``template.render()`` method to generate the output HTML.

- Fixed bug in ``python_quoted_string`` regex.

- Fixed regression in Word(min).

- Fixed bug in bad exception messages raised by Forward expressions.

- Fixed regression in SkipTo, where ignored expressions were not checked when looking
  for the target expression.

- Updated pep8 synonym wrappers for better type checking compatibility.

- Fixed empty error message bug. This _should_ return
  pyparsing's exception messages to a former, more helpful form. If you have code that
  parses the exception messages returned by pyparsing, this may require some code
  changes.

- Fixed issue where PEP8 compatibility names for ``ParserElement`` static methods were
  not themselves defined as ``staticmethods``. When called using a ``ParserElement`` instance,
  this resulted  in a ``TypeError`` exception.

- Fixed some cosmetics/bugs in railroad diagrams:

  - fixed groups being shown even when ``show_groups`` = False

  - show results names as quoted strings when ``show_results_names`` = True

  - only use integer loop counter if repetition > 2


New / Enhanced Examples
=======================
- Added example ``mongodb_query_expression.py``, to convert human-readable infix query
  expressions, such as::

      a==100 and b>=200

  and transform them into an equivalent query argument for the pymongo package::

      {'$and': [{'a': 100}, {'b': {'$gte': 200}}]}

  Supports many equality and inequality operators - see the docstring for the
  ``transform_query`` function for many more examples.

- ``invRegex.py`` example renamed to ``inv_regex.py`` and updated to PEP-8
  variable and method naming.

- Removed examples ``sparser.py`` and ``pymicko.py``, since each included its
  own GPL license in the header. Since this conflicts with pyparsing's
  MIT license, they were removed from the distribution to avoid
  confusion among those making use of them in their own projects.

- Updated the ``lucene_grammar.py`` example (better support for '*' and '?' wildcards)
  and corrected the test cases!

- Added ``bf.py`` Brainf*ck parser/executor example. Illustrates using
  a pyparsing grammar to parse language syntax, and attach executable AST nodes to
  the parsed results.

- Added ``tag_emitter.py`` to examples. This example demonstrates how to insert
  tags into your parsed results that are not part of the original parsed text.

- Updated example ``select_parser.py`` to use PEP8 names and added Groups for better retrieval
  of parsed values from multiple SELECT clauses.

- Added example ``email_address_parser.py``.

- Added example ``directx_x_file_parser.py`` to parse DirectX template definitions, and
  generate a Pyparsing parser from a template to parse .x files.

- ``delta_time``, ``lua_parser``, ``decaf_parser``, and ``roman_numerals`` examples cleaned up
  to use latest PEP8 names and add minor enhancements.

- Fixed bug (and corresponding test code) in ``delta_time`` example that did not handle
  weekday references in time expressions (like "Monday at 4pm") when the weekday was
  the same as the current weekday.


Acknowledgments
===============
Again, thanks to the many contributors who submitted issues, questions, suggestions,
and PRs.
