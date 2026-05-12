#
# cpp_enum_parser.py
#
# Posted by Mark Tolonen on comp.lang.python in August, 2009,
# Used with permission.
#
# Parser that scans through C or C++ code for enum definitions, and
# generates corresponding Python constant definitions.
#
#

import pyparsing as pp

# sample string with enums and other stuff
sample = """
    stuff before
    enum hello {
        Zero,
        One,
        Two,
        Three,
        Five=5,
        Six,
        Ten=10
        };
    in the middle
    enum blah
        {
        alpha,
        beta,
        gamma = 10 ,
        zeta = 50
        };
    at the end
    """

# syntax we don't want to see in the final parse tree
LBRACE, RBRACE, EQ, COMMA = pp.Suppress.using_each("{}=,")
_enum = pp.Suppress("enum")
identifier = pp.Word(pp.alphas + "_", pp.alphanums + "_")
integer = pp.Word(pp.nums)
enumValue = pp.Group(identifier("name") + pp.Optional(EQ + integer("value")))
enumList = pp.Group(enumValue + (COMMA + enumValue)[...])
enum = _enum + identifier("enum") + LBRACE + enumList("names") + RBRACE

# find instances of enums ignoring other syntax
for item, start, stop in enum.scan_string(sample):
    idx = 0
    for entry in item.names:
        if entry.value != "":
            idx = int(entry.value)
        print(f"{item.enum.upper()}_{entry.name.upper()} = {idx}")
        idx += 1
