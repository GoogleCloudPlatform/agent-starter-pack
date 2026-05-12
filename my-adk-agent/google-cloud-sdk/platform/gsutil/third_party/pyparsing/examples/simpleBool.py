#
# simpleBool.py
#
# Example of defining a boolean logic parser using
# the operatorGrammar helper method in pyparsing.
#
# In this example, parse actions associated with each
# operator expression will "compile" the expression
# into BoolXXX class instances, which can then
# later be evaluated for their boolean value.
#
# Copyright 2006, by Paul McGuire
# Updated 2013-Sep-14 - improved Python 2/3 cross-compatibility
# Updated 2021-Sep-27 - removed Py2 compat; added type annotations
#
from typing import Callable, Iterable

from pyparsing import infixNotation, opAssoc, Keyword, Word, alphas, ParserElement

ParserElement.enablePackrat()


# define classes to be built at parse time, as each matching
# expression type is parsed
class BoolOperand:
    def __init__(self, t):
        self.label = t[0]
        self.value = eval(t[0])

    def __bool__(self) -> bool:
        return self.value

    def __str__(self) -> str:
        return self.label

    __repr__ = __str__


class BoolNot:
    def __init__(self, t):
        self.arg = t[0][1]

    def __bool__(self) -> bool:
        v = bool(self.arg)
        return not v

    def __str__(self) -> str:
        return "~" + str(self.arg)

    __repr__ = __str__


class BoolBinOp:
    repr_symbol: str = ""
    eval_fn: Callable[
        [Iterable[bool]], bool
    ] = lambda _: False

    def __init__(self, t):
        self.args = t[0][0::2]

    def __str__(self) -> str:
        sep = f" {self.repr_symbol} "
        return f"({sep.join(map(str, self.args))})"

    def __bool__(self) -> bool:
        return self.eval_fn(bool(a) for a in self.args)


class BoolAnd(BoolBinOp):
    repr_symbol = "&"
    eval_fn = all


class BoolOr(BoolBinOp):
    repr_symbol = "|"
    eval_fn = any


# define keywords and simple infix notation grammar for boolean
# expressions
TRUE = Keyword("True")
FALSE = Keyword("False")
NOT = Keyword("not")
AND = Keyword("and")
OR = Keyword("or")
boolOperand = TRUE | FALSE | Word(alphas, max=1)
boolOperand.setParseAction(BoolOperand).setName("bool_operand")

# define expression, based on expression operand and
# list of operations in precedence order
boolExpr = infixNotation(
    boolOperand,
    [
        (NOT, 1, opAssoc.RIGHT, BoolNot),
        (AND, 2, opAssoc.LEFT, BoolAnd),
        (OR, 2, opAssoc.LEFT, BoolOr),
    ],
).setName("boolean_expression")


if __name__ == "__main__":
    p = True
    q = False
    r = True
    tests = [
        ("p", True),
        ("q", False),
        ("p and q", False),
        ("p and not q", True),
        ("not not p", True),
        ("not(p and q)", True),
        ("q or not p and r", False),
        ("q or not p or not r", False),
        ("q or not (p and r)", False),
        ("p or q or r", True),
        ("p or q or r and False", True),
        ("(p or q or r) and False", False),
    ]

    print("p =", p)
    print("q =", q)
    print("r =", r)
    print()
    for test_string, expected in tests:
        res = boolExpr.parseString(test_string)[0]
        success = "PASS" if bool(res) == expected else "FAIL"
        print(test_string, "\n", res, "=", bool(res), "\n", success, "\n")
