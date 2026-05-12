#
# decaf_parser.py
#
# Rudimentary parser for decaf language, used in Stanford University CS143
# (https://web.stanford.edu/class/archive/cs/cs143/cs143.1128/handouts/030%20Decaf%20Specification.pdf)
#
# To convert this parser into one that gives more of an AST, change all the Group wrappers to add parse
# actions that will result in ASTNode classes, or statement-specific subclasses.
#
# Copyright 2018, Paul McGuire
#
# fmt: off
"""
    Program ::= Decl+
    Decl ::= VariableDecl | FunctionDecl  | ClassDecl | InterfaceDecl
    VariableDecl ::= Variable ;
    Variable ::= Type ident
    Type ::= int | double | bool | string | ident | Type []
    FunctionDecl ::= Type ident ( Formals ) StmtBlock | void ident ( Formals ) StmtBlock
    Formals ::= Variable+, |  e
    ClassDecl ::= class ident <extends ident>  <implements ident + ,>  { Field* }
    Field ::= VariableDecl | FunctionDecl
    InterfaceDecl ::= interface ident { Prototype* }
    Prototype ::= Type ident ( Formals ) ; | void ident ( Formals ) ;
    StmtBlock ::= { VariableDecl*  Stmt* }
    Stmt ::=  <Expr> ; | IfStmt  | WhileStmt |  ForStmt | BreakStmt   | ReturnStmt  | PrintStmt  | StmtBlock
    IfStmt ::= if ( Expr ) Stmt <else Stmt>
    WhileStmt ::= while ( Expr ) Stmt
    ForStmt ::= for ( <Expr> ; Expr ; <Expr> ) Stmt
    ReturnStmt ::= return <Expr> ;
    BreakStmt ::= break ;
    PrintStmt ::= Print ( Expr+, ) ;
    Expr ::= LValue = Expr | Constant | LValue | this | Call
            | ( Expr )
            | Expr + Expr | Expr - Expr | Expr * Expr | Expr / Expr |  Expr % Expr | - Expr
            | Expr < Expr | Expr <= Expr | Expr > Expr | Expr >= Expr | Expr == Expr | Expr != Expr
            | Expr && Expr | Expr || Expr | ! Expr
            | ReadInteger ( ) | ReadLine ( ) | new ident | NewArray ( Expr , Typev)
    LValue ::= ident |  Expr  . ident | Expr [ Expr ]
    Call ::= ident  ( Actuals ) |  Expr  .  ident  ( Actuals )
    Actuals ::=  Expr+, | e
    Constant ::= intConstant | doubleConstant | boolConstant |  stringConstant | null
"""
import pyparsing as pp
from pyparsing import pyparsing_common as ppc

pp.ParserElement.enable_packrat()

# keywords
keywords_ = (
    VOID, INT, DOUBLE, BOOL, STRING, CLASS, INTERFACE, NULL, THIS, EXTENDS,
    IMPLEMENTS, FOR, WHILE, IF, ELSE, RETURN, BREAK, NEW, NEWARRAY,
    PRINT, READINTEGER, READLINE, TRUE, FALSE,
) = list(
        pp.Keyword.using_each(
        """
        void int double bool string class interface null this extends implements or while
        if else return break new NewArray Print ReadInteger ReadLine true false
        """.split(),
    )
)
keywords = pp.MatchFirst(keywords_).set_name("any_keyword")

(
    LPAR, RPAR, LBRACE, RBRACE, LBRACK, RBRACK, DOT, EQ, COMMA, SEMI
) = pp.Suppress.using_each("(){}[].=,;")

hex_constant = pp.Regex(r"0[xX][0-9a-fA-F]+").add_parse_action(
    lambda t: int(t[0][2:], 16)
)
int_constant = hex_constant | ppc.integer
double_constant = ppc.real
bool_constant = TRUE | FALSE
string_constant = pp.dbl_quoted_string
null = NULL
constant = double_constant | bool_constant | int_constant | string_constant | null
ident = ~keywords + ppc.identifier
type_ = pp.Group((INT | DOUBLE | BOOL | STRING | ident) + pp.Literal("[]")[...])

variable = type_ + ident
variable_decl = variable + SEMI

