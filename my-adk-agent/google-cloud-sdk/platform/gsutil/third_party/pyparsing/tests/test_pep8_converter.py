from pyparsing.tools.cvt_pyparsing_pep8_names import (
    pep8_converter, pre_pep8_arg_names, pre_pep8_method_names, special_changes
)
import pytest


def test_conversion_composed():
    orig = ("\n".join(
        f"{method_name}()"
        for method_name in sorted(pre_pep8_method_names) + list(special_changes)
    ) + "\n"
    + "\n".join(
        f"fn(100, {arg_name}=True)"
        for arg_name in sorted(pre_pep8_arg_names)
    ))
    expected = """\
add_condition()
add_parse_action()
any_close_tag()
any_open_tag()
as_dict()
as_list()
c_style_comment()
can_parse_next()
condition_as_parse_action()
convert_to_date()
convert_to_datetime()
convert_to_float()
convert_to_integer()
counted_array()
cpp_style_comment()
dbl_quoted_string()
dbl_slash_comment()
default_name()
dict_of()
disable_memoization()
downcase_tokens()
enable_left_recursion()
enable_packrat()
get_name()
html_comment()
ignore_whitespace()
indented_block()
infix_notation()
inline_literals_using()
java_style_comment()
leave_whitespace()
line_end()
line_start()
located_expr()
match_only_at_col()
match_previous_expr()
match_previous_literal()
nested_expr()
null_debug_action()
one_of()
original_text_for()
parse_file()
parse_string()
parse_with_tabs()
python_style_comment()
quoted_string()
remove_quotes()
replace_with()
reset_cache()
rest_of_line()
run_tests()
scan_string()
search_string()
set_break()
set_debug()
set_debug_actions()
set_default_whitespace_chars()
set_fail_action()
set_name()
set_parse_action()
set_results_name()
set_whitespace_chars()
sgl_quoted_string()
string_end()
string_start()
token_map()
trace_parse_action()
transform_string()
try_parse()
unicode_string()
upcase_tokens()
with_attribute()
with_class()
OpAssoc()
DelimitedList()
DelimitedList()
replace_html_entity()
make_html_tags()
make_xml_tags()
common_html_entity()
strip_html_tags()
fn(100, as_group_list=True)
fn(100, as_keyword=True)
fn(100, as_match=True)
fn(100, as_string=True)
fn(100, body_chars=True)
fn(100, call_during_try=True)
fn(100, convert_whitespace_escapes=True)
fn(100, end_quote_char=True)
fn(100, esc_char=True)
fn(100, esc_quote=True)
fn(100, exclude_chars=True)
fn(100, fail_on=True)
fn(100, failure_tests=True)
fn(100, full_dump=True)
fn(100, ident_chars=True)
fn(100, ignore_expr=True)
fn(100, include_separators=True)
fn(100, init_chars=True)
fn(100, int_expr=True)
fn(100, join_string=True)
fn(100, list_all_matches=True)
fn(100, marker_string=True)
fn(100, match_string=True)
fn(100, max_matches=True)
fn(100, max_mismatches=True)
fn(100, not_chars=True)
fn(100, parse_all=True)
fn(100, post_parse=True)
fn(100, print_results=True)
fn(100, quote_char=True)
fn(100, stop_on=True)
fn(100, unquote_results=True)
fn(100, use_regex=True)
fn(100, word_chars=True)"""
    converted = pep8_converter.transform_string(orig)
    assert converted == expected

