#
# gen_ctypes.py
#
# Parse a .h header file to generate ctypes argtype and return type definitions
#
# Copyright 2004-2016, by Paul McGuire
#
from pyparsing import *

typemap = {
    "byte": "c_byte",
    "char": "c_char",
    "char *": "c_char_p",
    "double": "c_double",
    "float": "c_float",
    "int": "c_int",
    "int16": "c_int16",
    "int32": "c_int32",
    "int64": "c_int64",
    "int8": "c_int8",
    "long": "c_long",
    "longlong": "c_longlong",
    "short": "c_short",
    "size_t": "c_size_t",
    "ubyte": "c_ubyte",
    "uchar": "c_ubyte",
    "u_char": "c_ubyte",
    "uint": "c_uint",
    "u_int": "c_uint",
    "uint16": "c_uint16",
    "uint32": "c_uint32",
    "uint64": "c_uint64",
    "uint8": "c_uint8",
    "u_long": "c_ulong",
    "ulong": "c_ulong",
    "ulonglong": "c_ulonglong",
    "ushort": "c_ushort",
    "u_short": "c_ushort",
    "void *": "c_void_p",
    "voidp": "c_voidp",
    "wchar": "c_wchar",
    "wchar *": "c_wchar_p",
    "Bool": "c_bool",
    "void": "None",
}

LPAR, RPAR, LBRACE, RBRACE, COMMA, SEMI = Suppress.using_each("(){},;")
ident = pyparsing_common.identifier
integer = Regex(r"[+-]?\d+")
hexinteger = Regex(r"0x[0-9a-fA-F]+")

const = Suppress("const")
primitiveType = one_of(t for t in typemap if not t.endswith("*"))
structType = Suppress("struct") + ident
vartype = (
    Opt(const) + (primitiveType | structType | ident) + Opt(Word("*")("ptr"))
)


def normalizetype(t):
    if isinstance(t, ParseResults):
        return " ".join(t)
        # ~ ret = ParseResults([' '.join(t)])
        # ~ return ret


vartype.set_parse_action(normalizetype)

arg = Group(vartype("argtype") + Opt(ident("argname")))
func_def = (
    vartype("fn_type")
    + ident("fn_name")
    + LPAR
    + Opt(DelimitedList(arg | "..."))("fn_args")
    + RPAR
    + SEMI
)


def derivefields(t):
    if t.fn_args and t.fn_args[-1] == "...":
        t["varargs"] = True


func_def.set_parse_action(derivefields)

fn_typedef = "typedef" + func_def
var_typedef = "typedef" + primitiveType("primType") + ident("name") + SEMI

enum_def = (
    Keyword("enum")
    + LBRACE
    + DelimitedList(Group(ident("name") + "=" + (hexinteger | integer)("value")))(
        "evalues"
    )
    + Opt(COMMA)
    + RBRACE
)

c_header = open("snmp_api.h").read()


module = "pynetsnmp"

user_defined_types = set()
typedefs = []
fn_typedefs = []
functions = []
enum_constants = []

# add structures commonly included from std lib headers
def addStdType(t, namespace=""):
    fullname = namespace + "_" + t if namespace else t
    typemap[t] = fullname
    user_defined_types.add(t)


addStdType("fd_set", "sys_select")
addStdType("timeval", "sys_time")


def getUDType(typestr):
    key = typestr.rstrip(" *")
    if key not in typemap:
        user_defined_types.add(key)
        typemap[key] = "{}_{}".format(module, key)


def typeAsCtypes(typestr):
    if typestr in typemap:
        return typemap[typestr]
    if typestr.endswith("*"):
        return f"POINTER({typeAsCtypes(typestr.rstrip(' *'))})"
    return typestr


# scan input header text for primitive typedefs
for td, _, _ in var_typedef.scan_string(c_header):
    typedefs.append((td.name, td.primType))
    # add typedef type to typemap to map to itself
    typemap[td.name] = td.name

# scan input header text for function typedefs
fn_typedefs = fn_typedef.search_string(c_header)
# add each function typedef to typemap to map to itself
for fntd in fn_typedefs:
    typemap[fntd.fn_name] = fntd.fn_name

# scan input header text, and keep running list of user-defined types
for fn, _, _ in (
    cStyleComment.suppress() | fn_typedef.suppress() | func_def
).scan_string(c_header):
    if not fn:
        continue
    getUDType(fn.fn_type)
    for arg in fn.fn_args:
        if arg != "...":
            if arg.argtype not in typemap:
                getUDType(arg.argtype)
    functions.append(fn)

# scan input header text for enums
enum_def.ignore(cpp_style_comment)
for en_, _, _ in enum_def.scan_string(c_header):
    for ev in en_.evalues:
        enum_constants.append((ev.name, ev.value))

print("from ctypes import *")
print("{} = CDLL('{}.dll')".format(module, module))
print()
print("# user defined types")
for tdname, tdtyp in typedefs:
    print("{} = {}".format(tdname, typemap[tdtyp]))
for fntd in fn_typedefs:
    print(
        "{} = CFUNCTYPE({})".format(
            fntd.fn_name, ",\n    ".join(typeAsCtypes(a.argtype) for a in fntd.fn_args)
        )
    )
for udtype in user_defined_types:
    print(f"class {typemap[udtype]}(Structure): pass")

print()
print("# constant definitions")
for en, ev in enum_constants:
    print("{} = {}".format(en, ev))

print()
print("# functions")
for fn in functions:
    prefix = "{}.{}".format(module, fn.fn_name)

    print("{}.restype = {}".format(prefix, typeAsCtypes(fn.fn_type)))
    if fn.varargs:
        print(f"# warning - {prefix} takes variable argument list")
        del fn.fn_args[-1]

    if fn.fn_args.asList() != [["void"]]:
        print(
            "{}.argtypes = ({},)".format(
                prefix, ",".join(typeAsCtypes(a.argtype) for a in fn.fn_args)
            )
        )
    else:
        print(f"{prefix}.argtypes = ()")
