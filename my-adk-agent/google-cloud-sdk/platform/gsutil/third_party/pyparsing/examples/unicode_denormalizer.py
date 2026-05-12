# unicode_denormalizer.py
#
# Demonstration of the pyparsing's transform_string() method, to
# convert identifiers in Python source code to equivalent Unicode
# characters. Python's compiler automatically normalizes Unicode
# characters back to their ASCII equivalents, so that identifiers may
# be rewritten using other Unicode characters, and normalize back to
# the same identifier. For instance, Python treats "print" and "𝕡𝓻ᵢ𝓃𝘁"
# and "𝖕𝒓𝗂𝑛ᵗ" all as the same identifier.
#
# The converter must take care to *only* transform identifiers -
# Python keywords must always be represented in base ASCII form. To
# skip over keywords, they are added to the parser/transformer, but
# contain no transforming parse action.
#
# The converter also detects identifiers in placeholders within f-strings.
#
# Copyright 2022, by Paul McGuire
#
import keyword
import random
import unicodedata

import pyparsing as pp
ppu = pp.pyparsing_unicode

_· = "_·"
ident_chars = (
    "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
    + "0123456789" + _·
)

# build map of each ASCII character to a string of
# all the characters in the Basic Multilingual Plane
# that NFKC normalizes back to that ASCII character
ident_char_map = {c: [] for c in ident_chars}
for ch in ppu.BMP.identbodychars:
    normal = unicodedata.normalize("NFKC", ch)
    if normal in ident_char_map:
        ident_char_map[normal].append(ch)

# ligatures will also normalize back to ASCII
# (doubled elements have higher chance of being chosen by random.choice)
ligature_map = {
    'IJ': ('Ĳ', 'Ĳ', 'IJ'),
    'LJ': ('Ǉ', 'Ǉ', 'LJ'),
    'NJ': ('Ǌ', 'Ǌ', 'NJ'),
    'DZ': ('Ǳ', 'Ǳ', 'DZ'),
    'II': ('Ⅱ', 'Ⅱ', 'II'),
    'IV': ('Ⅳ', 'Ⅳ', 'IV'),
    'VI': ('Ⅵ', 'Ⅵ', 'VI'),
    'IX': ('Ⅸ', 'Ⅸ', 'IX'),
    'XI': ('Ⅺ', 'Ⅺ', 'XI'),
    'ffl': ('ﬄ', 'ﬄ', 'ﬀl', 'fﬂ', 'ffl'),
    'ffi': ('ﬃ', 'ﬃ', 'ﬀi', 'fﬁ', 'ffi'),
    'ff': ('ﬀ', 'ﬀ', 'ff'),
    'fi': ('ﬁ', 'ﬁ', 'fi'),
    'fl': ('ﬂ', 'ﬂ', 'fl'),
    'ij': ('ĳ', 'ĳ', 'ij'),
    'lj': ('ǉ', 'ǉ', 'lj'),
    'nj': ('ǌ', 'ǌ', 'nj'),
    'dz': ('ǳ', 'ǳ', 'dz'),
    'ii': ('ⅱ', 'ⅱ', 'ii'),
    'iv': ('ⅳ', 'ⅳ', 'iv'),
    'vi': ('ⅵ', 'ⅵ', 'vi'),
    'ix': ('ⅸ', 'ⅸ', 'ix'),
    'xi': ('ⅺ', 'ⅺ', 'xi'),
}

ligature_transformer = pp.one_of(ligature_map).add_parse_action(
    lambda t: random.choice(ligature_map[t[0]])
)


def make_mixed_font(t):
    # extract leading character and remainder to process separately
    t_first, t_rest = t[0][0], t[0][1:]

    # a leading '_' must be written using the ASCII character '_'
    ret = ['_' if t_first == '_'
           else random.choice(ident_char_map.get(t_first, t_first))]
    t_rest = ligature_transformer.transform_string(t_rest)
    ret.extend(random.choice(ident_char_map.get(c, c)) for c in t_rest)
    return ''.join(ret)


# define a pyparsing expression to match any identifier; add a parse
# action to convert to mixed Unicode characters
identifier = pp.pyparsing_common.identifier
identifier.add_parse_action(make_mixed_font)

# match quoted strings (which may be f-strings)
python_quoted_string = pp.Opt(pp.Char("fF")("f_string_prefix")) + (
        pp.python_quoted_string
)("quoted_string_body")


def mix_fstring_expressions(t):
    if not t.f_string_prefix:
        return

    # define an expression and transformer to handle embedded
    # f-string field expressions
    fstring_arg = pp.QuotedString("{", end_quote_char="}")
    fstring_arg.add_parse_action(
        lambda tt: "{" + transformer.transform_string(tt[0]) + "}"
    )

    return (
        t.f_string_prefix
        + fstring_arg.transform_string(t.quoted_string_body)
    )

# add parse action to transform identifiers in f-strings
python_quoted_string.add_parse_action(mix_fstring_expressions)

# match keywords separately from identifiers - keywords must be kept in their
# original ASCII
any_keyword = pp.one_of(
    list(keyword.kwlist) + getattr(keyword, "softkwlist", []),
    as_keyword=True
)

# quoted strings and keywords will be parsed, but left untransformed
transformer = python_quoted_string | any_keyword | identifier


def demo():
    import textwrap
    hello_source = textwrap.dedent("""
    def hello():
        try:
            hello_ = "Hello"
            world_ = "World"
            print(f"{hello_}, {world_}!")
        except TypeError as exc:
            print("failed: {}".format(exc))
    
    if __name__ == "__main__":
        hello()
    """)

    # use transformer to generate code with denormalized identifiers
    transformed = transformer.transform_string(hello_source)
    print(transformed)

    # does it really work? compile the transformed code and run it!
    code = compile(transformed, "inline source", mode="exec")
    exec(code)

    if 1:
        # pick some code from the stdlib
        import unittest.util as lib_module
        import inspect
        source = inspect.getsource(lib_module)
        transformed = transformer.transform_string(source)
        print()
        print(transformed)

if __name__ == '__main__':
    demo()
