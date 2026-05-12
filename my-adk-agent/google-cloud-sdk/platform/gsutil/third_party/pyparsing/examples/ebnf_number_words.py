#
# ebnftest_number_parser.py
#
#     BNF from number_parser.py:
#
#     optional_and ::= ["and" | "-"]
#     optional_dash ::= ["-"]
#     units ::= "one" | "two" | "three" | ... | "nine"
#     tens ::= "twenty" | "thirty" | ... | "ninety"
#     one_to_99 ::= units | ten | teens | (tens [optional_dash units])
#     ten ::= "ten"
#     teens ::= "eleven" | "twelve" | ... | "nineteen"
#     hundreds ::= (units | teens_only | tens optional_dash units) "hundred"
#     thousands ::= one_to_99 "thousand"
#
#     # number from 1-999,999
#     number ::= [thousands [optional_and]] [hundreds[optional_and]] one_to_99
#                | [thousands [optional_and]] hundreds
#                | thousands
#

import ebnf

grammar = """
    (*
    EBNF for number_words.py
    *)
    number = [thousands, [and]], [hundreds, [and]], [one_to_99];
    thousands = one_to_99, "thousand";
    hundreds_mult = units | teens | multiples_of_ten, ["-"], units; 
    hundreds = hundreds_mult, "hundred";
    teens = 
        "eleven"
        | "twelve"
        | "thirteen"
        | "fourteen"
        | "fifteen"
        | "sixteen"
        | "seventeen"
        | "eighteen"
        | "nineteen"
    ;
    one_to_99 = units | teens | ten | multiples_of_ten, [["-"], units];
    ten = "ten";
    multiples_of_ten = "twenty" | "thirty" | "forty" | "fifty" | "sixty" | "seventy" | "eighty" | "ninety";
    units = "one" | "two" | "three" | "four" | "five" | "six" | "seven" | "eight" | "nine";
    and = "and" | "-";
    """

parsers = ebnf.parse(grammar)
number_parser = parsers["number"]

try:
    number_parser.create_diagram("ebnf_number_parser_diagram.html")
except Exception as e:
    print("Failed to create diagram for EBNF-generated number parser"
          f" - {type(e).__name__}: {e}")

number_parser.run_tests(
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
    twenty five hundred and one
    ninety nine thousand nine hundred and ninety nine

    # invalid
    twenty hundred
    """,
    full_dump=False
)