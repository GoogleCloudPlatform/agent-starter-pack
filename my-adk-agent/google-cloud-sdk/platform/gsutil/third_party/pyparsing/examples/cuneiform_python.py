#
# cuneiform_python.py
#
# Example showing how to create a custom Unicode set for parsing
#
# Copyright Paul McGuire, 2021
#
from typing import List, Tuple
import pyparsing as pp


class Cuneiform(pp.unicode_set):
    """Unicode set for Cuneiform Character Range"""

    _ranges: List[Tuple[int, ...]] = [
        (0x10380, 0x103d5),
        (0x12000, 0x123FF),
        (0x12400, 0x1247F),
    ]


# list out all valid identifier characters
# print(Cuneiform.identchars)


"""
Simple Cuneiform Python language transformer

Define Cuneiform "words"
    print: 𒄑𒉿𒅔𒋫
    hello: 𒀄𒂖𒆷𒁎
    world: 𒍟𒁎𒉿𒆷𒀳
    def: 𒁴𒈫
"""

# uncomment to show parse-time debugging
# pp.enable_diag(pp.Diagnostics.enable_debug_on_named_expressions)

# define a MINIMAL Python parser
LPAR, RPAR, COLON, EQ = map(pp.Suppress, "():=")
def_ = pp.Keyword("𒁴𒈫", ident_chars=Cuneiform.identbodychars).set_name("def")
any_keyword = def_
ident = (~any_keyword) + pp.Word(
    Cuneiform.identchars, Cuneiform.identbodychars, asKeyword=True
)
str_expr = pp.infix_notation(
    pp.QuotedString('"') | pp.common.integer,
    [
        ("*", 2, pp.OpAssoc.LEFT),
        ("+", 2, pp.OpAssoc.LEFT),
    ],
)

rvalue = pp.Forward()
fn_call = (ident + pp.Group(LPAR + pp.Optional(rvalue) + RPAR)).set_name("fn_call")

rvalue <<= fn_call | ident | str_expr | pp.common.number
assignment_stmt = ident + EQ + rvalue

stmt = pp.Group(fn_call | assignment_stmt).set_name("stmt")

fn_def = pp.Group(
    def_ + ident + pp.Group(LPAR + pp.Optional(rvalue) + RPAR) + COLON
).set_name("fn_def")
fn_body = pp.IndentedBlock(stmt).set_name("fn_body")
fn_expr = pp.Group(fn_def + pp.Group(fn_body))

script = fn_expr[...] + stmt[...]


# parse some Python written in Cuneiform
cuneiform_hello_world = r"""
𒁴𒈫 𒀄𒂖𒆷𒁎():
    𒀁 = "𒀄𒂖𒆷𒁎, 𒍟𒁎𒉿𒆷𒀳!\n" * 3
    𒄑𒉿𒅔𒋫(𒀁)

𒀄𒂖𒆷𒁎()"""
script.parseString(cuneiform_hello_world).pprint(width=40)


# use transform_string to convert keywords and builtins to runnable Python
names_map = {
    "𒄑𒉿𒅔𒋫": "print",
}
ident.add_parse_action(lambda t: names_map.get(t[0], t[0]))
def_.add_parse_action(lambda: "def")

print("\nconvert Cuneiform Python to executable Python")
transformed = (
    # always put ident last
    (def_ | ident)
    .ignore(pp.quoted_string)
    .transform_string(cuneiform_hello_world)
    .strip()
)
print(
    "=================\n"
    + cuneiform_hello_world.strip()
    + "\n=================\n"
    + transformed
    + "\n=================\n"
)
print("# run transformed Python")
exec(transformed)
