#
# mongodb_conditional_expression.py
#
# Pyparsing parser and wrapper method to parse infix arithmetic and boolean
# expressions and transform them to MongoDB's nested dict queries with
# associated operator tags.
#
# Example:
#    mongo_query = transform_query("100 < a <= 200")
#    print(mongo_query)
#
# Prints:
#    {'$and': [{'a': {'$gt': 100}}, {'a': {'$lte': 200}}]}
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
    "query_condition_expr_with_comment",
    "transform_query",
]


class InvalidExpressionException(pp.ParseFatalException):
    pass


def key_phrase(expr: Union[str, pp.ParserElement]) -> pp.ParserElement:
    if isinstance(expr, str):
        expr = pp.And(pp.CaselessKeyword.using_each(expr.split()))
    return pp.Combine(expr, adjacent=False, join_string=" ")


def unique(seq):
    yield from dict.fromkeys(seq, None)


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

AND, OR, NOT, IN, CONTAINS, ALL, ANY, NONE, LIKE, SEARCH, FOR = (
    pp.CaselessKeyword.using_each(
        "and or not in contains all any none like search for".split()
    )
)
NOT_IN = key_phrase(NOT + IN)
NOT_LIKE = key_phrase(NOT + LIKE)
CONTAINS_ALL = key_phrase(CONTAINS + ALL)
CONTAINS_NONE = key_phrase(CONTAINS + NONE)
CONTAINS_ANY = key_phrase(CONTAINS + ANY)
SEARCH_FOR = key_phrase(SEARCH + FOR)


def binary_eq_neq(s, l, tokens):
    """
    Parse action called for '=' and '!=' comparisons.
    """
    a, op, b = tokens[0]
    try:
        {a: None}
    except TypeError as te:
        raise InvalidExpressionException(
            s, l, f"Could not create query expression using field {a!r}"
        ) from te

    if op in ("=", "=="):
        return {a: b}
    return {a: {"$ne": b}}


def binary_comparison_op(s, l, tokens):
    """
    Parse action called for '<', '>', '<=', and '>=' comparisons.
    Includes logic to handle chained inequalities, like '100 <= a < 200'.
    """
    tokens = tokens[0]
    binary_map = {
        "<": "$lt",
        ">": "$gt",
        "<=": "$lte",
        ">=": "$gte",
        "!=": "$ne",
        # add Unicode operators, because we can
        "≤": "$lte",
        "≥": "$gte",
        "≠": "$ne",
    }
    inequality_inv_map = {
        "<": "$gt",
        ">": "$lt",
        "<=": "$gte",
        ">=": "$lte",
        "≤": "$gte",
        "≥": "$lte",
    }
    operator_compatibility_map = {
        "<": {"<", "<=", "≤"},
        ">": {">", ">=", "≥"},
        "<=": {"<", "<=", "≤"},
        ">=": {">", ">=", "≥"},
        "≤": {"<", "<=", "≤"},
        "≥": {">", ">=", "≥"},
    }

    try:
        field, op, value = tokens
    except ValueError:
        # special handling for 'x < field < y'
        if len(tokens) == 5:
            a, op1, field, op2, b = tokens
            for op_ in (op1, op2):
                if op_ not in inequality_inv_map:
                    raise InvalidExpressionException(
                        s, l, f"{op_} cannot be used in a chained expression"
                    )
            if op2 not in operator_compatibility_map[op1]:
                raise InvalidExpressionException(
                    s, l, f"cannot chain {op1!r} and {op2!r} in the same expression"
                )
            op1 = inequality_inv_map[op1]
            op2 = binary_map[op2]
            return binary_multi_op([[{field: {op1: a}}, "and", {field: {op2: b}}]])
        raise InvalidExpressionException(
            s,
            l,
            f"{tokens[1]!r} comparison operator may not be chained with more than 2 terms",
        )

    return {field: {binary_map[op]: value}}


