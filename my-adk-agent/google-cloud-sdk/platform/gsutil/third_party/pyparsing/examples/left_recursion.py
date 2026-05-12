#
# left_recursion.py
#
# Example code illustrating use of left-recursion in Pyparsing.
#
import pyparsing as pp

# comment out this line to see the effects without LR parsing enabled
pp.ParserElement.enableLeftRecursion()

item_list = pp.Forward()

# a common left-recursion definition
# define a list of items as 'list + item | item'
# BNF:
#   item_list := item_list item | item
#   item := word of alphas
item = pp.Word(pp.alphas)
item_list <<= item_list + item | item

item_list.runTests(
    """\
    To parse or not to parse that is the question
    """
)

# Define a parser for an expression that can be an identifier, a quoted string, or a
# function call that starts with an expression
# BNF:
#   expr := function_call | name | string | '(' expr ')'
#   function_call := expr '(' expr,... ')'
#   name := Python identifier
#   string := a quoted string
# from https://stackoverflow.com/questions/32809389/parse-python-code-using-pyparsing/32822575#32822575

LPAR, RPAR = map(pp.Suppress, "()")
expr = pp.Forward()
string = pp.quotedString
function_call = expr + pp.Group(LPAR + pp.Optional(pp.delimitedList(expr)) + RPAR)
name = pp.Word(pp.alphas + "_", pp.alphanums + "_")
# left recursion - call starts with an expr
expr <<= function_call | string | name | pp.Group(LPAR + expr + RPAR)

expr.runTests(
    """\
    print("Hello, World!")
    (lookup_function("fprintf"))(stderr, "Hello, World!")
    """,
    fullDump=False,
)
