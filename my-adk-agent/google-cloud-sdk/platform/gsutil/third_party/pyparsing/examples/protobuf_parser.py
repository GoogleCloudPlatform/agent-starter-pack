# protobuf_parser.py
#
#  simple parser for parsing protobuf .proto files
#
#  Copyright 2010, Paul McGuire
#

from pyparsing import (
    Word,
    alphas,
    alphanums,
    Regex,
    Suppress,
    Forward,
    Group,
    one_of,
    Opt,
    DelimitedList,
    rest_of_line,
    quotedString,
    Dict,
    Keyword,
)

ident = Word(alphas + "_", alphanums + "_").set_name("identifier")
integer = Regex(r"[+-]?\d+")

LBRACE, RBRACE, LBRACK, RBRACK, LPAR, RPAR, EQ, SEMI = Suppress.using_each("{}[]()=;")

kwds = """message required optional repeated enum extensions extends extend
          to package service rpc returns true false option import syntax"""
for kw in kwds.split():
    exec("{}_ = Keyword('{}')".format(kw.upper(), kw))

messageBody = Forward()

messageDefn = MESSAGE_ - ident("messageId") + LBRACE + messageBody("body") + RBRACE

typespec = (
    one_of(
        "double float int32 int64 uint32 uint64 sint32 sint64"
        " fixed32 fixed64 sfixed32 sfixed64 bool string bytes"
    )
    | ident
)
rvalue = integer | TRUE_ | FALSE_ | ident
fieldDirective = LBRACK + Group(ident + EQ + rvalue) + RBRACK
fieldDefnPrefix = REQUIRED_ | OPTIONAL_ | REPEATED_
fieldDefn = (
    Opt(fieldDefnPrefix)
    + typespec("typespec")
    + ident("ident")
    + EQ
    + integer("fieldint")
    + fieldDirective[...]
    + SEMI
)

# enumDefn ::= 'enum' ident '{' { ident '=' integer ';' }* '}'
enumDefn = (
    ENUM_("typespec")
    - ident("name")
    + LBRACE
    + Dict((Group(ident + EQ + integer + SEMI))[...])("values")
    + RBRACE
)

# extensionsDefn ::= 'extensions' integer 'to' integer ';'
extensionsDefn = EXTENSIONS_ - integer + TO_ + integer + SEMI

# messageExtension ::= 'extend' ident '{' messageBody '}'
messageExtension = EXTEND_ - ident + LBRACE + messageBody + RBRACE

# messageBody ::= { fieldDefn | enumDefn | messageDefn | extensionsDefn | messageExtension }*
messageBody <<= Group(
    Group(
        fieldDefn | enumDefn | messageDefn | extensionsDefn | messageExtension
    )[...]
)

# methodDefn ::= 'rpc' ident '(' [ ident ] ')' 'returns' '(' [ ident ] ')' ';'
methodDefn = (
    RPC_
    - ident("methodName")
    + LPAR
    + Opt(ident("methodParam"))
    + RPAR
    + RETURNS_
    + LPAR
    + Opt(ident("methodReturn"))
    + RPAR
)

# serviceDefn ::= 'service' ident '{' methodDefn* '}'
serviceDefn = (
    SERVICE_ - ident("serviceName") + LBRACE + Group(methodDefn)[...] + RBRACE
)

syntaxDefn = SYNTAX_ + EQ - quotedString("syntaxString") + SEMI

# packageDirective ::= 'package' ident [ '.' ident]* ';'
packageDirective = Group(PACKAGE_ - DelimitedList(ident, ".", combine=True) + SEMI)

comment = "//" + rest_of_line

importDirective = IMPORT_ - quotedString("importFileSpec") + SEMI

optionDirective = (
    OPTION_ - ident("optionName") + EQ + quotedString("optionValue") + SEMI
)

topLevelStatement = Group(
    messageDefn
    | messageExtension
    | enumDefn
    | serviceDefn
    | importDirective
    | optionDirective
    | syntaxDefn
)

parser = Opt(packageDirective) + topLevelStatement[...]

parser.ignore(comment)


if __name__ == "__main__":

    test1 = """message Person {
      required int32 id = 1;
      required string name = 2;
      optional string email = 3;
    }"""

    test2 = """package tutorial;
    
    message Person {
      required string name = 1;
      required int32 id = 2;
      optional string email = 3;
    
      enum PhoneType {
        MOBILE = 0;
        HOME = 1;
        WORK = 2;
      }
    
      message PhoneNumber {
        required string number = 1;
        optional PhoneType type = 2 [default = HOME];
      }
    
      repeated PhoneNumber phone = 4;
    }
    
    message AddressBook {
      repeated Person person = 1;
    }"""

    test3 = """syntax = "proto3";
    
    import "test.proto";
    
    message SearchRequest {
      string query = 1;
      int32 page_number = 2;
      int32 result_per_page = 3;
    }
    """

    parser.run_tests([test1, test2, test3])
