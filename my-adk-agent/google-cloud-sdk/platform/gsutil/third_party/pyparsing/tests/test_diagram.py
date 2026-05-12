import unittest
from io import StringIO
from pathlib import Path
from typing import List

from examples.jsonParser import jsonObject
from examples.simpleBool import boolExpr
from examples.simpleSQL import simpleSQL
from examples.mozillaCalendarParser import calendars
from pyparsing.diagram import to_railroad, railroad_to_html, NamedDiagram, AnnotatedItem
import pyparsing as pp
import railroad
import tempfile
import os
import sys


print(f"Running {__file__}")
print(sys.version_info)

curdir = Path(__file__).parent


def is_run_with_coverage():
    """Check whether test is run with coverage.
    From https://stackoverflow.com/a/69812849/165216
    """
    gettrace = getattr(sys, "gettrace", None)

    if gettrace is None:
        return False
    else:
        gettrace_result = gettrace()

    try:
        from coverage.pytracer import PyTracer
        from coverage.tracer import CTracer

        if isinstance(gettrace_result, (CTracer, PyTracer)):
            return True
    except ImportError:
        pass

    return False


def running_in_debug() -> bool:
    """
    Returns True if we're in debug mode (determined by either setting
    environment var, or running in a debugger which sets sys.settrace)
    """
    return (
        os.environ.get("RAILROAD_DEBUG", False)
        or sys.gettrace()
        and not is_run_with_coverage()
    )


