"""Defines a recursive parser for parsing mathematical expressions in infix notation.

Supports binary, unary, and variadic operations. These can also be customized
in the InfixExpressionParser class variables. Utilizes some regex to improve its
performance.

Examples of parsing:

The expression "f_1 + f_2 - 1e-3" is parsed into [['f_1', '+', 'f_2', '-', 0.001]]

The expression "Max(Ln(x) + Lb(Abs(y)), Ceil(Sqrt(garlic) * 3), (potato ** 2) / 4, Abs(cosmic) + 10)"
is parsed into
[['Max', [[['Ln', ['x']], '+', ['Lb', [['Abs', ['y']]]]], ['Ceil', [[['Sqrt', ['garlic']], '*', 3]]], [['potato', '**', 2], '/', 4], [['Abs', ['cosmic']], '+', 10]]]]
"""

from pyparsing import (
    Forward,
    Group,
    Literal,
    ParserElement,
    Suppress,
    DelimitedList,
    infix_notation,
    one_of,
    OpAssoc,
    pyparsing_common,
    ParseResults,
    Regex,
)

# Enable Packrat for better performance in recursive parsing
ParserElement.enablePackrat(None)


class InfixExpressionParser:
    """A class for defining an infix notation parsers."""

    # Supported infix binary operators, i.e., '1+1'. The key is the notation of the operator in infix format,
    # and the value the notation in parsed format.
    BINARY_OPERATORS: dict[str, str] = {
        "+": "Add",
        "-": "Subtract",
        "*": "Multiply",
        "/": "Divide",
        "**": "Power",
    }

    # Supported infix unary operators, i.e., 'Cos(90)'. The key is the notation of the operator in infix format,
    # and the value the notation in parsed format.
    UNARY_OPERATORS: dict[str, str] = {
        "Cos": "Cos",
        "Sin": "Sin",
        "Tan": "Tan",
        "Exp": "Exp",
        "Ln": "Ln",
        "Lb": "Lb",
        "Lg": "Lg",
        "LogOnePlus": "LogOnePlus",
        "Sqrt": "Sqrt",
        "Square": "Square",
        "Abs": "Abs",
        "Ceil": "Ceil",
        "Floor": "Floor",
        "Arccos": "Arccos",
        "Arccosh": "Arccosh",
        "Arcsin": "Arcsin",
        "Arcsinh": "Arcsinh",
        "Arctan": "Arctan",
        "Arctanh": "Arctanh",
        "Cosh": "Cosh",
        "Sinh": "Sinh",
        "Tanh": "Tanh",
        "Rational": "Rational",
    }

    # Supported infix variadic operators (operators that take one or more comma separated arguments),
    # i.e., 'Max(1,2, Cos(3)). The key is the notation of the operator in infix format,
    # and the value the notation in parsed format.
    VARIADIC_OPERATORS: dict[str, str] = {"Max": "Max"}

    def __init__(self):
        """A parser for infix notation, e.g., the human readable way of notating mathematical expressions.

        The parser can parse infix notation stored in a string. For instance,
        "Cos(2 + f_1) - 7.2 + Max(f_2, -f_3)" is parsed to the list:
        ['Cos', [[2, '+', 'f_1']]], '-', 7.2, '+', ['Max', ['f_2', ['-', 'f_3']].

        """
        # Scope limiters
        lparen = Suppress("(")
        rparen = Suppress(")")

        # Define keywords (Note that binary operators must be defined manually)
        symbols_variadic = set(InfixExpressionParser.VARIADIC_OPERATORS)
        symbols_unary = set(InfixExpressionParser.UNARY_OPERATORS)

        # Define binary operation symbols (this is the manual part)
        # If new binary operators are to be added, they must be defined here.
        signop = one_of("+ -")
        multop = one_of("* /")
        plusop = one_of("+ -")
        expop = Literal("**")

        # Dynamically create Keyword objects for variadic functions
        variadic_pattern = r"\b(" + f"{'|'.join([*symbols_variadic])}" + r")\b"
        variadic_func_names = Regex(variadic_pattern).set_name("variadic function")

        # Dynamically create Keyword objects for unary functions
        unary_pattern = r"\b(" + f"{'|'.join([*symbols_unary])}" + r")\b"
        unary_func_names = Regex(unary_pattern).set_name("unary function")

        # Define operands
        # Integers
        integer = pyparsing_common.integer.set_name("integer")

        # Scientific notation
        scientific = pyparsing_common.sci_real.set_name("float")

        # Complete regex pattern with exclusions and identifier pattern
        exclude = f"{'|'.join([*symbols_variadic, *symbols_unary])}"
        pattern = r"(?!\b(" + exclude + r")\b)(\b[a-zA-Z_][a-zA-Z0-9_]*\b)"
        variable = Regex(pattern).set_name("variable")

        operands = variable | scientific | integer

        # Forward declarations of variadic and unary function calls
        variadic_call = Forward()
        unary_call = Forward()

        # The parsed expressions are assumed to follow a standard infix syntax. The operands
        # of the infix syntax can be either the literal 'operands' defined above (these are singletons),
        # or either a variadic function call or a unary function call. These latter two will be
        # defined to be recursive.
        #
        # Note that the order of the operators in the second argument (the list) of infix_notation matters!
        # The operation with the highest precedence is listed first.
        infix_expn = infix_notation(
            operands | variadic_call | unary_call,
            [
                (expop, 2, OpAssoc.LEFT),
                (signop, 1, OpAssoc.RIGHT),
                (multop, 2, OpAssoc.LEFT),
                (plusop, 2, OpAssoc.LEFT),
            ],
        )

        # These are recursive definitions of the forward declarations of the two type of function calls.
        # In essence, the recursion continues until a singleton operand is encountered.
        variadic_call <<= Group(
            variadic_func_names + lparen + Group(DelimitedList(infix_expn)) + rparen
        )
        unary_call <<= Group(unary_func_names + lparen + Group(infix_expn) + rparen)

        self.expn = infix_expn

    def parse(self, str_expr: str) -> ParseResults:
        """Parse a string expression into a list."""
        return self.expn.parse_string(str_expr, parse_all=True)


if __name__ == "__main__":
    infix_parser = InfixExpressionParser()

    expressions = [
        "f_1 + f_2 - 1e-3",
        "(x_1 + (x_2 * (c_1 + 3.3) / (x_3 - 2))) * 1.5",
        "Max(Ln(x) + Lb(Abs(y)), Ceil(Sqrt(garlic) * 3), (potato ** 2) / 4, Abs(cosmic) + 10)",
        "Max(Sqrt(Abs(x) + y ** 2), Lg(Max(cosmic, potato)), Ceil(Tanh(x) + Arctan(garlic)))",
        "((garlic**3 - 2**Lb(cosmic)) + Ln(x**2 + 1)) / (Sqrt(Square(y) + LogOnePlus(potato + 3.1)))",
    ]

    infix_parser.expn.run_tests(expressions)