def binary_array_comparison_op(s, l, tokens):
    """
    Parse action to handle array membership tests, such as 'in', 'not in', etc.
    """
    tokens = tokens[0]
    binary_map = {
        "in": "$in",
        "not in": "$nin",
        "contains any": "$in",
        "contains all": "$all",
        # add Unicode operators, because we can
        "⊇": "$all",
        "∈": "$in",
        "∉": "$nin",
    }

    try:
        field, op, value = tokens
    except ValueError:
        raise InvalidExpressionException(
            s, l, f"{tokens[1]!r} operator may not be chained with more than 2 terms"
        )

    # check for inverted "in" conditions
    if op == "in" and not isinstance(value, list):
        field, value = value, field
        field, op, value = (
            field,
            "contains any",
            value if isinstance(value, list) else [value],
        )

    elif op == "not in" and not isinstance(value, list):
        field, value = value, field
        field, op, value = (
            field,
            "contains none",
            value if isinstance(value, list) else [value],
        )

    if op == "contains none":
        return {
            field: {"$nin": list(unique(value)) if isinstance(value, list) else {value}}
        }

    if op == "contains any":
        return {
            field: {"$in": list(unique(value)) if isinstance(value, list) else {value}}
        }

    return {
        field: {
            binary_map[op]: list(unique(value)) if isinstance(value, list) else {value}
        }
    }


def regex_comparison_op(s, l, tokens):
    """
    Parse action to handle regex and wildcard ("LIKE" syntax) matching.
    """
    tokens = tokens[0]
    try:
        field, op, value = tokens
    except ValueError:
        raise InvalidExpressionException(
            s, l, f"{tokens[1]!r} operations may not be chained"
        )

    # early return for query wildcards that accept or reject any value
    if (op, value) in (
        ("=~", ""),
        ("=~", ".*"),
        ("like", ""),
        ("like", "%"),
    ):
        return {field: {"$exists": True}}

    if (op, value) in (
        ("not like", ""),
        ("not like", "%"),
    ):
        return {field: {"$exists": False}}

    # =~ means value is already a regex
    if op == "=~":
        return {field: {"$regex": value}}

    # op is LIKE or NOT LIKE; value is a "%" wildcard string, convert it to a regex

    # convert "%" wild cards to ".*" and add anchors
    value = re.escape(value)
    xform = {
        (False, False): lambda ss: f"^{ss}$",
        (False, True): lambda ss: f"^{ss[:-1]}",
        (True, False): lambda ss: f"{ss[1:]}$",
        (True, True): lambda ss: ss[1:-1],
    }[value.startswith("%"), value.endswith("%")]

    # convert "%" to ".*" and "%%" to "%"
    DBL_PCT = "\x80"
    re_string = (
        xform(value).replace("%%", DBL_PCT).replace("%", ".*").replace(DBL_PCT, "%")
    )

    if op == "like":
        return {field: {"$regex": re_string}}
    else:
        return {"$nor": [{field: {"$regex": re_string}}]}


def binary_multi_op(tokens):
    """
    Parse action to handle binary Boolean operators 'and' and 'or',
    combining 2 or more condition expressions.

    When this action is called, all the operators will be the same (all 'and' or all 'or').
    If an expression contains multiple 'and' operators (as in 'a=100 and b=200 and c=300'),
    then it will receive them as [{'a': 100}, 'and', {'b': 200}, 'and', {'c': 300}] (the
    individual equality tests having already been processed by binary_eq_neq and converted
    to dicts). There is no limit to the number of terms that can be combined using 'and'
    or 'or'. This method will merge all the parsed value conditions into a single
    dict expression.
    """
    tokens = tokens[0]
    oper_map = {
        "and": "$and",
        "or": "$or",
    }
    op = oper_map[tokens[1]]
    values = tokens[::2]

    if op == "$and":
        # collapse all equality checks into a single term
        literal_values = []
        expr_values = []
        for dd in values:
            k, v = next(iter(dd.items()))
            (literal_values, expr_values)[isinstance(v, (dict, list))].append(dd)

        # collapse literal equalities into a single dict
        collapsed_literal_values = {}
        for dd in literal_values:
            k, v = next(iter(dd.items()))
            if k not in collapsed_literal_values:
                collapsed_literal_values.update(dd)
            else:
                if v != collapsed_literal_values[k]:
                    raise InvalidExpressionException(
                        "multiple equality terms for same field but with different values"
                    )

        if expr_values:
            if collapsed_literal_values:
                return {"$and": [collapsed_literal_values, *expr_values]}
            else:
                return {"$and": expr_values}
        else:
            return collapsed_literal_values

    return {op: values}


def unary_op(tokens):
    """
    Parse action to handle 'not' Boolean operator or 'search for' operator.
    """
    tokens = tokens[0]
    oper_map = {
        "not": "$nor",
    }
    op, value = tokens

    if op == "search for":
        return {"$text": {"$search": value}}

    # detect 'not not'
    k, v = next(iter(value.items()))
    if k == "$nor":
        return v

    return {oper_map[op]: [value]}


