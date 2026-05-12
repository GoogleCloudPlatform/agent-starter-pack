# This module tries to implement ISO 14977 standard with pyparsing.
# pyparsing version 1.1 or greater is required.
from typing import Any

# ISO 14977 standardize The Extended Backus-Naur Form(EBNF) syntax.
# You can read a final draft version here:
# https://www.cl.cam.ac.uk/~mgk25/iso-ebnf.html
#
# Submitted 2004 by Seo Sanghyeon
# Updated to current pyparsing styles 2025 by Paul McGuire
#

import pyparsing as pp


all_names = """
integer
meta_identifier
terminal_string
optional_sequence
repeated_sequence
grouped_sequence
syntactic_primary
syntactic_factor
syntactic_term
single_definition
definitions_list
syntax_rule
syntax
""".split()

LBRACK, RBRACK, LBRACE, RBRACE, LPAR, RPAR, DASH, STAR, EQ, SEMI = pp.Suppress.using_each(
    "[]{}()-*=;"
)

integer = pp.common.integer()
meta_identifier = pp.common.identifier()
terminal_string = pp.Regex(
    r'"[^"]*"'
    r"|"
    r"'[^']*'"
).add_parse_action(pp.remove_quotes)

definitions_list = pp.Forward()
optional_sequence = LBRACK + definitions_list + RBRACK
repeated_sequence = LBRACE + definitions_list + RBRACE
grouped_sequence = LPAR + definitions_list + RPAR
syntactic_primary = (
    optional_sequence
    | repeated_sequence
    | grouped_sequence
    | meta_identifier
    | terminal_string
)
syntactic_factor = pp.Optional(integer + STAR) + syntactic_primary
syntactic_term = syntactic_factor + pp.Optional(DASH + syntactic_factor)
single_definition = pp.DelimitedList(syntactic_term, ",")
definitions_list <<= pp.DelimitedList(single_definition, "|")
syntax_rule = meta_identifier + EQ + definitions_list + SEMI

ebnfComment = (
    ("(*" + (pp.CharsNotIn("*") | ("*" + ~pp.Literal(")")))[...] + "*)")
    .streamline()
    .setName("ebnfComment")
)

syntax = syntax_rule[1, ...]
syntax.ignore(ebnfComment)


def do_integer(toks):
    return int(toks[0])


def do_meta_identifier(toks):
    if toks[0] in symbol_table:
        return symbol_table[toks[0]]
    else:
        symbol_table[toks[0]] = pp.Forward()
        return symbol_table[toks[0]]


def do_terminal_string(toks):
    return pp.Literal(toks[0])


def do_optional_sequence(toks):
    return pp.Optional(toks[0])


def do_repeated_sequence(toks):
    return pp.ZeroOrMore(toks[0])


def do_grouped_sequence(toks):
    return pp.Group(toks[0])


def do_syntactic_primary(toks):
    return toks[0]


def do_syntactic_factor(toks):
    if len(toks) == 2 and toks[0] > 1:
        # integer * syntactic_primary
        return pp.And([toks[1]] * toks[0])
    else:
        # syntactic_primary
        return [toks[0]]


def do_syntactic_term(toks):
    if len(toks) == 2:
        # syntactic_factor - syntactic_factor
        return pp.NotAny(toks[1]) + toks[0]
    else:
        # syntactic_factor
        return [toks[0]]


def do_single_definition(toks):
    toks = toks.asList()
    if len(toks) > 1:
        # syntactic_term , syntactic_term , ...
        return pp.And(toks)
    else:
        # syntactic_term
        return [toks[0]]


def do_definitions_list(toks):
    toks = toks.asList()
    if len(toks) > 1:
        # single_definition | single_definition | ...
        return pp.Or(toks)
    else:
        # single_definition
        return [toks[0]]


def do_syntax_rule(toks):
    # meta_identifier = definitions_list ;
    assert toks[0].expr is None, "Duplicate definition"
    toks[0] <<= toks[1]
    return [toks[0]]


def do_syntax():
    # syntax_rule syntax_rule ...
    return symbol_table


for name in all_names:
    expr = vars()[name]
    action = vars()["do_" + name]
    expr.set_name(name)
    expr.add_parse_action(action)
    # expr.setDebug()


symbol_table: dict[str, pp.Forward] = {}


def parse(ebnf, given_table=None, *, enable_debug=False):
    given_table = given_table or {}
    symbol_table.clear()
    symbol_table.update(given_table)
    table = syntax.parse_string(ebnf, parse_all=True)[0]
    missing_definitions = [
        k for k, v in table.items()
        if k not in given_table and v.expr is None
    ]
    assert not missing_definitions, f"Missing definitions for {missing_definitions}"
    for name, expr in table.items():
        expr.set_name(name)
        expr.set_debug(enable_debug)
    return table


if __name__ == '__main__':
    try:
        syntax.create_diagram("ebnf_diagram.html")
    except Exception as e:
        print("Failed to create diagram for EBNF syntax parser"
              f" - {type(e).__name__}: {e}")
