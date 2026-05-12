#
# mongodb_conditional_expression_step_0.py
#
# Pyparsing parser and wrapper method to parse infix arithmetic and boolean
# expressions and transform them to MongoDB's nested dict queries with
# associated operator tags.
#
# This Step #0 is the initial definition of just the parser. The subsequent Python
# script will contain the parse actions needed to convert the parsed query expression
# into the pymongo dict queries.
#
# Example:
#    mongo_query = transform_query("100 < a <= 200")
#    print(mongo_query)
#
# Prints:
#    {'$and': [{'a': {'$gt': 100}}, {'a': {'$lte': 200}}]}
#
#
# Query BNF:
#
#    query_expression := query_and_expression [OR query_and_expression]...
#    query_and_expression := query_not_expression [AND query_not_expression]...
#    query_not_expression := [NOT] query_expression_operand
#    query_expression_operand := arith_comparison_expression | "(" query_expression ")"
#
#    arith_comparison_expression := arith_comparison | inverse_arith_comparison | chained_arith_comparison
#    arith_comparison := arith_lvalue (equality_operator | like_operator | contains_operator) arith_rvalue
#    inverse_arith_comparison := arith_rvalue (in_operator) arith_lvalue
#    chained_arith_comparison := arith_rvalue equality_operator arith_lvalue equality_operator arith_rvalue
#
#    equality_operator := "<=" | ">=" | "<" | ">" | "≤" | "≥" | "=" | "==" | "!=" | "≠"
#    like_operator := "like" | "not like" | "=~"
#    contains_operator := "contains" ["any" | "all" | "none"] | "⊇"
#    in_operator := "in" | "not in" | "∈" | "∉"
#
#    arith_lvalue := identifier ["." (arith_lvalue | integer) | "[" integer "]"]
#    arith_rvalue := quoted_string | date_time | date | real | integer | "[" arith_rvalue "]"
#
#    quoted_string := character string enclosed in ''s or ""s
#    date := YYYY/MM/DD | YYYY-MM-DD
#    date_time := date HH:MM[:SS[.SSS]]
#    real : a real number
#    integer: [-]'0'-'9'...
#
#
# Copyright 2024, Paul McGuire
#
from datetime import datetime
import re
from typing import Union, Dict

import pyparsing as pp

pp.ParserElement.enable_packrat()

ppc = pp.common

__all__ = [
    "query_condition_expr",
]


def key_phrase(expr: Union[str, pp.ParserElement]) -> pp.ParserElement:
    if isinstance(expr, str):
        expr = pp.And(pp.CaselessKeyword.using_each(expr.split()))
    return pp.Combine(expr, adjacent=False, join_string=" ")


LBRACK, RBRACK = pp.Suppress.using_each("[]")

integer = ppc.integer()
array_ref = LBRACK + integer + RBRACK
array_ref.add_parse_action(lambda t: f".{t[0]}")
ident = pp.Combine(
    ppc.identifier + ("." + (ppc.identifier() | integer) | array_ref)[...]
)
num = ppc.number()

date = pp.Regex(r"\d{4}(/|-)\d{2}(\1)\d{2}")
date_time = pp.Regex(r"\d{4}(/|-)\d{2}(\1)\d{2} \d{2}:\d{2}(:\d{2}(\.\d+)?)?")
date.add_parse_action(lambda t: datetime.fromisoformat(t[0].replace("/", "-")))
date_time.add_parse_action(lambda t: datetime.fromisoformat(t[0].replace("/", "-")))

operand = (
    ident
    | (pp.QuotedString('"') | pp.QuotedString("'")).set_name("quoted_string")
    | date_time
    | date
    | num
)
operand.set_name("operand")
operand_list = pp.Group(
    LBRACK + pp.Optional(pp.DelimitedList(operand)) + RBRACK, aslist=True
)

AND, OR, NOT, IN, CONTAINS, ALL, ANY, NONE, LIKE, SEARCH, FOR = pp.CaselessKeyword.using_each(
    "and or not in contains all any none like search for".split()
)
NOT_IN = key_phrase(NOT + IN)
NOT_LIKE = key_phrase(NOT + LIKE)
CONTAINS_ALL = key_phrase(CONTAINS + ALL)
CONTAINS_NONE = key_phrase(CONTAINS + NONE)
CONTAINS_ANY = key_phrase(CONTAINS + ANY)
SEARCH_FOR = key_phrase(SEARCH + FOR)


