#
# tests copied from matplotlib.tests.test_mathtext
#
import platform
import re

import pytest

try:
    import matplotlib.mathtext as mpl_mathtext
except ImportError:
    mpl_mathtext = None

# fmt: off
@pytest.mark.parametrize(
    "math, msg",
    [
        (r"$\hspace{}$", r"Expected \hspace{space}"),
        (r"$\hspace{foo}$", r"Expected \hspace{space}"),
        (r"$\sinx$", r"Unknown symbol: \sinx"),
        (r"$\dotx$", r"Unknown symbol: \dotx"),
        (r"$\frac$", r"Expected \frac{num}{den}"),
        (r"$\frac{}{}$", r"Expected \frac{num}{den}"),
        (r"$\binom$", r"Expected \binom{num}{den}"),
        (r"$\binom{}{}$", r"Expected \binom{num}{den}"),
        (r"$\genfrac$", r"Expected \genfrac{ldelim}{rdelim}{rulesize}{style}{num}{den}"),
        (r"$\genfrac{}{}{}{}{}{}$", r"Expected \genfrac{ldelim}{rdelim}{rulesize}{style}{num}{den}"),
        (r"$\sqrt$", r"Expected \sqrt{value}"),
        (r"$\sqrt f$", r"Expected \sqrt{value}"),
        (r"$\overline$", r"Expected \overline{body}"),
        (r"$\overline{}$", r"Expected \overline{body}"),
        (r"$\leftF$", r"Expected a delimiter"),
        (r"$\rightF$", r"Unknown symbol: \rightF"),
        (r"$\left(\right$", r"Expected a delimiter"),
        # PyParsing 2 uses double quotes, PyParsing 3 uses single quotes and an
        # extra backslash.
        (r"$\left($", re.compile(r'Expected ("|\'\\)\\right["\']')),
        (r"$\dfrac$", r"Expected \dfrac{num}{den}"),
        (r"$\dfrac{}{}$", r"Expected \dfrac{num}{den}"),
        (r"$\overset$", r"Expected \overset{annotation}{body}"),
        (r"$\underset$", r"Expected \underset{annotation}{body}"),
        (r"$\foo$", r"Unknown symbol: \foo"),
        (r"$a^2^2$", r"Double superscript"),
        (r"$a_2_2$", r"Double subscript"),
        (r"$a^2_a^2$", r"Double superscript"),
    ],
    ids=[
        "hspace without value",
        "hspace with invalid value",
        "function without space",
        "accent without space",
        "frac without parameters",
        "frac with empty parameters",
        "binom without parameters",
        "binom with empty parameters",
        "genfrac without parameters",
        "genfrac with empty parameters",
        "sqrt without parameters",
        "sqrt with invalid value",
        "overline without parameters",
        "overline with empty parameter",
        "left with invalid delimiter",
        "right with invalid delimiter",
        "unclosed parentheses with sizing",
        "unclosed parentheses without sizing",
        "dfrac without parameters",
        "dfrac with empty parameters",
        "overset without parameters",
        "underset without parameters",
        "unknown symbol",
        "double superscript",
        "double subscript",
        "super on sub without braces",
    ],
)
@pytest.mark.skipif("mpl_mathtext is None")
def test_mathtext_exceptions(math, msg):
    parser = mpl_mathtext.MathTextParser("agg")
    match = re.escape(msg) if isinstance(msg, str) else msg
    with pytest.raises(ValueError, match=match):
        parser.parse(math)
# fmt: on


@pytest.mark.skipif("mpl_mathtext is None")
def test_get_unicode_index_exception():
    with pytest.raises(ValueError):
        mpl_mathtext.get_unicode_index(r"\foo")
