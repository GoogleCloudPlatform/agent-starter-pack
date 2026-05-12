#
# original file: https://raw.githubusercontent.com/pyparsing/pyparsing/pyparsing_3.0.9/examples/invRegex.py
#
# Copyright 2008, Paul McGuire
#
# pyparsing script to expand a regular expression into all possible matching strings
# Supports:
# - {n} and {m,n} repetition, but not unbounded + or * repetition
# - ? optional elements
# - [] character ranges
# - () grouping
# - | alternation
#
__all__ = ["count", "invert"]

from pyparsing import (
    Literal,
    one_of,
    Empty,
    printables,
    ParserElement,
    Combine,
    SkipTo,
    infix_notation,
    ParseFatalException,
    Word,
    nums,
    OpAssoc,
    Suppress,
    ParseResults,
    srange,
)

ParserElement.enablePackrat()


class CharacterRangeEmitter:
    def __init__(self, chars):
        # remove duplicate chars in character range, but preserve original order
        seen = set()
        self.charset = "".join(seen.add(c) or c for c in chars if c not in seen)

    def __str__(self):
        return "[" + self.charset + "]"

    def __repr__(self):
        return "[" + self.charset + "]"

    def make_generator(self):
        def gen_chars():
            yield from self.charset

        return gen_chars


class OptionalEmitter:
    def __init__(self, expr):
        self.expr = expr

    def make_generator(self):
        def optional_gen():
            yield ""
            yield from self.expr.make_generator()()

        return optional_gen


class DotEmitter:
    def make_generator(self):
        def dot_gen():
            yield from printables

        return dot_gen


class GroupEmitter:
    def __init__(self, exprs):
        self.exprs = ParseResults(exprs)

    def make_generator(self):
        def group_gen():
            def recurse_list(elist):
                if len(elist) == 1:
                    yield from elist[0].make_generator()()
                else:
                    for s in elist[0].make_generator()():
                        for s2 in recurse_list(elist[1:]):
                            yield s + s2

            if self.exprs:
                yield from recurse_list(self.exprs)

        return group_gen


class AlternativeEmitter:
    def __init__(self, exprs):
        self.exprs = exprs

    def make_generator(self):
        def alt_gen():
            for e in self.exprs:
                yield from e.make_generator()()

        return alt_gen


class LiteralEmitter:
    def __init__(self, lit):
        self.lit = lit

    def __str__(self):
        return "Lit:" + self.lit

    def __repr__(self):
        return "Lit:" + self.lit

    def make_generator(self):
        def lit_gen():
            yield self.lit

        return lit_gen


def handle_range(toks):
    return CharacterRangeEmitter(srange(toks[0]))


def handle_repetition(toks):
    toks = toks[0]
    if toks[1] in "*+":
        raise ParseFatalException("", 0, "unbounded repetition operators not supported")
    if toks[1] == "?":
        return OptionalEmitter(toks[0])
    if "count" in toks:
        return GroupEmitter([toks[0]] * int(toks.count))
    if "minCount" in toks:
        mincount = int(toks.minCount)
        maxcount = int(toks.maxCount)
        optcount = maxcount - mincount
        if optcount:
            opt = OptionalEmitter(toks[0])
            for i in range(1, optcount):
                opt = OptionalEmitter(GroupEmitter([toks[0], opt]))
            return GroupEmitter([toks[0]] * mincount + [opt])
        else:
            return [toks[0]] * mincount


def handle_literal(toks):
    lit = ""
    for t in toks:
        if t[0] == "\\":
            if t[1] == "t":
                lit += "\t"
            else:
                lit += t[1]
        else:
            lit += t
    return LiteralEmitter(lit)


def handle_macro(toks):
    macro_char = toks[0][1]
    if macro_char == "d":
        return CharacterRangeEmitter("0123456789")
    elif macro_char == "w":
        return CharacterRangeEmitter(srange("[A-Za-z0-9_]"))
    elif macro_char == "s":
        return LiteralEmitter(" ")
    else:
        raise ParseFatalException(
            "", 0, "unsupported macro character (" + macro_char + ")"
        )


def handle_sequence(toks):
    return GroupEmitter(toks[0])


def handle_dot():
    return CharacterRangeEmitter(printables)


def handle_alternative(toks):
    return AlternativeEmitter(toks[0])


_parser = None


