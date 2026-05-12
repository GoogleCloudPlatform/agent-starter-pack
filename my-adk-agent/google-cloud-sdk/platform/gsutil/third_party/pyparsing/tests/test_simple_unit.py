#
# test_simple_unit.py
#
# While these unit tests *do* perform low-level unit testing of the classes in pyparsing,
# this testing module should also serve an instructional purpose, to clearly show simple passing
# and failing parse cases of some basic pyparsing expressions.
#
# Copyright (c) 2018  Paul T. McGuire
#
import unittest
from collections.abc import Iterable, Mapping
from datetime import datetime, timezone
from typing import NamedTuple

import pyparsing as pp
ppt = pp.pyparsing_test
TestParseResultsAsserts = ppt.TestParseResultsAsserts


# Test spec data class for specifying simple pyparsing test cases
class PyparsingTest(NamedTuple):
    desc: str = ""
    expr: pp.ParserElement = pp.Empty()
    text: str = ""
    parse_fn: str = "parse_string"
    expected_list: Iterable = None
    expected_dict: Mapping = None
    expected_fail_locn: int = None


NL = "\n"


class PyparsingExpressionTestCase(ppt.TestParseResultsAsserts, unittest.TestCase):
    """
    Base pyparsing testing class to parse various pyparsing expressions against
    given text strings. Subclasses must define a class attribute 'tests' which
    is a list of PyparsingTest instances.
    """

    tests = []

    def runTest(self):
        if self.__class__ is PyparsingExpressionTestCase:
            return

        for test_spec in self.tests:
            # for each spec in the class's tests list, create a subtest
            # that will either:
            #  - parse the string with expected success, display the
            #    results, and validate the returned ParseResults
            #  - or parse the string with expected failure, display the
            #    error message and mark the error location, and validate
            #    the location against an expected value
            with self.subTest(test_spec=test_spec):
                test_spec.expr.streamline()
                print(
                    f"{NL}{test_spec.desc} - {type(test_spec.expr).__name__}({test_spec.expr})"
                )

                parse_function = getattr(test_spec.expr, test_spec.parse_fn)
                if test_spec.expected_fail_locn is None:
                    # expect success
                    subtest_result = parse_function(test_spec.text)
                    if test_spec.parse_fn == "parse_string":
                        print(subtest_result.dump())
                        # compare results against given list and/or dict
                        self.assertParseResultsEquals(
                            subtest_result,
                            expected_list=test_spec.expected_list,
                            expected_dict=test_spec.expected_dict,
                        )
                    elif test_spec.parse_fn == "transformString":
                        print(subtest_result)
                        # compare results against given list and/or dict
                        if test_spec.expected_list is not None:
                            self.assertEqual([subtest_result], test_spec.expected_list)
                    elif test_spec.parse_fn == "searchString":
                        print(subtest_result)
                        # compare results against given list and/or dict
                        if test_spec.expected_list is not None:
                            self.assertEqual([subtest_result], test_spec.expected_list)
                else:
                    # expect fail
                    with self.assertRaisesParseException():
                        try:
                            parse_function(test_spec.text)
                        except pp.ParseBaseException as exc:
                            print(pp.ParseException.explain(exc))
                            self.assertEqual(exc.loc, test_spec.expected_fail_locn)
                            raise


# =========== TEST DEFINITIONS START HERE ==============


class TestLiteral(PyparsingExpressionTestCase):
    tests = [
        PyparsingTest(
            desc="Simple match",
            expr=pp.Literal("xyz"),
            text="xyz",
            expected_list=["xyz"],
        ),
        PyparsingTest(
            desc="Simple match after skipping whitespace",
            expr=pp.Literal("xyz"),
            text="  xyz",
            expected_list=["xyz"],
        ),
        PyparsingTest(
            desc="Simple fail - parse an empty string",
            expr=pp.Literal("xyz"),
            text="",
            expected_fail_locn=0,
        ),
        PyparsingTest(
            desc="Simple fail - parse a mismatching string",
            expr=pp.Literal("xyz"),
            text="xyu",
            expected_fail_locn=0,
        ),
        PyparsingTest(
            desc="Simple fail - parse a partially matching string",
            expr=pp.Literal("xyz"),
            text="xy",
            expected_fail_locn=0,
        ),
        PyparsingTest(
            desc="Fail - parse a partially matching string by matching individual letters",
            expr=pp.Literal("x") + pp.Literal("y") + pp.Literal("z"),
            text="xy",
            expected_fail_locn=2,
        ),
    ]


