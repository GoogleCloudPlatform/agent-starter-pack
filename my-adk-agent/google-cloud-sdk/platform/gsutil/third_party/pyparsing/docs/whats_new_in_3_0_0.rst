=============================
What's New in Pyparsing 3.0.0
=============================

:author: Paul McGuire

:date: May, 2022

:abstract: This document summarizes the changes made
    in the 3.0.0 release of pyparsing.
    (Updated to reflect changes up to 3.0.10)

.. sectnum::    :depth: 4

.. contents::   :depth: 4


New Features
============

PEP-8 naming
------------
This release of pyparsing will (finally!) include PEP-8 compatible names and arguments.
Backward-compatibility is maintained by defining synonyms using the old camelCase names
pointing to the new snake_case names.

This code written using non-PEP8 names::

    wd = pp.Word(pp.printables, excludeChars="$")
    wd_list = pp.delimitedList(wd, delim="$")
    print(wd_list.parseString("dkls$134lkjk$lsd$$").asList())

can now be written as::

    wd = pp.Word(pp.printables, exclude_chars="$")
    wd_list = pp.delimited_list(wd, delim="$")
    print(wd_list.parse_string("dkls$134lkjk$lsd$$").as_list())

Pyparsing 3.0 will run both versions of this example.

New code should be written using the PEP-8 compatible names. The compatibility
synonyms will be removed in a future version of pyparsing.


Railroad diagramming
--------------------
An excellent new enhancement is the new railroad diagram
generator for documenting pyparsing parsers.::

    import pyparsing as pp

    # define a simple grammar for parsing street addresses such
    # as "123 Main Street"
    #     number word...
    number = pp.Word(pp.nums).set_name("number")
    name = pp.Word(pp.alphas).set_name("word")[1, ...]

    parser = number("house_number") + name("street")
    parser.set_name("street address")

    # construct railroad track diagram for this parser and
    # save as HTML
    parser.create_diagram('parser_rr_diag.html')

``create_diagram`` accepts these named arguments:

- ``vertical`` (int) - threshold for formatting multiple alternatives vertically
  instead of horizontally (default=3)
- ``show_results_names`` - bool flag whether diagram should show annotations for
  defined results names
- ``show_groups`` - bool flag whether groups should be highlighted with an unlabeled surrounding box
- ``embed`` - bool flag whether generated HTML should omit ``<HEAD>``, ``<BODY>``, and ``<DOCTYPE>`` tags to embed
  the resulting HTML in an enclosing HTML source (new in 3.0.10)
- ``head`` - str containing additional HTML to insert into the ``<HEAD>`` section of the
  generated code; can be used to insert custom CSS styling
- ``body`` - str containing additional HTML to insert at the beginning of the ``<BODY>`` section of the
  generated code

To use this new feature, install the supporting diagramming packages using::

    pip install pyparsing[diagrams]

See more in the examples directory: ``make_diagram.py`` and ``railroad_diagram_demo.py``.

(Railroad diagram enhancement contributed by Michael Milton)

Support for left-recursive parsers
----------------------------------
Another significant enhancement in 3.0 is support for left-recursive (LR)
parsers. Previously, given a left-recursive parser, pyparsing would
recurse repeatedly until hitting the Python recursion limit. Following
the methods of the Python PEG parser, pyparsing uses a variation of
packrat parsing to detect and handle left-recursion during parsing.::

    import pyparsing as pp
    pp.ParserElement.enable_left_recursion()

    # a common left-recursion definition
    # define a list of items as 'list + item | item'
    # BNF:
    #   item_list := item_list item | item
    #   item := word of alphas
    item_list = pp.Forward()
    item = pp.Word(pp.alphas)
    item_list <<= item_list + item | item

    item_list.run_tests("""\
        To parse or not to parse that is the question
        """)

Prints::

    ['To', 'parse', 'or', 'not', 'to', 'parse', 'that', 'is', 'the', 'question']

See more examples in ``left_recursion.py`` in the pyparsing examples directory.

(LR parsing support contributed by Max Fischer)

Packrat/memoization enable and disable methods
----------------------------------------------
As part of the implementation of left-recursion support, new methods have been added
to enable and disable packrat parsing.

