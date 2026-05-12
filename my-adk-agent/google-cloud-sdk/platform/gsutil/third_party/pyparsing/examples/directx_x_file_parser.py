#
# directx_x_file_parser.py
#
# Parses .x files used for DirectX.
# Based on format documentation at http://paulbourke.net/dataformats/directx/
#
# Copyright 2024, Paul McGuire
#
import pyparsing as pp


LBRACE, RBRACE, LBRACK, RBRACK, SEMI = pp.Suppress.using_each("{}[];")

ident = pp.Word(pp.alphas, pp.alphanums + "_").set_name("identifier")
integer = pp.Word("123456789", pp.nums).add_parse_action(lambda t: int(t[0]))

# scalar_type = pp.one_of(
#     "WORD DWORD FLOAT DOUBLE CHAR UCHAR BYTE STRING CSTRING UNICODE", as_keyword=True
# ).set_name("base_type")
scalar_type = pp.MatchFirst(
    pp.Keyword.using_each(
        "WORD DWORD FLOAT DOUBLE CHAR UCHAR BYTE STRING CSTRING UNICODE".split()
    )
).set_name("scalar_type")
type_ref = scalar_type | ident

ARRAY = pp.Keyword("array")
array_type_ref = pp.Group(ARRAY + type_ref("element_type"))
array_dim = LBRACK + (integer | ident) + RBRACK
member_defn = pp.Group(
    (
        array_type_ref("type") + ident("name") + array_dim[...]("dims")
        | type_ref("type") + ident("name")
    )
    + SEMI
)

TEMPLATE = pp.Keyword("template")
uuid = pp.Regex(
    r"<[0-9a-fA-F]{8}(-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}>"
).set_parse_action(lambda t: t[0][1:-1])
open_template_indicator = pp.Combine(LBRACK + "..." + RBRACK, adjacent=False)
restriction = pp.Group(type_ref("type") + pp.Optional(uuid)("uuid"))
template_restrictions = LBRACK + pp.DelimitedList(restriction) + RBRACK
directx_template_defn = (
    TEMPLATE
    + ident("name")
    + LBRACE
    + pp.Optional(uuid)("uuid")
    + member_defn[...]("members")
    + pp.Optional(
        open_template_indicator.set_parse_action(lambda: True), default=False
    )("open_template")
    + pp.Optional(template_restrictions)("restrictions")
    + RBRACE
).set_name("template_defn")
directx_template_defn.add_parse_action(
    lambda t: t.__setitem__("closed", not (t.open_template or t.restrictions))
)

directx_template_defn.ignore(pp.cpp_style_comment)


def make_template_parser(template_defn: pp.ParseResults) -> pp.ParserElement:
    """
    Create a pyparsing parser from a DirectX template definition.
    (Limited to templates containing scalar types, or arrays of scalars.)
    """
    float_ = pp.common.real
    type_map = {
        "WORD": integer,
        "DWORD": integer,
        "FLOAT": float_,
        "DOUBLE": float_,
        "CHAR": integer,
        "UCHAR": integer,
        "BYTE": integer,
        "STRING": pp.QuotedString('"'),
        "CSTRING": pp.QuotedString('"'),
        "UNICODE": pp.QuotedString('"'),
    }
    member_parsers = []
    for member in template_defn.members:
        if member.type in type_map:
            expr = pp.ungroup(type_map[member.type] + SEMI)
        elif member.dims:
            expr = type_map[member.type.element_type]
            for dim in member.dims:
                expr = pp.Group(pp.DelimitedList(expr, max=dim) + SEMI)
        member_parsers.append(expr(member.name))

    pp.autoname_elements()

    return (
        pp.Keyword(template_defn.name)("type")
        + ident("name")
        + LBRACE
        + pp.Group(pp.And(member_parsers))("fields")
        + RBRACE
    )


if __name__ == "__main__":
    import contextlib

    with contextlib.suppress(Exception):
        # create railroad diagram
        directx_template_defn.create_diagram(
            "directx_x_file_parser.html", show_results_names=True, show_groups=False
        )


    sample = """
    some stuff...

    template Mesh {
    <3D82AB44-62DA-11cf-AB39-0020AF71E433>
    DWORD nVertices;
    array Vector vertices[nVertices];
    DWORD nFaces;
    array MeshFace faces[nFaces];
     [ ... ]                // An open template
    }
    
    template PolyArray {
    <3D82AB44-62DA-11cf-AB39-0020AF71E433>
    DWORD nPolys;
    array FLOAT polys[nPolys][3];
    }

    template Vector {
    <3D82AB5E-62DA-11cf-AB39-0020AF71E434>
    FLOAT x;
    FLOAT y;
    FLOAT z;
    }                        // A closed template

    template FileSystem {
    <3D82AB5E-62DA-11cf-AB39-0020AF71E435>
    STRING name;
    [ Directory <3D82AB5E-62DA-11cf-AB39-0020AF71E436>, File <3D82AB5E-62DA-11cf-AB39-0020AF71E437> ]    // A restricted template
    }

    more stuff...

    template mytemp {
    DWORD myvar;
    DWORD myvar2;
    }

    template container {
    DWORD count;
    array mytemp tempArray[count];
    }
    """

    for template in directx_template_defn.search_string(sample):
        # print(template.dump())
        print(
            f"Name: {template.name!r}"
            f" UUID: {template.uuid}"
            f" Open: {template.open_template!r}"
            f" Closed: {template.closed!r}"
            f" Restricted: {bool(template.restrictions)}"
        )
        # print()

    vector_template = directx_template_defn.parse_string(
        """\
    template Vector {
        <3D82AB5E-62DA-11cf-AB39-0020AF71E434>
        STRING label;
        FLOAT x;
        FLOAT y;
        FLOAT z;
    }  
    """
    )
    vector_parser = make_template_parser(vector_template)

    with contextlib.suppress(Exception):
        vector_parser.create_diagram(
            "directx_x_vector_parser.html", show_results_names=True, show_groups=False
        )

    v = vector_parser.parse_string('Vector p1 {"datum_A"; 1.0; 3.0; 5.0;}')
    print(v.dump())

    vector_template = directx_template_defn.parse_string(
        """\
    template Vector {
        <3D82AB5E-62DA-11cf-AB39-0020AF71E434>
        STRING label;
        array FLOAT coords[3];
    }  
    """
    )
    vector_parser = make_template_parser(vector_template)
    vector_parser.create_diagram(
        "directx_x_vector_parser.html", show_results_names=True, show_groups=False
    )
    v = vector_parser.parse_string('Vector p1 {"datum_A"; 1.0, 3.0, 5.0;}')
    print(v.dump())