# use pyparsing's infix_notation function to define a recursive grammar
# implementing the various operator expressions and their associated parse
# actions, as well as expressions nested in ()'s to override the default
# precedence of operations
arith_comparison_expr = pp.infix_notation(
    (operand | operand_list).set_name("arith_comparison_operand"),
    [
        (pp.one_of("<= >= < > ≤ ≥"), 2, pp.OpAssoc.LEFT,),
        (pp.one_of("= == != ≠"), 2, pp.OpAssoc.LEFT,),
        ( LIKE | NOT_LIKE | "=~", 2, pp.OpAssoc.LEFT,),
        (
            (
                IN
                | NOT_IN
                | CONTAINS_ALL
                | CONTAINS_NONE
                | CONTAINS_ANY
                | CONTAINS
                | pp.one_of("⊇ ∈ ∉")
            ),
            2,
            pp.OpAssoc.LEFT,
        ),
    ],
)

# "not" operator only matches if not followed by "in" or "like"
NOT_OP = NOT + ~(IN | LIKE)
AND_OP = AND | pp.Literal("∧").add_parse_action(pp.replace_with("and"))
OR_OP = OR | pp.Literal("∨").add_parse_action(pp.replace_with("or"))


boolean_comparison_expr = pp.infix_notation(
    (arith_comparison_expr | ident).set_name("boolean_comparison_operand"),
    [
        (NOT_OP, 1, pp.OpAssoc.RIGHT,),
        (AND_OP, 2, pp.OpAssoc.LEFT,),
        (OR_OP, 2, pp.OpAssoc.LEFT,),
    ],
)
query_condition_expr = boolean_comparison_expr

pp.autoname_elements()


def main():
    from pprint import pprint
    from textwrap import dedent

    for test in dedent(
        """\
        a = 100
        a = 100 and b = 200
        a = 100 and b < 200 and c > 300 and d = 400
        a > 1000
        a==100 and b>=200
        a==100 and b>=200 or c<200
        a==100 and (b>=200 or c<200)
        a==100 and not (b>=200 or c<200)
        xyz < 2000 and abc > 32
        xyz < 2000 and abc > 32 and def == 100
        xyz == 2000 and abc == 32 and def == 100
        xyz == 2000 or abc == '32' or def == "foo"
        100 < a < 200
        a==100 and not (100 < b <= 200)
        1900 < "wine vintage" < 2000
        name > "M"
        100 < a ≤ 200 or 300 > b ≥ 200 or c ≠ -1
        100 < a ≤ 200 ∧ 300 > b ≥ 200 ∧ c ≠ -1
        100 < a ≤ 200 ∨ 300 > b ≥ 200 ∨ c ≠ -1
        a==100 and b > 100
        a==100 and not (b > 100)
        a==100 and not not (b > 100)
        a==100 and not not not (b > 100)
        a==100 and not not not not (b > 100)
        name in ["Alice", "Bob"]
        name ∈ ["Alice", "Bob"]
        name not in ["Alice", "Bob"]
        name ∉ ["Alice", "Bob"]
        names contains all ["Alice", "Bob"]
        names ⊇ ["Alice", "Bob"]
        names contains none ["Alice", "Bob"]
        names contains any ["Alice", "Bob"]
        names contains "Alice"
        "Alice" in names
        "Bob" not in names
        a.b > 1000
        a.0 == "Alice"
        a[0] == "Alice"
        a.0.b > 1000
        a[0].b == "Alice"
        name like "%Al"
        name like "Al%"
        name like "%Al%"
        name like "A%e"
        name like "%A%e%"
        name like "%A%%e%"
        name like "%A+"
        name not like "%A+"
        name =~ "Al$"
        name =~ "^Al"
        name =~ "Al"
        name =~ "A+"
        a = 100 and a = 100
        y2k_day = 2000/01/01
        y2k_sec = 2000/01/01 00:00:00
        y2k_msec = 2000/01/01 00:00:00.000
        event.timestamp = 1969/07/20 10:56
        1946 <= birth_year <= 1964
        1946-01-01 <= dob <= 1964-12-31
        # redundant equality conditions get collapsed
        a = 100 and a = 100
        # cannot define conflicting equality conditions
        a = 100 and a = 200
        """
        r"name =~ 'Al\d+'"
    ).splitlines():
        print(test)
        if test.startswith("#"):
            continue
        try:
            transformed = query_condition_expr.parse_string(test, parse_all=True)
        except Exception as exc:
            print(pp.ParseException.explain_exception(exc))
        else:
            pprint(transformed.as_list()[0])
        print()


if __name__ == "__main__":
    query_condition_expr.create_diagram("mongodb_query_expression_0.html")
    main()
