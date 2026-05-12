#
# make_diagram.py
#
# Sample railroad diagrams of selected pyparsing examples.
#
# Copyright 2021, Paul McGuire

# Uncomment the related import statement and rerun to construct railroad diagram

from examples.delta_time import time_expression as imported_expr

# from examples.sexpParser import sexp as imported_expr
# from examples.ebnftest import ebnf_parser as imported_expr
# from examples.jsonParser import jsonObject as imported_expr
# from examples.lucene_grammar import expression as imported_expr
# from examples.invRegex import parser; imported_expr = parser()
# from examples.oc import program as imported_expr
# from examples.mozillaCalendarParser import calendars as imported_expr
# from examples.pgn import pgnGrammar as imported_expr
# from examples.idlParse import CORBA_IDL_BNF; imported_expr = CORBA_IDL_BNF()
# from examples.chemical_formulas import formula as imported_expr
# from examples.roman_numerals import roman_numeral as imported_expr
# from examples.protobuf_parser import parser as imported_expr
# from examples.parsePythonValue import listItem as imported_expr
# from examples.one_to_ninety_nine import one_to_99 as imported_expr
# from examples.simpleSQL import simpleSQL as imported_expr
# from examples.simpleBool import boolExpr as imported_expr
# from examples.adventureEngine import Parser; imported_expr = Parser().bnf
# from examples.lua_parser import lua_script as imported_expr


grammar = imported_expr

# or define a custom grammar here
# import pyparsing as pp
# grammar = pp.Or(["foo", "bar"]) + pp.Word(pp.nums) + pp.pyparsing_common.uuid

grammar.create_diagram(output_html="output.html", show_results_names=True)