======================  =======================================================
Name                       Description
----------------------  -------------------------------------------------------
enable_packrat          Enable packrat parsing (with specified cache size)
enable_left_recursion   Enable left-recursion cache
disable_memoization     Disable all internal parsing caches
======================  =======================================================

Type annotations on all public methods
--------------------------------------
Python 3.6 and upward compatible type annotations have been added to most of the
public methods in pyparsing. This should facilitate developing pyparsing-based
applications using IDEs for development-time type checking.

New string constants ``identchars`` and ``identbodychars`` to help in defining identifier Word expressions
----------------------------------------------------------------------------------------------------------
Two new module-level strings have been added to help when defining identifiers,
``identchars`` and ``identbodychars``.

Instead of writing::

    import pyparsing as pp
    identifier = pp.Word(pp.alphas + "_", pp.alphanums + "_")

you will be able to write::

    identifier = pp.Word(pp.identchars, pp.identbodychars)

Those constants have also been added to all the Unicode string classes::

    import pyparsing as pp
    ppu = pp.pyparsing_unicode

    cjk_identifier = pp.Word(ppu.CJK.identchars, ppu.CJK.identbodychars)
    greek_identifier = pp.Word(ppu.Greek.identchars, ppu.Greek.identbodychars)


Refactored/added diagnostic flags
---------------------------------
Expanded ``__diag__`` and ``__compat__`` to actual classes instead of
just namespaces, to add some helpful behavior:

- ``pyparsing.enable_diag()`` and ``pyparsing.disable_diag()`` methods to give extra
  help when setting or clearing flags (detects invalid
  flag names, detects when trying to set a ``__compat__`` flag
  that is no longer settable). Use these methods now to
  set or clear flags, instead of directly setting to ``True`` or
  ``False``::

        import pyparsing as pp
        pp.enable_diag(pp.Diagnostics.warn_multiple_tokens_in_named_alternation)

- ``pyparsing.enable_all_warnings()`` is another helper that sets
  all "warn*" diagnostics to ``True``::

        pp.enable_all_warnings()

- added support for calling ``enable_all_warnings()`` if warnings are enabled
  using the Python ``-W`` switch, or setting a non-empty value to the environment
  variable ``PYPARSINGENABLEALLWARNINGS``. (If using ``-Wd`` for testing, but
  wishing to disable pyparsing warnings, add ``-Wi:::pyparsing``.)

- added new warning, ``warn_on_match_first_with_lshift_operator`` to
  warn when using ``'<<'`` with a ``'|'`` ``MatchFirst`` operator,
  which will
  create an unintended expression due to precedence of operations.

  Example: This statement will erroneously define the ``fwd`` expression
  as just ``expr_a``, even though ``expr_a | expr_b`` was intended,
  since ``'<<'`` operator has precedence over ``'|'``::

      fwd << expr_a | expr_b

  To correct this, use the ``'<<='`` operator (preferred) or parentheses
  to override operator precedence::

        fwd <<= expr_a | expr_b

  or::

        fwd << (expr_a | expr_b)

- ``warn_on_parse_using_empty_Forward`` - warns that a ``Forward``
  has been included in a grammar, but no expression was
  attached to it using ``'<<='`` or ``'<<'``

- ``warn_on_assignment_to_Forward`` - warns that a ``Forward`` has
  been created, but was probably later overwritten by
  erroneously using ``'='`` instead of ``'<<='`` (this is a common
  mistake when using Forwards)
  (**currently not working on PyPy**)

Support for yielding native Python ``list`` and ``dict`` types in place of ``ParseResults``
-------------------------------------------------------------------------------------------
To support parsers that are intended to generate native Python collection
types such as lists and dicts, the ``Group`` and ``Dict`` classes now accept an
additional boolean keyword argument ``aslist`` and ``asdict`` respectively. See
the ``jsonParser.py`` example in the ``pyparsing/examples`` source directory for
how to return types as ``ParseResults`` and as Python collection types, and the
distinctions in working with the different types.

