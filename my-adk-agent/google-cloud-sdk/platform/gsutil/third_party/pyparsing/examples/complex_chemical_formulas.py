#
# complex_chemical_formulas.py
#
# Example that expands on the basic chemical_formulas.py parser to
# include grouped multiplication notation, such as "3(C₆H₅OH)₂".
#
# Copyright (c) 2024, Paul McGuire
#

from collections import Counter

import pyparsing as pp

ppc = pp.common

# fmt: off
table_of_elements: dict[str, float] = {
    "H": 1.007, "He": 4.002, "Li": 6.941, "Be": 9.012, "B": 10.811, "C": 12.011,
    "N": 14.007, "O": 15.999, "F": 18.998, "Ne": 20.18, "Na": 22.99, "Mg": 24.305,
    "Al": 26.982, "Si": 28.086, "P": 30.974, "S": 32.065, "Cl": 35.453, "Ar": 39.948,
    "K": 39.098, "Ca": 40.078, "Sc": 44.956, "Ti": 47.867, "V": 50.942, "Cr": 51.996,
    "Mn": 54.938, "Fe": 55.845, "Co": 58.933, "Ni": 58.693, "Cu": 63.546, "Zn": 65.38,
    "Ga": 69.723, "Ge": 72.64, "As": 74.922, "Se": 78.96, "Br": 79.904, "Kr": 83.798,
    "Rb": 85.468, "Sr": 87.62, "Y": 88.906, "Zr": 91.224, "Nb": 92.906, "Mo": 95.96,
    "Tc": 98.0, "Ru": 101.07, "Rh": 102.906, "Pd": 106.42, "Ag": 107.868,
    "Cd": 112.411, "In": 114.818, "Sn": 118.71, "Sb": 121.76, "Te": 127.6,
    "I": 126.904, "Xe": 131.293, "Cs": 132.905, "Ba": 137.327, "La": 138.905,
    "Ce": 140.116, "Pr": 140.908, "Nd": 144.242, "Pm": 145.0, "Sm": 150.36,
    "Eu": 151.964, "Gd": 157.25, "Tb": 158.925, "Dy": 162.5, "Ho": 164.93,
    "Er": 167.259, "Tm": 168.934, "Yb": 173.054, "Lu": 174.967, "Hf": 178.49,
    "Ta": 180.948, "W": 183.84, "Re": 186.207, "Os": 190.23, "Ir": 192.217,
    "Pt": 195.084, "Au": 196.967, "Hg": 200.59, "Tl": 204.383, "Pb": 207.2,
    "Bi": 208.98, "Po": 210.0, "At": 210.0, "Rn": 222.0, "Fr": 223.0, "Ra": 226.0,
    "Ac": 227.0, "Th": 232.038, "Pa": 231.036, "U": 238.029, "Np": 237.0,
    "Pu": 244.0, "Am": 243.0, "Cm": 247.0, "Bk": 247.0, "Cf": 251.0, "Es": 252.0,
    "Fm": 257.0, "Md": 258.0, "No": 259.0, "Lr": 262.0, "Rf": 261.0, "Db": 262.0,
    "Sg": 266.0, "Bh": 264.0, "Hs": 267.0, "Mt": 268.0, "Ds": 271.0, "Rg": 272.0,
    "Cn": 285.0, "Nh": 284.0, "Fl": 289.0, "Mc": 288.0, "Lv": 292.0, "Ts": 295.0,
    "Og": 294.0,
}
# fmt: on

# basic parser elements
#  - element - a chemical symbol, corresponding to one of the entries
#    in table_of_elements
#  - subcript_int - an integer made up of subscript digits
#  (a normal integer definition uses the one defined in pyparsing.common)
#
# element = pp.one_of(table_of_elements).set_name("element")
element = pp.Regex(pp.util.make_compressed_re(table_of_elements)).set_name("element")
element.add_parse_action(lambda t: Counter([t[0]]))

subscript_digits = "₀₁₂₃₄₅₆₇₈₉"
subscript_int = pp.Word(subscript_digits).set_name("subscript")

# define mapping of the int value of each subscript digit
subscript_int_map = {digit: value for value, digit in enumerate(subscript_digits)}

@subscript_int.add_parse_action
def convert_subscript_int(s: pp.ParseResults) -> int:
    ret = 0
    for c in s[0]:
        ret = ret * 10 + subscript_int_map[c]
    return ret

#
# parse actions used internally by the infix_notation expression
#

def lmult(s, l, t):
    """
    Multiply <element><subscript_integer>
    """
    *terms, qty = t[0]
    return sum(qty * terms, Counter())


def rmult(s, l, t):
    """
    Multiply <integer><element>
    """
    qty, *terms = t[0]
    return sum(qty * terms, Counter())


def element_ref_sum(s, l, t):
    """
    Add multiple consecutive element references
    """
    return sum(t[0], Counter())


# optional separator in some chemical formulas
optional_separator = pp.Optional(pp.one_of("= ·").suppress())

# define infix expression, where multipliers and subscripts
# are treated like operators, so that grouping in ()'s gets
# properly handled, even when they are nested
element_ref = pp.infix_notation(
    element,
    [
        (subscript_int, 1, pp.OpAssoc.LEFT, lmult),
        (ppc.integer, 1, pp.OpAssoc.RIGHT, rmult),
        (optional_separator, 2, pp.OpAssoc.LEFT, element_ref_sum),
    ],
)

# define the overall parser for a chemical formula, made up
# of one or more element_ref's
formula = element_ref[1, ...].set_name("chemical_formula")

# set names on unnamed expressions for better diagram output
pp.autoname_elements()


def molecular_weight(c: Counter) -> float:
    """
    Compute overall molecular weight of a chemical formula,
    whose elements have been parsed into a Counter containing
    chemical symbols and counts of each element, using
    the table_of_elements dict to map chemical symbols to
    each element's atomic weight.
    """
    return sum(table_of_elements[k] * v for k, v in c.items())

if __name__ == '__main__':
    import contextlib

    # create railroad diagram for this parser
    with contextlib.suppress(Exception):
        formula.create_diagram(
            "complex_chemical_formulas_diagram.html", vertical=2, show_groups=True
        )

    formula.run_tests(
        """\
        NaCl
        HOH
        H₂O
        H₂O₂
        C₆H₅OH
        C₁₀H₂₁OH
        (C₆H₅OH)₂
        3(C₆H₅OH)₂
        C(OH)₆
        CH₃(CH₂)₂OH
        (CH₃)₃CH
        CH₃(CH₂)₅CH₃
        Ba(BrO₃)₂·H₂O
        Ba(BrO₃)₂·2(H₂O)
        """,
        full_dump=False,
        post_parse=(
            lambda _, tokens:
            f"Molecular counts/weight: {dict(tokens[0])}"
            f", {molecular_weight(tokens[0]):.3f}"
        ),
    )
    print()
