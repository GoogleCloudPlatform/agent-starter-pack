#
# ebnftest.py
#
# Test script for ebnf.py
#
# Submitted 2004 by Seo Sanghyeon
#
print("Importing pyparsing...")
import pyparsing as pp

print("Constructing EBNF parser with pyparsing...")
import ebnf


grammar = """
    (*
        ISO 14977 standardize The Extended Backus-Naur Form(EBNF) syntax.
        You can read a final draft version here:
        https://www.cl.cam.ac.uk/~mgk25/iso-ebnf.html
    *)
    syntax = (syntax_rule), {(syntax_rule)};
    syntax_rule = meta_identifier, '=', definitions_list, ';';
    definitions_list = single_definition, {'|', single_definition};
    single_definition = syntactic_term, {',', syntactic_term};
    syntactic_term = syntactic_factor,['-', syntactic_factor];
    syntactic_factor = [integer, '*'], syntactic_primary;
    syntactic_primary = optional_sequence | repeated_sequence |
      grouped_sequence | meta_identifier | terminal_string;
    optional_sequence = '[', definitions_list, ']';
    repeated_sequence = '{', definitions_list, '}';
    grouped_sequence = '(', definitions_list, ')';
    (*
    terminal_string = "'", character - "'", {character - "'"}, "'" |
      '"', character - '"', {character - '"'}, '"';
     meta_identifier = letter, {letter | digit};
    integer = digit, {digit};
    *)
"""

table: dict[str, pp.ParserElement] = {
    # "character": pp.Char(pp.printables),
    # "letter": pp.Char(pp.alphas + '_'),
    # "digit": pp.Char(nums),
    "terminal_string": pp.sgl_quoted_string | pp.dbl_quoted_string,
    "meta_identifier": pp.Word(pp.alphas + "_", pp.alphas + "_" + pp.nums),
    "integer": pp.common.integer,
}

print("Parsing EBNF grammar with EBNF parser...")
parsers = ebnf.parse(grammar, table)
ebnf_parser = parsers["syntax"]

ebnf_parser.ignore(ebnf.ebnfComment)

ebnf_parser.create_diagram("ebnftest_diagram.html")

print("Parsing EBNF grammar with generated EBNF parser...\n")
parsed_chars = ebnf_parser.parse_string(grammar, parse_all=True)
print("\n".join(str(pc) for pc in parsed_chars.as_list()))
