# rangeCheck.py
#
#   A sample program showing how parse actions can convert parsed
# strings into a data type or object, and to validate the parsed value.
#
# Updated to use new addCondition method and expr() copy.
#
# Copyright 2011,2015 Paul T. McGuire
#

import pyparsing as pp
from datetime import date
from typing import Any


def ranged_value(
        expr: pp.ParserElement,
        min_val: Any = None,
        max_val: Any = None,
        label: str = ""
) -> pp.ParserElement:

    # have to specify at least one range boundary
    if (min_val, max_val) == (None, None):
        raise ValueError("min_val or max_val must be specified")

    expr_label = label or "value"

    # set range testing function and error message depending on
    # whether either or both min and max values are given
    in_range_condition = {
        (False, True): lambda s, l, t: t[0] <= max_val,
        (True, False): lambda s, l, t: min_val <= t[0],
        (True, True): lambda s, l, t: min_val <= t[0] <= max_val,
    }[min_val is not None, max_val is not None]

    out_of_range_message = {
        (False, True): f"{expr_label} is greater than {max_val}",
        (True, False): f"{expr_label} is less than {min_val}",
        (True, True): f"{expr_label} is not in the range ({min_val} to {max_val})",
    }[min_val is not None, max_val is not None]

    ret = expr().add_condition(in_range_condition, message=out_of_range_message)

    if label:
        ret.set_name(label)

    return ret


# define the expressions for a date of the form YYYY/MM/DD or YYYY/MM (assumes YYYY/MM/01)
integer = pp.Word(pp.nums).set_name("integer")
integer.set_parse_action(lambda t: int(t[0]))

month = ranged_value(integer, 1, 12, "month")
day = ranged_value(integer, 1, 31, "day")
year = ranged_value(integer, 2000, None, "year")

SLASH = pp.Suppress("/")
date_expr = year("year") + SLASH + month("month") + pp.Opt(SLASH + day("day"))
date_expr.set_name("date")

# convert date fields to datetime (also validates dates as truly valid dates)
date_expr.set_parse_action(lambda t: date(t.year, t.month, t.day or 1))

# add range checking on dates
min_date = date(2002, 1, 1)
max_date = date.today()
range_checked_date_expr = ranged_value(date_expr, min_date, max_date, "date")

range_checked_date_expr.create_diagram("range_check.html")

# tests of valid dates
success_valid_tests, _ = range_checked_date_expr.run_tests(
    """
    # valid date
    2011/5/8
    
    # leap day
    2004/2/29

    # default day of month to 1
    2004/2
    """
)

# tests of invalid dates
success_invalid_tests, _ = range_checked_date_expr.run_tests(
    """
    # all values are in range, but date is too early
    2001/1/1

    # not a leap day
    2005/2/29

    # year number is < 2000
    1999/12/31

    # bad year field
    XXXX/1/1

    # bad month field
    2010/XX/1

    # bad day field
    2010/11/XX
    """,
    failure_tests=True
)

assert (success_valid_tests and success_invalid_tests)
