#
# one_to_ninety_nine.py
#
# Copyright 2021, Paul McGuire
#
# Parser/evaluator for expressions of numbers as written out in words:
#  - one
#  - seven
#  - twelve
#  - twenty six
#  - forty-two
#
#  BNF:
#     units ::= one | two | three | ... | nine
#     teens ::= ten | eleven | twelve | ... | nineteen
#     tens ::= twenty | thirty | ... | ninety
#     one_to_99 ::= units | teens | (tens [["-"] units])
#
import pyparsing as pp


def define_numeric_word_range(
    names: str, from_: int, to_: int, step: int = 1
) -> pp.MatchFirst:
    """
    Compose a MatchFirst of CaselessKeywords, given their names and values,
    which when parsed, are converted to their value
    """

    def define_numeric_word(nm: str, val: int):
        return pp.CaselessKeyword(nm).add_parse_action(lambda: val)

    names = names.split()
    values = range(from_, to_ + 1, step)
    return pp.MatchFirst(
        define_numeric_word(name, value) for name, value in zip(names, values)
    )


units = define_numeric_word_range(
    "one two three four five six seven eight nine", 1, 9
).set_name("units")
teens = define_numeric_word_range(
    "ten eleven twelve thirteen fourteen fifteen sixteen seventeen eighteen nineteen",
    10,
    19,
).set_name("teens")
tens = define_numeric_word_range(
    "twenty thirty forty fifty sixty seventy eighty ninety", 20, 90, step=10
).set_name("tens")

opt_dash = pp.Opt(pp.Suppress("-"))
twenty_to_99 = tens + pp.Opt(opt_dash + units)

one_to_99 = (units | teens | twenty_to_99).set_name("1-99")

# for expressions that parse multiple values, add them up
one_to_99.add_parse_action(sum)

numeric_expression = one_to_99

if __name__ == "__main__":
    numeric_expression.run_tests(
        """
        one
        seven
        twelve
        twenty six
        forty-two
        """
    )

    # create railroad diagram
    numeric_expression.create_diagram("one_to_99_diagram.html", vertical=5)
