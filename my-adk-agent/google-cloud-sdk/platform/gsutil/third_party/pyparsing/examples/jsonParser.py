# jsonParser.py
#
# Implementation of a simple JSON parser, returning a hierarchical
# ParseResults object support both list- and dict-style data access.
#
# Copyright 2006, by Paul McGuire
#
# Updated 8 Jan 2007 - fixed dict grouping bug, and made elements and
#   members optional in array and object collections
#
# Updated 9 Aug 2016 - use more current pyparsing constructs/idioms
#
json_bnf = """
object
    { members }
    {}
members
    string : value
    members , string : value
array
    [ elements ]
    []
elements
    value
    elements , value
value
    string
    number
    object
    array
    true
    false
    null
"""

import pyparsing as pp
from pyparsing import pyparsing_common as ppc


def make_keyword(kwd_str, kwd_value):
    return pp.Keyword(kwd_str).setParseAction(pp.replaceWith(kwd_value))


# set to False to return ParseResults
RETURN_PYTHON_COLLECTIONS = True

TRUE = make_keyword("true", True)
FALSE = make_keyword("false", False)
NULL = make_keyword("null", None)

LBRACK, RBRACK, LBRACE, RBRACE, COLON = map(pp.Suppress, "[]{}:")

jsonString = pp.dblQuotedString().setParseAction(pp.removeQuotes)
jsonNumber = ppc.number().setName("jsonNumber")

jsonObject = pp.Forward().setName("jsonObject")
jsonValue = pp.Forward().setName("jsonValue")

jsonElements = pp.delimitedList(jsonValue).setName(None)
# jsonArray = pp.Group(LBRACK + pp.Optional(jsonElements, []) + RBRACK)
# jsonValue << (
#     jsonString | jsonNumber | pp.Group(jsonObject) | jsonArray | TRUE | FALSE | NULL
# )
# memberDef = pp.Group(jsonString + COLON + jsonValue).setName("jsonMember")

jsonArray = pp.Group(
    LBRACK + pp.Optional(jsonElements) + RBRACK, aslist=RETURN_PYTHON_COLLECTIONS
).setName("jsonArray")

jsonValue << (jsonString | jsonNumber | jsonObject | jsonArray | TRUE | FALSE | NULL)

memberDef = pp.Group(
    jsonString + COLON + jsonValue, aslist=RETURN_PYTHON_COLLECTIONS
).setName("jsonMember")

jsonMembers = pp.delimitedList(memberDef).setName(None)
# jsonObject << pp.Dict(LBRACE + pp.Optional(jsonMembers) + RBRACE)
jsonObject << pp.Dict(
    LBRACE + pp.Optional(jsonMembers) + RBRACE, asdict=RETURN_PYTHON_COLLECTIONS
)

jsonComment = pp.cppStyleComment
jsonObject.ignore(jsonComment)


if __name__ == "__main__":
    testdata = """
    {
        "glossary": {
            "title": "example glossary",
            "GlossDiv": {
                "title": "S",
                "GlossList": [
                    {
                    "ID": "SGML",
                    "SortAs": "SGML",
                    "GlossTerm": "Standard Generalized Markup Language",
                    "TrueValue": true,
                    "FalseValue": false,
                    "Gravity": -9.8,
                    "LargestPrimeLessThan100": 97,
                    "AvogadroNumber": 6.02E23,
                    "EvenPrimesGreaterThan2": null,
                    "PrimesLessThan10" : [2,3,5,7],
                    "Acronym": "SGML",
                    "Abbrev": "ISO 8879:1986",
                    "GlossDef": "A meta-markup language, used to create markup languages such as DocBook.",
                    "GlossSeeAlso": ["GML", "XML", "markup"],
                    "EmptyDict" : {},
                    "EmptyList" : []
                    }
                ]
            }
        }
    }
    """

    results = jsonObject.parseString(testdata)

    results.pprint()
    if RETURN_PYTHON_COLLECTIONS:
        from pprint import pprint

        pprint(results)
    else:
        results.pprint()
    print()

    def testPrint(x):
        print(type(x), repr(x))

    if RETURN_PYTHON_COLLECTIONS:
        results = results[0]
        print(list(results["glossary"]["GlossDiv"]["GlossList"][0].keys()))
        testPrint(results["glossary"]["title"])
        testPrint(results["glossary"]["GlossDiv"]["GlossList"][0]["ID"])
        testPrint(results["glossary"]["GlossDiv"]["GlossList"][0]["FalseValue"])
        testPrint(results["glossary"]["GlossDiv"]["GlossList"][0]["Acronym"])
        testPrint(
            results["glossary"]["GlossDiv"]["GlossList"][0]["EvenPrimesGreaterThan2"]
        )
        testPrint(results["glossary"]["GlossDiv"]["GlossList"][0]["PrimesLessThan10"])
    else:
        print(list(results.glossary.GlossDiv.GlossList.keys()))
        testPrint(results.glossary.title)
        testPrint(results.glossary.GlossDiv.GlossList.ID)
        testPrint(results.glossary.GlossDiv.GlossList.FalseValue)
        testPrint(results.glossary.GlossDiv.GlossList.Acronym)
        testPrint(results.glossary.GlossDiv.GlossList.EvenPrimesGreaterThan2)
        testPrint(results.glossary.GlossDiv.GlossList.PrimesLessThan10)