class TestCaselessLiteral(PyparsingExpressionTestCase):
    tests = [
        PyparsingTest(
            desc="Match colors, converting to consistent case",
            expr=(
                pp.CaselessLiteral("RED")
                | pp.CaselessLiteral("GREEN")
                | pp.CaselessLiteral("BLUE")
            )[...],
            text="red Green BluE blue GREEN green rEd",
            expected_list=["RED", "GREEN", "BLUE", "BLUE", "GREEN", "GREEN", "RED"],
        ),
    ]


class TestWord(PyparsingExpressionTestCase):
    tests = [
        PyparsingTest(
            desc="Simple Word match",
            expr=pp.Word("xy"),
            text="xxyxxyy",
            expected_list=["xxyxxyy"],
        ),
        PyparsingTest(
            desc="Simple Word match of two separate Words",
            expr=pp.Word("x") + pp.Word("y"),
            text="xxxxxyy",
            expected_list=["xxxxx", "yy"],
        ),
        PyparsingTest(
            desc="Simple Word match of two separate Words - implicitly skips whitespace",
            expr=pp.Word("x") + pp.Word("y"),
            text="xxxxx yy",
            expected_list=["xxxxx", "yy"],
        ),
    ]


class TestCombine(PyparsingExpressionTestCase):
    tests = [
        PyparsingTest(
            desc="Parsing real numbers - fail, parsed numbers are in pieces",
            expr=(pp.Word(pp.nums) + "." + pp.Word(pp.nums))[...],
            text="1.2 2.3 3.1416 98.6",
            # fmt: off
            expected_list=["1", ".", "2", "2", ".", "3", "3", ".", "1416", "98", ".", "6"],
            # fmt: on
        ),
        PyparsingTest(
            desc="Parsing real numbers - better, use Combine to combine multiple tokens into one",
            expr=pp.Combine(pp.Word(pp.nums) + "." + pp.Word(pp.nums))[...],
            text="1.2 2.3 3.1416 98.6",
            expected_list=["1.2", "2.3", "3.1416", "98.6"],
        ),
    ]


