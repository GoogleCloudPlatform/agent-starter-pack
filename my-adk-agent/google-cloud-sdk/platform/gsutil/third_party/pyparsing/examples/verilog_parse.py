#
# verilogParse.py
#
# an example of using the pyparsing module to be able to process Verilog files
# uses BNF defined at http://www.verilog.com/VerilogBNF.html
#
#    Copyright (c) 2004-2011 Paul T. McGuire.  All rights reserved.
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# If you find this software to be useful, please make a donation to one
# of the following charities:
# - the Red Cross (https://www.redcross.org/)
# - Hospice Austin (https://www.hospiceaustin.org/)
#
#    DISCLAIMER:
#    THIS SOFTWARE IS PROVIDED BY PAUL T. McGUIRE ``AS IS'' AND ANY EXPRESS OR
#    IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF
#    MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED.  IN NO
#    EVENT SHALL PAUL T. McGUIRE OR CO-CONTRIBUTORS BE LIABLE FOR ANY DIRECT,
#    INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
#    BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OFUSE,
#    DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY
#    OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING
#    NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE,
#    EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#
#    For questions or inquiries regarding this license, or commercial use of
#    this software, contact the author via e-mail: ptmcg@users.sourceforge.net
#
# Todo:
#  - add pre-process pass to implement compilerDirectives (ifdef, include, etc.)
#
# Revision History:
#
#   1.0   - Initial release
#   1.0.1 - Fixed grammar errors:
#           . real declaration was incorrect
#           . tolerant of '=>' for '*>' operator
#           . tolerant of '?' as hex character
#           . proper handling of mintypmax_expr within path delays
#   1.0.2 - Performance tuning (requires pyparsing 1.3)
#   1.0.3 - Performance updates, using Regex (requires pyparsing 1.4)
#   1.0.4 - Performance updates, enable packrat parsing (requires pyparsing 1.4.2)
#   1.0.5 - Converted keyword Literals to Keywords, added more use of Group to
#           group parsed results tokens
#   1.0.6 - Added support for module header with no ports list (thanks, Thomas Dejanovic!)
#   1.0.7 - Fixed erroneous '<<' Forward definition in timCheckCond, omitting ()'s
#   1.0.8 - Re-released under MIT license
#   1.0.9 - Enhanced udpInstance to handle identifiers with leading '\' and subscripting
#   1.0.10 - Fixed change added in 1.0.9 to work for all identifiers, not just those used
#           for udpInstance.
#   1.0.11 - Fixed bug in inst_args, content alternatives were reversed
#   1.1.0 - Some performance fixes, convert most literal strs to Keywords
#
from pathlib import Path
import pprint
import time

__version__ = "1.1.0"

__all__ = ["__version__", "verilogbnf"]

from pyparsing import (
    Literal,
    Keyword,
    Word,
    Forward,
    DelimitedList,
    Group,
    Optional,
    Combine,
    alphas,
    nums,
    restOfLine,
    alphanums,
    dbl_quoted_string,
    empty,
    ParseBaseException,
    one_of,
    StringEnd,
    FollowedBy,
    ParserElement,
    Regex,
    cppStyleComment,
)
import pyparsing

usePackrat = True

packratOn = False
if usePackrat:
    try:
        ParserElement.enable_packrat()
    except Exception:
        pass
    else:
        packratOn = True


verilogbnf = None


