#
# lineno_example.py
#
# an example of using the location value returned by pyparsing to
# extract the line and column number of the location of the matched text,
# or to extract the entire line of text.
#
# Copyright (c) 2006, Paul McGuire
#
import pyparsing as pp

data = """Now is the time
for all good men
to come to the aid
of their country."""


# demonstrate use of lineno, line, and col in a parse action
def report_long_words(st, locn, toks):
    word = toks[0]
    if len(word) > 3:
        print(
            f"Found {word!r} on line {pp.lineno(locn, st)} at column {pp.col(locn, st)}"
        )
        print("The full line of text was:")
        print(f"{pp.line(locn, st)!r}")
        print(f" {'^':>{pp.col(locn, st)}}")
        print()


wd = pp.Word(pp.alphas).set_parse_action(report_long_words)
wd[1, ...].parse_string(data)


# demonstrate returning an object from a parse action, containing more information
# than just the matching token text
class Token:
    def __init__(self, st, locn, tok_string):
        self.token_string = tok_string
        self.locn = locn
        self.source_line = pp.line(locn, st)
        self.line_no = pp.lineno(locn, st)
        self.col = pp.col(locn, st)

    def __str__(self):
        return f"{self.token_string!r} (line: {self.line_no}, col: {self.col})"


def create_token_object(st, locn, toks):
    return Token(st, locn, toks[0])


wd = pp.Word(pp.alphas).set_parse_action(create_token_object)

for token_obj in wd[1, ...].parse_string(data):
    print(token_obj)