def parser():
    global _parser
    if _parser is None:
        ParserElement.set_default_whitespace_chars("")
        lbrack, rbrack, lbrace, rbrace, lparen, rparen, colon, qmark = Literal.using_each(
            "[]{}():?"
        )

        re_macro = Combine("\\" + one_of("d w s"))
        escaped_char = ~re_macro + Combine("\\" + one_of(list(printables)))
        re_literal_char = (
            "".join(c for c in printables if c not in r"\[]{}().*?+|") + " \t"
        )

        re_range = Combine(lbrack + SkipTo(rbrack, ignore=escaped_char) + rbrack) # type: ignore 
        re_literal = escaped_char | one_of(list(re_literal_char))
        re_non_capture_group = Suppress("?:")
        re_dot = Literal(".")
        repetition = (
            (lbrace + Word(nums)("count") + rbrace)
            | (lbrace + Word(nums)("minCount") + "," + Word(nums)("maxCount") + rbrace)
            | one_of(list("*+?"))
        )

        re_range.add_parse_action(handle_range)
        re_literal.add_parse_action(handle_literal)
        re_macro.add_parse_action(handle_macro)
        re_dot.add_parse_action(handle_dot)

        re_term = re_literal | re_range | re_macro | re_dot | re_non_capture_group
        re_expr = infix_notation(
            re_term,
            [
                (repetition, 1, OpAssoc.LEFT, handle_repetition),
                (Empty(), 2, OpAssoc.LEFT, handle_sequence),
                (Suppress("|"), 2, OpAssoc.LEFT, handle_alternative),
            ],
        )
        _parser = re_expr

    return _parser


def count(gen):
    """Simple function to count the number of elements returned by a generator."""
    return sum(1 for _ in gen)


def invert(regex):
    r"""
    Call this routine as a generator to return all the strings that
    match the input regular expression.
        for s in invert(r"[A-Z]{3}\d{3}"):
            print s
    """
    invre = GroupEmitter(parser().parseString(regex)).make_generator()
    return invre()


def main():
    tests = r"""
    [A-EA]
    [A-D]*
    [A-D]{3}
    X[A-C]{3}Y
    X[A-C]{3}\(
    X\d
    foobar\d\d
    foobar{2}
    foobar{2,9}
    fooba[rz]{2}
    (foobar){2}
    ([01]\d)|(2[0-5])
    (?:[01]\d)|(2[0-5])
    ([01]\d\d)|(2[0-4]\d)|(25[0-5])
    [A-C]{1,2}
    [A-C]{0,3}
    [A-C]\s[A-C]\s[A-C]
    [A-C]\s?[A-C][A-C]
    [A-C]\s([A-C][A-C])
    [A-C]\s([A-C][A-C])?
    [A-C]{2}\d{2}
    @|TH[12]
    @(@|TH[12])?
    @(@|TH[12]|AL[12]|SP[123]|TB(1[0-9]?|20?|[3-9]))?
    @(@|TH[12]|AL[12]|SP[123]|TB(1[0-9]?|20?|[3-9])|OH(1[0-9]?|2[0-9]?|30?|[4-9]))?
    (([ECMP]|HA|AK)[SD]|HS)T
    [A-CV]{2}
    A[cglmrstu]|B[aehikr]?|C[adeflmorsu]?|D[bsy]|E[rsu]|F[emr]?|G[ade]|H[efgos]?|I[nr]?|Kr?|L[airu]|M[dgnot]|N[abdeiop]?|Os?|P[abdmortu]?|R[abefghnu]|S[bcegimnr]?|T[abcehilm]|Uu[bhopqst]|U|V|W|Xe|Yb?|Z[nr]
    (a|b)|(x|y)
    (a|b) (x|y)
    [ABCDEFG](?:#|##|b|bb)?(?:maj|min|m|sus|aug|dim)?[0-9]?(?:/[ABCDEFG](?:#|##|b|bb)?)?
    (Fri|Mon|S(atur|un)|T(hur|ue)s|Wednes)day
    A(pril|ugust)|((Dec|Nov|Sept)em|Octo)ber|(Febr|Jan)uary|Ju(ly|ne)|Ma(rch|y)
    """.splitlines()

    for t in tests:
        t = t.strip()
        if not t:
            continue
        print("-" * 50)
        print(t)
        try:
            num = count(invert(t))
            print(num)
            maxprint = 30
            for s in invert(t):
                print(s)
                maxprint -= 1
                if not maxprint:
                    break
        except ParseFatalException as pfe:
            print(pfe.msg)
            print("")
            continue
        print("")


if __name__ == "__main__":
    main()