In addition parse actions that must return a value of list type (which would
normally be converted internally to a ``ParseResults``) can override this default
behavior by returning their list wrapped in the new ``ParseResults.List`` class::

      # this parse action tries to return a list, but pyparsing
      # will convert to a ParseResults
      def return_as_list_but_still_get_parse_results(tokens):
          return tokens.asList()

      # this parse action returns the tokens as a list, and pyparsing will
      # maintain its list type in the final parsing results
      def return_as_list(tokens):
          return ParseResults.List(tokens.asList())

This is the mechanism used internally by the ``Group`` class when defined
using ``aslist=True``.

New Located class to replace ``locatedExpr`` helper method
----------------------------------------------------------
The new ``Located`` class will replace the current ``locatedExpr`` method for
marking parsed results with the start and end locations of the parsed data in
the input string.  ``locatedExpr`` had several bugs, and returned its results
in a hard-to-use format (location data and results names were mixed in with
the located expression's parsed results, and wrapped in an unnecessary extra
nesting level).

For this code::

        wd = Word(alphas)
        for match in locatedExpr(wd).search_string("ljsdf123lksdjjf123lkkjj1222"):
            print(match)

the docs for ``locatedExpr`` show this output::

        [[0, 'ljsdf', 5]]
        [[8, 'lksdjjf', 15]]
        [[18, 'lkkjj', 23]]

The parsed values and the start and end locations are merged into a single
nested ``ParseResults`` (and any results names in the parsed values are also
merged in with the start and end location names).

Using ``Located``, the output is::

        [0, ['ljsdf'], 5]
        [8, ['lksdjjf'], 15]
        [18, ['lkkjj'], 23]

With ``Located``, the parsed expression values and results names are kept
separate in the second parsed value, and there is no extra grouping level
on the whole result.

The existing ``locatedExpr`` is retained for backward-compatibility, but will be
deprecated in a future release.

New ``AtLineStart`` and ``AtStringStart`` classes
-------------------------------------------------
As part of fixing some matching behavior in ``LineStart`` and ``StringStart``, two new
classes have been added: ``AtLineStart`` and ``AtStringStart``.

``LineStart`` and ``StringStart`` can be treated as separate elements, including whitespace skipping.
``AtLineStart`` and ``AtStringStart`` enforce that an expression starts exactly at column 1, with no
leading whitespace.::

    (LineStart() + Word(alphas)).parseString("ABC")    # passes
    (LineStart() + Word(alphas)).parseString("  ABC")  # passes
    AtLineStart(Word(alphas)).parseString("  ABC")     # fails

[This is a fix to behavior that was added in 3.0.0, but was actually a regression from 2.4.x.]

New ``IndentedBlock`` class to replace ``indentedBlock`` helper method
----------------------------------------------------------------------
The new ``IndentedBlock`` class will replace the current ``indentedBlock`` method
for defining indented blocks of text, similar to Python source code. Using
``IndentedBlock``, the expression instance itself keeps track of the indent stack,
so a separate external ``indentStack`` variable is no longer required.

Here is a simple example of an expression containing an alphabetic key, followed
by an indented list of integers::

    integer = pp.Word(pp.nums)
    group = pp.Group(pp.Char(pp.alphas) + pp.IndentedBlock(integer))

parses::

    A
        100
        101
    B
        200
        201

as::

    [['A', [100, 101]], ['B', [200, 201]]]

By default, the results returned from the ``IndentedBlock`` are grouped.

``IndentedBlock`` may also be used to define a recursive indented block (containing nested
indented blocks).

The existing ``indentedBlock`` is retained for backward-compatibility, but will be
deprecated in a future release.

Shortened tracebacks
--------------------
Cleaned up default tracebacks when getting a ``ParseException`` when calling
``parse_string``. Exception traces should now stop at the call in ``parse_string``,
and not include the internal pyparsing traceback frames. (If the full traceback
is desired, then set ``ParserElement.verbose_traceback`` to ``True``.)

Improved debug logging
----------------------
Debug logging has been improved by:

- Including ``try/match/fail`` logging when getting results from the
  packrat cache (previously cache hits did not show debug logging).
  Values returned from the packrat cache are marked with an '*'.

- Improved fail logging, showing the failed expression, text line, and marker where
  the failure occurred.

