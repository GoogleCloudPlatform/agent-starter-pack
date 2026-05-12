# parsePythonValue.py
#
# Copyright, 2006, by Paul McGuire
#
import pyparsing as pp
from pyparsing import ParseResults, autoname_elements

convert_bool = lambda t: t[0] == "True"
convert_int = lambda toks: int(toks[0])
convert_real = lambda toks: float(toks[0])
convert_tuple = lambda toks: tuple(toks.as_list())
convert_set = lambda toks: set(toks.as_list())
convert_dict = lambda toks: dict(toks.as_list())
convert_list = lambda toks: [toks.as_list()]

# define punctuation as suppressed literals
lparen, rparen, lbrack, rbrack, lbrace, rbrace, colon, comma = pp.Suppress.using_each("()[]{}:,")

integer = pp.Regex(r"[+-]?\d+").set_name("integer").add_parse_action(convert_int)
real = pp.Regex(r"[+-]?\d+\.\d*([Ee][+-]?\d+)?").set_name("real").add_parse_action(convert_real)

# containers must be defined using a Forward, since they get parsed recursively
tuple_str = pp.Forward().set_name("tuple_expr")
list_str = pp.Forward().set_name("list_expr")
set_str = pp.Forward().set_name("set_expr")
dict_str = pp.Forward().set_name("dict_expr")

quoted_str = pp.quotedString().add_parse_action(lambda t: t[0][1:-1])
bool_literal = pp.oneOf("True False", as_keyword=True).add_parse_action(convert_bool)
none_literal = pp.Keyword("None").add_parse_action(pp.replace_with(None))

list_item = (
    real
    | integer
    | quoted_str
    | bool_literal
    | none_literal
    | pp.Group(list_str)
    | tuple_str
    | set_str
    | dict_str
).set_name("list_item")

# tuple must have a comma-separated list of 2 or more items, with optional
# trailing comma, or a single item with required trailing comma
tuple_str <<= (
    lparen + pp.Opt(
            pp.DelimitedList(list_item, min=2, allow_trailing_delim=True)
            | list_item + comma
            )
    + rparen
)
tuple_str.add_parse_action(convert_tuple)

set_str <<= (
    lbrace + pp.DelimitedList(list_item, allow_trailing_delim=True) + rbrace
)
set_str.add_parse_action(convert_set)

list_str <<= (
    lbrack + pp.Opt(pp.DelimitedList(list_item, allow_trailing_delim=True)) + rbrack
)
list_str.add_parse_action(convert_list, lambda t: t[0])

dict_entry = pp.Group(list_item + colon + list_item).set_name("dict_entry")
dict_str <<= (
    lbrace + pp.Opt(pp.DelimitedList(dict_entry, allow_trailing_delim=True)) + rbrace
)
dict_str.add_parse_action(convert_dict)

python_value = list_item

autoname_elements()

def main():
    from ast import literal_eval
    import contextlib

    with contextlib.suppress(Exception):
        list_item.create_diagram("parse_python_value.html")

    non_list_tests = """\
        # dict of str to int or dict
        { 'A':1, 'B':2, 'C': {'a': 1.2, 'b': 3.4} }

        # dict of str or tuple keys
        {'A':1, 'B':2, (1, 2): {'a', 1.2, 'b', 3.4}}

        # empty dict
        {}

        # set of mixed types
        {1, 2, 11, "blah"}

        # empty set
        {()}

        # a tuple of mixed types
        ('A', 100, -2.71828, {'b':99})

        # a tuple with just one value
        ('A',)

        # empty tuple
        ()

        # float
        3.14159

        # int
        42

        # float in scientific notation
        6.02E23
        6.02e+023
        1.0e-7

        # quoted string
        'a quoted string'
    """

    list_tests = """\
        # list of mixed types
        ['a', 100, ('A', [101,102]), 3.14, [ +2.718, 'xyzzy', -1.414] ]

        # list of dicts
        [{0: [2], 1: []}, {0: [], 1: [], 2: []}, {0: [1, 2]}]

        # empty list
        []
    """

    def validate_parsed_value(test_str: str, result: ParseResults) -> bool:
        python_value = literal_eval(test_str)
        return python_value == result[0]

    def validate_parsed_list(test_str: str, result: ParseResults) -> bool:
        python_value = literal_eval(test_str)
        return python_value == result.as_list()[0]

    success1, report_1 = list_item.run_tests(non_list_tests)
    success1 = success1 and all(validate_parsed_value(*rpt) for rpt in report_1)

    success2, report_2 = list_item.run_tests(list_tests)
    success2 = success2 and all(validate_parsed_list(*rpt) for rpt in report_2)

    assert success1 and success2


if __name__ == "__main__":
    main()
