# romanNumerals.py
#
# Copyright (c) 2006, 2019, Paul McGuire
#

import pyparsing as pp


def roman_numeral_literal(numeral_string, value):
    return (
        pp.Literal(numeral_string)
        .set_parse_action(pp.replace_with(value))
        .leave_whitespace()
    )


one = roman_numeral_literal("I", 1)
four = roman_numeral_literal("IV", 4)
five = roman_numeral_literal("V", 5)
nine = roman_numeral_literal("IX", 9)
ten = roman_numeral_literal("X", 10)
forty = roman_numeral_literal("XL", 40)
fifty = roman_numeral_literal("L", 50)
ninety = roman_numeral_literal("XC", 90)
onehundred = roman_numeral_literal("C", 100)
fourhundred = roman_numeral_literal("CD", 400)
fivehundred = roman_numeral_literal("D", 500)
ninehundred = roman_numeral_literal("CM", 900)
onethousand = roman_numeral_literal("M", 1000)

# lenient parser - passes all legal Roman numerals but does not detect illegal
# numeral = (
#     onethousand
#     | ninehundred
#     | fivehundred
#     | fourhundred
#     | onehundred
#     | ninety
#     | fifty
#     | forty
#     | ten
#     | nine
#     | five
#     | four
#     | one
# )
#
# roman_numeral = numeral[1, ...].set_parse_action(sum)

# strict parser - rejects illegal Roman numerals
roman_numeral = (
    onethousand[...]
    + (ninehundred | fourhundred | fivehundred[0, 1] + onehundred[0, 3])[0, 1]
    + (ninety | forty | fifty[0, 1] + ten[0, 3])[0, 1]
    + (nine | four | five[0, 1] + one[0, 3])[0, 1]
).set_parse_action(sum)
pp.autoname_elements()


# unit tests
def make_roman_numeral(n):
    def add_digits(n, limit, c, s):
        while n >= limit:
            n -= limit
            s += c
        return n, s

    ret = ""
    n, ret = add_digits(n, 1000, "M", ret)
    n, ret = add_digits(n, 900, "CM", ret)
    n, ret = add_digits(n, 500, "D", ret)
    n, ret = add_digits(n, 400, "CD", ret)
    n, ret = add_digits(n, 100, "C", ret)
    n, ret = add_digits(n, 90, "XC", ret)
    n, ret = add_digits(n, 50, "L", ret)
    n, ret = add_digits(n, 40, "XL", ret)
    n, ret = add_digits(n, 10, "X", ret)
    n, ret = add_digits(n, 9, "IX", ret)
    n, ret = add_digits(n, 5, "V", ret)
    n, ret = add_digits(n, 4, "IV", ret)
    n, ret = add_digits(n, 1, "I", ret)
    return ret


def main():
    import contextlib

    with contextlib.suppress(Exception):
        # generate railroad diagram
        roman_numeral.create_diagram("roman_numerals_diagram.html")

    # make a string of all roman numerals from I to MMMMM
    tests = " ".join(make_roman_numeral(i) for i in range(1, 5000 + 1))

    # parse each roman numeral, and populate map for validation below
    roman_int_map = {}
    for expected, (t, s, e) in enumerate(roman_numeral.scan_string(tests), start=1):
        orig = tests[s:e]
        assert t[0] == expected, f"==> Incorrect result for {orig}: {t}"
        roman_int_map[orig] = t[0]

    def verify_value(s, tokens):
        expected_value = roman_int_map[s]
        if tokens[0] != expected_value:
            raise Exception(
                f"incorrect value for {s} ({tokens[0]}), expected {expected_value}"
            )

    success1, _ = roman_numeral.runTests(
        """\
        XVI
        XXXIX
        XIV
        XIX
        MCMLXXX
        MMVI
        MMMMM
        """,
        parse_all=True,
        post_parse=verify_value,
    )

    assert success1, "failed to parse one or more legal Roman numerals"

    print("\nRun failure tests")
    success2, _ = roman_numeral.runTests(
        """\
        # too many X's
        XXXX

        # X after XL
        XLX
        """,
        parse_all=True,
        failure_tests=True,
    )

    assert success2, "parsed one or more illegal Roman numerals"


if __name__ == "__main__":
    main()