- Adding ``with_line_numbers`` to ``pyparsing_testing``. Use ``with_line_numbers``
  to visualize the data being parsed, with line and column numbers corresponding
  to the values output when enabling ``set_debug()`` on an expression::

      data = """\
         A
            100"""
      expr = pp.Word(pp.alphanums).set_name("word").set_debug()
      print(ppt.with_line_numbers(data))
      expr[...].parseString(data)

  prints::

      .          1
        1234567890
      1:   A
      2:      100
      Match word at loc 3(1,4)
          A
          ^
      Matched word -> ['A']
      Match word at loc 11(2,7)
             100
             ^
      Matched word -> ['100']

New / improved examples
-----------------------
- ``number_words.py`` includes a parser/evaluator to parse ``"forty-two"``
  and return ``42``. Also includes example code to generate a railroad
  diagram for this parser.

- ``BigQueryViewParser.py`` added to examples directory, submitted
  by Michael Smedberg.

- ``booleansearchparser.py`` added to examples directory, submitted
  by xecgr. Builds on searchparser.py, adding support for '*'
  wildcards and non-Western alphabets.

- Improvements in ``select_parser.py``, to include new SQL syntax
  from SQLite, submitted by Robert Coup.

- Off-by-one bug found in the ``roman_numerals.py`` example, a bug
  that has been there for about 14 years! Submitted by
  Jay Pedersen.

- A simplified Lua parser has been added to the examples
  (``lua_parser.py``).

- Demonstration of defining a custom Unicode set for cuneiform
  symbols, as well as simple Cuneiform->Python conversion is included
  in ``cuneiform_python.py``.

- Fixed bug in ``delta_time.py`` example, when using a quantity
  of seconds/minutes/hours/days > 999.

Other new features
------------------
- ``url`` expression added to ``pyparsing_common``, with named fields for
  common fields in URLs. See the updated ``urlExtractorNew.py`` file in the
  ``examples`` directory. Submitted by Wolfgang Fahl.

- ``DelimitedList`` now supports an additional flag ``allow_trailing_delim``,
  to optionally parse an additional delimiter at the end of the list.
  Submitted by Kazantcev Andrey.

- Added global method ``autoname_elements()`` to call ``set_name()`` on all locally
  defined ``ParserElements`` that haven't been explicitly named using ``set_name()``, using
  their local variable name. Useful for setting names on multiple elements when
  creating a railroad diagram::

            a = pp.Literal("a")
            b = pp.Literal("b").set_name("bbb")
            pp.autoname_elements()

  ``a`` will get named "a", while ``b`` will keep its name "bbb".

- Enhanced default strings created for ``Word`` expressions, now showing
  string ranges if possible. ``Word(alphas)`` would formerly
  print as ``W:(ABCD...)``, now prints as ``W:(A-Za-z)``.

- Better exception messages to show full word where an exception occurred.::

      Word(alphas)[...].parse_string("abc 123", parse_all=True)

  Was::

      pyparsing.ParseException: Expected end of text, found '1'  (at char 4), (line:1, col:5)

  Now::

      pyparsing.exceptions.ParseException: Expected end of text, found '123'  (at char 4), (line:1, col:5)

- Using ``...`` for ``SkipTo`` can now be wrapped in ``Suppress`` to suppress
  the skipped text from the returned parse results.::

     source = "lead in START relevant text END trailing text"
     start_marker = Keyword("START")
     end_marker = Keyword("END")
     find_body = Suppress(...) + start_marker + ... + end_marker
     print(find_body.parse_string(source).dump())

  Prints::

      ['START', 'relevant text ', 'END']
      - _skipped: ['relevant text ']

- Added ``ignore_whitespace(recurse:bool = True)`` and added a
  ``recurse`` argument to ``leave_whitespace``, both added to provide finer
  control over pyparsing's whitespace skipping. Contributed by
  Michael Milton.

- Added ``ParserElement.recurse()`` method to make it simpler for
  grammar utilities to navigate through the tree of expressions in
  a pyparsing grammar.

- The ``repr()`` string for ``ParseResults`` is now of the form::

    ParseResults([tokens], {named_results})

  The previous form omitted the leading ``ParseResults`` class name,
  and was easily misinterpreted as a ``tuple`` containing a ``list`` and
  a ``dict``.

