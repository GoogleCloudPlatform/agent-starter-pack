# macro_expander.py
#
# Example pyparsing program for performing macro expansion, similar to
# the C pre-processor.  This program is not as fully-featured, simply
# processing macros of the form:
#     #def xxx yyyyy
# and replacing xxx with yyyyy in the rest of the input string.  Macros
# can also be composed using other macros, such as
#     #def zzz xxx+1
# Since xxx was previously defined as yyyyy, then zzz will be replaced
# with yyyyy+1.
#
# Copyright 2007, 2023 by Paul McGuire
#
import pyparsing as pp

# define the structure of a macro definition (the empty term is used
# to advance to the next non-whitespace character)
identifier = pp.common.identifier
macro_def = "#def" + identifier("macro") + pp.empty + pp.restOfLine("value")

# define a placeholder for defined macros - initially nothing
macro_expr = pp.Forward()
macro_expr << pp.NoMatch()

# global dictionary for macro definitions
macros = {}


# parse action for macro definitions
def process_macro_defn(t):
    macro_val = macro_expander.transform_string(t.value)
    macros[t.macro] = macro_val
    macro_expr << pp.MatchFirst(map(pp.Keyword, macros))
    return f"#def {t.macro} {macro_val}"


# parse action to replace macro references with their respective definition
def process_macro_ref(t):
    return macros[t[0]]


# attach parse actions to expressions
macro_expr.set_parse_action(process_macro_ref)
macro_def.set_parse_action(process_macro_defn)

# define pattern for scanning through the input string
macro_expander = macro_expr | macro_def


# test macro substitution using transformString
test_string = """
    #def A 100
    #def ALEN A+1

    char Astring[ALEN];
    char AA[A];
    typedef char[ALEN] Acharbuf;
    """

print(test_string)
print("-" * 40)
print(macro_expander.transform_string(test_string))
print(macros)