class TestRepetition(PyparsingExpressionTestCase):
    tests = [
        PyparsingTest(
            desc="Match several words",
            expr=(pp.Word("x") | pp.Word("y"))[...],
            text="xxyxxyyxxyxyxxxy",
            expected_list=["xx", "y", "xx", "yy", "xx", "y", "x", "y", "xxx", "y"],
        ),
        PyparsingTest(
            desc="Match several words, skipping whitespace",
            expr=(pp.Word("x") | pp.Word("y"))[...],
            text="x x  y xxy yxx y xyx  xxy",
            # fmt: off
            expected_list=["x", "x", "y", "xx", "y", "y", "xx", "y", "x", "y", "x", "xx", "y"],
            # fmt: on
        ),
        PyparsingTest(
            desc="Match several words, skipping whitespace (old style)",
            expr=pp.OneOrMore(pp.Word("x") | pp.Word("y")),
            text="x x  y xxy yxx y xyx  xxy",
            # fmt: off
            expected_list=["x", "x", "y", "xx", "y", "y", "xx", "y", "x", "y", "x", "xx", "y"],
            # fmt: on
        ),
        PyparsingTest(
            desc="Match words and numbers - show use of results names to collect types of tokens",
            expr=(pp.Word(pp.alphas)("alpha*") | pp.pyparsing_common.integer("int*"))[
                ...
            ],
            text="sdlfj23084ksdfs08234kjsdlfkjd0934",
            expected_list=["sdlfj", 23084, "ksdfs", 8234, "kjsdlfkjd", 934],
            expected_dict={
                "alpha": ["sdlfj", "ksdfs", "kjsdlfkjd"],
                "int": [23084, 8234, 934],
            },
        ),
        PyparsingTest(
            desc="Using DelimitedList (comma is the default delimiter)",
            expr=pp.DelimitedList(pp.Word(pp.alphas)),
            text="xxyx,xy,y,xxyx,yxx, xy",
            expected_list=["xxyx", "xy", "y", "xxyx", "yxx", "xy"],
        ),
        PyparsingTest(
            desc="Using DelimitedList (comma is the default delimiter) with trailing delimiter",
            expr=pp.DelimitedList(pp.Word(pp.alphas), allow_trailing_delim=True),
            text="xxyx,xy,y,xxyx,yxx, xy,",
            expected_list=["xxyx", "xy", "y", "xxyx", "yxx", "xy"],
        ),
        PyparsingTest(
            desc="Using DelimitedList (comma is the default delimiter) with minimum size",
            expr=pp.DelimitedList(pp.Word(pp.alphas), min=3),
            text="xxyx,xy",
            expected_fail_locn=7,
        ),
        PyparsingTest(
            desc="Using DelimitedList (comma is the default delimiter) with maximum size",
            expr=pp.DelimitedList(pp.Word(pp.alphas), max=3),
            text="xxyx,xy,y,xxyx,yxx, xy,",
            expected_list=["xxyx", "xy", "y"],
        ),
        PyparsingTest(
            desc="Using DelimitedList, with ':' delimiter",
            expr=pp.DelimitedList(
                pp.Word(pp.hexnums, exact=2), delim=":", combine=True
            ),
            text="0A:4B:73:21:FE:76",
            expected_list=["0A:4B:73:21:FE:76"],
        ),
        PyparsingTest(
            desc="Using DelimitedList, with ':' delimiter",
            expr=pp.DelimitedList(
                pp.Word(pp.hexnums, exact=2),
                delim=":",
                combine=True,
                allow_trailing_delim=True,
            ),
            text="0A:4B:73:21:FE:76:",
            expected_list=["0A:4B:73:21:FE:76:"],
        ),
    ]


class TestResultsName(PyparsingExpressionTestCase):
    tests = [
        PyparsingTest(
            desc="Match with results name",
            expr=pp.Literal("xyz").set_results_name("value"),
            text="xyz",
            expected_dict={"value": "xyz"},
            expected_list=["xyz"],
        ),
        PyparsingTest(
            desc="Match with results name - using naming short-cut",
            expr=pp.Literal("xyz")("value"),
            text="xyz",
            expected_dict={"value": "xyz"},
            expected_list=["xyz"],
        ),
        PyparsingTest(
            desc="Define multiple results names",
            expr=pp.Word(pp.alphas, pp.alphanums)("key")
            + "="
            + pp.pyparsing_common.integer("value"),
            text="range=5280",
            expected_dict={"key": "range", "value": 5280},
            expected_list=["range", "=", 5280],
        ),
    ]


class TestGroups(PyparsingExpressionTestCase):
    EQ = pp.Suppress("=")
    tests = [
        PyparsingTest(
            desc="Define multiple results names in groups",
            expr=pp.Group(
                pp.Word(pp.alphas)("key") + EQ + pp.pyparsing_common.number("value")
            )[...],
            text="range=5280 long=-138.52 lat=46.91",
            expected_list=[["range", 5280], ["long", -138.52], ["lat", 46.91]],
        ),
        PyparsingTest(
            desc=(
                "Define multiple results names in groups"
                " - use Dict to define results names using parsed keys"
            ),
            expr=pp.Dict(
                pp.Group(pp.Word(pp.alphas) + EQ + pp.pyparsing_common.number)[...]
            ),
            text="range=5280 long=-138.52 lat=46.91",
            expected_list=[["range", 5280], ["long", -138.52], ["lat", 46.91]],
            expected_dict={"lat": 46.91, "long": -138.52, "range": 5280},
        ),
        PyparsingTest(
            desc="Define multiple value types",
            expr=pp.Dict(
                pp.Group(
                    pp.Word(pp.alphas)
                    + EQ
                    + (
                        pp.pyparsing_common.number
                        | pp.oneOf("True False")
                        | pp.QuotedString("'")
                    )
                )[...]
            ),
            text="long=-122.47 lat=37.82 public=True name='Golden Gate Bridge'",
            expected_list=[
                ["long", -122.47],
                ["lat", 37.82],
                ["public", "True"],
                ["name", "Golden Gate Bridge"],
            ],
            expected_dict={
                "long": -122.47,
                "lat": 37.82,
                "public": "True",
                "name": "Golden Gate Bridge",
            },
        ),
    ]