def make_verilog_bnf():
    global verilogbnf

    if verilogbnf is None:

        # compiler directives
        compilerDirective = Combine(
            "`"
            + one_of(
                "define undef ifdef else endif default_nettype"
                " include resetall timescale unconnected_drive"
                " nounconnected_drive celldefine endcelldefine",
                as_keyword=True,
            )
            + restOfLine
        ).set_name("compilerDirective")

        # primitives
        (
            SEMI,
            COLON,
            LPAR,
            RPAR,
            LBRACE,
            RBRACE,
            LBRACK,
            RBRACK,
            DOT,
            COMMA,
            EQ,
        ) = Literal.using_each(";:(){}[].,=")

        identLead = alphas + "$_"
        identBody = alphanums + "$_"
        identifier1 = Regex(
            rf"\.?[{identLead}][{identBody}]*(\.[{identLead}][{identBody}]*)*"
        ).set_name("baseIdent")
        identifier2 = (
            Regex(r"\\\S+").setParseAction(lambda t: t[0][1:]).set_name("escapedIdent")
        )  # .setDebug()
        identifier = identifier1 | identifier2
        assert identifier2 == r"\abc"

        hexnums = nums + "abcdefABCDEF" + "_?"
        base = Regex("'[bBoOdDhH]").set_name("base")
        basedNumber = Combine(
            (Word(nums + "_") | "") + base + Word(hexnums + "xXzZ"),
            joinString=" ",
            adjacent=False,
        ).set_name("basedNumber")
        # number = ( basedNumber | Combine( Word( "+-"+spacedNums, spacedNums ) +
        # Optional( DOT + Optional( Word( spacedNums ) ) ) +
        # Optional( e + Word( "+-"+spacedNums, spacedNums ) ) ).set_name("numeric") )
        number = (
            basedNumber | Regex(r"[+-]?[0-9_]+(\.[0-9_]*)?([Ee][+-]?[0-9_]+)?")
        ).set_name("numeric")

        expr = Forward().set_name("expr")
        concat = Group(LBRACE + DelimitedList(expr) + RBRACE)
        multiConcat = Group("{" + expr + concat + "}").set_name("multiConcat")
        funcCall = Group(
            identifier + LPAR + (DelimitedList(expr) | "") + RPAR
        ).set_name("funcCall")

        subscrRef = Group(LBRACK + DelimitedList(expr, COLON) + RBRACK)
        subscrIdentifier = Group(identifier + (subscrRef | ""))
        # scalarConst = "0" | (( FollowedBy('1') + one_of("1'b0 1'b1 1'bx 1'bX 1'B0 1'B1 1'Bx 1'BX 1") ))
        scalarConst = Regex("0|1('[Bb][01xX])?")
        mintypmaxExpr = Group(expr + COLON + expr + COLON + expr).set_name("mintypmax")
        primary = (
            number
            | (LPAR + mintypmaxExpr + RPAR)
            | (LPAR + Group(expr) + RPAR).set_name("nestedExpr")
            | multiConcat
            | concat
            | dbl_quoted_string
            | funcCall
            | subscrIdentifier
        )

        unop = one_of("+  -  !  ~  &  ~&  |  ^|  ^  ~^").set_name("unop")
        binop = one_of(
            "+  -  *  /  %  ==  !=  ===  !==  &&  "
            "||  <  <=  >  >=  &  |  ^  ^~  >>  << ** <<< >>>"
        ).set_name("binop")

        expr <<= (
            (unop + expr)
            | (primary + "?" + expr + COLON + expr)  # must be first!
            | (primary + ((binop + expr) | ""))
        )

        lvalue = subscrIdentifier | concat

        # keywords
        reg = Keyword("reg")
        trireg = Keyword("trireg")
        signed = Keyword("signed")
        parameter = Keyword("parameter")
        input_, output, inout = Keyword.using_each("input output inout".split())
        time = Keyword("time")
        integer = Keyword("integer")
        real = Keyword("real")
        event = Keyword("event")
        scalared = Keyword("scalared")
        vectored = Keyword("vectored")
        if_ = Keyword("if")
        else_ = Keyword("else")
        always = Keyword("always")
        initial = Keyword("initial")
        small, medium, large = Keyword.using_each("small medium large".split())
        edge = Keyword("edge")
        posedge = Keyword("posedge")
        negedge = Keyword("negedge")
        specify, endspecify = Keyword.using_each("specify endspecify".split())
        primitive, endprimitive = Keyword.using_each("primitive endprimitive".split())
        fork = Keyword("fork")
        join = Keyword("join")
        begin = Keyword("begin")
        end = Keyword("end")
        default = Keyword("default")
        forever = Keyword("forever")
        repeat = Keyword("repeat")
        while_ = Keyword("while")
        for_ = Keyword("for")
        case = one_of("case casez casex", as_keyword=True)
        endcase = Keyword("endcase")
        wait = Keyword("wait")
        disable = Keyword("disable")
        deassign = Keyword("deassign")
        force = Keyword("force")
        release = Keyword("release")
        assign = Keyword("assign")
        table, endtable = Keyword.using_each("table endtable".split())
        function, endfunction = Keyword.using_each("function endfunction".split())
        task, endtask = Keyword.using_each("task endtask".split())
        module, macromodule, endmodule = Keyword.using_each(
            "module macromodule endmodule".split()
        )

        eventExpr = Forward()
        eventTerm = (
            (posedge + expr) | (negedge + expr) | expr | (LPAR + eventExpr + RPAR)
        )
        eventExpr <<= Group(DelimitedList(eventTerm, Keyword("or")))
        eventControl = Group(
            "@" + ((LPAR + eventExpr + RPAR) | identifier | "*")
        ).set_name("eventCtrl")

        delayArg = (
            number
            | Word(alphanums + "$_")
            | (LPAR + Group(DelimitedList(mintypmaxExpr | expr)) + RPAR)  # identifier |
        ).set_name(
            "delayArg"
        )  # .setDebug()
        delay = Group("#" + delayArg).set_name("delay")  # .setDebug()
        delayOrEventControl = delay | eventControl

        assgnmt = Group(lvalue + EQ + (delayOrEventControl | "") + expr).set_name(
            "assgnmt"
        )
        nbAssgnmt = Group(
            (lvalue + "<=" + (delay | "") + expr)
            | (lvalue + "<=" + (eventControl | "") + expr)
        ).set_name("nbassgnmt")

        range_ = LBRACK + expr + COLON + expr + RBRACK

        paramAssgnmt = Group(identifier + EQ + expr).set_name("paramAssgnmt")
        parameterDecl = Group(
            parameter + (range_ | "") + DelimitedList(paramAssgnmt) + SEMI
        ).set_name("paramDecl")

        inputDecl = Group(input_ + (range_ | "") + DelimitedList(identifier) + SEMI)
        outputDecl = Group(output + (range_ | "") + DelimitedList(identifier) + SEMI)
        inoutDecl = Group(inout + (range_ | "") + DelimitedList(identifier) + SEMI)

        regIdentifier = Group(identifier + (LBRACK + expr + COLON + expr + RBRACK | ""))
        regDecl = Group(
            reg + (signed | "") + (range_ | "") + DelimitedList(regIdentifier) + SEMI
        ).set_name("regDecl")
        timeDecl = Group(time + DelimitedList(regIdentifier) + SEMI)
        integerDecl = Group(integer + DelimitedList(regIdentifier) + SEMI)

        strength0 = one_of("supply0  strong0  pull0  weak0  highz0", as_keyword=True)
        strength1 = one_of("supply1  strong1  pull1  weak1  highz1", as_keyword=True)
        driveStrength = Group(
            LPAR
            + ((strength0 + COMMA + strength1) | (strength1 + COMMA + strength0))
            + RPAR
        ).set_name("driveStrength")
        nettype = one_of(
            "wire  tri  tri1  supply0  wand  triand  tri0  supply1  wor  trior  trireg",
            as_keyword=True,
        )
        expandRange = (scalared | vectored | "") + range_
        realDecl = Group(real + DelimitedList(identifier) + SEMI)

        eventDecl = Group(event + DelimitedList(identifier) + SEMI)

        blockDecl = (
            parameterDecl | regDecl | integerDecl | realDecl | timeDecl | eventDecl
        )

        stmt = Forward().set_name("stmt")  # .setDebug()
        stmtOrNull = stmt | SEMI
        caseItem = (DelimitedList(expr) + COLON + stmtOrNull) | (
            default + Optional(":") + stmtOrNull
        )
        stmt <<= Group(
            (begin + Group(stmt[...:end]) + end).set_name("begin-end")
            | (
                if_ + Group(LPAR + expr + RPAR) + stmtOrNull + (else_ + stmtOrNull | "")
            ).set_name("if")
            | (delayOrEventControl + stmtOrNull)
            | (case + LPAR + expr + RPAR + caseItem[1, ...] + endcase)
            | (forever + stmt)
            | (repeat + LPAR + expr + RPAR + stmt)
            | (while_ + LPAR + expr + RPAR + stmt)
            | (
                for_
                + LPAR
                + assgnmt
                + SEMI
                + Group(expr)
                + SEMI
                + assgnmt
                + RPAR
                + stmt
            )
            | (fork + stmt[...] + join)
            | (fork + COLON + identifier + blockDecl[...] + stmt[...] + end)
            | (wait + LPAR + expr + RPAR + stmtOrNull)
            | ("->" + identifier + SEMI)
            | (disable + identifier + SEMI)
            | (assign + assgnmt + SEMI)
            | (deassign + lvalue + SEMI)
            | (force + assgnmt + SEMI)
            | (release + lvalue + SEMI)
            | (begin + COLON + identifier + blockDecl[...] + stmt[...] + end).set_name(
                "begin:label-end"
            )
            |
            # these  *have* to go at the end of the list!!!
            (assgnmt + SEMI)
            | (nbAssgnmt + SEMI)
            | (
                Combine(Optional("$") + identifier)
                + (LPAR + DelimitedList(expr | empty) + RPAR | "")
                + SEMI
            )
        ).set_name("stmtBody")
        """
        x::=<blocking_assignment> ;
        x||= <non_blocking_assignment> ;
        x||= if ( <expression> ) <statement_or_null>
        x||= if ( <expression> ) <statement_or_null> else <statement_or_null>
        x||= case ( <expression> ) <case_item>+ endcase
        x||= casez ( <expression> ) <case_item>+ endcase
        x||= casex ( <expression> ) <case_item>+ endcase
        x||= forever <statement>
        x||= repeat ( <expression> ) <statement>
        x||= while ( <expression> ) <statement>
        x||= for ( <assignment> ; <expression> ; <assignment> ) <statement>
        x||= <delay_or_event_control> <statement_or_null>
        x||= wait ( <expression> ) <statement_or_null>
        x||= -> <name_of_event> ;
        x||= <seq_block>
        x||= <par_block>
        x||= <task_enable>
        x||= <system_task_enable>
        x||= disable <name_of_task> ;
        x||= disable <name_of_block> ;
        x||= assign <assignment> ;
        x||= deassign <lvalue> ;
        x||= force <assignment> ;
        x||= release <lvalue> ;
        """
        alwaysStmt = Group(always + (eventControl | "") + stmt).set_name("alwaysStmt")
        initialStmt = Group(initial + stmt).set_name("initialStmt")

        chargeStrength = Group(LPAR + (small | medium | large) + RPAR).set_name(
            "chargeStrength"
        )

        continuousAssign = Group(
            assign + (driveStrength | "") + (delay | "") + DelimitedList(assgnmt) + SEMI
        ).set_name("continuousAssign")

        tfDecl = (
            parameterDecl
            | inputDecl
            | outputDecl
            | inoutDecl
            | regDecl
            | timeDecl
            | integerDecl
            | realDecl
        )

        functionDecl = Group(
            function
            + (range_ | "integer" | "real" | "")
            + identifier
            + SEMI
            + Group(tfDecl[1, ...])
            + Group(stmt[...])
            + endfunction
        )

        inputOutput = input_ | output
        netDecl1Arg = (
            nettype
            + (expandRange | "")
            + (delay | "")
            + Group(DelimitedList(~inputOutput + identifier))
        )
        netDecl2Arg = (
            trireg
            + (chargeStrength | "")
            + (expandRange | "")
            + (delay | "")
            + Group(DelimitedList(~inputOutput + identifier))
        )
        netDecl3Arg = (
            nettype
            + (driveStrength | "")
            + (expandRange | "")
            + (delay | "")
            + Group(DelimitedList(assgnmt))
        )
        netDecl1 = Group(netDecl1Arg + SEMI).set_name("netDecl1")
        netDecl2 = Group(netDecl2Arg + SEMI).set_name("netDecl2")
        netDecl3 = Group(netDecl3Arg + SEMI).set_name("netDecl3")

        gateType = one_of(
            "and  nand  or  nor xor  xnor buf  bufif0 bufif1 "
            "not  notif0 notif1  pulldown pullup nmos  rnmos "
            "pmos rpmos cmos rcmos   tran rtran  tranif0  "
            "rtranif0  tranif1 rtranif1",
            as_keyword=True,
        )
        gateInstance = (
            (Group(identifier + (range_ | "")) | "")
            + LPAR
            + Group(DelimitedList(expr))
            + RPAR
        )
        gateDecl = Group(
            gateType
            + (driveStrength | "")
            + (delay | "")
            + DelimitedList(gateInstance)
            + SEMI
        )

        udpInstance = Group(
            Group(identifier + (range_ | subscrRef | ""))
            + LPAR
            + Group(DelimitedList(expr))
            + RPAR
        )
        udpInstantiation = Group(
            identifier
            - (driveStrength | "")
            + (delay | "")
            + DelimitedList(udpInstance)
            + SEMI
        ).set_name("udpInstantiation")

        parameterValueAssignment = Group(
            Literal("#") + LPAR + Group(DelimitedList(expr)) + RPAR
        )
        namedPortConnection = Group(DOT + identifier + LPAR + expr + RPAR).set_name(
            "namedPortConnection"
        )  # .setDebug()
        # assert r".\abc (abc )" == namedPortConnection
        modulePortConnection = expr | empty
        inst_args = Group(
            LPAR
            + (DelimitedList(namedPortConnection) | DelimitedList(modulePortConnection))
            + RPAR
        ).set_name("inst_args")
        moduleInstance = Group(Group(identifier + (range_ | "")) + inst_args).set_name(
            "moduleInstance"
        )  # .setDebug()

        moduleInstantiation = Group(
            identifier
            + (parameterValueAssignment | "")
            + DelimitedList(moduleInstance).set_name("moduleInstanceList")
            + SEMI
        ).set_name("moduleInstantiation")

        parameterOverride = Group("defparam" + DelimitedList(paramAssgnmt) + SEMI)
        task = Group(task + identifier + SEMI + tfDecl[...] + stmtOrNull + endtask)

        specparamDecl = Group("specparam" + DelimitedList(paramAssgnmt) + SEMI)

        pathDescr1 = Group(LPAR + subscrIdentifier + "=>" + subscrIdentifier + RPAR)
        pathDescr2 = Group(
            LPAR
            + Group(DelimitedList(subscrIdentifier))
            + "*>"
            + Group(DelimitedList(subscrIdentifier))
            + RPAR
        )
        pathDescr3 = Group(
            LPAR
            + Group(DelimitedList(subscrIdentifier))
            + "=>"
            + Group(DelimitedList(subscrIdentifier))
            + RPAR
        )
        pathDelayValue = Group(
            (LPAR + Group(DelimitedList(mintypmaxExpr | expr)) + RPAR)
            | mintypmaxExpr
            | expr
        )
        pathDecl = Group(
            (pathDescr1 | pathDescr2 | pathDescr3) + EQ + pathDelayValue + SEMI
        ).set_name("pathDecl")

        portConditionExpr = Forward()
        portConditionTerm = (unop | "") + subscrIdentifier
        portConditionExpr <<= portConditionTerm + (binop + portConditionExpr | "")
        polarityOp = one_of("+ -")
        levelSensitivePathDecl1 = Group(
            if_
            + Group(LPAR + portConditionExpr + RPAR)
            + subscrIdentifier
            + (polarityOp | "")
            + "=>"
            + subscrIdentifier
            + EQ
            + pathDelayValue
            + SEMI
        )
        levelSensitivePathDecl2 = Group(
            if_
            + Group(LPAR + portConditionExpr + RPAR)
            + LPAR
            + Group(DelimitedList(subscrIdentifier))
            + (polarityOp | "")
            + "*>"
            + Group(DelimitedList(subscrIdentifier))
            + RPAR
            + EQ
            + pathDelayValue
            + SEMI
        )
        levelSensitivePathDecl = levelSensitivePathDecl1 | levelSensitivePathDecl2

        edgeIdentifier = posedge | negedge
        edgeSensitivePathDecl1 = Group(
            (if_ + Group(LPAR + expr + RPAR) | "")
            + LPAR
            + (edgeIdentifier | "")
            + subscrIdentifier
            + "=>"
            + LPAR
            + subscrIdentifier
            + (polarityOp | "")
            + COLON
            + expr
            + RPAR
            + RPAR
            + EQ
            + pathDelayValue
            + SEMI
        )
        edgeSensitivePathDecl2 = Group(
            (if_ + Group(LPAR + expr + RPAR) | "")
            + LPAR
            + (edgeIdentifier | "")
            + subscrIdentifier
            + "*>"
            + LPAR
            + DelimitedList(subscrIdentifier)
            + (polarityOp | "")
            + COLON
            + expr
            + RPAR
            + RPAR
            + EQ
            + pathDelayValue
            + SEMI
        )
        edgeSensitivePathDecl = edgeSensitivePathDecl1 | edgeSensitivePathDecl2

        edgeDescr = one_of("01 10 0x x1 1x x0").set_name("edgeDescr")

        timCheckEventControl = Group(
            posedge | negedge | (edge + LBRACK + DelimitedList(edgeDescr) + RBRACK)
        )
        timCheckCond = Forward()
        timCondBinop = one_of("== === != !==")
        timCheckCondTerm = (expr + timCondBinop + scalarConst) | (Optional("~") + expr)
        timCheckCond <<= (LPAR + timCheckCond + RPAR) | timCheckCondTerm
        timCheckEvent = Group(
            (timCheckEventControl | "") + subscrIdentifier + ("&&&" + timCheckCond | "")
        )
        timCheckLimit = expr
        controlledTimingCheckEvent = Group(
            timCheckEventControl + subscrIdentifier + ("&&&" + timCheckCond | "")
        )
        notifyRegister = identifier

        systemTimingCheck1 = Group(
            "$setup"
            + LPAR
            + timCheckEvent
            + COMMA
            + timCheckEvent
            + COMMA
            + timCheckLimit
            + (COMMA + notifyRegister | "")
            + RPAR
            + SEMI
        )
        systemTimingCheck2 = Group(
            "$hold"
            + LPAR
            + timCheckEvent
            + COMMA
            + timCheckEvent
            + COMMA
            + timCheckLimit
            + (COMMA + notifyRegister | "")
            + RPAR
            + SEMI
        )
        systemTimingCheck3 = Group(
            "$period"
            + LPAR
            + controlledTimingCheckEvent
            + COMMA
            + timCheckLimit
            + (COMMA + notifyRegister | "")
            + RPAR
            + SEMI
        )
        systemTimingCheck4 = Group(
            "$width"
            + LPAR
            + controlledTimingCheckEvent
            + COMMA
            + timCheckLimit
            + (COMMA + expr + COMMA + notifyRegister | "")
            + RPAR
            + SEMI
        )
        systemTimingCheck5 = Group(
            "$skew"
            + LPAR
            + timCheckEvent
            + COMMA
            + timCheckEvent
            + COMMA
            + timCheckLimit
            + (COMMA + notifyRegister | "")
            + RPAR
            + SEMI
        )
        systemTimingCheck6 = Group(
            "$recovery"
            + LPAR
            + controlledTimingCheckEvent
            + COMMA
            + timCheckEvent
            + COMMA
            + timCheckLimit
            + (COMMA + notifyRegister | "")
            + RPAR
            + SEMI
        )
        systemTimingCheck7 = Group(
            "$setuphold"
            + LPAR
            + timCheckEvent
            + COMMA
            + timCheckEvent
            + COMMA
            + timCheckLimit
            + COMMA
            + timCheckLimit
            + (COMMA + notifyRegister | "")
            + RPAR
            + SEMI
        )
        systemTimingCheck = (
            FollowedBy("$")
            + (
                systemTimingCheck1
                | systemTimingCheck2
                | systemTimingCheck3
                | systemTimingCheck4
                | systemTimingCheck5
                | systemTimingCheck6
                | systemTimingCheck7
            )
        ).set_name("systemTimingCheck")
        sdpd = (
            if_
            + Group(LPAR + expr + RPAR)
            + (pathDescr1 | pathDescr2)
            + EQ
            + pathDelayValue
            + SEMI
        )

        specifyItem = (
            specparamDecl
            | pathDecl
            | levelSensitivePathDecl
            | edgeSensitivePathDecl
            | systemTimingCheck
            | sdpd
        )
        """
        x::= <specparam_declaration>
        x||= <path_declaration>
        x||= <level_sensitive_path_declaration>
        x||= <edge_sensitive_path_declaration>
        x||= <system_timing_check>
        x||= <sdpd>
        """
        specifyBlock = Group(
            specify + specifyItem[...:endspecify] + endspecify
        ).set_name("specifyBlock")

        moduleItem = (
            parameterDecl
            | inputDecl
            | outputDecl
            | inoutDecl
            | regDecl
            | netDecl3
            | netDecl1
            | netDecl2
            | timeDecl
            | integerDecl
            | realDecl
            | eventDecl
            | gateDecl
            | parameterOverride
            | continuousAssign
            | specifyBlock
            | initialStmt
            | alwaysStmt
            | task
            | functionDecl
            # these have to be at the end - they start with identifiers
            | moduleInstantiation
            | udpInstantiation
        )
        """  All possible moduleItems, from Verilog grammar spec
        x::= <parameter_declaration>
        x||= <input_declaration>
        x||= <output_declaration>
        x||= <inout_declaration>
        ?||= <net_declaration>  (spec does not seem consistent for this item)
        x||= <reg_declaration>
        x||= <time_declaration>
        x||= <integer_declaration>
        x||= <real_declaration>
        x||= <event_declaration>
        x||= <gate_declaration>
        x||= <UDP_instantiation>
        x||= <module_instantiation>
        x||= <parameter_override>
        x||= <continuous_assign>
        x||= <specify_block>
        x||= <initial_statement>
        x||= <always_statement>
        x||= <task>
        x||= <function>
        """
        portRef = subscrIdentifier
        portExpr = portRef | Group(LBRACE + DelimitedList(portRef) + RBRACE)
        port = portExpr | Group(DOT + identifier + LPAR + portExpr + RPAR)

        moduleHdr = Group(
            (module | macromodule)
            + identifier
            + (
                LPAR
                + Group(
                    (
                        DelimitedList(
                            Group(
                                (input_ | output)
                                + (netDecl1Arg | netDecl2Arg | netDecl3Arg)
                            )
                            | port
                        )
                        | ""
                    )
                )
                + RPAR
                | ""
            )
            + SEMI
        ).set_name("moduleHdr")

        module_expr = Group(
            moduleHdr + Group(moduleItem[...:endmodule]) + endmodule
        ).set_name(
            "module"
        )  # .setDebug()

        udpDecl = outputDecl | inputDecl | regDecl
        # udpInitVal = one_of("1'b0 1'b1 1'bx 1'bX 1'B0 1'B1 1'Bx 1'BX 1 0 x X")
        udpInitVal = (Regex("1'[bB][01xX]|[01xX]")).set_name("udpInitVal")
        udpInitialStmt = Group(
            "initial" + identifier + EQ + udpInitVal + SEMI
        ).set_name("udpInitialStmt")

        levelSymbol = one_of("0   1   x   X   ?   b   B")
        levelInputList = Group(levelSymbol[1, ...].set_name("levelInpList"))

        outputSymbol = one_of("0   1   x   X")
        combEntry = Group(levelInputList + COLON + outputSymbol + SEMI)
        edgeSymbol = one_of("r   R   f   F   p   P   n   N   *")
        edge = Group(LPAR + levelSymbol + levelSymbol + RPAR) | Group(edgeSymbol)
        edgeInputList = Group(levelSymbol[...] + edge + levelSymbol[...])
        inputList = levelInputList | edgeInputList
        seqEntry = Group(
            inputList + COLON + levelSymbol + COLON + (outputSymbol | "-") + SEMI
        ).set_name("seqEntry")
        udpTableDefn = Group(
            table + (combEntry | seqEntry)[1, ...] + endtable
        ).set_name("table")

        """
        <UDP>
        ::= primitive <name_of_UDP> ( <name_of_variable> <,<name_of_variable>>* ) ;
                <UDP_declaration>+
                <UDP_initial_statement>?
                <table_definition>
                endprimitive
        """
        udp = Group(
            primitive
            + identifier
            + LPAR
            + Group(DelimitedList(identifier))
            + RPAR
            + SEMI
            + udpDecl[1, ...]
            + (udpInitialStmt | "")
            + udpTableDefn
            + endprimitive
        )

        verilogbnf = (module_expr | udp)[1, ...] + StringEnd()

        verilogbnf.ignore(cppStyleComment)
        verilogbnf.ignore(compilerDirective)

    return verilogbnf


