#
# tag_emitter.py
#
# Example showing how to inject tags into the parsed results by adding
# an Empty() with a parse action to return the desired added data.
#
# Copyright 2023, Paul McGuire
#
import pyparsing as pp

# define expressions to parse different forms of integer constants
# add parse actions that will evaluate the integer correctly
binary_int = ("0b" + pp.Word("01")).add_parse_action(lambda t: int(t[1], base=2))
hex_int = ("0x" + pp.Word(pp.hexnums)).add_parse_action(lambda t: int(t[1], base=16))
dec_int = pp.Word(pp.nums).add_parse_action(lambda t: int(t[0]))


# define a parser that includes the tag for each integer format type
int_parser = (binary_int("value") + pp.Tag("original_format", "binary")
              | hex_int("value") + pp.Tag("original_format", "hex")
              | dec_int("value") + pp.Tag("original_format", "decimal")
              )

# parse some integers
int_parser.run_tests("""\
    0b11011000001
    0x6c1
    1729""")
