==========================
Using the pyparsing module
==========================

:author: Paul McGuire
:address: ptmcg.pm+pyparsing@gmail.com

:revision: 3.2.0
:date: October, 2024

:copyright: Copyright |copy| 2003-2024 Paul McGuire.

.. |copy| unicode:: 0xA9

:abstract: This document provides how-to instructions for the
    pyparsing library, an easy-to-use Python module for constructing
    and executing basic text parsers.  The pyparsing module is useful
    for evaluating user-definable
    expressions, processing custom application language commands, or
    extracting data from formatted reports.

.. sectnum::    :depth: 4

.. contents::   :depth: 4

Note: While this content is still valid, there are more detailed
descriptions and extensive examples at the `online doc server
<https://pyparsing-docs.readthedocs.io/en/latest/pyparsing.html>`_, and
in the online help for the various pyparsing classes and methods (viewable
using the Python interpreter's built-in ``help()`` function). You will also
find many example scripts in the `examples <https://github.com/pyparsing/pyparsing/tree/master/examples>`_
directory of the pyparsing GitHub repo.

-----------

**Note**: *In pyparsing 3.0, many method and function names which were
originally written using camelCase have been converted to PEP8-compatible
snake_case. So ``parseString()`` is being renamed to ``parse_string()``,
``delimitedList`` to DelimitedList_, and so on. You may see the old
names in legacy parsers, and they will be supported for a time with
synonyms, but the synonyms will be removed in a future release.*

*If you are using this documentation, but working with a 2.4.x version of pyparsing,
you'll need to convert methods and arguments from the documented snake_case
names to the legacy camelCase names. In pyparsing 3.x, both forms are
supported, but the legacy forms are deprecated; they will be dropped in a
future 4.0 release.*

-----------


Steps to follow
===============

To parse an incoming data string, the client code must follow these steps:

1. First define the tokens and patterns to be matched, and assign
   this to a program variable.  Optional results names or parse
   actions can also be defined at this time.

2. Call ``parse_string()``, ``scan_string()``, or ``search_string()``
   on this variable, passing in the string to
   be parsed.  During the matching process, whitespace between
   tokens is skipped by default (although this can be changed).
   When token matches occur, any defined parse action methods are
   called.

3. Process the parsed results, returned as a ParseResults_ object.
   The ParseResults_ object can be accessed as if it were a list of
   strings. Matching results may also be accessed as named attributes of
   the returned results, if names are defined in the definition of
   the token pattern, using ``set_results_name()``.


Hello, World!
-------------

The following complete Python program will parse the greeting ``"Hello, World!"``,
or any other greeting of the form "<salutation>, <addressee>!"::

    import pyparsing as pp

    greet = pp.Word(pp.alphas) + "," + pp.Word(pp.alphas) + "!"
    for greeting_str in [
                "Hello, World!",
                "Bonjour, Monde!",
                "Hola, Mundo!",
                "Hallo, Welt!",
            ]:
        greeting = greet.parse_string(greeting_str)
        print(greeting)

The parsed tokens are returned in the following form::

    ['Hello', ',', 'World', '!']
    ['Bonjour', ',', 'Monde', '!']
    ['Hola', ',', 'Mundo', '!']
    ['Hallo', ',', 'Welt', '!']


Usage notes
-----------

- The pyparsing module can be used to interpret simple command
  strings or algebraic expressions, or can be used to extract data
  from text reports with complicated format and structure ("screen
  or report scraping").  However, it is possible that your defined
  matching patterns may accept invalid inputs.  Use pyparsing to
  extract data from strings assumed to be well-formatted.

- To keep up the readability of your code, use operators_  such as ``+``, ``|``,
  ``^``, and ``~`` to combine expressions.  You can also combine
  string literals with ``ParseExpressions`` - they will be
  automatically converted to Literal_ objects.  For example::

    integer  = Word(nums)            # simple unsigned integer
    variable = Char(alphas)          # single letter variable, such as x, z, m, etc.
    arith_op = one_of("+ - * /")      # arithmetic operators
    equation = variable + "=" + integer + arith_op + integer    # will match "x=2+2", etc.

  In the definition of ``equation``, the string ``"="`` will get added as
  a ``Literal("=")``, but in a more readable way.

- The pyparsing module's default behavior is to ignore whitespace.  This is the
  case for 99% of all parsers ever written.  This allows you to write simple, clean,
  grammars, such as the above ``equation``, without having to clutter it up with
  extraneous ``ws`` markers.  The ``equation`` grammar will successfully parse all of the
  following statements::

    x=2+2
    x = 2+2
    a = 10   *   4
    r= 1234/ 100000

  Of course, it is quite simple to extend this example to support more elaborate expressions, with
  nesting with parentheses, floating point numbers, scientific notation, and named constants
  (such as ``e`` or ``pi``).  See `fourFn.py <https://github.com/pyparsing/pyparsing/blob/master/examples/fourFn.py>`_,
  and `simpleArith.py <https://github.com/pyparsing/pyparsing/blob/master/examples/simpleArith.py>`_
  included in the examples directory.

- To modify pyparsing's default whitespace skipping, you can use one or
  more of the following methods:

  - use the static method ``ParserElement.set_default_whitespace_chars``
    to override the normal set of whitespace chars (``' \t\n'``).  For instance
    when defining a grammar in which newlines are significant, you should
    call ``ParserElement.set_default_whitespace_chars(' \t')`` to remove
    newline from the set of skippable whitespace characters.  Calling
    this method will affect all pyparsing expressions defined afterward.

  - call ``leave_whitespace()`` on individual expressions, to suppress the
    skipping of whitespace before trying to match the expression

  - use ``Combine`` to require that successive expressions must be
    adjacent in the input string.  For instance, this expression::

      real = Word(nums) + '.' + Word(nums)

    will match "3.14159", but will also match "3 . 12".  It will also
    return the matched results as ['3', '.', '14159'].  By changing this
    expression to::

      real = Combine(Word(nums) + '.' + Word(nums))

    it will not match numbers with embedded spaces, and it will return a
    single concatenated string '3.14159' as the parsed token.

- Repetition of expressions can be indicated using ``*`` or ``[]`` notation.  An
  expression may be multiplied by an integer value (to indicate an exact
  repetition count), or indexed with a tuple, representing min and max repetitions
  (with ``...`` representing no min or no max, depending whether it is the first or
  second tuple element).  See the following examples, where n is used to
  indicate an integer value:

  - ``expr*3`` is equivalent to ``expr + expr + expr``

  - ``expr[2, 3]`` is equivalent to ``expr + expr + Opt(expr)``

  - ``expr[n, ...]`` or ``expr[n,]`` is equivalent
    to ``expr*n + ZeroOrMore(expr)`` (read as "at least n instances of expr")

  - ``expr[... ,n]`` is equivalent to ``expr*(0, n)``
    (read as "0 to n instances of expr")

  - ``expr[...]``, ``expr[0, ...]`` and ``expr * ...`` are equivalent to ``ZeroOrMore(expr)``

  - ``expr[1, ...]`` is equivalent to ``OneOrMore(expr)``

  Note that ``expr[..., n]`` does not raise an exception if
  more than n exprs exist in the input stream; that is,
  ``expr[..., n]`` does not enforce a maximum number of expr
  occurrences.  If this behavior is desired, then write
  ``expr[..., n] + ~expr``.

- ``[]`` notation will also accept a stop expression using ':' slice
  notation:

  - ``expr[...:end_expr]`` is equivalent to ``ZeroOrMore(expr, stop_on=end_expr)``

- MatchFirst_ expressions are matched left-to-right, and the first
  match found will skip all later expressions within, so be sure
  to define less-specific patterns after more-specific patterns.
  If you are not sure which expressions are most specific, use Or_
  expressions (defined using the ``^`` operator) - they will always
  match the longest expression, although they are more
  compute-intensive.

- Or_ expressions will evaluate all of the specified subexpressions
  to determine which is the "best" match, that is, which matches
  the longest string in the input data.  In case of a tie, the
  left-most expression in the Or_ list will win.

- If parsing the contents of an entire file, pass it to the
  ``parse_file`` method using::

    expr.parse_file(source_file)

- ``ParseExceptions`` will report the location where an expected token
  or expression failed to match.  For example, if we tried to use our
  "Hello, World!" parser to parse "Hello World!" (leaving out the separating
  comma), we would get an exception, with the message::

    pyparsing.ParseException: Expected "," (6), (1,7)

  In the case of complex
  expressions, the reported location may not be exactly where you
  would expect.  See more information under ParseException_ .

- Use the ``Group`` class to enclose logical groups of tokens within a
  sublist.  This will help organize your results into more
  hierarchical form (the default behavior is to return matching
  tokens as a flat list of matching input strings).

- Punctuation may be significant for matching, but is rarely of
  much interest in the parsed results.  Use the ``suppress()`` method
  to keep these tokens from cluttering up your returned lists of
  tokens.  For example, DelimitedList_ matches a succession of
  one or more expressions, separated by delimiters (commas by
  default), but only returns a list of the actual expressions -
  the delimiters are used for parsing, but are suppressed from the
  returned output.

- Parse actions can be used to convert values from strings to
  other data types (ints, floats, booleans, etc.).

- Results names are recommended for retrieving tokens from complex
  expressions.  It is much easier to access a token using its field
  name than using a positional index, especially if the expression
  contains optional elements.  You can also shortcut
  the ``set_results_name`` call::

    stats = ("AVE:" + real_num.set_results_name("average")
             + "MIN:" + real_num.set_results_name("min")
             + "MAX:" + real_num.set_results_name("max"))

  can more simply and cleanly be written as this::

    stats = ("AVE:" + real_num("average")
             + "MIN:" + real_num("min")
             + "MAX:" + real_num("max"))

- Be careful when defining parse actions that modify global variables or
  data structures (as in fourFn.py_), especially for low level tokens
  or expressions that may occur within an And_ expression; an early element
  of an And_ may match, but the overall expression may fail.


Classes
=======

All the pyparsing classes can be found in this
`UML class diagram <_static/pyparsingClassDiagram_3.0.9.jpg>`_.

Classes in the pyparsing module
-------------------------------

``ParserElement`` - abstract base class for all pyparsing classes;
methods for code to use are:

- ``parse_string(source_string, parse_all=False)`` - only called once, on the overall
  matching pattern; returns a ParseResults_ object that makes the
  matched tokens available as a list, and optionally as a dictionary,
  or as an object with named attributes; if ``parse_all`` is set to True, then
  ``parse_string`` will raise a ParseException_ if the grammar does not process
  the complete input string.

- ``parse_file(source_file)`` - a convenience function, that accepts an
  input file object or filename.  The file contents are passed as a
  string to ``parse_string()``.  ``parse_file`` also supports the ``parse_all`` argument.

- ``scan_string(source_string)`` - generator function, used to find and
  extract matching text in the given source string; for each matched text,
  returns a tuple of:

  - matched tokens (packaged as a ParseResults_ object)

  - start location of the matched text in the given source string

  - end location in the given source string

  ``scan_string`` allows you to scan through the input source string for
  random matches, instead of exhaustively defining the grammar for the entire
  source text (as would be required with ``parse_string``).

- ``transform_string(source_string)`` - convenience wrapper function for
  ``scan_string``, to process the input source string, and replace matching
  text with the tokens returned from parse actions defined in the grammar
  (see set_parse_action_).

- ``search_string(source_string)`` - another convenience wrapper function for
  ``scan_string``, returns a list of the matching tokens returned from each
  call to ``scan_string``.

- ``set_name(name)`` - associate a short descriptive name for this
  element, useful in displaying exceptions and trace information

- ``run_tests(tests_string)`` - useful development and testing method on
  expressions, to pass a multiline string of sample strings to test against
  the expression. Comment lines (beginning with ``#``) can be inserted
  and they will be included in the test output::

    digits = Word(nums).set_name("numeric digits")
    real_num = Combine(digits + '.' + digits)
    real_num.run_tests("""\
        # valid number
        3.14159

        # no integer part
        .00001

        # no decimal
        101

        # no decimal value
        101.
        """)

  will print::

    # valid number
    3.14159
    ['3.14159']

    # no integer part
    .00001
    ^
    FAIL: Expected numeric digits, found '.'  (at char 0), (line:1, col:1)

    # no decimal
    101
       ^
    FAIL: Expected ".", found end of text  (at char 3), (line:1, col:4)

    # no decimal value
    101.
        ^
    FAIL: Expected numeric digits, found end of text  (at char 4), (line:1, col:5)

.. _set_results_name:

- ``set_results_name(string, list_all_matches=False)`` - name to be given
  to tokens matching
  the element; if multiple tokens within
  a repetition group (such as ZeroOrMore_ or DelimitedList_) the
  default is to return only the last matching token - if ``list_all_matches``
  is set to True, then a list of all the matching tokens is returned.

  ``expr.set_results_name("key")`` can also be written ``expr("key")``
  (a results name with a trailing '*' character will be
  interpreted as setting ``list_all_matches`` to ``True``).

  Note:
  ``set_results_name`` returns a *copy* of the element so that a single
  basic element can be referenced multiple times and given
  different names within a complex grammar.

.. _using_each:

- ``using_each(list_of_symbols)`` a short-cut for defining a number of
  symbols of a particular ``ParserElement`` subclass::

     LBRACK, RBRACK, LBRACE, RBRACE, LPAR, RPAR = Suppress.using_each("[]{}()")
     AND, OR, NOT = Keyword.using_each("and or not".split())

.. _set_parse_action:

- ``set_parse_action(*fn)`` - specify one or more functions to call after successful
  matching of the element; each function is defined as ``fn(s, loc, toks)``, where:

  - ``s`` is the original parse string

  - ``loc`` is the location in the string where matching started

  - ``toks`` is the list of the matched tokens, packaged as a ParseResults_ object

  Parse actions can have any of the following signatures::

    fn(s: str, loc: int, tokens: ParseResults)
    fn(loc: int, tokens: ParseResults)
    fn(tokens: ParseResults)
    fn()

  Multiple functions can be attached to a ``ParserElement`` by specifying multiple
  arguments to ``set_parse_action``, or by calling ``add_parse_action``. Calls to ``set_parse_action``
  will replace any previously defined parse actions. ``set_parse_action(None)`` will clear
  all previously defined parse actions.

  Each parse action function can return a modified ``toks`` list, to perform conversion, or
  string modifications.  For brevity, ``fn`` may also be a
  lambda - here is an example of using a parse action to convert matched
  integer tokens from strings to integers::

    int_number = Word(nums).set_parse_action(lambda s, l, t: [int(t[0])])

  If ``fn`` modifies the ``toks`` list in-place, it does not need to return
  and pyparsing will use the modified ``toks`` list.
  
  If ``set_parse_action`` is called with an argument of ``None``, then this clears all parse actions
  attached to that expression.
  
  A nice short-cut for calling ``set_parse_action`` is to use it as a decorator::
  
    identifier = Word(alphas, alphanums + "_")
    
    @identifier.set_parse_action
    def resolve_identifier(results: ParseResults):
        return variable_values.get(results[0])
  
  (Posted by @MisterMiyagi in this SO answer: https://stackoverflow.com/a/63031959/165216)

- ``add_parse_action`` - similar to ``set_parse_action``, but instead of replacing any
  previously defined parse actions, will append the given action or actions to the
  existing defined parse actions.

- ``add_condition`` - a simplified form of ``add_parse_action`` if the purpose
  of the parse action is to simply do some validation, and raise an exception
  if the validation fails. Takes a method that takes the same arguments,
  but simply returns ``True`` or ``False``. If ``False`` is returned, an exception will be
  raised.

- ``set_break(break_flag=True)`` - if ``break_flag`` is ``True``, calls ``pdb.set_break()``
  as this expression is about to be parsed

- ``copy()`` - returns a copy of a ``ParserElement``; can be used to use the same
  parse expression in different places in a grammar, with different parse actions
  attached to each; a short-form ``expr()`` is equivalent to ``expr.copy()``

- ``leave_whitespace()`` - change default behavior of skipping
  whitespace before starting matching (mostly used internally to the
  pyparsing module, rarely used by client code)

- ``set_whitespace_chars(chars)`` - define the set of chars to be ignored
  as whitespace before trying to match a specific ``ParserElement``, in place of the
  default set of whitespace (space, tab, newline, and return)

- ``set_default_whitespace_chars(chars)`` - class-level method to override
  the default set of whitespace chars for all subsequently created ParserElements
  (including copies); useful when defining grammars that treat one or more of the
  default whitespace characters as significant (such as a line-sensitive grammar, to
  omit newline from the list of ignorable whitespace)

- ``suppress()`` - convenience function to suppress the output of the
  given element, instead of wrapping it with a ``Suppress`` object.

- ``ignore(expr)`` - function to specify parse expression to be
  ignored while matching defined patterns; can be called
  repeatedly to specify multiple expressions; useful to specify
  patterns of comment syntax, for example

- ``set_debug(flag=True)`` - function to enable/disable tracing output
  when trying to match this element

- ``validate()`` - function to verify that the defined grammar does not
  contain infinitely recursive constructs.

  *(``validate()`` is deprecated, and
  will be removed in a future pyparsing release. Pyparsing now supports
  left-recursive parsers, which this function attempted to catch.)*

.. _parse_with_tabs:

- ``parse_with_tabs()`` - function to override default behavior of converting
  tabs to spaces before parsing the input string; rarely used, except when
  specifying whitespace-significant grammars using the White_ class.

- ``enable_packrat()`` - a class-level static method to enable a memoizing
  performance enhancement, known as "packrat parsing".  packrat parsing is
  disabled by default, since it may conflict with some user programs that use
  parse actions.  To activate the packrat feature, your
  program must call the class method ``ParserElement.enable_packrat()``. For best
  results, call ``enable_packrat()`` immediately after importing pyparsing.

- ``enable_left_recursion()`` - a class-level static method to enable
  pyparsing with left-recursive (LR) parsers. Similar to ``ParserElement.enable_packrat()``,
  your program must call the class method ``ParserElement.enable_left_recursion()`` to
  enable this feature. ``enable_left_recursion()`` uses a separate packrat cache, and so
  is incompatible with ``enable_packrat()``.

Basic ParserElement subclasses
------------------------------

.. _Literal:

- ``Literal`` - construct with a string to be matched exactly

.. _CaselessLiteral:

- ``CaselessLiteral`` - construct with a string to be matched, but
  without case checking; results are always returned as the
  defining literal, NOT as they are found in the input string

.. _Keyword:

- ``Keyword`` - similar to Literal_, but must be immediately followed by
  whitespace, punctuation, or other non-keyword characters; prevents
  accidental matching of a non-keyword that happens to begin with a
  defined keyword

- ``CaselessKeyword`` - similar to Keyword_, but with caseless matching
  behavior as described in CaselessLiteral_.

.. _Word:

- ``Word`` - one or more contiguous characters; construct with a
  string containing the set of allowed initial characters, and an
  optional second string of allowed body characters; for instance,
  a common ``Word`` construct is to match a code identifier - in C, a
  valid identifier must start with an alphabetic character or an
  underscore ('_'), followed by a body that can also include numeric
  digits.  That is, ``a``, ``i``, ``MAX_LENGTH``, ``_a1``, ``b_109_``, and
  ``plan9FromOuterSpace``
  are all valid identifiers; ``9b7z``, ``$a``, ``.section``, and ``0debug``
  are not.  To
  define an identifier using a ``Word``, use either of the following::

    Word(alphas+"_", alphanums+"_")
    Word(srange("[a-zA-Z_]"), srange("[a-zA-Z0-9_]"))

  Pyparsing also provides pre-defined strings ``identchars`` and
  ``identbodychars`` so that you can also write::

    Word(identchars, identbodychars)

  If only one
  string given, it specifies that the same character set defined
  for the initial character is used for the word body; for instance, to
  define an identifier that can only be composed of capital letters and
  underscores, use one of::

    ``Word("ABCDEFGHIJKLMNOPQRSTUVWXYZ_")``
    ``Word(srange("[A-Z_]"))``

  A ``Word`` may
  also be constructed with any of the following optional parameters:

  - ``min`` - indicating a minimum length of matching characters

  - ``max`` - indicating a maximum length of matching characters

  - ``exact`` - indicating an exact length of matching characters;
    if ``exact`` is specified, it will override any values for ``min`` or ``max``

  - ``as_keyword`` - indicating that preceding and following characters must
    be whitespace or non-keyword characters

  - ``exclude_chars`` - a string of characters that should be excluded from
    init_chars and body_chars

    Sometimes you want to define a word using all
    characters in a range except for one or two of them; you can do this
    with the ``exclude_chars`` argument. This is helpful if you want to define
    a word with all ``printables`` except for a single delimiter character, such
    as '.'. Previously, you would have to create a custom string to pass to Word.
    With this change, you can just create ``Word(printables, exclude_chars='.')``.

- ``Char`` - a convenience form of ``Word`` that will match just a single character from
  a string of matching characters::

      single_digit = Char(nums)

- ``CharsNotIn`` - similar to Word_, but matches characters not
  in the given constructor string (accepts only one string for both
  initial and body characters); also supports ``min``, ``max``, and ``exact``
  optional parameters.

- ``Regex`` - a powerful construct, that accepts a regular expression
  to be matched at the current parse position; accepts an optional
  ``flags`` parameter, corresponding to the flags parameter in the ``re.compile``
  method; if the expression includes named sub-fields, they will be
  represented in the returned ParseResults_.

- ``QuotedString`` - supports the definition of custom quoted string
  formats, in addition to pyparsing's built-in ``dbl_quoted_string`` and
  ``sgl_quoted_string``.  ``QuotedString`` allows you to specify the following
  parameters:

  - ``quote_char`` - string of one or more characters defining the quote delimiting string

  - ``esc_char`` - character to escape quotes, typically backslash (default=None)

  - ``esc_quote`` - special quote sequence to escape an embedded quote string (such as SQL's "" to escape an embedded ") (default=None)

  - ``multiline`` - boolean indicating whether quotes can span multiple lines (default=False)

  - ``unquote_results`` - boolean indicating whether the matched text should be unquoted (default=True)

  - ``end_quote_char`` - string of one or more characters defining the end of the quote delimited string (default=None => same as ``quote_char``)

.. _SkipTo:

- ``SkipTo`` - skips ahead in the input string, accepting any
  characters up to the specified pattern; may be constructed with
  the following optional parameters:

  - ``include`` - if set to true, also consumes the match expression
    (default is false)

  - ``ignore`` - allows the user to specify patterns to not be matched,
    to prevent false matches

  - ``fail_on`` - if a literal string or expression is given for this argument, it defines an expression that
    should cause the SkipTo_ expression to fail, and not skip over that expression

  ``SkipTo`` can also be written using ``...``::

    LBRACE, RBRACE = Literal.using_each("{}")

    brace_expr = LBRACE + SkipTo(RBRACE) + RBRACE
    # can also be written as
    brace_expr = LBRACE + ... + RBRACE

.. _White:

- ``White`` - also similar to Word_, but matches whitespace
  characters.  Not usually needed, as whitespace is implicitly
  ignored by pyparsing.  However, some grammars are whitespace-sensitive,
  such as those that use leading tabs or spaces to indicating grouping
  or hierarchy.  (If matching on tab characters, be sure to call
  parse_with_tabs_ on the top-level parse element.)

- ``Empty`` - a null expression, requiring no characters - will always
  match; useful for debugging and for specialized grammars

- ``NoMatch`` - opposite of ``Empty``, will never match; useful for debugging
  and for specialized grammars


Expression subclasses
---------------------

.. _And:

- ``And`` - construct with a list of ``ParserElements``, all of which must
  match for ``And`` to match; can also be created using the '+'
  operator; multiple expressions can be ``Anded`` together using the '*'
  operator as in::

    ip_address = Word(nums) + ('.' + Word(nums)) * 3

  A tuple can be used as the multiplier, indicating a min/max::

    us_phone_number = Word(nums) + ('-' + Word(nums)) * (1,2)

  A special form of ``And`` is created if the '-' operator is used
  instead of the '+' operator.  In the ``ip_address`` example above, if
  no trailing '.' and ``Word(nums)`` are found after matching the initial
  ``Word(nums)``, then pyparsing will back up in the grammar and try other
  alternatives to ``ip_address``.  However, if ``ip_address`` is defined as::

    strict_ip_address = Word(nums) - ('.'+Word(nums))*3

  then no backing up is done.  If the first ``Word(nums)`` of ``strict_ip_address``
  is matched, then any mismatch after that will raise a ``ParseSyntaxException``,
  which will halt the parsing process immediately.  By careful use of the
  '-' operator, grammars can provide meaningful error messages close to
  the location where the incoming text does not match the specified
  grammar.

.. _Or:

- ``Or`` - construct with a list of ``ParserElements``, any of which must
  match for ``Or`` to match; if more than one expression matches, the
  expression that makes the longest match will be used; can also
  be created using the '^' operator

.. _MatchFirst:

- ``MatchFirst`` - construct with a list of ``ParserElements``, any of
  which must match for ``MatchFirst`` to match; matching is done
  left-to-right, taking the first expression that matches; can
  also be created using the '|' operator

.. _Each:

- ``Each`` - similar to And_, in that all of the provided expressions
  must match; however, ``Each`` permits matching to be done in any order;
  can also be created using the '&' operator

- ``Opt`` - construct with a ``ParserElement``, but this element is
  not required to match; can be constructed with an optional ``default`` argument,
  containing a default string or object to be supplied if the given optional
  parse element is not found in the input string; parse action will only
  be called if a match is found, or if a default is specified.

  An optional element ``expr`` can also be expressed using ``expr | ""``.

  (``Opt`` was formerly named ``Optional``, but since the standard Python
  library module ``typing`` now defines ``Optional``, the pyparsing class has
  been renamed to ``Opt``. A compatibility synonym ``Optional`` is defined,
  but will be removed in a future release.)

.. _ZeroOrMore:

- ``ZeroOrMore`` - similar to ``Opt``, but can be repeated; ``ZeroOrMore(expr)``
  can also be written as ``expr[...]``.

.. _OneOrMore:

- ``OneOrMore`` - similar to ZeroOrMore_, but at least one match must
  be present; ``OneOrMore(expr)`` can also be written as ``expr[1, ...]``.

.. _DelimitedList:

- ``DelimitedList`` - used for
  matching one or more occurrences of ``expr``, separated by ``delim``.
  By default, the delimiters are suppressed, so the returned results contain
  only the separate list elements.  Can optionally specify ``combine=True``,
  indicating that the expressions and delimiters should be returned as one
  combined value (useful for scoped variables, such as ``"a.b.c"``, or
  ``"a::b::c"``, or paths such as ``"a/b/c"``). Can also optionally specify ``min` and ``max``
  restrictions on the length of the list, and
  ``allow_trailing_delim`` to accept a trailing delimiter at the end of the list.

.. _FollowedBy:

- ``FollowedBy`` - a lookahead expression, requires matching of the given
  expressions, but does not advance the parsing position within the input string

.. _NotAny:

- ``NotAny`` - a negative lookahead expression, prevents matching of named
  expressions, does not advance the parsing position within the input string;
  can also be created using the unary '~' operator


.. _operators:

Expression operators
--------------------

- ``+`` - creates And_ using the expressions before and after the operator

- ``|`` - creates MatchFirst_ (first left-to-right match) using the expressions before and after the operator

- ``^`` - creates Or_ (longest match) using the expressions before and after the operator

- ``&`` - creates Each_ using the expressions before and after the operator

- ``*`` - creates And_ by multiplying the expression by the integer operand; if
  expression is multiplied by a 2-tuple, creates an And_ of ``(min,max)``
  expressions (similar to ``{min,max}`` form in regular expressions); if
  ``min`` is ``None``, interpret as ``(0,max)``; if ``max`` is ``None``, interpret as
  ``expr*min + ZeroOrMore(expr)``

- ``-`` - like ``+`` but with no backup and retry of alternatives

- ``~`` - creates NotAny_ using the expression after the operator

- ``==`` - matching expression to string; returns ``True`` if the string matches the given expression

- ``<<=`` - inserts the expression following the operator as the body of the
  ``Forward`` expression before the operator (``<<`` can also be used, but ``<<=`` is preferred
  to avoid operator precedence misinterpretation of the pyparsing expression)

- ``...`` - inserts a SkipTo_ expression leading to the next expression, as in
  ``Keyword("start") + ... + Keyword("end")``.

- ``[min, max]`` - specifies repetition similar to ``*`` with ``min`` and ``max`` specified
  as the minimum and maximum number of repetitions. ``...`` can be used in place of ``None``.
  For example ``expr[...]`` is equivalent to ``ZeroOrMore(expr)``, ``expr[1, ...]`` is
  equivalent to ``OneOrMore(expr)``, and ``expr[..., 3]`` is equivalent to "up to 3 instances
  of ``expr``".

- ``[:stop_on]`` - specifies a stopping expression for the current repetition (may be combined
  with ``...`` or ``min, max``), as in ``Keyword("start") + Word(alphas)[...:Keyword("end")] + Keyword("end")``

Positional subclasses
---------------------

- ``StringStart`` - matches beginning of the text

- ``StringEnd`` - matches the end of the text

- ``LineStart`` - matches beginning of a line (lines delimited by ``\n`` characters)

- ``LineEnd`` - matches the end of a line

- ``WordStart`` - matches a leading word boundary

- ``WordEnd`` - matches a trailing word boundary



Converter subclasses
--------------------

- ``Combine`` - joins all matched tokens into a single string, using
  specified ``join_string`` (default ``join_string=""``); expects
  all matching tokens to be adjacent, with no intervening
  whitespace (can be overridden by specifying ``adjacent=False`` in constructor)

- ``Suppress`` - clears matched tokens; useful to keep returned
  results from being cluttered with required but uninteresting
  tokens (such as list delimiters)


Special subclasses
------------------

- ``Group`` - causes the matched tokens to be enclosed in a list;
  useful in repeated elements like ZeroOrMore_ and OneOrMore_ to
  break up matched tokens into groups for each repeated pattern

- ``Dict`` - like ``Group``, but also constructs a dictionary, using the
  ``[0]``'th elements of all enclosed token lists as the keys, and
  each token list as the value

- ``Forward`` - placeholder token used to define recursive token
  patterns; when defining the actual expression later in the
  program, insert it into the ``Forward`` object using the ``<<=``
  operator (see fourFn.py_ for an example).

- ``Tag`` - a non-parsing token that always matches, and inserts
  a tag and value into the current parsed tokens; useful for adding
  metadata or annotations to parsed results (see `examples/tag_example.py <../examples/tag_example.py>`_).


Other classes
-------------
.. _ParseResults:

- ``ParseResults`` - class used to contain and manage the lists of tokens
  created from parsing the input using the user-defined parse
  expression.  ``ParseResults`` can be accessed in a number of ways:

  - as a list

    - total list of elements can be found using ``len()``

    - individual elements can be found using ``[0], [1], [-1],`` etc.,
      or retrieved using slices

    - elements can be deleted using ``del``

    - the last element can be extracted and removed in a single operation
      using ``pop()``, or any element can be extracted and removed
      using ``pop(n)``

    - a nested ParseResults_ can be created by using the pyparsing ``Group`` class
      around elements in an expression::

          Word(alphas) + Group(Word(nums)[...]) + Word(alphas)

      will parse the string "abc 100 200 300 end" as::

          ['abc', ['100', '200', '300'], 'end']

      If the ``Group`` is constructed using ``aslist=True``, the resulting tokens
      will be a Python list instead of a ParseResults_. In this case, the returned value will
      no longer support the extended features or methods of a ParseResults_.

  - as a dictionary

    - if ``set_results_name()`` is used to name elements within the
      overall parse expression, then these fields can be referenced
      as dictionary elements or as attributes

    - the ``Dict`` class generates dictionary entries using the data of the
      input text - in addition to ParseResults_ listed as ``[ [ a1, b1, c1, ...], [ a2, b2, c2, ...]  ]``
      it also acts as a dictionary with entries defined as ``{ a1 : [ b1, c1, ... ] }, { a2 : [ b2, c2, ... ] }``;
      this is especially useful when processing tabular data where the first column contains a key
      value for that line of data; when constructed with ``asdict=True``, will
      return an actual Python ``dict`` instead of a ParseResults_. In this case, the returned value will
      no longer support the extended features or methods of a ParseResults_.

    - list elements that are deleted using ``del`` will still be accessible by their
      dictionary keys

    - supports ``get()``, ``items()`` and ``keys()`` methods, similar to a dictionary

    - a keyed item can be extracted and removed using ``pop(key)``.  Here
      ``key`` must be non-numeric (such as a string), in order to use dict
      extraction instead of list extraction.

    - new named elements can be added (in a parse action, for instance), using the same
      syntax as adding an item to a dict (``parse_results["X"] = "new item"``);
      named elements can be removed using ``del parse_results["X"]``

  - as a nested list

    - results returned from the Group class are encapsulated within their
      own list structure, so that the tokens can be handled as a hierarchical
      tree

  - as an object

    - named elements can be accessed as if they were attributes of an object:
      if an element is referenced that does not exist, it will return ``""``.

  ParseResults_ can also be converted to an ordinary list of strings
  by calling ``as_list()``.  Note that this will strip the results of any
  field names that have been defined for any embedded parse elements.
  (The ``pprint`` module is especially good at printing out the nested contents
  given by ``as_list()``.)

  If a ParseResults_ is built with expressions that use results names (see _set_results_name) or
  using the ``Dict`` class, then those names and values can be extracted as a Python
  dict using ``as_dict()``.

  Finally, ParseResults_ can be viewed by calling ``dump()``. ``dump()`` will first show
  the ``as_list()`` output, followed by an indented structure listing parsed tokens that
  have been assigned results names.

  Here is sample code illustrating some of these methods::

    >>> number = Word(nums)
    >>> name = Combine(Word(alphas)[...], adjacent=False, join_string=" ")
    >>> parser = number("house_number") + name("street_name")
    >>> result = parser.parse_string("123 Main St")
    >>> print(result)
    ['123', 'Main St']
    >>> print(type(result))
    <class 'pyparsing.ParseResults'>
    >>> print(repr(result))
    (['123', 'Main St'], {'house_number': ['123'], 'street_name': ['Main St']})
    >>> result.house_number
    '123'
    >>> result["street_name"]
    'Main St'
    >>> result.as_list()
    ['123', 'Main St']
    >>> result.as_dict()
    {'house_number': '123', 'street_name': 'Main St'}
    >>> print(result.dump())
    ['123', 'Main St']
    - house_number: '123'
    - street_name: 'Main St'


Exception classes and Troubleshooting
-------------------------------------

.. _ParseException:

- ``ParseException`` - exception returned when a grammar parse fails;
  ``ParseExceptions`` have attributes ``loc``, ``msg``, ``line``, ``lineno``, and ``column``; to view the
  text line and location where the reported ParseException occurs, use::

    except ParseException as err:
        print(err.line)
        print(" " * (err.column - 1) + "^")
        print(err)

  ``ParseExceptions`` also have an ``explain()`` method that gives this same information::

    except ParseException as err:
        print(err.explain())

- ``RecursiveGrammarException`` - exception returned by ``validate()`` if
  the grammar contains a recursive infinite loop, such as::

    bad_grammar = Forward()
    good_token = Literal("A")
    bad_grammar <<= Opt(good_token) + bad_grammar

- ``ParseFatalException`` - exception that parse actions can raise to stop parsing
  immediately.  Should be used when a semantic error is found in the input text, such
  as a mismatched XML tag.

- ``ParseSyntaxException`` - subclass of ``ParseFatalException`` raised when a
  syntax error is found, based on the use of the '-' operator when defining
  a sequence of expressions in an And_ expression.

- You can also get some insights into the parsing logic using diagnostic parse actions,
  and ``set_debug()``, or test the matching of expression fragments by testing them using
  ``search_string()`` or ``scan_string()``.

- Use ``with_line_numbers`` from ``pyparsing_testing`` to display the input string
  being parsed, with line and column numbers that correspond to the values reported
  in set_debug() output::

      import pyparsing as pp
      ppt = pp.testing

      data = """\
         A
            100"""

      expr = pp.Word(pp.alphanums).set_name("word").set_debug()
      print(ppt.with_line_numbers(data))
      expr[...].parse_string(data)

  prints::

      .          1
        1234567890
      1:   A|
      2:      100|

      Match word at loc 3(1,4)
          A
          ^
      Matched word -> ['A']
      Match word at loc 11(2,7)
             100
             ^
      Matched word -> ['100']

  `with_line_numbers` has several options for displaying control characters, end-of-line
  and space markers, Unicode symbols for control characters - these are documented in the
  function's docstring.

- Diagnostics can be enabled using ``pyparsing.enable_diag`` and passing
  one of the following enum values defined in ``pyparsing.Diagnostics``

  - ``warn_multiple_tokens_in_named_alternation`` - flag to enable warnings when a results
    name is defined on a MatchFirst_ or Or_ expression with one or more And_ subexpressions

  - ``warn_ungrouped_named_tokens_in_collection`` - flag to enable warnings when a results
    name is defined on a containing expression with ungrouped subexpressions that also
    have results names

  - ``warn_name_set_on_empty_Forward`` - flag to enable warnings when a ``Forward`` is defined
    with a results name, but has no contents defined

  - ``warn_on_parse_using_empty_Forward`` - flag to enable warnings when a ``Forward`` is
    defined in a grammar but has never had an expression attached to it

  - ``warn_on_assignment_to_Forward`` - flag to enable warnings when a ``Forward`` is defined
    but is overwritten by assigning using ``'='`` instead of ``'<<='`` or ``'<<'``

  - ``warn_on_multiple_string_args_to_oneof`` - flag to enable warnings when ``one_of`` is
    incorrectly called with multiple str arguments

  - ``enable_debug_on_named_expressions`` - flag to auto-enable debug on all subsequent
    calls to ``ParserElement.set_name``

  All warnings can be enabled by calling ``pyparsing.enable_all_warnings()``.
  Sample::

    import pyparsing as pp
    pp.enable_all_warnings()

    fwd = pp.Forward().set_results_name("recursive_expr")

    >>> UserWarning: warn_name_set_on_empty_Forward: setting results name 'recursive_expr'
                     on Forward expression that has no contained expression

  Warnings can also be enabled using the Python ``-W`` switch (using ``-Wd`` or
  ``-Wd:::pyparsing``) or setting a non-empty value to the environment variable
  ``PYPARSINGENABLEALLWARNINGS``. (If using ``-Wd`` for testing, but wishing to
  disable pyparsing warnings, add ``-Wi:::pyparsing``.)


Miscellaneous attributes and methods
====================================

Helper methods
--------------

- ``counted_array(expr)`` - convenience function for a pattern where an list of
  instances of the given expression are preceded by an integer giving the count of
  elements in the list.  Returns an expression that parses the leading integer,
  reads exactly that many expressions, and returns the array of expressions in the
  parse results - the leading integer is suppressed from the results (although it
  is easily reconstructed by using len on the returned array).

- ``one_of(choices, caseless=False, as_keyword=False)`` - convenience function for quickly declaring an
  alternative set of Literal_ expressions. ``choices`` can be passed as a list of strings
  or as a single string of values separated by spaces. The values are sorted so that longer
  matches are attempted first; this ensures that a short value does
  not mask a longer one that starts with the same characters. If ``caseless=True``,
  will create an alternative set of CaselessLiteral_ tokens. If ``as_keyword=True``,
  ``one_of`` will declare Keyword_ expressions instead of Literal_ expressions.

- ``dict_of(key, value)`` - convenience function for quickly declaring a
  dictionary pattern of ``Dict(ZeroOrMore(Group(key + value)))``.

- ``make_html_tags(tag_str)`` and ``make_xml_tags(tag_str)`` - convenience
  functions to create definitions of opening and closing tag expressions.  Returns
  a pair of expressions, for the corresponding ``<tag>`` and ``</tag>`` strings.  Includes
  support for attributes in the opening tag, such as ``<tag attr1="abc">`` - attributes
  are returned as named results in the returned ParseResults_.  ``make_html_tags`` is less
  restrictive than ``make_xml_tags``, especially with respect to case sensitivity.

- ``infix_notation(base_operand, operator_list)`` -
  convenience function to define a grammar for parsing infix notation
  expressions with a hierarchical precedence of operators. To use the ``infix_notation``
  helper:

  1.  Define the base "atom" operand term of the grammar.
      For this simple grammar, the smallest operand is either
      an integer or a variable.  This will be the first argument
      to the ``infix_notation`` method.

  2.  Define a list of tuples for each level of operator
      precedence.  Each tuple is of the form
      ``(operand_expr, num_operands, right_left_assoc, parse_action)``, where:

      - ``operand_expr`` - the pyparsing expression for the operator;
        may also be a string, which will be converted to a Literal_; if
        ``None``, indicates an empty operator, such as the implied
        multiplication operation between 'm' and 'x' in "y = mx + b".

      - ``num_operands`` - the number of terms for this operator (must
        be 1, 2, or 3)

      - ``right_left_assoc`` is the indicator whether the operator is
        right or left associative, using the pyparsing-defined
        constants ``OpAssoc.RIGHT`` and ``OpAssoc.LEFT``.

      - ``parse_action`` is the parse action to be associated with
        expressions matching this operator expression (the
        ``parse_action`` tuple member may be omitted)

  3.  Call ``infix_notation`` passing the operand expression and
      the operator precedence list, and save the returned value
      as the generated pyparsing expression.  You can then use
      this expression to parse input strings, or incorporate it
      into a larger, more complex grammar.

  Here is an ``infix_notation`` definition for 4-function arithmetic,
  taking numbers or variables as operands. The order of definition of
  the operators follows the standard precedence of operations for
  arithmetic::

        number = pp.common.number()
        variable = pp.common.identifier()
        arithmetic_expression = pp.infix_notation(
            integer | variable,
            [
                ("-", 1, pp.OpAssoc.RIGHT),
                (pp.one_of("* /"), 2, pp.OpAssoc.LEFT),
                (pp.one_of("+ -"), 2, pp.OpAssoc.LEFT),
            ]
        )

  ``infix_notation`` also supports optional arguments ``lpar`` and ``rpar``, to
  parse groups with symbols other than "(" and ")". They may be passed as strings
  (in which case they will be converted to ``Suppress`` objects, and suppressed from
  the parsed results), or passed as pyparsing expressions, in which case they will
  be kept as-is, and grouped with their contents.

  For instance, to use "<" and ">" for grouping symbols, you could write::

        expr = infix_notation(int_expr,
            [
                (one_of("+ -"), 2, OpAssoc.LEFT),
            ],
            lpar="<",
            rpar=">"
            )
        expr.parse_string("3 - <2 + 11>")

  returning::

        [3, '-', [2, '+', 11]]

  If the grouping symbols are to be retained, then pass them as pyparsing ``Literals``::

        expr = infix_notation(int_expr,
            [
                (one_of("+ -"), 2, OpAssoc.LEFT),
            ],
            lpar=Literal("<"),
            rpar=Literal(">")
            )
        expr.parse_string("3 - <2 + 11>")

  returning::

        [3, '-', ['<', [2, '+', 11], '>']]

- ``match_previous_literal`` and ``match_previous_expr`` - function to define an
  expression that matches the same content
  as was parsed in a previous parse expression.  For instance::

        first = Word(nums)
        match_expr = first + ":" + match_previous_literal(first)

  will match "1:1", but not "1:2".  Since this matches at the literal
  level, this will also match the leading "1:1" in "1:10".

  In contrast::

        first = Word(nums)
        match_expr = first + ":" + match_previous_expr(first)

  will *not* match the leading "1:1" in "1:10"; the expressions are
  evaluated first, and then compared, so "1" is compared with "10".

- ``nested_expr(opener, closer, content=None, ignore_expr=quoted_string)`` - method for defining nested
  lists enclosed in opening and closing delimiters.

  - ``opener`` - opening character for a nested list (default="("); can also be a pyparsing expression

  - ``closer`` - closing character for a nested list (default=")"); can also be a pyparsing expression

  - ``content`` - expression for items within the nested lists (default=None)

  - ``ignore_expr`` - expression for ignoring opening and closing delimiters (default=``quoted_string``)

  If an expression is not provided for the content argument, the nested
  expression will capture all whitespace-delimited content between delimiters
  as a list of separate values.

  Use the ``ignore_expr`` argument to define expressions that may contain
  opening or closing characters that should not be treated as opening
  or closing characters for nesting, such as ``quoted_string`` or a comment
  expression.  Specify multiple expressions using an Or_ or MatchFirst_.
  The default is ``quoted_string``, but if no expressions are to be ignored,
  then pass ``None`` for this argument.


- ``IndentedBlock(statement_expr, recursive=False, grouped=True)`` -
  function to define an indented block of statements, similar to
  indentation-based blocking in Python source code:

  - ``statement_expr`` - the expression defining a statement that
    will be found in the indented block; a valid ``IndentedBlock``
    must contain at least 1 matching ``statement_expr``

  - ``recursive`` - flag indicating whether the IndentedBlock can
    itself contain nested sub-blocks of the same type of expression
    (default=False)

  - ``grouped`` - flag indicating whether the tokens returned from
    parsing the IndentedBlock should be grouped (default=True)

.. _originalTextFor:

- ``original_text_for(expr)`` - helper function to preserve the originally parsed text, regardless of any
  token processing or conversion done by the contained expression.  For instance, the following expression::

        full_name = Word(alphas) + Word(alphas)

  will return the parse of "John Smith" as ['John', 'Smith'].  In some applications, the actual name as it
  was given in the input string is what is desired.  To do this, use ``original_text_for``::

        full_name = original_text_for(Word(alphas) + Word(alphas))

- ``ungroup(expr)`` - function to "ungroup" returned tokens; useful
  to undo the default behavior of And_ to always group the returned tokens, even
  if there is only one in the list.

- ``lineno(loc, string)`` - function to give the line number of the
  location within the string; the first line is line 1, newlines
  start new rows

- ``col(loc, string)`` - function to give the column number of the
  location within the string; the first column is column 1,
  newlines reset the column number to 1

- ``line(loc, string)`` - function to retrieve the line of text
  representing ``lineno(loc, string)``; useful when printing out diagnostic
  messages for exceptions

- ``srange(range_spec)`` - function to define a string of characters,
  given a string of the form used by regexp string ranges, such as ``"[0-9]"`` for
  all numeric digits, ``"[A-Z_]"`` for uppercase characters plus underscore, and
  so on (note that ``range_spec`` does not include support for generic regular
  expressions, just string range specs)

- ``trace_parse_action(fn)`` - decorator function to debug parse actions. Lists
  each call, called arguments, and return value or exception



Helper parse actions
--------------------

- ``remove_quotes`` - removes the first and last characters of a quoted string;
  useful to remove the delimiting quotes from quoted strings

- ``replace_with(repl_string)`` - returns a parse action that simply returns the
  ``repl_string``; useful when using ``transform_string``, or converting HTML entities, as in::

      nbsp = Literal("&nbsp;").set_parse_action(replace_with("<BLANK>"))

- ``original_text_for``- restores any internal whitespace or suppressed
  text within the tokens for a matched parse
  expression.  This is especially useful when defining expressions
  for ``scan_string`` or ``transform_string`` applications.

- ``with_attribute(*args, **kwargs)`` - helper to create a validating parse action to be used with start tags created
  with ``make_xml_tags`` or ``make_html_tags``. Use ``with_attribute`` to qualify a starting tag
  with a required attribute value, to avoid false matches on common tags such as
  ``<TD>`` or ``<DIV>``.

  ``with_attribute`` can be called with:

  - keyword arguments, as in ``(class="Customer", align="right")``, or

  - a list of name-value tuples, as in ``(("ns1:class", "Customer"), ("ns2:align", "right"))``

  An attribute can be specified to have the special value
  ``with_attribute.ANY_VALUE``, which will match any value - use this to
  ensure that an attribute is present but any attribute value is
  acceptable.

- ``match_only_at_col(column_number)`` - a parse action that verifies that
  an expression was matched at a particular column, raising a
  ``ParseException`` if matching at a different column number; useful when parsing
  tabular data

- ``common.convert_to_integer()`` - converts all matched tokens to int

- ``common.convert_to_float()`` - converts all matched tokens to float

- ``common.convert_to_date()`` - converts matched token to a datetime.date

- ``common.convert_to_datetime()`` - converts matched token to a datetime.datetime

- ``common.strip_html_tags()`` - removes HTML tags from matched token

- ``common.downcase_tokens()`` - converts all matched tokens to lowercase

- ``common.upcase_tokens()`` - converts all matched tokens to uppercase


Common string and token constants
---------------------------------

- ``alphas`` - same as ``string.ascii_letters``

- ``nums`` - same as ``string.digits``

- ``alphanums`` - a string containing ``alphas + nums``

- ``alphas8bit`` - a string containing alphabetic 8-bit characters::

    ÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖØÙÚÛÜÝÞßàáâãäåæçèéêëìíîïðñòóôõöøùúûüýþ

.. _identchars:

- ``identchars`` - a string containing characters that are valid as initial identifier characters::

    ABCDEFGHIJKLMNOPQRSTUVWXYZ_abcdefghijklmnopqrstuvwxyzª
    µºÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖØÙÚÛÜÝÞßàáâãäåæçèéêëìíîïðñòóôõöøùúûüýþÿ

- ``identbodychars`` - a string containing characters that are valid as identifier body characters (those following a
  valid leading identifier character as given in identchars_)::

    0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ_abcdefghijklmnopqrstuvwxyzª
    µ·ºÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖØÙÚÛÜÝÞßàáâãäåæçèéêëìíîïðñòóôõöøùúûüýþÿ

- ``printables`` - same as ``string.printable``, minus the space (``' '``) character

- ``empty`` - a global ``Empty()``; will always match

- ``sgl_quoted_string`` - a string of characters enclosed in 's; may
  include whitespace, but not newlines

- ``dbl_quoted_string`` - a string of characters enclosed in "s; may
  include whitespace, but not newlines

- ``quoted_string`` - ``sgl_quoted_string | dbl_quoted_string``

- ``python_quoted_string`` - ``quoted_string | multiline quoted string``

- ``c_style_comment`` - a comment block delimited by ``'/*'`` and ``'*/'`` sequences; can span
  multiple lines, but does not support nesting of comments

- ``html_comment`` - a comment block delimited by ``'<!--'`` and ``'-->'`` sequences; can span
  multiple lines, but does not support nesting of comments

- ``comma_separated_list`` - similar to DelimitedList_, except that the
  list expressions can be any text value, or a quoted string; quoted strings can
  safely include commas without incorrectly breaking the string into two tokens

- ``rest_of_line`` - all remaining printable characters up to but not including the next
  newline

- ``common.integer`` - an integer with no leading sign; parsed token is converted to int

- ``common.hex_integer`` - a hexadecimal integer; parsed token is converted to int

- ``common.signed_integer`` - an integer with optional leading sign; parsed token is converted to int

- ``common.fraction`` - signed_integer '/' signed_integer; parsed tokens are converted to float

- ``common.mixed_integer`` - signed_integer '-' fraction; parsed tokens are converted to float

- ``common.real`` - real number; parsed tokens are converted to float

- ``common.sci_real`` - real number with optional scientific notation; parsed tokens are convert to float

- ``common.number`` - any numeric expression; parsed tokens are returned as converted by the matched expression

- ``common.fnumber`` - any numeric expression; parsed tokens are converted to float

- ``common.ieee_float`` - any floating-point literal (int, real number, infinity, or NaN), returned as float

- ``common.identifier`` - a programming identifier (follows Python's syntax convention of leading alpha or "_",
  followed by 0 or more alpha, num, or "_")

- ``common.ipv4_address`` - IPv4 address

- ``common.ipv6_address`` - IPv6 address

- ``common.mac_address`` - MAC address (with ":", "-", or "." delimiters)

- ``common.iso8601_date`` - date in ``YYYY-MM-DD`` format

- ``common.iso8601_datetime`` - datetime in ``YYYY-MM-DDThh:mm:ss.s(Z|+-00:00)`` format; trailing seconds,
  milliseconds, and timezone optional; accepts separating ``'T'`` or ``' '``

- ``common.url`` - matches URL strings and returns a ParseResults with named fields like those returned
  by ``urllib.parse.urlparse()``


Unicode character sets for international parsing
------------------------------------------------
Pyparsing includes the ``unicode`` namespace that contains definitions for ``alphas``, ``nums``, ``alphanums``,
``identchars``, ``identbodychars``, and ``printables`` for character ranges besides 7- or 8-bit ASCII. You can
access them using code like the following::

    import pyparsing as pp
    ppu = pp.unicode

    greek_word = pp.Word(ppu.Greek.alphas)
    greek_word[...].parse_string("Καλημέρα κόσμε")

The following language ranges are defined.

==========================    =================     ========================================================
Unicode set                   Alternate names       Description
--------------------------    -----------------     --------------------------------------------------------
``Arabic``                        العربية
``Chinese``                   中文
``CJK``                                             Union of Chinese, Japanese, and Korean sets
``Cyrillic``                  кириллица
``Devanagari``                देवनागरी
``Greek``                     Ελληνικά
``Hangul``                    Korean, 한국어
``Hebrew``                        עִברִית
``Japanese``                  日本語                 Union of Kanji, Katakana, and Hiragana sets
``Japanese.Hiragana``         ひらがな
``Japanese.Kanji``            漢字
``Japanese.Katakana``         カタカナ
``Latin1``                                          All Unicode characters up to code point 0x7f (255)
``LatinA``                                          Unicode characters for code points 0x100-0x17f (256-383)
``LatinB``                                          Unicode characters for code points 0x180-0x24f (384-591)
``Thai``                      ไทย
``BasicMultilingualPlane``    BMP                   All Unicode characters up to code point 0xffff (65535)
==========================    =================     ========================================================

The base ``unicode`` class also includes definitions based on all Unicode code points up to ``sys.maxunicode``. This
set will include emojis, wingdings, and many other specialized and typographical variant characters.


Generating Railroad Diagrams
============================
Grammars are conventionally represented in what are called "railroad diagrams", which allow you to visually follow
the sequence of tokens in a grammar along lines which are a bit like train tracks. You might want to generate a
railroad diagram for your grammar in order to better understand it yourself, or maybe to communicate it to others.

Usage
-----
To generate a railroad diagram in pyparsing, you first have to install pyparsing with the ``diagrams`` extra.
To do this, just run ``pip install pyparsing[diagrams]``, and make sure you add ``pyparsing[diagrams]`` to any
``setup.py`` or ``requirements.txt`` that specifies pyparsing as a dependency.

Create your parser as you normally would. Then call ``create_diagram()``, passing the name of an output HTML file.::

    street_address = Word(nums).set_name("house_number") + Word(alphas)[1, ...].set_name("street_name")
    street_address.set_name("street_address")
    street_address.create_diagram("street_address_diagram.html")

This will result in the railroad diagram being written to ``street_address_diagram.html``.

`create_diagram` takes the following arguments:

- ``output_html`` (str or file-like object) - output target for generated diagram HTML

- ``vertical`` (int) - threshold for formatting multiple alternatives vertically instead of horizontally (default=3)

- ``show_results_names`` - bool flag whether diagram should show annotations for defined results names

- ``show_groups`` - bool flag whether groups should be highlighted with an unlabeled surrounding box

- ``show_hidden`` - bool flag whether internal pyparsing elements that are normally omitted in diagrams should be shown (default=False)

- ``embed`` - bool flag whether generated HTML should omit <HEAD>, <BODY>, and <DOCTYPE> tags to embed
  the resulting HTML in an enclosing HTML source (such as PyScript HTML)

- ``head`` - str containing additional HTML to insert into the <HEAD> section of the generated code;
  can be used to insert custom CSS styling

- ``body`` - str containing additional HTML to insert at the beginning of the <BODY> section of the
  generated code


Example
-------
You can view an example railroad diagram generated from `a pyparsing grammar for
SQL SELECT statements <_static/sql_railroad.html>`_ (generated from
`examples/select_parser.py <https://github.com/pyparsing/pyparsing/blob/master/examples/select_parser.py>`_).

Naming tip
----------
Parser elements that are separately named will be broken out as their own sub-diagrams. As a short-cut alternative
to going through and adding ``.set_name()`` calls on all your sub-expressions, you can use ``autoname_elements()`` after
defining your complete grammar. For example::

    a = pp.Literal("a")
    b = pp.Literal("b").set_name("bbb")
    pp.autoname_elements()

`a` will get named "a", while `b` will keep its name "bbb".

Customization
-------------
You can customize the resulting diagram in a few ways.
To do so, run ``pyparsing.diagrams.to_railroad`` to convert your grammar into a form understood by the
`railroad-diagrams <https://github.com/tabatkins/railroad-diagrams/blob/gh-pages/README-py.md>`_ module, and
then ``pyparsing.diagrams.railroad_to_html`` to convert that into an HTML document. For example::

    from pyparsing.diagram import to_railroad, railroad_to_html

    with open('output.html', 'w') as fp:
        railroad = to_railroad(my_grammar)
        fp.write(railroad_to_html(railroad))

This will result in the railroad diagram being written to ``output.html``

You can then pass in additional keyword arguments to ``pyparsing.diagrams.to_railroad``, which will be passed
into the ``Diagram()`` constructor of the underlying library,
`as explained here <https://github.com/tabatkins/railroad-diagrams/blob/gh-pages/README-py.md#diagrams>`_.

In addition, you can edit global options in the underlying library, by editing constants::

    from pyparsing.diagram import to_railroad, railroad_to_html
    import railroad

    railroad.DIAGRAM_CLASS = "my-custom-class"
    my_railroad = to_railroad(my_grammar)

These options `are documented here <https://github.com/tabatkins/railroad-diagrams/blob/gh-pages/README-py.md#options>`_.

Finally, you can edit the HTML produced by ``pyparsing.diagrams.railroad_to_html`` by passing in certain keyword
arguments that will be used in the HTML template. Currently, these are:

- ``head``: A string containing HTML to use in the ``<head>`` tag. This might be a stylesheet or other metadata

- ``body``: A string containing HTML to use in the ``<body>`` tag, above the actual diagram. This might consist of a
  heading, description, or JavaScript.

If you want to provide a custom stylesheet using the ``head`` keyword, you can make use of the following CSS classes:

- ``railroad-group``: A group containing everything relating to a given element group (ie something with a heading)

- ``railroad-heading``: The title for each group

- ``railroad-svg``: A div containing only the diagram SVG for each group

- ``railroad-description``: A div containing the group description (unused)
