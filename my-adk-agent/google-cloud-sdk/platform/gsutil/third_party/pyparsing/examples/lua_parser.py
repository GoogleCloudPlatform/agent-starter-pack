#
# lua_parser.py
#
# A simple parser for the Lua language.
#
# Copyright 2020, Paul McGuire
#

"""
from https://www.lua.org/manual/5.1/manual.html#8

    chunk ::= {stat [';']} [laststat [';']]

    block ::= chunk

    stat ::=  varlist '=' explist |
         functioncall |
         do block end |
         while exp do block end |
         repeat block until exp |
         if exp then block {elseif exp then block} [else block] end |
         for Name '=' exp ',' exp [',' exp] do block end |
         for namelist in explist do block end |
         function funcname funcbody |
         local function Name funcbody |
         local namelist ['=' explist]

    laststat ::= return [explist] | break

    funcname ::= Name {'.' Name} [':' Name]

    varlist ::= var {',' var}

    var ::=  Name | prefixexp '[' exp ']' | prefixexp '.' Name

    namelist ::= Name {',' Name}

    explist ::= {exp ','} exp

    exp ::=  nil | false | true | Number | String | '...' | function |
         prefixexp | tableconstructor | exp binop exp | unop exp

    prefixexp ::= var | functioncall | '(' exp ')'

    functioncall ::=  prefixexp args | prefixexp ':' Name args

    args ::=  '(' [explist] ')' | tableconstructor | String

    function ::= function funcbody

    funcbody ::= '(' [parlist] ')' block end

    parlist ::= namelist [',' '...'] | '...'

    tableconstructor ::= '{' [fieldlist] '}'

    fieldlist ::= field {fieldsep field} [fieldsep]

    field ::= '[' exp ']' '=' exp | Name '=' exp | exp

    fieldsep ::= ',' | ';'

    binop ::= '+' | '-' | '*' | '/' | '^' | '%' | '..' |
         '<' | '<=' | '>' | '>=' | '==' | '~=' |
         and | or

    unop ::= '-' | not | '#'

operator precedence:

     or
     and
     <     >     <=    >=    ~=    ==
     |
     ~
     &
     <<    >>
     ..
     +     -
     *     /     //    %
     unary operators (not   #     -     ~)
     ^

"""
import pyparsing as pp

ppc = pp.pyparsing_common
pp.ParserElement.enable_packrat()

LBRACK, RBRACK, LBRACE, RBRACE, LPAR, RPAR = pp.Suppress.using_each("[]{}()")
COMMA, SEMI, COLON = pp.Suppress.using_each(",;:")
OPT_SEMI = pp.Optional(SEMI).suppress()
ELLIPSIS = pp.Literal("...")
EQ = pp.Literal("=")

keywords = {
    k.upper(): pp.Keyword(k)
    for k in """\
    return break do end while if then elseif else for in function
    local repeat until nil false true and or not
    """.split()
}
vars().update(keywords)
any_keyword = pp.MatchFirst(keywords.values()).set_name("keyword")

comment_intro = pp.Literal("--")
short_comment = comment_intro + pp.rest_of_line
long_comment = comment_intro + LBRACK + ... + RBRACK
lua_comment = long_comment | short_comment

# must use negative lookahead to ensure we don't parse a keyword as an identifier
ident = ~any_keyword + ppc.identifier

name = pp.DelimitedList(ident, delim=".", combine=True)

namelist = pp.DelimitedList(name)
number = ppc.number

# does not parse levels
multiline_string = pp.QuotedString("[[", endQuoteChar="]]", multiline=True)
string = pp.QuotedString("'") | pp.QuotedString('"') | multiline_string

exp = pp.Forward()

#     explist1 ::= {exp ','} exp
explist1 = pp.DelimitedList(exp)

# set up for recursive definition of 'stmt' (since some statements are
# composed of nested statements)
stat = pp.Forward().set_name("stat")

#    laststat ::= return [explist1]  |  break
laststat = pp.Group(RETURN + explist1) | BREAK

#    block ::= {stat [';']} [laststat[';']]
block = pp.Group((stat + OPT_SEMI)[1, ...] + pp.Optional(laststat + OPT_SEMI))

#    field ::= '[' exp ']' '=' exp  |  Name '=' exp  |  exp
field = pp.Group(
    LBRACK + exp + RBRACK + EQ + pp.Group(exp) | name + EQ + pp.Group(exp) | exp
)

#    fieldsep ::= ','  |  ';'
fieldsep = COMMA | SEMI

#    fieldlist ::= field {fieldsep field} [fieldsep]
field_list = pp.DelimitedList(field, delim=fieldsep, allow_trailing_delim=True)

#    tableconstructor ::= '{' [fieldlist] '}'
tableconstructor = pp.Group(LBRACE + pp.Optional(field_list) + RBRACE)

#    parlist1 ::= namelist [',' '...']  |  '...'
parlist = namelist + pp.Optional(COMMA + ELLIPSIS) | ELLIPSIS