class TestParseAction(PyparsingExpressionTestCase):
    tests = [
        PyparsingTest(
            desc="Parsing real numbers - use parse action to convert to float at parse time",
            expr=pp.Combine(pp.Word(pp.nums) + "." + pp.Word(pp.nums)).add_parse_action(
                lambda t: float(t[0])
            )[...],
            text="1.2 2.3 3.1416 98.6",
            # note, these are now floats, not strs
            expected_list=[1.2, 2.3, 3.1416, 98.6],
        ),
        PyparsingTest(
            desc="Match with numeric string converted to int",
            expr=pp.Word("0123456789").addParseAction(lambda t: int(t[0])),
            text="12345",
            expected_list=[12345],  # note - result is type int, not str
        ),
        PyparsingTest(
            desc="Use two parse actions to convert numeric string, then convert to datetime",
            expr=pp.Word(pp.nums).add_parse_action(
                lambda t: int(t[0]),
                lambda t: datetime.fromtimestamp(t[0], timezone.utc),
            ),
            text="1537415628",
            expected_list=[datetime(2018, 9, 20, 3, 53, 48, tzinfo=timezone.utc)],
        ),
        PyparsingTest(
            desc="Use tokenMap for parse actions that operate on a single-length token",
            expr=pp.Word(pp.nums).add_parse_action(
                pp.token_map(int),
                pp.token_map(lambda t: datetime.fromtimestamp(t, timezone.utc)),
            ),
            text="1537415628",
            expected_list=[datetime(2018, 9, 20, 3, 53, 48, tzinfo=timezone.utc)],
        ),
        PyparsingTest(
            desc="Using a built-in function that takes a sequence of strs as a parse action",
            expr=pp.Word(pp.hexnums, exact=2)[...].add_parse_action(":".join),
            text="0A4B7321FE76",
            expected_list=["0A:4B:73:21:FE:76"],
        ),
        PyparsingTest(
            desc="Using a built-in function that takes a sequence of strs as a parse action",
            expr=pp.Word(pp.hexnums, exact=2)[...].add_parse_action(sorted),
            text="0A4B7321FE76",
            expected_list=["0A", "21", "4B", "73", "76", "FE"],
        ),
    ]


class TestResultsModifyingParseAction(PyparsingExpressionTestCase):
    # do not make staticmethod
    # @staticmethod
    def compute_stats_parse_action(t):
        # by the time this parse action is called, parsed numeric words
        # have been converted to ints by a previous parse action, so
        # they can be treated as ints
        t["sum"] = sum(t)
        t["ave"] = sum(t) / len(t)
        t["min"] = min(t)
        t["max"] = max(t)

    tests = [
        PyparsingTest(
            desc="A parse action that adds new key-values",
            expr=pp.pyparsing_common.integer[...].addParseAction(
                compute_stats_parse_action
            ),
            text="27 1 14 22 89",
            expected_list=[27, 1, 14, 22, 89],
            expected_dict={"ave": 30.6, "max": 89, "min": 1, "sum": 153},
        ),
    ]


class TestRegex(PyparsingExpressionTestCase):
    tests = [
        PyparsingTest(
            desc="Parsing real numbers - using Regex instead of Combine",
            expr=pp.Regex(r"\d+\.\d+").add_parse_action(lambda t: float(t[0]))[...],
            text="1.2 2.3 3.1416 98.6",
            # note, these are now floats, not strs
            expected_list=[1.2, 2.3, 3.1416, 98.6],
        ),
    ]


class TestParseCondition(PyparsingExpressionTestCase):
    tests = [
        PyparsingTest(
            desc="Define a condition to only match numeric values that are multiples of 7",
            expr=pp.Word(pp.nums).addCondition(lambda t: int(t[0]) % 7 == 0)[...],
            text="14 35 77 12 28",
            expected_list=["14", "35", "77"],
        ),
        PyparsingTest(
            desc="Separate conversion to int and condition into separate parse action/conditions",
            expr=pp.Word(pp.nums)
            .add_parse_action(lambda t: int(t[0]))
            .add_condition(lambda t: t[0] % 7 == 0)[...],
            text="14 35 77 12 28",
            expected_list=[14, 35, 77],
        ),
    ]