def test(strng):
    tokens = []
    try:
        tokens = make_verilog_bnf().parse_string(strng)
    except ParseBaseException as err:
        print()
        print(err.explain())
    return tokens


if __name__ == "__main__":

    def main():
        import sys

        sys.setrecursionlimit(5000)
        print(f"Verilog parser test (V {__version__})")
        print(f" - using pyparsing version {pyparsing.__version__}")
        print(f" - using Python version {sys.version}")
        if packratOn:
            print(" - using packrat parsing")
        print()

        import gc

        failCount = 0
        make_verilog_bnf()
        numlines = 0
        fileDir = "verilog"
        if len(sys.argv) > 1:
            fileDir = sys.argv[1]
        fileDir = Path(fileDir)
        allFiles = [f for f in fileDir.rglob("*.v")]

        pretty = pprint.PrettyPrinter(indent=2)
        totalTime = 0
        for vfile in allFiles:
            gc.collect()
            gc.collect()
            filelines = vfile.read_text().splitlines()
            print(vfile.name, len(filelines), end=" ")
            numlines += len(filelines)
            teststr = "\n".join(filelines)
            time1 = time.perf_counter()
            tokens = test(teststr)
            time2 = time.perf_counter()
            elapsed = time2 - time1
            totalTime += elapsed
            if len(tokens):
                print(f"OK {elapsed}")

                (fileDir / "parseOutput").mkdir(exist_ok=True)
                outfile = fileDir / "parseOutput" / (vfile.name + ".parsed.txt")
                outfile.write_text(f"{teststr}\n\n{pretty.pformat(tokens.as_list())}\n")
            else:
                print(f"failed {elapsed}")
                failCount += 1
                # for i, line in enumerate(filelines, 1):
                #     print(f"{i:4d}: {line.rstrip()}")

        print(f"Total parse time: {totalTime}")
        print(f"Total source lines: {numlines}")
        print(f"Average lines/sec: {numlines / (totalTime + 0.05):.1f}")
        if failCount:
            print(f"FAIL - {failCount} files failed to parse")
        else:
            print("SUCCESS - all files parsed")

        return 0

    main()
