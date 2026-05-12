# Pyparsing Examples

This directory contains a number of examples of parsers created using pyparsing. They fall into a few general 
categories (several examples include supporting railroad diagrams):

<!-- TOC -->
* [Pyparsing tutorial and language feature demonstrations](#pyparsing-tutorial-and-language-feature-demonstrations)
* [Language parsers](#language-parsers)
* [Domain Specific Language parsers](#domain-specific-language-parsers)
* [Search and query language parsers](#search-and-query-language-parsers)
* [Data format parsers](#data-format-parsers)
* [Logical and arithmetic infix notation parsers and examples](#logical-and-arithmetic-infix-notation-parsers-and-examples)
* [Helpful utilities](#helpful-utilities)
<!-- TOC -->

## Pyparsing tutorial and language feature demonstrations
  * Hello World!
    * [greeting.py](./greeting.py)
    * [greetingInGreek.py](./greetingInGreek.py)
    * [greetingInKorean.py](./greetingInKorean.py)
    * [hola_mundo.py](./hola_mundo.py)
  * left recursion
    * [left_recursion.py](./left_recursion.py)
  * macro expansion
    * [macro_expander.py](./macro_expander.py)
  * Roman numerals
    * [roman_numerals.py](./roman_numerals.py)
  * Unicode text handling
    * [tag_metadata.py](./tag_metadata.py) [(diagram)](./tag_metadata_diagram.html)
  * chemical formulas
    * [chemical_formulas.py](./chemical_formulas.py)
    * [complex_chemical_formulas.py](./complex_chemical_formulas.py)
  * API checker
    * [apicheck.py](./apicheck.py) [(diagram)](./apicheck_diagram.html)
  * scan_string examples
    * [scanExamples.py](./scanExamples.py)
  * transform_string examples
    * [include_preprocessor.py](./include_preprocessor.py)
    * [macro_expander.py](./macro_expander.py)
    * [nested_markup.py](./nested_markup.py)
  * parse actions and conditions
    * [shapes.py](./shapes.py)
    * [number_words.py](./number_words.py) [(diagram)](./number_words_diagram.html)
    * [wordsToNum.py](./wordsToNum.py)
    * [range_check.py](./range_check.py)
    * [one_to_ninety_nine.py](./one_to_ninety_nine.py)
  * railroad diagrams
    * [railroad_diagram_demo.py](./railroad_diagram_demo.py) [(diagram)](./railroad_diagram_demo.html)
  * web page scraping
    * [getNTPserversNew.py](./getNTPserversNew.py)
    * [html_stripper.py](./html_stripper.py)
    * [html_table_parser.py](./html_table_parser.py)
    * [urlExtractorNew.py](./urlExtractorNew.py)
## Language parsers
  * C
    * [oc.py](./oc.py)
  * lua
    * [lua_parser.py](./lua_parser.py) [(diagram)](./lua_parser_diagram.html)
  * lox
    * [lox_parser.py](./lox_parser.py) [(diagram)](./lox_parser_diagram.html)
  * verilog
    * [verilog_parse.py](./verilog_parse.py)
  * brainf*ck
    * [bf.py](./bf.py) [(diagram)](./bf_diagram.html)
  * decaf
    * [decaf_parser.py](./decaf_parser.py) [(diagram)](./decaf_parser_diagram.html)
  * S-expression
    * [sexpParser.py](./sexpParser.py)
  * rosetta code
    * [rosettacode.py](./rosettacode.py) [(diagram)](./rosettacode_diagram.html)
## Domain Specific Language parsers
  * adventureEngine - interactive fiction parser and game runner
    * [adventureEngine.py](./adventureEngine.py) [(diagram)](./adventure_game_parser_diagram.html)
  * pgn - Chess notation parser
    * [pgn.py](./pgn.py)
  * TAP - Test results parser
    * [TAP.py](./TAP.py) [(diagram)](./TAP_diagram.html)
  * EBNF - Extended Backus-Naur Format parser (and compiler to a running pyparsing parser)
    * [ebnf.py](./ebnf.py) [(diagram)](./ebnf_diagram.html)
    * [ebnf_number_words.py](./ebnf_number_words.py) [(diagram)](./ebnf_number_parser_diagram.html)
## Search and query language parsers
  * basic search
    * [searchparser.py](./searchparser.py) [demo](./searchParserAppDemo.py)
  * lucene
    * [lucene_grammar.py](./lucene_grammar.py) [(diagram)](./lucene_grammar_diagram.html)
  * mongodb query
    * [mongodb_query_expression.py](./mongodb_query_expression.py) [(diagram)](./mongodb_query_expression.html)
  * SQL
    * [select_parser.py](./select_parser.py) (SELECT statements)
    * [sql2dot.py](./sql2dot.py) (TABLE DML statements)
  * BigQuery view
    * [bigquery_view_parser.py](./bigquery_view_parser.py)
## Data format parsers
  * JSON
    * [jsonParser.py](./jsonParser.py)
  * protobuf
    * [protobuf_parser.py](./protobuf_parser.py)
  * stackish
    * [stackish.py](./stackish.py)
  * CORBA IDL
    * [idlparse.py](./idlparse.py)
## Logical and arithmetic infix notation parsers and examples
  * [fourFn.py](./fourFn.py)
  * [simpleArith.py](./simpleArith.py)
  * [eval_arith.py](./eval_arith.py)
  * [simpleCalc.py](./simpleCalc.py)
  * [LAparser.py](./LAparser.py) (linear algebra)
  * [simpleBool.py](./simpleBool.py)
## Helpful utilities
  * parse time expressions ("2pm the day after tomorrow")
    * [delta_time.py](./delta_time.py) [(diagram)](./delta_time_diagram.html)
  * invert regex (generate sample strings matching a regex)
    * [inv_regex.py](./inv_regex.py)
  * email addresses
    * [email_address_parser.py](./email_address_parser.py)
  * Excel cell formula
    * [excel_expr.py](./excel_expr.py)
  * ctypes interfaces code generator from C include.h file
    * [gen_ctypes.py](./gen_ctypes.py)
  * log file parsing
    * [httpServerLogPaser.py](./httpServerLogPaser.py)