- Minor reformatting of output from ``run_tests`` to make embedded
  comments more visible.

- New ``pyparsing_test`` namespace, assert methods and classes added to support writing
  unit tests.

  - ``assertParseResultsEquals``
  - ``assertParseAndCheckList``
  - ``assertParseAndCheckDict``
  - ``assertRunTestResults``
  - ``assertRaisesParseException``
  - ``reset_pyparsing_context`` context manager, to restore pyparsing
    config settings

- Enhanced error messages and error locations when parsing fails on
  the ``Keyword`` or ``CaselessKeyword`` classes due to the presence of a
  preceding or trailing keyword character.

- Enhanced the ``Regex`` class to be compatible with re's compiled with the
  re-equivalent ``regex`` module. Individual expressions can be built with
  regex compiled expressions using::

    import pyparsing as pp
    import regex

    # would use regex for this expression
    integer_parser = pp.Regex(regex.compile(r'\d+'))

- Fixed handling of ``ParseSyntaxExceptions`` raised as part of ``Each``
  expressions, when sub-expressions contain ``'-'`` backtrack
  suppression.

- Potential performance enhancement when parsing ``Word``
  expressions built from ``pyparsing_unicode`` character sets. ``Word`` now
  internally converts ranges of consecutive characters to regex
  character ranges (converting ``"0123456789"`` to ``"0-9"`` for instance).

- Added a caseless parameter to the ``CloseMatch`` class to allow for casing to be
  ignored when checking for close matches. Contributed by Adrian Edwards.


API Changes
===========

- [Note added in pyparsing 3.0.7, reflecting a change in 3.0.0]
  Fixed a bug in the ``ParseResults`` class implementation of ``__bool__``, which
  would formerly return ``False`` if the ``ParseResults`` item list was empty, even if it
  contained named results. Now ``ParseResults`` will return ``True`` if either the item
  list is not empty *or* if the named results list is not empty::

      # generate an empty ParseResults by parsing a blank string with a ZeroOrMore
      result = Word(alphas)[...].parse_string("")
      print(result.as_list())
      print(result.as_dict())
      print(bool(result))

      # add a results name to the result
      result["name"] = "empty result"
      print(result.as_list())
      print(result.as_dict())
      print(bool(result))

  Prints::

      []
      {}
      False

      []
      {'name': 'empty result'}
      True

  In previous versions, the second call to ``bool()`` would return ``False``.

- [Note added in pyparsing 3.0.4, reflecting a change in 3.0.0]
  The ``ParseResults`` class now uses ``__slots__`` to pre-define instance attributes. This
  means that code written like this (which was allowed in pyparsing 2.4.7)::

    result = Word(alphas).parseString("abc")
    result.xyz = 100

  now raises this Python exception::

    AttributeError: 'ParseResults' object has no attribute 'xyz'

  To add new attribute values to ParseResults object in 3.0.0 and later, you must
  assign them using indexed notation::

    result["xyz"] = 100

  You will still be able to access this new value as an attribute or as an
  indexed item.

- ``enable_diag()`` and ``disable_diag()`` methods to
  enable specific diagnostic values (instead of setting them
  to ``True`` or ``False``). ``enable_all_warnings()`` has
  also been added.

- ``counted_array`` formerly returned its list of items nested
  within another list, so that accessing the items required
  indexing the 0'th element to get the actual list. This
  extra nesting has been removed. In addition, if there are
  other metadata fields parsed between the count and the
  list items, they can be preserved in the resulting list
  if given results names.

- ``ParseException.explain()`` is now an instance method of
  ``ParseException``::

        expr = pp.Word(pp.nums) * 3
        try:
            expr.parse_string("123 456 A789")
        except pp.ParseException as pe:
            print(pe.explain(depth=0))

  prints::

        123 456 A789
                ^
        ParseException: Expected W:(0-9), found 'A789'  (at char 8), (line:1, col:9)

  To run explain against other exceptions, use
  ``ParseException.explain_exception()``.

