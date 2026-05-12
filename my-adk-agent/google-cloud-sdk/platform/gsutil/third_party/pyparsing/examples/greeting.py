# greeting.py
#
# Demonstration of the pyparsing module, on the prototypical "Hello, World!"
# example
#
# Copyright 2003, 2019 by Paul McGuire
#
import pyparsing as pp

# define grammar
greet = pp.Word(pp.alphas) + "," + pp.Word(pp.alphas) + pp.one_of("! ? .")

# input string
hello = "Hello, World!"

# parse input string
print(hello, "->", greet.parse_string(hello))

# parse a bunch of input strings
greet.run_tests(
    """\
    Hello, World!
    Ahoy, Matey!
    Howdy, Pardner!
    Morning, Neighbor!
    """
)