def test_conversion_examples():
    orig = r"""
            L = equation.parseString(input_string)
    equation.runTests((t[1] for t in testcases), postParse=post_test)
                L = pattern.parseString(input_string, parseAll=True)
        itemRef = pp.OneOrMore(pp.Word(pp.alphas)).set_parse_action(self.validate_item_name).setName("item_ref")
        doorsCommand = doorsVerb.setName("DOORS")
    originalTextFor,
    cStyleComment,
    oneOf,
    delimitedList,
    oneOf(list(r"nrtbf\">" + "'")) | ("u" + Word(hexnums, exact=4)) | SGL_PRINTABLE
    | (SCOPE_.suppress() + delimitedList(id) + SEMI)
    | (SCOPE_.suppress() + ACTION + SCOPE_.suppress() + delimitedList(id) + SEMI)
    (id("result_name") + oneOf("= +=")("labelOp") + atom("atom") + Optional(ebnfSuffix))
    | (id("result_name") + oneOf("= +=")("labelOp") + block + Optional(ebnfSuffix))
    antlrGrammarTree = grammar().parseString(text)
    pyparsingTree = pyparsingRule.parseString("2 - 5 * 42 + 7 / 25")
        antlr_grammar.optionsSpec.parseString(text)  # @UndefinedVariable
        antlr_grammar.tokensSpec.parseString(text)  # @UndefinedVariable
        antlr_grammar.block.parseString(text)  # @UndefinedVariable
        antlr_grammar.rule.parseString(text)  # @UndefinedVariable
        # antlr_grammar.rule.parseString(text) #@UndefinedVariable
        antlrGrammarTree = antlr_grammar.grammarDef.parseString(
        pyparsingTree = pyparsingRule.parseString("2 - 5 * 42 + 7 / 25")
        pyparsingTreeList = pyparsingTree.asList()
    api_scanner = apiRef.scanString(test)
            api_scanner = apiRef.scanString(test)
        BigQueryViewParser._get_parser().parseString(sql_stmt, parseAll=True)
        ParserElement.enablePackrat()
        ungrouped_select_stmt = Forward().setName("select statement")
        QUOTED_BRACKETS = QuotedString("[", endQuoteChar="]")
        expr = Forward().setName("expression")
        bind_parameter = Word("?", nums) | Combine(oneOf(": @ $") + parameter_name)
        type_name = oneOf(
        date_part = oneOf(
            + delimitedList(function_arg)
        partition_expression_list = delimitedList(grouping_term)(
            + Optional(ORDER + BY + delimitedList(ordering_term))
            Optional(ARRAY + Optional(LT + delimitedList(type_name) + GT))
            + delimitedList(expr)
            + Optional(LT + delimitedList(type_name) + GT)
            + Optional(delimitedList(expr + Optional(AS + identifier)))
        struct_term = LPAR + delimitedList(expr_term) + RPAR
        expr <<= infixNotation(
                (oneOf("- + ~") | NOT, UNARY, opAssoc.RIGHT),
                (ISNULL | NOTNULL | NOT + NULL, UNARY, opAssoc.LEFT),
                ("||", BINARY, opAssoc.LEFT),
                (oneOf("* / %"), BINARY, opAssoc.LEFT),
                (oneOf("+ -"), BINARY, opAssoc.LEFT),
                (oneOf("<< >> & |"), BINARY, opAssoc.LEFT),
                (oneOf("= > < >= <= <> != !< !> =="), BINARY, opAssoc.LEFT),
                    opAssoc.LEFT,
                ((BETWEEN, AND), TERNARY, opAssoc.LEFT),
                    + Group(ungrouped_select_stmt | delimitedList(expr))
                (AND, BINARY, opAssoc.LEFT),
                (OR, BINARY, opAssoc.LEFT),
                | USING + LPAR + Group(delimitedList(qualified_column_name)) + RPAR
            identifier_list = t.asList()
        ).setParseAction(record_table_identifier)
        ).setParseAction(record_quoted_table_identifier)
        ).setName("table_identifier")
        over_partition = (PARTITION + BY + delimitedList(partition_expression_list))(
        over_order = ORDER + BY + delimitedList(ordering_term)
            EXCEPT + LPAR + delimitedList(column_name) + RPAR
        with_stmt = Forward().setName("with statement")
                delimitedList(
                GROUP + BY + Group(delimitedList(grouping_term))("group_by_terms")
                ORDER + BY + Group(delimitedList(ordering_term))("order_by_terms")
            + Optional(delimitedList(window_select_clause))
        sql_comment = oneOf("-- #") + restOfLine | cStyleComment
            identifier.setParseAction(record_with_alias)
        with_stmt <<= WITH + delimitedList(with_clause)
    return bibfile.parseString(str)
    stmt.runTests('''\
        (Literal("#").suppress() + Word(nums)).setParseAction(
    + Optional(Group(delimitedList(identifier | number_value | string_value)))
            i.setParseAction(action)
            retval[f] = object_definition.parseFile(f)
    vert + pp.Word(pp.alphas) + vert + pp.delimitedList(number, "|") + vert
            results = BNF().parseString(s, parseAll=True)
    cStyleComment.suppress() | fn_typedef.suppress() | func_def
    if fn.fn_args.asList() != [["void"]]:
    fullDump=False,
    dblQuotedString,
    removeQuotes,
        ipAddress = delimitedList(integer, ".", combine=True)
            ipAddress.setResultsName("ipAddr")
            + ("-" | Word(alphas + nums + "@._")).setResultsName("auth")
            + serverDateTime.setResultsName("timestamp")
            + dblQuotedString.setResultsName("cmd").setParseAction(getCmdFields)
            + (integer | "-").setResultsName("statusCode")
            + (integer | "-").setResultsName("numBytesSent")
            + dblQuotedString.setResultsName("referrer").setParseAction(removeQuotes)
            + dblQuotedString.setResultsName("clientSfw").setParseAction(removeQuotes)
    fields = getLogLineBNF().parseString(line)
            + include_directive.transformString(included_file_contents)
    # use include_directive.transformString to perform includes
    expanded_source = include_directive.transformString(initial_file)
    "def" + identifier + Group("(" + Optional(delimitedList(identifier)) + ")") + ":"
    invre = GroupEmitter(parser().parseString(regex)).make_generator()
        (pp.one_of("! -"), 1, pp.opAssoc.RIGHT),
        (pp.one_of("/ *"), 2, pp.opAssoc.LEFT),
        (pp.one_of("- +"), 2, pp.opAssoc.LEFT),
        (pp.one_of("> >= < <="), 2, pp.opAssoc.LEFT),
        (pp.one_of("!= =="), 2, pp.opAssoc.LEFT),
        (AND, 2, pp.opAssoc.LEFT),
        (OR, 2, pp.opAssoc.LEFT),
        ("^", 2, pp.opAssoc.LEFT),
        ((NOT | pp.oneOf("# - ~")).set_name("not op"), 1, pp.opAssoc.RIGHT),
        (pp.oneOf("* / // %"), 2, pp.opAssoc.LEFT),
        (pp.oneOf("+ -"), 2, pp.opAssoc.LEFT),
        ("..", 2, pp.opAssoc.LEFT),
        (pp.oneOf("<< >>"), 2, pp.opAssoc.LEFT),
        ("&", 2, pp.opAssoc.LEFT),
        ("~", 2, pp.opAssoc.LEFT),
        ("|", 2, pp.opAssoc.LEFT),
        (pp.oneOf("< > <= >= ~= =="), 2, pp.opAssoc.LEFT),
        result = lua_script.parseString(sample)
    success2, _ = expression.run_tests(failtests, failureTests=True)
       UID DTSTAMP LAST-MODIFIED X RRULE EXDATE''', asKeyword=True
        return opening + wiki_markup.transformString(t[1][1:-1]) + closing
    t["link_text"] = wiki_markup.transformString(link_text)
        postParse=lambda _, s: "{:,}".format(s[0]),
    ast = program.parse_string(test, parseAll=True)
            expr.copy().addCondition(
    print(row.parseString(line).dump())
    + pp.Word("ACGTN")[1, ...].addParseAction("".join)("gene")
    for t, startLoc, endLoc in searchseq.scanString(g.gene, overlap=True):
    return Empty().setParseAction(lambda s, l, t: t.__setitem__(name, l))
    quotedString,
    OPTION_ - ident("optionName") + EQ + quotedString("optionValue") + SEMI
            return cls(t[0].asList())
    (bnfToken | quotedString | optionalTerm | (LPAREN + bnfExpr + RPAREN))
                          ).setName("street_address")
              ).setName("header with various elements")("header")
                                   (plus_minus().setName("pos_neg"), 1, pp.opAssoc.RIGHT),
                                   (mult_div, 2, pp.opAssoc.LEFT),
                                   (plus_minus, 2, pp.opAssoc.LEFT),
                               ]).setName("simple_arithmetic")
           ).setName("grammar")
    restOfLine,
    replaceWith,
    + ident.setResultsName("name")
    + restOfLine.setResultsName("value")
        operatorWord = Group(Combine(Word(alphanums) + Suppress("*"))).setResultsName(
        ) | Group(Word(alphanums)).setResultsName("word")
            Group(Suppress('"') + operatorQuotesContent + Suppress('"')).setResultsName(
            Group(Suppress("(") + operatorOr + Suppress(")")).setResultsName(
            Group(Suppress(Keyword("not", caseless=True)) + operatorNot).setResultsName(
            ).setResultsName("and")
                operatorNot + OneOrMore(~oneOf("and or") + operatorAnd)
            ).setResultsName("or")
        return operatorOr.parseString
        return self._methods[argument.getName()](argument)
    sexp.run_tests(alltests, fullDump=False)
        self.__dict__.update(tokens.asDict())
    shape = shapeExpr.parseString(t)[0]
        (factop, 1, opAssoc.LEFT),
        (expop, 2, opAssoc.RIGHT),
        (signop, 1, opAssoc.RIGHT),
        (multop, 2, opAssoc.LEFT),
        (plusop, 2, opAssoc.LEFT),
    print(expr.parseString(t))
    + Word(alphas, alphanums + "_").setResultsName("tablename")
    + field_list_def.setResultsName("columns")
    + Word(alphanums + "_").setResultsName("fromtable")
    + Word(alphanums + "_").setResultsName("fromcolumn")
    + Word(alphanums + "_").setResultsName("totable")
    + Word(alphanums + "_").setResultsName("tocolumn")
                self.assertEqual("2t", name_type.parseString("2t")[0])
                self.assertRaises(ParseException, name_type.parseString, "2t")
                self.assertRaises(ParseException, name_type.parseString, char)
            self.assertEqual("simple_test", name_type.parseString("simple_test")[0])
        self.assertRaises(ParseException, mr.parseString, "2t")
            self.assertRaises(ParseException, mr.parseString, char)
        self.assertEqual("simple_test", mr.parseString("simple_test")[0].name)
        self.assertEqual("1066", bp.number.parseString("1066")[0])
        self.assertEqual("0", bp.number.parseString("0")[0])
        self.assertRaises(ParseException, bp.number.parseString, "-4")
        self.assertRaises(ParseException, bp.number.parseString, "+4")
        self.assertRaises(ParseException, bp.number.parseString, ".4")
        self.assertEqual("0", bp.number.parseString("0.4")[0])
        self.assertEqual(bp.chars_no_quotecurly.parseString("x")[0], "x")
        self.assertEqual(bp.chars_no_quotecurly.parseString("a string")[0], "a string")
        self.assertEqual(bp.chars_no_quotecurly.parseString('a "string')[0], "a ")
        self.assertEqual(bp.chars_no_curly.parseString("x")[0], "x")
        self.assertEqual(bp.chars_no_curly.parseString("a string")[0], "a string")
        self.assertEqual(bp.chars_no_curly.parseString("a {string")[0], "a ")
        self.assertEqual(bp.chars_no_curly.parseString("a }string")[0], "a ")
            self.assertEqual(obj.parseString("{}").asList(), [])
            self.assertEqual(obj.parseString('{a "string}')[0], 'a "string')
                obj.parseString("{a {nested} string}").asList(),
                obj.parseString("{a {double {nested}} string}").asList(),
            self.assertEqual([], obj.parseString('""').asList())
            self.assertEqual("a string", obj.parseString('"a string"')[0])
                obj.parseString('"a {nested} string"').asList(),
                obj.parseString('"a {double {nested}} string"').asList(),
        self.assertEqual(Macro("someascii"), bp.string.parseString("someascii")[0])
        self.assertRaises(ParseException, bp.string.parseString, "%#= validstring")
        self.assertEqual(bp.string.parseString("1994")[0], "1994")
        self.assertEqual(Macro("aname"), fv.parseString("aname")[0])
        self.assertEqual(Macro("aname"), fv.parseString("ANAME")[0])
            fv.parseString('aname # "some string"').asList(),
            fv.parseString("aname # {some {string}}").asList(),
            ["a string", "1994"], fv.parseString('"a string" # 1994').asList()
            fv.parseString('"a string" # 1994 # a_macro').asList(),
        res = bp.comment.parseString("@Comment{about something}")
        self.assertEqual(res.asList(), ["comment", "{about something}"])
            bp.comment.parseString("@COMMENT{about something").asList(),
            bp.comment.parseString("@comment(about something").asList(),
            bp.comment.parseString("@COMment about something").asList(),
            ParseException, bp.comment.parseString, "@commentabout something"
            ParseException, bp.comment.parseString, "@comment+about something"
            ParseException, bp.comment.parseString, '@comment"about something'
        res = bp.preamble.parseString('@preamble{"about something"}')
        self.assertEqual(res.asList(), ["preamble", "about something"])
            bp.preamble.parseString("@PREamble{{about something}}").asList(),
            bp.preamble.parseString(
            ).asList(),
        res = bp.macro.parseString('@string{ANAME = "about something"}')
        self.assertEqual(res.asList(), ["string", "aname", "about something"])
            bp.macro.parseString("@string{aname = {about something}}").asList(),
        res = bp.entry.parseString(txt)
            res.asList(),
        res = bp.bibfile.parseString(txt)
        self.assertEqual(res.asList(), res2.asList())
        res3 = [r.asList()[0] for r, start, end in bp.definitions.scanString(txt)]
        self.assertEqual(res.asList(), res3)
    print(toks.asList())
    parsed = ppc.url.parseString(url)
    cppStyleComment,
            + restOfLine
            Regex(r"\\\S+").setParseAction(lambda t: t[0][1:]).set_name("escapedIdent")
        )  # .setDebug()
            joinString=" ",
            | (LPAR + Group(expr) + RPAR).set_name("nestedExpr")
        delay = Group("#" + delayArg).set_name("delay")  # .setDebug()
        stmt = Forward().set_name("stmt")  # .setDebug()
        verilogbnf.ignore(cppStyleComment)
    return ret.set_parse_action(pp.replaceWith(val))
"""

    expected = r"""
            L = equation.parse_string(input_string)
    equation.run_tests((t[1] for t in testcases), post_parse=post_test)
                L = pattern.parse_string(input_string, parse_all=True)
        itemRef = pp.OneOrMore(pp.Word(pp.alphas)).set_parse_action(self.validate_item_name).set_name("item_ref")
        doorsCommand = doorsVerb.set_name("DOORS")
    original_text_for,
    c_style_comment,
    one_of,
    DelimitedList,
    one_of(list(r"nrtbf\">" + "'")) | ("u" + Word(hexnums, exact=4)) | SGL_PRINTABLE
    | (SCOPE_.suppress() + DelimitedList(id) + SEMI)
    | (SCOPE_.suppress() + ACTION + SCOPE_.suppress() + DelimitedList(id) + SEMI)
    (id("result_name") + one_of("= +=")("labelOp") + atom("atom") + Optional(ebnfSuffix))
    | (id("result_name") + one_of("= +=")("labelOp") + block + Optional(ebnfSuffix))
    antlrGrammarTree = grammar().parse_string(text)
    pyparsingTree = pyparsingRule.parse_string("2 - 5 * 42 + 7 / 25")
        antlr_grammar.optionsSpec.parse_string(text)  # @UndefinedVariable
        antlr_grammar.tokensSpec.parse_string(text)  # @UndefinedVariable
        antlr_grammar.block.parse_string(text)  # @UndefinedVariable
        antlr_grammar.rule.parse_string(text)  # @UndefinedVariable
        # antlr_grammar.rule.parse_string(text) #@UndefinedVariable
        antlrGrammarTree = antlr_grammar.grammarDef.parse_string(
        pyparsingTree = pyparsingRule.parse_string("2 - 5 * 42 + 7 / 25")
        pyparsingTreeList = pyparsingTree.as_list()
    api_scanner = apiRef.scan_string(test)
            api_scanner = apiRef.scan_string(test)
        BigQueryViewParser._get_parser().parse_string(sql_stmt, parse_all=True)
        ParserElement.enable_packrat()
        ungrouped_select_stmt = Forward().set_name("select statement")
        QUOTED_BRACKETS = QuotedString("[", end_quote_char="]")
        expr = Forward().set_name("expression")
        bind_parameter = Word("?", nums) | Combine(one_of(": @ $") + parameter_name)
        type_name = one_of(
        date_part = one_of(
            + DelimitedList(function_arg)
        partition_expression_list = DelimitedList(grouping_term)(
            + Optional(ORDER + BY + DelimitedList(ordering_term))
            Optional(ARRAY + Optional(LT + DelimitedList(type_name) + GT))
            + DelimitedList(expr)
            + Optional(LT + DelimitedList(type_name) + GT)
            + Optional(DelimitedList(expr + Optional(AS + identifier)))
        struct_term = LPAR + DelimitedList(expr_term) + RPAR
        expr <<= infix_notation(
                (one_of("- + ~") | NOT, UNARY, OpAssoc.RIGHT),
                (ISNULL | NOTNULL | NOT + NULL, UNARY, OpAssoc.LEFT),
                ("||", BINARY, OpAssoc.LEFT),
                (one_of("* / %"), BINARY, OpAssoc.LEFT),
                (one_of("+ -"), BINARY, OpAssoc.LEFT),
                (one_of("<< >> & |"), BINARY, OpAssoc.LEFT),
                (one_of("= > < >= <= <> != !< !> =="), BINARY, OpAssoc.LEFT),
                    OpAssoc.LEFT,
                ((BETWEEN, AND), TERNARY, OpAssoc.LEFT),
                    + Group(ungrouped_select_stmt | DelimitedList(expr))
                (AND, BINARY, OpAssoc.LEFT),
                (OR, BINARY, OpAssoc.LEFT),
                | USING + LPAR + Group(DelimitedList(qualified_column_name)) + RPAR
            identifier_list = t.as_list()
        ).set_parse_action(record_table_identifier)
        ).set_parse_action(record_quoted_table_identifier)
        ).set_name("table_identifier")
        over_partition = (PARTITION + BY + DelimitedList(partition_expression_list))(
        over_order = ORDER + BY + DelimitedList(ordering_term)
            EXCEPT + LPAR + DelimitedList(column_name) + RPAR
        with_stmt = Forward().set_name("with statement")
                DelimitedList(
                GROUP + BY + Group(DelimitedList(grouping_term))("group_by_terms")
                ORDER + BY + Group(DelimitedList(ordering_term))("order_by_terms")
            + Optional(DelimitedList(window_select_clause))
        sql_comment = one_of("-- #") + rest_of_line | c_style_comment
            identifier.set_parse_action(record_with_alias)
        with_stmt <<= WITH + DelimitedList(with_clause)
    return bibfile.parse_string(str)
    stmt.run_tests('''\
        (Literal("#").suppress() + Word(nums)).set_parse_action(
    + Optional(Group(DelimitedList(identifier | number_value | string_value)))
            i.set_parse_action(action)
            retval[f] = object_definition.parse_file(f)
    vert + pp.Word(pp.alphas) + vert + pp.DelimitedList(number, "|") + vert
            results = BNF().parse_string(s, parse_all=True)
    c_style_comment.suppress() | fn_typedef.suppress() | func_def
    if fn.fn_args.as_list() != [["void"]]:
    full_dump=False,
    dbl_quoted_string,
    remove_quotes,
        ipAddress = DelimitedList(integer, ".", combine=True)
            ipAddress.set_results_name("ipAddr")
            + ("-" | Word(alphas + nums + "@._")).set_results_name("auth")
            + serverDateTime.set_results_name("timestamp")
            + dbl_quoted_string.set_results_name("cmd").set_parse_action(getCmdFields)
            + (integer | "-").set_results_name("statusCode")
            + (integer | "-").set_results_name("numBytesSent")
            + dbl_quoted_string.set_results_name("referrer").set_parse_action(remove_quotes)
            + dbl_quoted_string.set_results_name("clientSfw").set_parse_action(remove_quotes)
    fields = getLogLineBNF().parse_string(line)
            + include_directive.transform_string(included_file_contents)
    # use include_directive.transform_string to perform includes
    expanded_source = include_directive.transform_string(initial_file)
    "def" + identifier + Group("(" + Optional(DelimitedList(identifier)) + ")") + ":"
    invre = GroupEmitter(parser().parse_string(regex)).make_generator()
        (pp.one_of("! -"), 1, pp.OpAssoc.RIGHT),
        (pp.one_of("/ *"), 2, pp.OpAssoc.LEFT),
        (pp.one_of("- +"), 2, pp.OpAssoc.LEFT),
        (pp.one_of("> >= < <="), 2, pp.OpAssoc.LEFT),
        (pp.one_of("!= =="), 2, pp.OpAssoc.LEFT),
        (AND, 2, pp.OpAssoc.LEFT),
        (OR, 2, pp.OpAssoc.LEFT),
        ("^", 2, pp.OpAssoc.LEFT),
        ((NOT | pp.one_of("# - ~")).set_name("not op"), 1, pp.OpAssoc.RIGHT),
        (pp.one_of("* / // %"), 2, pp.OpAssoc.LEFT),
        (pp.one_of("+ -"), 2, pp.OpAssoc.LEFT),
        ("..", 2, pp.OpAssoc.LEFT),
        (pp.one_of("<< >>"), 2, pp.OpAssoc.LEFT),
        ("&", 2, pp.OpAssoc.LEFT),
        ("~", 2, pp.OpAssoc.LEFT),
        ("|", 2, pp.OpAssoc.LEFT),
        (pp.one_of("< > <= >= ~= =="), 2, pp.OpAssoc.LEFT),
        result = lua_script.parse_string(sample)
    success2, _ = expression.run_tests(failtests, failure_tests=True)
       UID DTSTAMP LAST-MODIFIED X RRULE EXDATE''', as_keyword=True
        return opening + wiki_markup.transform_string(t[1][1:-1]) + closing
    t["link_text"] = wiki_markup.transform_string(link_text)
        post_parse=lambda _, s: "{:,}".format(s[0]),
    ast = program.parse_string(test, parse_all=True)
            expr.copy().add_condition(
    print(row.parse_string(line).dump())
    + pp.Word("ACGTN")[1, ...].add_parse_action("".join)("gene")
    for t, startLoc, endLoc in searchseq.scan_string(g.gene, overlap=True):
    return Empty().set_parse_action(lambda s, l, t: t.__setitem__(name, l))
    quoted_string,
    OPTION_ - ident("optionName") + EQ + quoted_string("optionValue") + SEMI
            return cls(t[0].as_list())
    (bnfToken | quoted_string | optionalTerm | (LPAREN + bnfExpr + RPAREN))
                          ).set_name("street_address")
              ).set_name("header with various elements")("header")
                                   (plus_minus().set_name("pos_neg"), 1, pp.OpAssoc.RIGHT),
                                   (mult_div, 2, pp.OpAssoc.LEFT),
                                   (plus_minus, 2, pp.OpAssoc.LEFT),
                               ]).set_name("simple_arithmetic")
           ).set_name("grammar")
    rest_of_line,
    replace_with,
    + ident.set_results_name("name")
    + rest_of_line.set_results_name("value")
        operatorWord = Group(Combine(Word(alphanums) + Suppress("*"))).set_results_name(
        ) | Group(Word(alphanums)).set_results_name("word")
            Group(Suppress('"') + operatorQuotesContent + Suppress('"')).set_results_name(
            Group(Suppress("(") + operatorOr + Suppress(")")).set_results_name(
            Group(Suppress(Keyword("not", caseless=True)) + operatorNot).set_results_name(
            ).set_results_name("and")
                operatorNot + OneOrMore(~one_of("and or") + operatorAnd)
            ).set_results_name("or")
        return operatorOr.parse_string
        return self._methods[argument.get_name()](argument)
    sexp.run_tests(alltests, full_dump=False)
        self.__dict__.update(tokens.as_dict())
    shape = shapeExpr.parse_string(t)[0]
        (factop, 1, OpAssoc.LEFT),
        (expop, 2, OpAssoc.RIGHT),
        (signop, 1, OpAssoc.RIGHT),
        (multop, 2, OpAssoc.LEFT),
        (plusop, 2, OpAssoc.LEFT),
    print(expr.parse_string(t))
    + Word(alphas, alphanums + "_").set_results_name("tablename")
    + field_list_def.set_results_name("columns")
    + Word(alphanums + "_").set_results_name("fromtable")
    + Word(alphanums + "_").set_results_name("fromcolumn")
    + Word(alphanums + "_").set_results_name("totable")
    + Word(alphanums + "_").set_results_name("tocolumn")
                self.assertEqual("2t", name_type.parse_string("2t")[0])
                self.assertRaises(ParseException, name_type.parse_string, "2t")
                self.assertRaises(ParseException, name_type.parse_string, char)
            self.assertEqual("simple_test", name_type.parse_string("simple_test")[0])
        self.assertRaises(ParseException, mr.parse_string, "2t")
            self.assertRaises(ParseException, mr.parse_string, char)
        self.assertEqual("simple_test", mr.parse_string("simple_test")[0].name)
        self.assertEqual("1066", bp.number.parse_string("1066")[0])
        self.assertEqual("0", bp.number.parse_string("0")[0])
        self.assertRaises(ParseException, bp.number.parse_string, "-4")
        self.assertRaises(ParseException, bp.number.parse_string, "+4")
        self.assertRaises(ParseException, bp.number.parse_string, ".4")
        self.assertEqual("0", bp.number.parse_string("0.4")[0])
        self.assertEqual(bp.chars_no_quotecurly.parse_string("x")[0], "x")
        self.assertEqual(bp.chars_no_quotecurly.parse_string("a string")[0], "a string")
        self.assertEqual(bp.chars_no_quotecurly.parse_string('a "string')[0], "a ")
        self.assertEqual(bp.chars_no_curly.parse_string("x")[0], "x")
        self.assertEqual(bp.chars_no_curly.parse_string("a string")[0], "a string")
        self.assertEqual(bp.chars_no_curly.parse_string("a {string")[0], "a ")
        self.assertEqual(bp.chars_no_curly.parse_string("a }string")[0], "a ")
            self.assertEqual(obj.parse_string("{}").as_list(), [])
            self.assertEqual(obj.parse_string('{a "string}')[0], 'a "string')
                obj.parse_string("{a {nested} string}").as_list(),
                obj.parse_string("{a {double {nested}} string}").as_list(),
            self.assertEqual([], obj.parse_string('""').as_list())
            self.assertEqual("a string", obj.parse_string('"a string"')[0])
                obj.parse_string('"a {nested} string"').as_list(),
                obj.parse_string('"a {double {nested}} string"').as_list(),
        self.assertEqual(Macro("someascii"), bp.string.parse_string("someascii")[0])
        self.assertRaises(ParseException, bp.string.parse_string, "%#= validstring")
        self.assertEqual(bp.string.parse_string("1994")[0], "1994")
        self.assertEqual(Macro("aname"), fv.parse_string("aname")[0])
        self.assertEqual(Macro("aname"), fv.parse_string("ANAME")[0])
            fv.parse_string('aname # "some string"').as_list(),
            fv.parse_string("aname # {some {string}}").as_list(),
            ["a string", "1994"], fv.parse_string('"a string" # 1994').as_list()
            fv.parse_string('"a string" # 1994 # a_macro').as_list(),
        res = bp.comment.parse_string("@Comment{about something}")
        self.assertEqual(res.as_list(), ["comment", "{about something}"])
            bp.comment.parse_string("@COMMENT{about something").as_list(),
            bp.comment.parse_string("@comment(about something").as_list(),
            bp.comment.parse_string("@COMment about something").as_list(),
            ParseException, bp.comment.parse_string, "@commentabout something"
            ParseException, bp.comment.parse_string, "@comment+about something"
            ParseException, bp.comment.parse_string, '@comment"about something'
        res = bp.preamble.parse_string('@preamble{"about something"}')
        self.assertEqual(res.as_list(), ["preamble", "about something"])
            bp.preamble.parse_string("@PREamble{{about something}}").as_list(),
            bp.preamble.parse_string(
            ).as_list(),
        res = bp.macro.parse_string('@string{ANAME = "about something"}')
        self.assertEqual(res.as_list(), ["string", "aname", "about something"])
            bp.macro.parse_string("@string{aname = {about something}}").as_list(),
        res = bp.entry.parse_string(txt)
            res.as_list(),
        res = bp.bibfile.parse_string(txt)
        self.assertEqual(res.as_list(), res2.as_list())
        res3 = [r.as_list()[0] for r, start, end in bp.definitions.scan_string(txt)]
        self.assertEqual(res.as_list(), res3)
    print(toks.as_list())
    parsed = ppc.url.parse_string(url)
    cpp_style_comment,
            + rest_of_line
            Regex(r"\\\S+").set_parse_action(lambda t: t[0][1:]).set_name("escapedIdent")
        )  # .set_debug()
            join_string=" ",
            | (LPAR + Group(expr) + RPAR).set_name("nested_expr")
        delay = Group("#" + delayArg).set_name("delay")  # .set_debug()
        stmt = Forward().set_name("stmt")  # .set_debug()
        verilogbnf.ignore(cpp_style_comment)
    return ret.set_parse_action(pp.replace_with(val))
"""
    failed = 0
    for o, e in zip(orig.splitlines(), expected.splitlines()):
        converted = pep8_converter.transform_string(o)
        try:
            assert converted == e
        except AssertionError:
            print()
            print(f"Expected: {e!r}\n"
                  f"Observed: {converted!r}")
            failed += 1

    if failed:
        raise AssertionError(f"Failed to convert some original code ({failed} lines)")
