# stackish.py
#
# Stackish is a data representation syntax, similar to JSON or YAML.  For more info on
# stackish, see http://www.savingtheinternetwithhate.com/stackish.html
#
# Copyright 2008, Paul McGuire
#

"""
NUMBER A simple integer type that's just any series of digits.
FLOAT A simple floating point type.
STRING A string is double quotes with anything inside that's not a " or
    newline character. You can include \n and \" to include these
    characters.
MARK Marks a point in the stack that demarcates the boundary for a nested
    group.
WORD Marks the root node of a group, with the other end being the nearest
    MARK.
GROUP Acts as the root node of an anonymous group.
ATTRIBUTE Assigns an attribute name to the previously processed node.
    This means that just about anything can be an attribute, unlike in XML.
BLOB A BLOB is unique to Stackish and allows you to record any content
    (even binary content) inside the structure. This is done by pre-
    sizing the data with the NUMBER similar to Dan Bernstein's netstrings
    setup.
SPACE White space is basically ignored. This is interesting because since
    Stackish is serialized consistently this means you can use \n as the
    separation character and perform reasonable diffs on two structures.
"""

import pyparsing as pp
ppc = pp.common

MARK, UNMARK, AT, COLON, QUOTE = pp.Suppress.using_each("[]@:'")

NUMBER = ppc.integer()
FLOAT = ppc.real()
STRING = pp.QuotedString('"', multiline=True) | pp.QuotedString("'", multiline=True)
WORD = pp.DelimitedList(pp.Word(pp.alphas, pp.alphanums + "_"), delim=":", combine=True)
ATTRIBUTE = pp.Combine(AT + WORD)

str_body = pp.Forward()


def set_body_length(tokens):
    str_body << pp.Word(pp.srange(r"[\0x00-\0xffff]"), exact=int(tokens[0]))
    return ""


BLOB = pp.Combine(
    QUOTE + pp.Word(pp.nums).set_parse_action(set_body_length) + COLON + str_body + QUOTE
)


def assign_using(s):
    def assign_pa(tokens):
        if s in tokens:
            tokens[tokens[s]] = tokens[0]
            del tokens[s]

    return assign_pa


item = pp.Forward()

GROUP = (
    MARK
    + pp.Group(
        (item + ATTRIBUTE[0, 1]("attr")).set_parse_action(assign_using("attr"))[...]
    )
    + (WORD("name") | UNMARK)
).set_parse_action(assign_using("name"))
item <<= FLOAT | NUMBER | STRING | BLOB | GROUP

if __name__ == '__main__':

    success, _ = item.run_tests(
        """\
        [ '10:1234567890' @name 25 @age +0.45 @percentage person:zed
        [ [ "hello" 1 child root
        [ "child" [ 200 '4:like' "I" "hello" things root
        [ [ "data" [ 2 1 ] @numbers child root
        [ [ 1 2 3 ] @test 4 5 6 root
        """
    )

    assert success