- Debug actions now take an added keyword argument ``cache_hit``.
  Now that debug actions are called for expressions matched in the
  packrat parsing cache, debug actions are now called with this extra
  flag, set to ``True``. For custom debug actions, it is necessary to add
  support for this new argument.

- ``ZeroOrMore`` expressions that have results names will now
  include empty lists for their name if no matches are found.
  Previously, no named result would be present. Code that tested
  for the presence of any expressions using ``"if name in results:"``
  will now always return ``True``. This code will need to change to
  ``"if name in results and results[name]:"`` or just
  ``"if results[name]:"``. Also, any parser unit tests that check the
  ``as_dict()`` contents will now see additional entries for parsers
  having named ``ZeroOrMore`` expressions, whose values will be ``[]``.

- ``ParserElement.set_default_whitespace_chars`` will now update
  whitespace characters on all built-in expressions defined
  in the pyparsing module.

- ``camelCase`` names have been converted to PEP-8 ``snake_case`` names.

  Method names and arguments that were camel case (such as ``parseString``)
  have been replaced with PEP-8 snake case versions (``parse_string``).

  Backward-compatibility synonyms for all names and arguments have
  been included, to allow parsers written using the old names to run
  without change. The synonyms will be removed in a future release.
  New parser code should be written using the new PEP-8 snake case names.

==============================  ================================
Name                            Previous name
------------------------------  --------------------------------
ParserElement
- parse_string                  parseString
- scan_string                   scanString
- search_string                 searchString
- transform_string              transformString
- add_condition                 addCondition
- add_parse_action              addParseAction
- can_parse_next                canParseNext
- default_name                  defaultName
- enable_left_recursion         enableLeftRecursion
- enable_packrat                enablePackrat
- ignore_whitespace             ignoreWhitespace
- inline_literals_using         inlineLiteralsUsing
- parse_file                    parseFile
- leave_whitespace              leaveWhitespace
- parse_string                  parseString
- parse_with_tabs               parseWithTabs
- reset_cache                   resetCache
- run_tests                     runTests
- scan_string                   scanString
- search_string                 searchString
- set_break                     setBreak
- set_debug                     setDebug
- set_debug_actions             setDebugActions
- set_default_whitespace_chars  setDefaultWhitespaceChars
- set_fail_action               setFailAction
- set_name                      setName
- set_parse_action              setParseAction
- set_results_name              setResultsName
- set_whitespace_chars          setWhitespaceChars
- transform_string              transformString
- try_parse                     tryParse

ParseResults
- as_list                       asList
- as_dict                       asDict
- get_name                      getName

ParseBaseException
- parser_element                parserElement

any_open_tag                    anyOpenTag
any_close_tag                   anyCloseTag
c_style_comment                 cStyleComment
common_html_entity              commonHTMLEntity
condition_as_parse_action       conditionAsParseAction
counted_array                   countedArray
cpp_style_comment               cppStyleComment
dbl_quoted_string               dblQuotedString
dbl_slash_comment               dblSlashComment
DelimitedList                   delimitedList
DelimitedList                   delimited_list
dict_of                         dictOf
html_comment                    htmlComment
infix_notation                  infixNotation
java_style_comment              javaStyleComment
line_end                        lineEnd
line_start                      lineStart
make_html_tags                  makeHTMLTags
make_xml_tags                   makeXMLTags
match_only_at_col               matchOnlyAtCol
match_previous_expr             matchPreviousExpr
match_previous_literal          matchPreviousLiteral
nested_expr                     nestedExpr
null_debug_action               nullDebugAction
one_of                          oneOf
OpAssoc                         opAssoc
original_text_for               originalTextFor
python_style_comment            pythonStyleComment
quoted_string                   quotedString
remove_quotes                   removeQuotes
replace_html_entity             replaceHTMLEntity
replace_with                    replaceWith
rest_of_line                    restOfLine
sgl_quoted_string               sglQuotedString
string_end                      stringEnd
string_start                    stringStart
token_map                       tokenMap
trace_parse_action              traceParseAction
unicode_string                  unicodeString
with_attribute                  withAttribute
with_class                      withClass
==============================  ================================

Discontinued Features
=====================