class TestRailroadDiagrams(unittest.TestCase):
    def get_temp(self):
        """
        Returns an appropriate temporary file for writing a railroad diagram
        """
        delete_on_close = not running_in_debug()
        return tempfile.NamedTemporaryFile(
            dir=".",
            delete=delete_on_close,
            mode="w",
            encoding="utf-8",
            suffix=".html",
        )

    def generate_railroad(
        self, expr: pp.ParserElement, label: str, show_results_names: bool = False
    ) -> List[NamedDiagram]:
        """
        Generate an intermediate list of NamedDiagrams from a pyparsing expression.
        """
        with self.get_temp() as temp:
            railroad = to_railroad(expr, show_results_names=show_results_names)
            temp.write(railroad_to_html(railroad))

        if running_in_debug():
            print(f"{label}: {temp.name}")

        return railroad

    def test_example_rr_diags(self):
        subtests = [
            ("jsonObject", jsonObject, 8),
            ("boolExpr", boolExpr, 6),
            ("simpleSQL", simpleSQL, 20),
            ("calendars", calendars, 13),
        ]
        for label, example_expr, expected_rr_len in subtests:
            with self.subTest(f"{label}: test rr diag without results names"):
                railroad = self.generate_railroad(example_expr, example_expr)
                if len(railroad) != expected_rr_len:
                    diag_html = railroad_to_html(railroad)
                    for line in diag_html.splitlines():
                        if 'h1 class="railroad-heading"' in line:
                            print(line)
                assert (
                    len(railroad) == expected_rr_len
                ), f"expected {expected_rr_len}, got {len(railroad)}"

            with self.subTest(f"{label}: test rr diag with results names"):
                railroad = self.generate_railroad(
                    example_expr, example_expr, show_results_names=True
                )
                if len(railroad) != expected_rr_len:
                    print(railroad_to_html(railroad))
                assert (
                    len(railroad) == expected_rr_len
                ), f"expected {expected_rr_len}, got {len(railroad)}"

    def test_nested_forward_with_inner_and_outer_names(self):
        outer = pp.Forward().setName("outer")
        inner = pp.Word(pp.alphas)[...].setName("inner")
        outer <<= inner

        railroad = self.generate_railroad(outer, "inner_outer_names")
        assert len(railroad) == 2
        railroad = self.generate_railroad(
            outer, "inner_outer_names", show_results_names=True
        )
        assert len(railroad) == 2

    def test_nested_forward_with_inner_name_only(self):
        outer = pp.Forward()
        inner = pp.Word(pp.alphas)[...].setName("inner")
        outer <<= inner

        railroad = self.generate_railroad(outer, "inner_only")
        assert len(railroad) == 1
        railroad = self.generate_railroad(outer, "inner_only", show_results_names=True)
        assert len(railroad) == 1

    def test_each_grammar(self):

        grammar = pp.Each(
            [
                pp.Word(pp.nums),
                pp.Word(pp.alphas),
                pp.pyparsing_common.uuid,
            ]
        ).setName("int-word-uuid in any order")
        railroad = self.generate_railroad(grammar, "each_expression")
        assert len(railroad) == 2
        railroad = self.generate_railroad(
            grammar, "each_expression", show_results_names=True
        )
        assert len(railroad) == 2

    def test_none_name(self):
        grammar = pp.Or(["foo", "bar"])
        railroad = to_railroad(grammar)
        assert len(railroad) == 1
        assert railroad[0].name is not None

    def test_none_name2(self):
        grammar = pp.Or(["foo", "bar"]) + pp.Word(pp.nums).setName("integer")
        railroad = to_railroad(grammar)
        assert len(railroad) == 2
        assert railroad[0].name is not None
        railroad = to_railroad(grammar, show_results_names=True)
        assert len(railroad) == 2

    def test_complete_combine_element(self):
        ints = pp.Word(pp.nums)
        grammar = pp.Combine(
            ints("hours") + ":" + ints("minutes") + ":" + ints("seconds")
        )
        railroad = to_railroad(grammar)
        assert len(railroad) == 1
        railroad = to_railroad(grammar, show_results_names=True)
        assert len(railroad) == 1

    def test_create_diagram(self):
        ints = pp.Word(pp.nums)
        grammar = pp.Combine(
            ints("hours") + ":" + ints("minutes") + ":" + ints("seconds")
        )

        diag_strio = StringIO()
        grammar.create_diagram(output_html=diag_strio)
        diag_str = diag_strio.getvalue().lower()
        tags = "<html> </html> <head> </head> <body> </body>".split()
        assert all(tag in diag_str for tag in tags)

    def test_create_diagram_embed(self):
        ints = pp.Word(pp.nums)
        grammar = pp.Combine(
            ints("hours") + ":" + ints("minutes") + ":" + ints("seconds")
        )

        diag_strio = StringIO()
        grammar.create_diagram(output_html=diag_strio, embed=True)
        diag_str = diag_strio.getvalue().lower()
        tags = "<html> </html> <head> </head> <body> </body>".split()
        assert not any(tag in diag_str for tag in tags)

    def test_create_diagram_for_oneormore_with_stopon(self):
        wd = pp.Word(pp.alphas)
        grammar = "start" + wd[1, ...:"end"] + "end"

        pp.autoname_elements()
        railroad_diag = to_railroad(grammar)
        assert len(railroad_diag) == 3
        assert isinstance(railroad_diag[1].diagram.items[1].item, railroad.Sequence)
        assert isinstance(
            railroad_diag[1].diagram.items[1].item.items[0], AnnotatedItem
        )
        assert isinstance(
            railroad_diag[1].diagram.items[1].item.items[1], railroad.NonTerminal
        )

    def test_kwargs_pass_thru_create_diagram(self):
        from io import StringIO

        # Creates a simple diagram with a blue body and
        # various other railroad features colored with
        # a complete disregard for taste

        # Very simple grammar for demo purposes
        salutation = pp.Word(pp.alphas).set_name("salutation")
        subject = pp.rest_of_line.set_name("subject")
        parse_grammar = salutation + subject

        # This is used to turn off the railroads
        # definition of DEFAULT_STYLE.
        # If this is set to 'None' the default style
        # will be written as part of each diagram
        # and will you will not be able to set the
        # css style globally and the string 'expStyle'
        # will have no effect.
        # There is probably a PR to railroad_diagram to
        # remove some cruft left in the SVG.
        DEFAULT_STYLE = ""

        # CSS Code to be placed into head of the html file
        expStyle = """
        <style type="text/css">

        body {
            background-color: blue;
        }

        .railroad-heading {
            font-family: monospace;
            color: bisque;
        }

        svg.railroad-diagram {
            background-color: hsl(264,45%,85%);
        }
        svg.railroad-diagram path {
            stroke-width: 3;
            stroke: green;
            fill: rgba(0,0,0,0);
        }
        svg.railroad-diagram text {
            font: bold 14px monospace;
            text-anchor: middle;
            white-space: pre;
        }
        svg.railroad-diagram text.diagram-text {
            font-size: 12px;
        }
        svg.railroad-diagram text.diagram-arrow {
            font-size: 16px;
        }
        svg.railroad-diagram text.label {
            text-anchor: start;
        }
        svg.railroad-diagram text.comment {
            font: italic 12px monospace;
        }
        svg.railroad-diagram g.non-terminal text {
            /*font-style: italic;*/
        }
        svg.railroad-diagram rect {
            stroke-width: 3;
            stroke: black;
            fill: hsl(55, 72%, 69%);
        }
        svg.railroad-diagram rect.group-box {
            stroke: rgb(33, 8, 225);
            stroke-dasharray: 10 5;
            fill: none;
        }
        svg.railroad-diagram path.diagram-text {
            stroke-width: 3;
            stroke: black;
            fill: white;
            cursor: help;
        }
        svg.railroad-diagram g.diagram-text:hover path.diagram-text {
            fill: #eee;
        }
        </style>
        """

        # the 'css=DEFAULT_STYLE' or 'css=""' is needed to turn off railroad_diagrams styling
        diag_html_capture = StringIO()
        parse_grammar.create_diagram(
            diag_html_capture,
            vertical=6,
            show_results_names=True,
            css=DEFAULT_STYLE,
            head=expStyle,
        )

        self.assertIn(expStyle, diag_html_capture.getvalue())


if __name__ == "__main__":
    unittest.main()
