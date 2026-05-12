"""
The Lox language grammar

From Robert Nystrom's "Crafting Interpreters"
http://craftinginterpreters.com/

The BNF for the Lox language is at http://craftinginterpreters.com/appendix-i.html
"""
import pyparsing as pp
pp.ParserElement.enable_packrat()

# punctuation
COMMA, LPAR, RPAR, LBRACE, RBRACE, EQ, SEMI = map(pp.Suppress, ",(){}=;")

# keywords
(CLASS, FUN, VAR, FOR, IF, ELSE, PRINT, RETURN, WHILE,
 TRUE, FALSE, NIL, THIS, SUPER, AND, OR) = pp.Keyword.using_each(
    "class fun var for if else print return while"
    " true false nil this super and or".split()
)

identifier = pp.Word(pp.alphas + "_", pp.alphanums + "_'")
string = pp.QuotedString('"')
number = pp.Regex(r"\d+(?:\.\d+)?")

declaration = pp.Forward()
statement = pp.Forward()
class_decl = pp.Forward()
expression = pp.Forward()
block = pp.Forward()

arguments = pp.DelimitedList(expression)
parameters = pp.DelimitedList(identifier)
function = identifier + LPAR + pp.Opt(parameters) + RPAR + block
property_ = identifier + block

fun_decl = FUN + function
var_decl = VAR + identifier + pp.Opt(EQ + expression) + SEMI
class_decl <<= (
        CLASS
        - identifier
        + pp.Opt("<" + identifier)
        + LBRACE
        + (function | property_ | class_decl)[...]
        + RBRACE
)


primary = (TRUE | FALSE | NIL | THIS | number | string | identifier
           | SUPER + "." + identifier
           # | LPAR + expression + RPAR  <-- not needed, infix_notation takes care of this
           ).set_name("primary")
call = primary + (
        LPAR + pp.Opt(arguments) + RPAR
        | "." + identifier
)[1, ...]

arith_expression = pp.infix_notation(
    (call | primary).set_name("arith_operand"),
    [
        (pp.one_of("! -"), 1, pp.opAssoc.RIGHT),
        (pp.one_of("/ *"), 2, pp.opAssoc.LEFT),
        (pp.one_of("- +"), 2, pp.opAssoc.LEFT),
        (pp.one_of("> >= < <="), 2, pp.opAssoc.LEFT),
        (pp.one_of("!= =="), 2, pp.opAssoc.LEFT),
        (AND, 2, pp.opAssoc.LEFT),
        (OR, 2, pp.opAssoc.LEFT),
    ]
)
assignment = pp.Forward()
assignment <<= (call | identifier) + EQ + (assignment | arith_expression)

expression <<= assignment ^ arith_expression ^ function

block <<= pp.Group(LBRACE + declaration[...] + RBRACE)
while_statement = WHILE + LPAR + expression + RPAR + statement
return_statement = RETURN + pp.Opt(expression) + SEMI
print_statement = PRINT + expression + SEMI
if_statement = IF + LPAR + expression + RPAR + statement + pp.Opt(ELSE + statement)
expr_statement = expression + ";"
for_statement = FOR + LPAR + pp.Group(
    (var_decl | expr_statement | ";")
    + pp.Opt(expression) + ";"
    + pp.Opt(expression)
) + RPAR + statement


statement <<= pp.Group(
    expr_statement
    | for_statement
    | if_statement
    | print_statement
    | return_statement
    | while_statement
    | block
)

declaration <<= (
    class_decl
    | fun_decl
    | var_decl
    | statement
)

program = declaration[...]
program.ignore(pp.dbl_slash_comment)

# define names so that we get a better diagram
pp.autoname_elements()


def main():
    import textwrap

    success, _ = program.run_tests(
        textwrap.dedent(t) for t in [
            """\
                var a = 1;
                {
                  var a = a + 2;
                  print a;
                }
                """,
            """\
                {
                  var i = 0;
                  while (i < 10) {
                    print i;
                    i = i + 1;
                  }
                }
            """,
            """\
                var a = 0;
                var temp;
                
                for (var b = 1; a < 10000; b = temp + b) {
                  print a;
                  temp = a;
                  a = b;
                }
            """,
            """\
                fun add(a, b, c) {
                  print a + b + c;
                }
                
                add(1, 2, 3);
            """,
            """\
                fun count(n) {
                  while (n < 100) {
                    if (n == 3) return n; // <--
                    print n;
                    n = n + 1;
                  }
                }
                
                count(1);
            """,
            """\
                fun fib(n) {
                  if (n <= 1) return n;
                  return fib(n - 2) + fib(n - 1);
                }
                
                for (var i = 0; i < 20; i = i + 1) {
                  print fib(i);
                }
            """,
            """\
                fun makeCounter() {
                  var i = 0;
                  fun count() {
                    i = i + 1;
                    print i;
                  }
                
                  return count;
                }
                
                var counter = makeCounter();
                counter(); // "1".
                counter(); // "2".
            """,
            """\
                fun thrice(fn) {
                  for (var i = 1; i <= 3; i = i + 1) {
                    fn(i);
                  }
                }
                
                thrice(fun (a) {
                  print a;
                });
                // "1".
                // "2".
                // "3".
            """,
            """\
                class Math {
                  square(n) {
                    return n * n;
                  }
                }
                
                print Math.square(3); // Prints "9".
            """,
            """\
                class Circle {
                  init(radius) {
                    this.radius = radius;
                  }
                
                  area {
                    return 3.141592653 * this.radius * this.radius;
                  }
                }
                
                var circle = Circle(4);
                print circle.area; // Prints roughly "50.2655".
            """,
            """\
                // Your first Lox program!
                print "Hello, world!";
            """
        ]
    )
    assert success


if __name__ == '__main__':
    import contextlib

    with contextlib.suppress(Exception):
        program.create_diagram("lox_parser_diagram.html", vertical=2, show_groups=True)

    main()