Python 2.x no longer supported
------------------------------
Removed Py2.x support and other deprecated features. Pyparsing
now requires Python 3.6.8 or later. If you are using an earlier
version of Python, you must use a Pyparsing 2.4.x version.

Other discontinued features
---------------------------
- ``ParseResults.asXML()`` - if used for debugging, switch
  to using ``ParseResults.dump()``; if used for data transfer,
  use ``ParseResults.as_dict()`` to convert to a nested Python
  dict, which can then be converted to XML or JSON or
  other transfer format

- ``operatorPrecedence`` synonym for ``infixNotation`` -
  convert to calling ``infix_notation``

- ``commaSeparatedList`` - convert to using
  ``pyparsing_common.comma_separated_list``

- ``upcaseTokens`` and ``downcaseTokens`` - convert to using
  ``pyparsing_common.upcase_tokens`` and ``downcase_tokens``

- ``__compat__.collect_all_And_tokens`` will not be settable to
  ``False`` to revert to pre-2.3.1 results name behavior -
  review use of names for ``MatchFirst`` and Or expressions
  containing ``And`` expressions, as they will return the
  complete list of parsed tokens, not just the first one.
  Use ``pyparsing.enable_diag(pyparsing.Diagnostics.warn_multiple_tokens_in_named_alternation)``
  to help identify those expressions in your parsers that
  will have changed as a result.

- Removed support for running ``python setup.py test``. The setuptools
  maintainers consider the ``test`` command deprecated (see
  <https://github.com/pypa/setuptools/issues/1684>). To run the Pyparsing tests,
  use the command ``tox``.


Fixed Bugs
==========

- [Reverted in 3.0.2]Fixed issue when ``LineStart()`` expressions would match input text that was not
  necessarily at the beginning of a line.

  [The previous behavior was the correct behavior, since it represents the ``LineStart`` as its own
  matching expression. ``ParserElements`` that must start in column 1 can be wrapped in the new
  ``AtLineStart`` class.]

- Fixed bug in regex definitions for ``real`` and ``sci_real`` expressions in
  ``pyparsing_common``.

- Fixed ``FutureWarning`` raised beginning in Python 3.7 for ``Regex`` expressions
  containing '[' within a regex set.

- Fixed bug in ``PrecededBy`` which caused infinite recursion.

- Fixed bug in ``CloseMatch`` where end location was incorrectly
  computed; and updated ``partial_gene_match.py`` example.

- Fixed bug in ``indentedBlock`` with a parser using two different
  types of nested indented blocks with different indent values,
  but sharing the same indent stack.

- Fixed bug in ``Each`` when using ``Regex``, when ``Regex`` expression would
  get parsed twice.

- Fixed bugs in ``Each`` when passed ``OneOrMore`` or ``ZeroOrMore`` expressions:
  . first expression match could be enclosed in an extra nesting level
  . out-of-order expressions now handled correctly if mixed with required expressions
  . results names are maintained correctly for these expression

- Fixed ``FutureWarning`` that sometimes is raised when ``'['`` passed as a
  character to ``Word``.

- Fixed debug logging to show failure location after whitespace skipping.

- Fixed ``ParseFatalExceptions`` failing to override normal exceptions or expression
  matches in ``MatchFirst`` expressions.

- Fixed bug in which ``ParseResults`` replaces a collection type value with an invalid
  type annotation (as a result of changed behavior in Python 3.9).

- Fixed bug in ``ParseResults`` when calling ``__getattr__`` for special double-underscored
  methods. Now raises ``AttributeError`` for non-existent results when accessing a
  name starting with '__'.

- Fixed bug in ``Located`` class when used with a results name.

- Fixed bug in ``QuotedString`` class when the escaped quote string is not a
  repeated character.

Acknowledgments
===============
And finally, many thanks to those who helped in the restructuring
of the pyparsing code base as part of this release. Pyparsing now
has more standard package structure, more standard unit tests,
and more standard code formatting (using black). Special thanks
to jdufresne, klahnakoski, mattcarmody, ckeygusuz,
tmiguelt, and toonarmycaptain to name just a few.

Thanks also to Michael Milton and Max Fischer, who added some
significant new features to pyparsing.