expr = pp.Forward()
expr_parens = pp.Group(LPAR + expr + RPAR)
actuals = pp.DelimitedList(expr) | ""
call = pp.Group(
    ident("call_ident") + LPAR + actuals("call_args") + RPAR
    | (expr_parens + (DOT + ident)[...])("call_ident_expr")
    + LPAR
    + actuals("call_args")
    + RPAR
)
lvalue = (
    (ident | expr_parens)
    + (DOT + (ident | expr_parens))[...]
    + (LBRACK + expr + RBRACK)[...]
)
assignment = pp.Group(lvalue("lhs") + EQ + expr("rhs"))
read_integer = pp.Group(READINTEGER + LPAR + RPAR)
read_line = pp.Group(READLINE + LPAR + RPAR)
new_statement = pp.Group(NEW + ident)
new_array = pp.Group(NEWARRAY + LPAR + expr + COMMA + type_ + RPAR)
rvalue = constant | call | read_integer | read_line | new_statement | new_array | ident
arith_expr = pp.infix_notation(
    rvalue.set_name("rvalue"),
    [
        ("-", 1, pp.OpAssoc.RIGHT,),
        (pp.one_of("* / %"), 2, pp.OpAssoc.LEFT,),
        (pp.one_of("+ -"), 2, pp.OpAssoc.LEFT,),
    ],
)
comparison_expr = pp.infix_notation(
    arith_expr.set_name("arith_expr"),
    [
        ("!", 1, pp.OpAssoc.RIGHT,),
        (pp.one_of("< > <= >="), 2, pp.OpAssoc.LEFT,),
        (pp.one_of("== !="), 2, pp.OpAssoc.LEFT,),
        (pp.one_of("&&"), 2, pp.OpAssoc.LEFT,),
        (pp.one_of("||"), 2, pp.OpAssoc.LEFT,),
    ],
)
expr <<= (
    assignment
    | call
    | THIS
    | comparison_expr
    | arith_expr
    | lvalue
    | constant
    | read_integer
    | read_line
    | new_statement
    | new_array
)

stmt = pp.Forward()
print_stmt = pp.Group(
    PRINT("statement")
    + LPAR
    + pp.Group(pp.DelimitedList(expr) | "")("args")
    + RPAR
    + SEMI
)
break_stmt = pp.Group(BREAK("statement") + SEMI)
return_stmt = pp.Group(RETURN("statement") + expr + SEMI)
for_stmt = pp.Group(
    FOR("statement")
    + LPAR
    + (expr | "")
    + SEMI
    + expr
    + SEMI
    + (expr | "")
    + RPAR
    + stmt
)
while_stmt = pp.Group(WHILE("statement") + LPAR + expr + RPAR + stmt)
if_stmt = pp.Group(
    IF("statement")
    + LPAR
    + pp.Group(expr)("condition")
    + RPAR
    + pp.Group(stmt)("then_statement")
    + pp.Group((ELSE + stmt | ""))("else_statement")
)
stmt_block = pp.Group(
    LBRACE + variable_decl[...] + stmt[...] + RBRACE
)
stmt <<= (
    if_stmt
    | while_stmt
    | for_stmt
    | break_stmt
    | return_stmt
    | print_stmt
    | stmt_block
    | pp.Group(expr + SEMI)
)

formals = pp.DelimitedList(variable) | ""
prototype = pp.Group(
    (type_ | VOID)("return_type")
    + ident("function_name")
    + LPAR
    + formals("args")
    + RPAR
    + SEMI
)("prototype")
function_decl = pp.Group(
    (type_ | VOID)("return_type")
    + ident("function_name")
    + LPAR
    + formals("args")
    + RPAR
    + stmt_block("body")
)("function_decl")

interface_decl = pp.Group(
    INTERFACE
    + ident("interface_name")
    + LBRACE
    + prototype[...]("prototypes")
    + RBRACE
)("interface")
field = variable_decl | function_decl
class_decl = pp.Group(
    CLASS
    + ident("class_name")
    + (EXTENDS + ident | "")("extends")
    + (IMPLEMENTS + pp.DelimitedList(ident) | "")("implements")
    + LBRACE
    + field[...]("fields")
    + RBRACE
)("class_decl")

decl = variable_decl | function_decl | class_decl | interface_decl | prototype
program = pp.Group(decl)[1, ...]
decaf_parser = program

pp.autoname_elements()

if __name__ == '__main__':
    import contextlib

    # create railroad diagram for this parser
    with contextlib.suppress(Exception):
        program.create_diagram(
            "decaf_parser_diagram.html", vertical=2, show_groups=True
        )

    stmt.runTests("""\
        sin(30);
        a = 1;
        b = 1 + 1;
        b = 1 != 2 && false;
        print("A");
        a.b = 100;
        a.b = 100.0;
        a[100] = b;
        a[0][0] = 2;
        a = 0x1234;
    """
    )

    test_program = """
        void getenv(string var);
        int main(string[] args) {
            if (a > 100) {
                Print(a, " is too big");
            } else if (a < 100) {
                Print(a, " is too small");
            } else {
                Print(a, "just right!");
            }
        }
    """

    print(decaf_parser.parse_string(test_program).dump())