# use pyparsing's infix_notation function to define a recursive grammar
# implementing the various operator expressions and their associated parse
# actions, as well as expressions nested in ()'s to override the default
# precedence of operations
arith_comparison_expr = pp.infix_notation(
    (operand | operand_list).set_name("arith_comparison_operand"),
    [
        (SEARCH_FOR, 1, pp.OpAssoc.RIGHT, unary_op),
        (pp.one_of("<= >= < > ≤ ≥"), 2, pp.OpAssoc.LEFT, binary_comparison_op),
        (pp.one_of("= == != ≠"), 2, pp.OpAssoc.LEFT, binary_eq_neq),
        ((LIKE | NOT_LIKE | "=~").set_name("like_operator"), 2, pp.OpAssoc.LEFT, regex_comparison_op),
        (
            (
                    IN
                    | NOT_IN
                    | CONTAINS_ALL
                    | CONTAINS_NONE
                    | CONTAINS_ANY
                    | pp.one_of("⊇ ∈ ∉")
            ).set_name("contain_operator"),
            2,
            pp.OpAssoc.LEFT,
            binary_array_comparison_op,
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
        (NOT_OP, 1, pp.OpAssoc.RIGHT, unary_op),
        (AND_OP, 2, pp.OpAssoc.LEFT, binary_multi_op),
        (OR_OP, 2, pp.OpAssoc.LEFT, binary_multi_op),
    ],
)

query_condition_expr = boolean_comparison_expr

# add $comment containing the original expression string
query_condition_expr_with_comment = pp.And([boolean_comparison_expr])
query_condition_expr_with_comment.add_parse_action(
    lambda s, l, t: t[0].__setitem__("$comment", s)
)

pp.autoname_elements()


def transform_query(query_string: str, include_comment: bool = False) -> Dict:
    r"""
    Parse a query string using boolean and arithmetic comparison operations,
    and convert it to a dict for the expression equivalent using MongoDB query
    expression structure. If 'include_comment' is set to True, the resulting
    query will include the original string as a `$comment` element in the
    generated query.

    Arithmetic comparison operators are (in order of precedence):
        search for
        <= >= < > ≤ ≥
        = == != ≠
        =~, like, not like
        ⊇ ∈ ∉, in, not in, contains, contains all, contains none, contains any

    Boolean operators are (in order of precedence):
        not
        and
        or

    '∧' and '∨' can be used interchangeably with 'and' and 'or'. Boolean operators are
    all of lower precedence than arithmetic comparison operators.

    '=' and '==' are equivalent, to accommodate variations in user expression dialects.

    '=~' performs regex search matching; use regex '^' or '$' anchors for matching
    leading or trailing expressions.

    'like' and 'not like' perform SQL-like wild card matching, using '%' to match
    any substring; the substring is assumed to be anchored at start and end of the string,
    unless it starts and/or ends with '%'. Use '%%' to match a literal '%' character.

    '⊇', '∈', '∉' correspond to 'contains all', 'in', and 'not in', and should be used
    on array fields, or when testing a scalar field for membership in a list.

    Array indexing can be done using 'field.0' form or 'field[0]' form.

    Embedded documents are accessed using '.' notation, as in 'field.embedded_doc_field'.

    All operator keywords are case-insensitive (i.e., 'LIKE' and 'like' are equivalent).

    Examples:
        a = 100 and b = 200
        {'a': 100, 'b': 200}

        a==100 and b>=200
        {'$and': [{'a': 100}, {'b': {'$gte': 200}}]}

        a==100 and not (b>=200 or c<200)
        {'$and': [{'a': 100}, {'$nor': [{'$or': [{'b': {'$gte': 200}}, {'c': {'$lt': 200}}]}]}]}

        name in ["Alice", "Bob"]
        {'name': {'$in': ['Alice', 'Bob']}}

    Also supported:
    - embedded and array references
        a.b > 1000
        {'a.b': {'$gt': 1000}}

        a.0 == "Alice"
        {'a.0': 'Alice'}

        a[0] < 100
        {'a.0': {'$lt': 100}}

    - chained inequalities
        100 < a < 200
        {'$and': [{'a': {'$gt': 100}}, {'a': {'$lt': 200}}]}

    - dates and datetimes
      (dates are in YYYY/MM/DD format, and may use '/' or '-' separators)
      (times may be HH:MM, HH:MM:SS, or HH:MM:SS.SSS format)
        1946-01-01 <= dob <= 1964-12-31
        {'$and': [
            {'dob': {'$gte': datetime.datetime(1946, 1, 1, 0, 0)}},
            {'dob': {'$lte': datetime.datetime(1964, 12, 31, 0, 0)}}
            ]
        }

        event.timestamp = 1969/07/20 10:56
        {'event.timestamp': datetime.datetime(1969, 7, 20, 10, 56)}

        y2k = 2000/01/01 00:00:00.000
        {'y2k': datetime.datetime(2000, 1, 1, 0, 0)}

    - `in` and `not in`
        name in ["Alice", "Bob"]
        {'name': {'$in': ['Alice', 'Bob']}}

        "Alice" in names
        {'names': {'$in': ['Alice']}}

        "Bob" not in names
        {'names': {'$nin': ['Bob']}}

    - `contains [any | all | none]`
        names contains any ["Alice", "Bob"]
        {'names': {'$in': ['Alice', 'Bob']}}

        names contains all ["Alice", "Bob"]
        {'names': {'$all': ['Alice', 'Bob']}}

        names contains none ["Alice", "Bob"]
        {'names': {'$nin': ['Alice', 'Bob']}}

    - LIKE, NOT LIKE, and regex matches
        a LIKE "ABC%"
        {'a': {'$regex': '^ABC'}}

        a LIKE "%ABC"
        {'a': {'$regex': 'ABC$'}}

        a LIKE "%AB%C"
        {'a': {'$regex': 'AB.*C$'}}

        a LIKE "%AB%"
        {'a': {'$regex': 'AB'}}

        a NOT LIKE "%AB%"
        {'$nor': [{'a': {'$regex': 'AB'}}]}

        a =~ "^ABC"
        {'a': {'$regex': '^ABC'}}

        a =~ "ABC$"
        {'a': {'$regex': 'ABC$'}}

        a =~ "ABC\d+"
        {'a': {'$regex': '^ABC\\d+'}}

    - SEARCH FOR keywords using text search indexes
        search for "birds"
        {'$text': {'$search': 'birds'}}

    - Unicode operators
        100 < a ≤ 200 and 300 > b ≥ 200 or c ≠ -1
        {'$or': [{'$and': [{'$and': [{'a': {'$gt': 100}}, {'a': {'$lte': 200}}]},
                           {'$and': [{'b': {'$lt': 300}}, {'b': {'$gte': 200}}]}]},
                 {'c': {'$ne': -1}}]}

        100 < a ≤ 200 ∧ 300 > b ≥ 200 ∨ c ≠ -1
        {'$or': [{'$and': [{'$and': [{'a': {'$gt': 100}}, {'a': {'$lte': 200}}]},
                           {'$and': [{'b': {'$lt': 300}}, {'b': {'$gte': 200}}]}]},
                 {'c': {'$ne': -1}}]}

        name ∈ ["Alice", "Bob"]
        {'name': {'$in': ['Alice', 'Bob']}}

        name ∉ ["Alice", "Bob"]
        {'name': {'$nin': ['Alice', 'Bob']}}

        names ⊇ ["Alice", "Bob"]
        {'names': {'$all': ['Alice', 'Bob']}}
    """
    transformer_expr = (
        query_condition_expr_with_comment
        if include_comment
        else boolean_comparison_expr
    )
    return transformer_expr.parse_string(query_string, parse_all=True)[0]


def main():
    from pprint import pprint

    for test in (
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

        # fields with embedded spaces
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
        names contains any ["Alice", "Bob"]
        names contains all ["Alice", "Bob"]
        names ⊇ ["Alice", "Bob"]
        names contains none ["Alice", "Bob"]
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
        search for "world"
        search for "hello" and a > 100
        """
        r"name =~ 'Al\d+'"
    ).splitlines():
        test = test.strip()
        if not test:
            continue

        print(test)

        if test.startswith("#"):
            continue

        try:
            transformed = transform_query(test)
        except pp.ParseBaseException as exc:
            print(exc.explain(depth=0))
        except Exception as exc:
            print(pp.ParseException.explain_exception(exc))
        else:
            pprint(transformed, indent=2, sort_dicts=False)
        print()


if __name__ == "__main__":
    import contextlib

    with contextlib.suppress(Exception):
        query_condition_expr.create_diagram(
            "mongodb_query_expression.html",
            vertical=3,
            show_results_names=True,
            show_groups=True
        )

    main()
