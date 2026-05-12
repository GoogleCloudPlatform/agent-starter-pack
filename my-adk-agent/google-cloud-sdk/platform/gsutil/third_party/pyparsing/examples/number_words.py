# number_words.py
#
# Copyright 2020, Paul McGuire
#
# Parser/evaluator for expressions of numbers as written out in words:
#  - one
#  - seven
#  - twelve
#  - twenty six
#  - forty-two
#  - one hundred and seven
#
#
#  BNF:
#    optional_and ::= ["and" | "-"]
#    optional_dash ::= ["-"]
#    units ::= "one" | "two" | "three" | ... | "nine"
#    ten ::= "ten"
#    tens ::= "twenty" | "thirty" | ... | "ninety"
#    one_to_99 ::= units | ten | teens | (tens [optional_dash units])
#    teens ::= "eleven" | "twelve" | ... | "nineteen"
#    hundreds ::= (units | teens | tens optional_dash units) "hundred"
#    thousands ::= one_to_99 "thousand"
#
#    # number from 1-999,999
#    number ::= [thousands [optional_and]] [hundreds[optional_and]] one_to_99
#               | [thousands [optional_and]] hundreds
#               | thousands
#

import pyparsing as pp
from operator import mul


def define_numeric_word_range(
    names: str, from_: int, to_: int = None, step: int = 1
) -> pp.MatchFirst:
    """
    Compose a MatchFirst of CaselessKeywords, given their names and values,
    which when parsed, are converted to their value
    """

    def define_numeric_word(nm: str, val: int):
        return pp.CaselessKeyword(nm).add_parse_action(lambda: val)

    names = names.split()
    if to_ is None:
        to_ = from_
    values = range(from_, to_ + 1, step)
    ret = pp.MatchFirst(
        define_numeric_word(name, value) for name, value in zip(names, values)
    )

    if len(names) == 1:
        ret.set_name(names[0])
    else:
        ret.set_name(f"{names[0]}-{names[-1]}")

    return ret


def multiply(t):
    """
    Parse action for hundreds and thousands.
    """
    return mul(*t)


opt_dash = pp.Opt(pp.Suppress("-")).set_name("'-'")
opt_and = pp.Opt((pp.CaselessKeyword("and") | "-").suppress()).set_name("'and/-'")

units = define_numeric_word_range("one two three four five six seven eight nine", 1, 9)
teens = define_numeric_word_range(
    "eleven twelve thirteen fourteen fifteen sixteen seventeen eighteen nineteen",
    11,
    19,
)
ten = define_numeric_word_range("ten", 10)

tens = define_numeric_word_range(
    "twenty thirty forty fifty sixty seventy eighty ninety", 20, 90, 10
)

hundred = define_numeric_word_range("hundred", 100)
thousand = define_numeric_word_range("thousand", 1000)

one_to_99_except_tens = (units | teens | (tens + opt_dash + units)).set_name("1-99 except tens")
one_to_99_except_tens.add_parse_action(sum)
one_to_99 = (one_to_99_except_tens | ten | tens).set_name("1-99")
one_to_99.add_parse_action(sum)

hundreds = one_to_99_except_tens + hundred
hundreds.set_name("100s")

one_to_999 = (
    (pp.Opt(hundreds + opt_and) + one_to_99 | hundreds).add_parse_action(sum)
).set_name("1-999")

thousands = one_to_999 + thousand
thousands.set_name("1000s")

# for hundreds and thousands, must scale up (multiply) accordingly
hundreds.add_parse_action(multiply)
thousands.add_parse_action(multiply)

numeric_expression = (
    pp.Opt(thousands + opt_and) + pp.Opt(hundreds + opt_and) + one_to_99
    | pp.Opt(thousands + opt_and) + hundreds
    | thousands
).set_name("numeric_words")

# sum all sub-results into total
numeric_expression.add_parse_action(sum)


if __name__ == "__main__":
    import contextlib

    with contextlib.suppress(Exception):
        # create railroad diagram
        numeric_expression.create_diagram("number_words_diagram.html", vertical=5)

    numeric_expression.run_tests(
        """
        one
        seven
        twelve
        twenty six
        forty-two
        two hundred
        twelve hundred
        one hundred and eleven
        seven thousand and six
        twenty five hundred
        twenty five hundred and one
        ninety nine thousand nine hundred and ninety nine
        nine hundred thousand nine hundred and ninety nine
        nine hundred and ninety nine thousand nine hundred and ninety nine
        nineteen hundred thousand nineteen hundred and ninety nine
        
        # invalid
        twenty hundred
        """,
        postParse=lambda _, s: "{:,}".format(s[0]),
    )