#    funcname ::= Name {'.' Name} [':' Name]
funcname = pp.Group(name + COLON + name) | name

#    function ::= function funcbody
#    funcbody ::= '(' [parlist1] ')' block end
funcbody = pp.Group(LPAR + parlist + RPAR) + block + END
function = FUNCTION + funcbody

#    args ::=  '(' [explist1] ')'  |  tableconstructor  |  String
args = LPAR + pp.Optional(explist1) + RPAR | tableconstructor | string

# this portion of the spec is left-recursive, must break LR loop
#    varlist1 ::= var {',' var}
#    var ::=  Name  |  prefixexp '[' exp ']'  |  prefixexp '.' Name
#    prefixexp ::= var  |  functioncall  |  '(' exp ')'
#    functioncall ::=  prefixexp args  |  prefixexp ':' Name args

exp_group = pp.Group(LPAR + exp + RPAR)
prefixexp = name | exp_group
functioncall = pp.Group(prefixexp + pp.Optional(COLON + name) + pp.Group(args))
var = pp.Forward()
var_atom = functioncall | name | exp_group
index_ref = pp.Group(LBRACK + exp + RBRACK)
var_part = pp.Group(var_atom + index_ref) | var_atom
var <<= pp.DelimitedList(var_part, delim=".")

varlist1 = pp.DelimitedList(var)

# exp ::=  nil  |  false  |  true  |  Number  |  String  |  '...'  |
#              function  |  prefixexp  |  tableconstructor
exp_atom = (
    NIL
    | FALSE
    | TRUE
    | number
    | string
    | ELLIPSIS
    | functioncall
    | var  # prefixexp
    | tableconstructor
).set_name("exp_atom")

# precedence of operations from https://www.lua.org/manual/5.3/manual.html#3.4.8
exp <<= pp.infix_notation(
    exp_atom,
    [
        ("^", 2, pp.opAssoc.LEFT),
        ((NOT | pp.oneOf("# - ~")).set_name("not op"), 1, pp.opAssoc.RIGHT),
        (pp.oneOf("* / // %"), 2, pp.opAssoc.LEFT),
        (pp.oneOf("+ -"), 2, pp.opAssoc.LEFT),
        ("..", 2, pp.opAssoc.LEFT),
        (pp.oneOf("<< >>"), 2, pp.opAssoc.LEFT),
        ("&", 2, pp.opAssoc.LEFT),
        ("~", 2, pp.opAssoc.LEFT),
        ("|", 2, pp.opAssoc.LEFT),
        (pp.oneOf("< > <= >= ~= =="), 2, pp.opAssoc.LEFT),
        (AND, 2, pp.opAssoc.LEFT),
        (OR, 2, pp.opAssoc.LEFT),
    ],
).set_name("exp")

assignment_stat = pp.Optional(LOCAL) + varlist1 + EQ + explist1
func_call_stat = pp.Optional(LOCAL) + functioncall
do_stat = DO + block + END
while_stat = WHILE + exp + block + END
repeat_stat = REPEAT + block + UNTIL + exp
for_loop_stat = (
    FOR + name + EQ + exp + COMMA + exp + pp.Optional(COMMA + exp) + DO + block + END
)
for_seq_stat = FOR + namelist + IN + explist1 + DO + block + END
if_stat = (
    IF
    + exp
    + THEN
    + block
    + pp.Group(ELSEIF + exp + THEN + block)[...]
    + pp.Optional(pp.Group(ELSE + block))
    + END
)
function_def = pp.Optional(LOCAL) + FUNCTION + funcname + funcbody

pp.autoname_elements()

#    stat ::=  varlist1 '=' explist1  |
#              functioncall  |
#              do block end  |
#              while exp do block end  |
#              repeat block until exp  |
#              if exp then block {elseif exp then block} [else block] end  |
#              for Name '=' exp ',' exp [',' exp] do block end  |
#              for namelist in explist1 do block end  |
#              function funcname funcbody  |
#              local function Name funcbody  |
#              local namelist ['=' explist1]
stat <<= pp.Group(
    assignment_stat
    | do_stat
    | while_stat
    | repeat_stat
    | for_loop_stat
    | for_seq_stat
    | func_call_stat
    | if_stat
    | function_def
)

lua_script = stat[...].set_name("script")

# ignore comments
lua_script.ignore(lua_comment)

if __name__ == "__main__":
    import contextlib

    with contextlib.suppress(Exception):
        lua_script.create_diagram(
            "lua_parser_diagram.html", vertical=2, show_groups=True
        )

    sample = r"""
    function test(x)
        local t = {foo=1, bar=2, arg=x}
        n = 0
        if t['foo'] then
            n = n + 1
        end
        if 10 > 8 then
            n = n + 2
        end
        if (10 > 8) then
            n = n + 2
        end
        for var in vars do
            print(var, '=', var)
        end
    end
    """

    try:
        result = lua_script.parseString(sample)
        result.pprint()
    except pp.ParseException as pe:
        print(pe.explain())
        raise