class TestTransformStringUsingParseActions(PyparsingExpressionTestCase):
    markup_convert_map = {
        "*": "B",
        "_": "U",
        "/": "I",
    }

    # do not make staticmethod
    # @staticmethod
    def markup_convert(t):
        htmltag = TestTransformStringUsingParseActions.markup_convert_map[
            t.markup_symbol
        ]
        return f"<{htmltag}>{t.body}</{htmltag}>"

    tests = [
        PyparsingTest(
            desc="Use transformString to convert simple markup to HTML",
            expr=(
                pp.one_of(markup_convert_map)("markup_symbol")
                + "("
                + pp.CharsNotIn(")")("body")
                + ")"
            ).add_parse_action(markup_convert),
            text="Show in *(bold), _(underscore), or /(italic) type",
            expected_list=[
                "Show in <B>bold</B>, <U>underscore</U>, or <I>italic</I> type"
            ],
            parse_fn="transformString",
        ),
    ]


class TestCommonHelperExpressions(PyparsingExpressionTestCase):
    tests = [
        PyparsingTest(
            desc="A comma-delimited list of words",
            expr=pp.DelimitedList(pp.Word(pp.alphas)),
            text="this, that, blah,foo,   bar",
            expected_list=["this", "that", "blah", "foo", "bar"],
        ),
        PyparsingTest(
            desc="A counted array of words",
            expr=pp.Group(pp.counted_array(pp.Word("ab")))[...],
            text="2 aaa bbb 0 3 abab bbaa abbab",
            expected_list=[["aaa", "bbb"], [], ["abab", "bbaa", "abbab"]],
        ),
        PyparsingTest(
            desc="skipping comments with ignore",
            expr=(
                pp.pyparsing_common.identifier("lhs")
                + "="
                + pp.pyparsing_common.fnumber("rhs")
            ).ignore(pp.cpp_style_comment),
            text="abc_100 = /* value to be tested */ 3.1416",
            expected_list=["abc_100", "=", 3.1416],
            expected_dict={"lhs": "abc_100", "rhs": 3.1416},
        ),
        PyparsingTest(
            desc=(
                "some pre-defined expressions in pyparsing_common, and"
                " building a dotted identifier with DelimitedList"
            ),
            expr=(
                pp.pyparsing_common.number("id_num")
                + pp.DelimitedList(pp.pyparsing_common.identifier, ".", combine=True)(
                    "name"
                )
                + pp.pyparsing_common.ipv4_address("ip_address")
            ),
            text="1001 www.google.com 192.168.10.199",
            expected_list=[1001, "www.google.com", "192.168.10.199"],
            expected_dict={
                "id_num": 1001,
                "name": "www.google.com",
                "ip_address": "192.168.10.199",
            },
        ),
        PyparsingTest(
            desc="using one_of (shortcut for Literal('a') | Literal('b') | Literal('c'))",
            expr=pp.one_of("a b c")[...],
            text="a b a b b a c c a b b",
            expected_list=["a", "b", "a", "b", "b", "a", "c", "c", "a", "b", "b"],
        ),
        PyparsingTest(
            desc="parsing nested parentheses",
            expr=pp.nested_expr(),
            text="(a b (c) d (e f g ()))",
            expected_list=[["a", "b", ["c"], "d", ["e", "f", "g", []]]],
        ),
        PyparsingTest(
            desc="parsing nested braces",
            expr=(
                pp.Keyword("if")
                + pp.nested_expr()("condition")
                + pp.nested_expr("{", "}")("body")
            ),
            text='if ((x == y) || !z) {printf("{}");}',
            expected_list=[
                "if",
                [["x", "==", "y"], "||", "!z"],
                ["printf(", '"{}"', ");"],
            ],
            expected_dict={
                "condition": [[["x", "==", "y"], "||", "!z"]],
                "body": [["printf(", '"{}"', ");"]],
            },
        ),
    ]


