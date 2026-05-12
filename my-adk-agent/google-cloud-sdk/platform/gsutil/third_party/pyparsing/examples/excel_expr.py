# excelExpr.py
#
# Copyright 2010, Paul McGuire
#
# A partial implementation of a parser of Excel formula expressions.
#
import pyparsing as pp
ppc = pp.common

pp.ParserElement.enable_packrat()

EQ, LPAR, RPAR, COLON, COMMA = pp.Suppress.using_each("=():,")
EXCL, DOLLAR = pp.Literal.using_each("!$")
sheet_ref = pp.Word(pp.alphas, pp.alphanums) | pp.QuotedString("'", escQuote="''")
col_ref = pp.Opt(DOLLAR) + pp.Word(pp.alphas, max=2)
row_ref = pp.Opt(DOLLAR) + pp.Word(pp.nums)
cell_ref = pp.Combine(
    pp.Group(pp.Opt(sheet_ref + EXCL)("sheet") + col_ref("col") + row_ref("row"))
)

cell_range = (
        pp.Group(cell_ref("start") + COLON + cell_ref("end"))("range")
        | cell_ref
        | pp.Word(pp.alphas, pp.alphanums)
)

expr = pp.Forward()

COMPARISON_OP = pp.one_of("< = > >= <= != <>")
cond_expr = expr + COMPARISON_OP + expr

if_func = (
    pp.CaselessKeyword("if")
    - LPAR
    + pp.Group(cond_expr)("condition")
    + COMMA
    + pp.Group(expr)("if_true")
    + COMMA
    + pp.Group(expr)("if_false")
    + RPAR
)


def stat_function(name):
    return pp.Group(pp.CaselessKeyword(name) + pp.Group(LPAR + pp.DelimitedList(expr) + RPAR))


sum_func = stat_function("sum")
min_func = stat_function("min")
max_func = stat_function("max")
ave_func = stat_function("ave")
func_call = if_func | sum_func | min_func | max_func | ave_func

mult_op = pp.one_of("* /")
add_op = pp.one_of("+ -")
numeric_literal = ppc.number
operand = numeric_literal | func_call | cell_range | cell_ref
arith_expr = pp.infix_notation(
    operand,
    [
        (mult_op, 2, pp.OpAssoc.LEFT),
        (add_op, 2, pp.OpAssoc.LEFT),
    ],
)

text_operand = pp.dbl_quoted_string | cell_ref
text_expr = pp.infix_notation(
    text_operand,
    [
        ("&", 2, pp.OpAssoc.LEFT),
    ],
)

expr <<= arith_expr | text_expr


def main():
    success, report = (EQ + expr).run_tests(
        """\
        =3*A7+5
        =3*Sheet1!$A$7+5
        =3*'Sheet 1'!$A$7+5
        =3*'O''Reilly''s sheet'!$A$7+5
        =if(Sum(A1:A25)>42,Min(B1:B25),if(Sum(C1:C25)>3.14, (Min(C1:C25)+3)*18,Max(B1:B25)))
        =sum(a1:a25,10,min(b1,c2,d3))
        =if("T"&a2="TTime", "Ready", "Not ready")
    """
    )
    assert success


if __name__ == '__main__':
    main()
