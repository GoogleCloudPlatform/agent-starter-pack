#
# chemicalFormulas.py
#
# Copyright (c) 2003,2019 Paul McGuire
#

import pyparsing as pp

atomic_weight = {
    "O": 15.9994,
    "H": 1.00794,
    "Na": 22.9897,
    "Cl": 35.4527,
    "C": 12.0107,
}

digits = "0123456789"

# Version 1
element = pp.Word(pp.alphas.upper(), pp.alphas.lower(), max=2).set_name("element")
# for stricter matching, use this Regex instead
# element = Regex("A[cglmrstu]|B[aehikr]?|C[adeflmorsu]?|D[bsy]|"
#                 "E[rsu]|F[emr]?|G[ade]|H[efgos]?|I[nr]?|Kr?|L[airu]|"
#                 "M[dgnot]|N[abdeiop]?|Os?|P[abdmortu]?|R[abefghnu]|"
#                 "S[bcegimnr]?|T[abcehilm]|U(u[bhopqst])?|V|W|Xe|Yb?|Z[nr]")
element_ref = pp.Group(element + pp.Optional(pp.Word(digits), default="1"))
formula = element_ref[...]


def sum_atomic_weights(element_list):
    return sum(atomic_weight[elem] * int(qty) for elem, qty in element_list)


formula.run_tests(
    """\
    NaCl
    H2O
    C6H5OH
    """,
    full_dump=False,
    post_parse=lambda _, tokens: f"Molecular weight: {sum_atomic_weights(tokens)}",
)
print()


# Version 2 - access parsed items by results name
element_ref = pp.Group(
    element("symbol") + pp.Optional(pp.Word(digits), default="1")("qty")
)
formula = element_ref[...]


def sum_atomic_weights_by_results_name(element_list):
    return sum(atomic_weight[elem.symbol] * int(elem.qty) for elem in element_list)


formula.run_tests(
    """\
    NaCl
    H2O
    C6H5OH
    """,
    full_dump=False,
    post_parse=lambda _, tokens:
        f"Molecular weight: {sum_atomic_weights_by_results_name(tokens)}",
)
print()

# Version 3 - convert integers during parsing process
integer = pp.Word(digits).set_name("integer")
integer.add_parse_action(lambda t: int(t[0]))
element_ref = pp.Group(element("symbol") + pp.Optional(integer, default=1)("qty"))
formula = element_ref[...].set_name("chemical_formula")


def sum_atomic_weights_by_results_name_with_converted_ints(element_list):
    return sum(atomic_weight[elem.symbol] * int(elem.qty) for elem in element_list)


formula.run_tests(
    """\
    NaCl
    H2O
    C6H5OH
    """,
    full_dump=False,
    post_parse=lambda _, tokens:
        f"Molecular weight: {sum_atomic_weights_by_results_name_with_converted_ints(tokens)}",
)
print()

# Version 4 - parse and convert integers as subscript digits
subscript_digits = "₀₁₂₃₄₅₆₇₈₉"
subscript_int_map = {digit: value for value, digit in enumerate(subscript_digits)}


def cvt_subscript_int(s):
    ret = 0
    for c in s[0]:
        ret = ret * 10 + subscript_int_map[c]
    return ret


subscript_int = pp.Word(subscript_digits).set_name("subscript")
subscript_int.add_parse_action(cvt_subscript_int)

element_ref = pp.Group(element("symbol") + pp.Optional(subscript_int, default=1)("qty"))
formula = element_ref[1, ...].set_name("chemical_formula")

if __name__ == '__main__':
    import contextlib

    with contextlib.suppress(Exception):
        formula.create_diagram("chemical_formulas.html")

    formula.run_tests(
        """\
        # sodium chloride
        NaCl
        # hydrogen hydroxide
        H₂O
        # phenol
        C₆H₅OH
        # ethanol
        C₂H₅OH
        # decanol
        C₁₀H₂₁OH
        """,
        full_dump=False,
        post_parse=lambda _, tokens:
            f"Molecular weight: {sum_atomic_weights_by_results_name_with_converted_ints(tokens)}",
    )

    print()