class TestWhitespaceMethods(PyparsingExpressionTestCase):
    tests = [
        # These test the single-element versions
        PyparsingTest(
            desc="The word foo",
            expr=pp.Literal("foo").ignore_whitespace(),
            text="      foo        ",
            expected_list=["foo"],
        ),
        PyparsingTest(
            desc="The word foo",
            expr=pp.Literal("foo").leave_whitespace(),
            text="      foo        ",
            expected_fail_locn=0,
        ),
        PyparsingTest(
            desc="The word foo",
            expr=pp.Literal("foo").ignore_whitespace(),
            text="foo",
            expected_list=["foo"],
        ),
        PyparsingTest(
            desc="The word foo",
            expr=pp.Literal("foo").leave_whitespace(),
            text="foo",
            expected_list=["foo"],
        ),
        # These test the composite elements
        PyparsingTest(
            desc=(
                "If we recursively leave whitespace on the parent, this"
                " whitespace-dependent grammar will succeed, even if the"
                " children themselves skip whitespace"
            ),
            expr=pp.And(
                [
                    pp.Literal(" foo").ignore_whitespace(),
                    pp.Literal(" bar").ignore_whitespace(),
                ]
            ).leave_whitespace(recursive=True),
            text=" foo bar",
            expected_list=[" foo", " bar"],
        ),
        #
        PyparsingTest(
            desc=(
                "If we recursively ignore whitespace in our parsing, this"
                " whitespace-dependent grammar will fail, even if the children"
                " themselves keep whitespace"
            ),
            expr=pp.And(
                [
                    pp.Literal(" foo").leave_whitespace(),
                    pp.Literal(" bar").leave_whitespace(),
                ]
            ).ignore_whitespace(recursive=True),
            text=" foo bar",
            expected_fail_locn=1,
        ),
        PyparsingTest(
            desc=(
                "If we leave whitespace on the parent, but it isn't recursive,"
                " this whitespace-dependent grammar will fail"
            ),
            expr=pp.And(
                [
                    pp.Literal(" foo").ignore_whitespace(),
                    pp.Literal(" bar").ignore_whitespace(),
                ]
            ).leave_whitespace(recursive=False),
            text=" foo bar",
            expected_fail_locn=5,
        ),
        # These test the Enhance classes
        PyparsingTest(
            desc=(
                "If we recursively leave whitespace on the parent,"
                " this whitespace-dependent grammar will succeed, even"
                " if the children themselves skip whitespace"
            ),
            expr=pp.Optional(pp.Literal(" foo").ignore_whitespace()).leave_whitespace(
                recursive=True
            ),
            text=" foo",
            expected_list=[" foo"],
        ),
        #
        PyparsingTest(
            desc=(
                "If we ignore whitespace on the parent, but it isn't recursive,"
                " parsing will fail because we skip to the first character"
                " 'f' before the internal expr can see it"
            ),
            expr=pp.Optional(pp.Literal(" foo").leave_whitespace()).ignore_whitespace(
                recursive=True
            ),
            text=" foo",
            expected_list=[],
        ),
        # PyparsingTest(
        #     desc=(
        #         "If we leave whitespace on the parent, this whitespace-dependent"
        #         " grammar will succeed, even if the children themselves skip whitespace"
        #     ),
        #     expr=pp.Optional(pp.Literal(" foo").ignoreWhitespace()).leaveWhitespace(
        #         recursive=False
        #     ),
        #     text=" foo",
        #     expected_list=[]
        # ),
    ]


def _get_decl_line_no(cls):
    import inspect

    return inspect.getsourcelines(cls)[1]


# get all test case classes defined in this module and sort them by decl line no
test_case_classes = list(PyparsingExpressionTestCase.__subclasses__())
test_case_classes.sort(key=_get_decl_line_no)

# make into a suite and run it - this will run the tests in the same order
# they are declared in this module
#
# runnable from setup.py using "python setup.py test -s simple_unit_tests.suite"
#
suite = unittest.TestSuite(cls() for cls in test_case_classes)


# ============ MAIN ================

if __name__ == "__main__":

    result = unittest.TextTestRunner().run(suite)

    exit(0 if result.wasSuccessful() else 1)
