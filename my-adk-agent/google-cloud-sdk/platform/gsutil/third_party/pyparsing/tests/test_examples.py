#
# test_examples.py
#
from importlib import import_module
import unittest

from pyparsing import testing as ppt


class TestExamples(unittest.TestCase):
    def _run(self, name):
        mod = import_module("examples." + name)

        # use pyparsing context to reset each test to clean
        # pyparsing settings
        with ppt.reset_pyparsing_context():
            getattr(mod, "main", lambda *args, **kwargs: None)()

    def test_numerics(self):
        self._run("numerics")

    def test_parse_python_value(self):
        self._run("parse_python_value")

    def test_tap(self):
        self._run("TAP")

    def test_roman_numerals(self):
        self._run("roman_numerals")

    def test_sexp_parser(self):
        self._run("sexpParser")

    def test_oc(self):
        self._run("oc")

    def test_delta_time(self):
        self._run("delta_time")

    def test_eval_arith(self):
        self._run("eval_arith")

    def test_select_parser(self):
        self._run("select_parser")

    def test_booleansearchparser(self):
        self._run("booleansearchparser")

    def test_rosettacode(self):
        self._run("rosettacode")

    def test_excelExpr(self):
        self._run("excel_expr")

    def test_lucene_grammar(self):
        self._run("lucene_grammar")

    def test_range_check(self):
        self._run("range_check")

    def test_stackish(self):
        self._run("stackish")

    def test_email_parser(self):
        self._run("email_address_parser")

    def test_mongodb_query_parser(self):
        self._run("mongodb_query_expression")

    def test_lox_parser(self):
        self._run("lox_parser")
