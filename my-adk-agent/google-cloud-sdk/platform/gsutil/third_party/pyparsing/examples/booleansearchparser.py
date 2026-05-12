"""
Boolean Search query parser (Based on searchparser: https://github.com/pyparsing/pyparsing/blob/master/examples/searchparser.py)

version 2018-07-22

This search query parser uses the excellent Pyparsing module
(http://pyparsing.sourceforge.net/) to parse search queries by users.
It handles:

* 'and', 'or' and implicit 'and' operators;
* parentheses;
* quoted strings;
* wildcards at the end of a search term (help*);
* wildcards at the beginning of a search term (*lp);
* non-western languages

Requirements:
* Python
* Pyparsing

SAMPLE USAGE:
from booleansearchparser import BooleanSearchParser
from __future__ import print_function
bsp = BooleanSearchParser()
text = u"wildcards at the beginning of a search term "
exprs= [
    u"*cards and term", #True
    u"wild* and term",  #True
    u"not terms",       #True
    u"terms or begin",  #False
]
for expr in exprs:
    print (bsp.match(text,expr))

#non-western samples
text = u"안녕하세요, 당신은 어떠세요?"
exprs= [
    u"*신은 and 어떠세요", #True
    u"not 당신은",       #False
    u"당신 or 당",  #False
]
for expr in exprs:
    print (bsp.match(text,expr))
-------------------------------------------------------------------------------
Copyright (c) 2006, Estrate, the Netherlands
All rights reserved.

Redistribution and use in source and binary forms, with or without modification,
are permitted provided that the following conditions are met:

* Redistributions of source code must retain the above copyright notice, this
  list of conditions and the following disclaimer.
* Redistributions in binary form must reproduce the above copyright notice,
  this list of conditions and the following disclaimer in the documentation
  and/or other materials provided with the distribution.
* Neither the name of Estrate nor the names of its contributors may be used
  to endorse or promote products derived from this software without specific
  prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR
ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
(INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON
ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

CONTRIBUTORS:
- Steven Mooij
- Rudolph Froger
- Paul McGuire
- Guiem Bosch
- Francesc Garcia

TODO:
- add more docs
- ask someone to check my English texts
- add more kinds of wildcards ('*' at the beginning and '*' inside a word)?

"""
from pyparsing import (
    Word,
    alphanums,
    CaselessKeyword,
    Group,
    Forward,
    Suppress,
    OneOrMore,
    one_of,
    ParserElement,
)
import re

ParserElement.enablePackrat()

# Updated on 02 Dec 2021 according to ftp://ftp.unicode.org/Public/UNIDATA/Blocks.txt
# (includes characters not found in the BasicMultilingualPlane)
alphabet_ranges = [
    # CYRILIC: https://en.wikipedia.org/wiki/Cyrillic_(Unicode_block)
    [int("0400", 16), int("04FF", 16)],
    # ARABIC: https://en.wikipedia.org/wiki/Arabic_(Unicode_block) (Arabic (0600–06FF)+ Syriac (0700–074F)+ Arabic Supplement (0750–077F))
    [int("0600", 16), int("07FF", 16)],
    # THAI: https://en.wikipedia.org/wiki/Thai_(Unicode_block)
    [int("0E00", 16), int("0E7F", 16)],
    # JAPANESE : https://en.wikipedia.org/wiki/Japanese_writing_system (Hiragana (3040–309F) + Katakana (30A0–30FF))
    [int("3040", 16), int("30FF", 16)],
    # Enclosed CJK Letters and Months
    [int("3200", 16), int("32FF", 16)],
    # CHINESE: https://en.wikipedia.org/wiki/CJK_Unified_Ideographs_(Unicode_block)
    [int("4E00", 16), int("9FFF", 16)],
    # KOREAN : https://en.wikipedia.org/wiki/Hangul
    [int("1100", 16), int("11FF", 16)],
    [int("3130", 16), int("318F", 16)],
    [int("A960", 16), int("A97F", 16)],
    [int("AC00", 16), int("D7AF", 16)],
    [int("D7B0", 16), int("D7FF", 16)],
    # Halfwidth and Fullwidth Forms
    [int("FF00", 16), int("FFEF", 16)],
]


class BooleanSearchParser:
    def __init__(self, only_parse=False):
        self._methods = {
            "and": self.evaluateAnd,
            "or": self.evaluateOr,
            "not": self.evaluateNot,
            "parenthesis": self.evaluateParenthesis,
            "quotes": self.evaluateQuotes,
            "word": self.evaluateWord,
            "wordwildcardprefix": self.evaluateWordWildcardPrefix,
            "wordwildcardsufix": self.evaluateWordWildcardSufix,
        }
        self._parser = self.parser()
        self.text = ""
        self.words = []

    def parser(self):
        """
        This function returns a parser.
        The grammar should be like most full text search engines (Google, Tsearch, Lucene).

        Grammar:
        - a query consists of alphanumeric words, with an optional '*'
          wildcard at the end or the beginning of a word
        - a sequence of words between quotes is a literal string
        - words can be used together by using operators ('and' or 'or')
        - words with operators can be grouped with parenthesis
        - a word or group of words can be preceded by a 'not' operator
        - the 'and' operator precedes an 'or' operator
        - if an operator is missing, use an 'and' operator
        """
        operatorOr = Forward()

        alphabet = alphanums

        # support for non-western alphabets
        for lo, hi in alphabet_ranges:
            alphabet += "".join(chr(c) for c in range(lo, hi + 1) if not chr(c).isspace())

        operatorWord = Group(Word(alphabet + "*")).set_results_name("word*")

        operatorQuotesContent = Forward()
        operatorQuotesContent << ((operatorWord + operatorQuotesContent) | operatorWord)

        operatorQuotes = (
            Group(Suppress('"') + operatorQuotesContent + Suppress('"')).set_results_name(
                "quotes"
            )
            | operatorWord
        )

        operatorParenthesis = (
            Group(Suppress("(") + operatorOr + Suppress(")")).set_results_name(
                "parenthesis"
            )
            | operatorQuotes
        )

        operatorNot = Forward()
        operatorNot << (
            Group(Suppress(CaselessKeyword("not")) + operatorNot).set_results_name(
                "not"
            )
            | operatorParenthesis
        )

        operatorAnd = Forward()
        operatorAnd << (
            Group(
                operatorNot + Suppress(CaselessKeyword("and")) + operatorAnd
            ).set_results_name("and")
            | Group(
                operatorNot + OneOrMore(~one_of("and or") + operatorAnd)
            ).set_results_name("and")
            | operatorNot
        )

        operatorOr << (
            Group(
                operatorAnd + Suppress(CaselessKeyword("or")) + operatorOr
            ).set_results_name("or")
            | operatorAnd
        )

        return operatorOr.parse_string

    def evaluateAnd(self, argument):
        return all(self.evaluate(arg) for arg in argument)

    def evaluateOr(self, argument):
        return any(self.evaluate(arg) for arg in argument)

    def evaluateNot(self, argument):
        return self.GetNot(self.evaluate(argument[0]))

    def evaluateParenthesis(self, argument):
        return self.evaluate(argument[0])

    def evaluateQuotes(self, argument):
        """Evaluate quoted strings

        First is does an 'and' on the individual search terms, then it asks the
        function GetQuoted to only return the subset of ID's that contain the
        literal string.
        """
        # r = set()
        r = False
        search_terms = []
        for item in argument:
            search_terms.append(item[0])
            r = r and self.evaluate(item)
        return self.GetQuotes(" ".join(search_terms), r)

    def evaluateWord(self, argument):
        wildcard_count = argument[0].count("*")
        if wildcard_count > 0:
            if wildcard_count == 1 and argument[0].startswith("*"):
                return self.GetWordWildcard(argument[0][1:], method="endswith")
            if wildcard_count == 1 and argument[0].endswith("*"):
                return self.GetWordWildcard(argument[0][:-1], method="startswith")
            else:
                _regex = argument[0].replace("*", ".+")
                matched = False
                for w in self.words:
                    matched = bool(re.search(_regex, w))
                    if matched:
                        break
                return matched

        return self.GetWord(argument[0])

    def evaluateWordWildcardPrefix(self, argument):
        return self.GetWordWildcard(argument[0], method="endswith")

    def evaluateWordWildcardSufix(self, argument):
        return self.GetWordWildcard(argument[0], method="startswith")

    def evaluate(self, argument):
        return self._methods[argument.getName()](argument)

    def Parse(self, query):
        return self.evaluate(self._parser(query)[0])

    def GetWord(self, word):
        return word in self.words

    def GetWordWildcard(self, word, method="startswith"):
        matched = False
        for w in self.words:
            matched = getattr(w, method)(word)
            if matched:
                break
        return matched

    """
    def GetKeyword(self, name, value):
        return set()

    def GetBetween(self, min, max):
        print (min,max)
        return set()
    """

    def GetQuotes(self, search_string, tmp_result):
        return search_string in self.text

    def GetNot(self, not_set):
        return not not_set

    def _split_words(self, text):
        words = []
        """
        >>> import string
        >>> string.punctuation
        '!"#$%&\'()*+,-./:;<=>?@[\\]^_`{|}~'
        """
        # it will keep @, # and
        # usernames and hashtags can contain dots, so a double check is done
        r = re.compile(r"[\s{}]+".format(re.escape("!\"$%&'()*+,-/:;<=>?[\\]^`{|}~")))
        _words = r.split(text)
        for _w in _words:
            if "." in _w and not _w.startswith("#") and not _w.startswith("@"):
                for __w in _w.split("."):
                    words.append(__w)
                continue

            words.append(_w)

        return words

    def match(self, text, expr):
        self.text = text
        self.words = self._split_words(text)

        return self.Parse(expr)


class ParserTest(BooleanSearchParser):
    """Tests the parser with some search queries
    tests contains a dictionary with tests and expected results.
    """

    def Test(self):
        # fmt: off
        exprs = {
            "0": "help",
            "1": "help or hulp",
            "2": "help and hulp",
            "3": "help hulp",
            "4": "help and hulp or hilp",
            "5": "help or hulp and hilp",
            "6": "help or hulp or hilp or halp",
            "7": "(help or hulp) and (hilp or halp)",
            "8": "help and (hilp or halp)",
            "9": "(help and (hilp or halp)) or hulp",
            "10": "not help",
            "11": "not hulp and halp",
            "12": "not (help and halp)",
            "13": '"help me please"',
            "14": '"help me please" or hulp',
            "15": '"help me please" or (hulp and halp)',
            "16": "help*",
            "17": "help or hulp*",
            "18": "help* and hulp",
            "19": "help and hulp* or hilp",
            "20": "help* or hulp or hilp or halp",
            "21": "(help or hulp*) and (hilp* or halp)",
            "22": "help* and (hilp* or halp*)",
            "23": "(help and (hilp* or halp)) or hulp*",
            "24": "not help* and halp",
            "25": "not (help* and helpe*)",
            "26": '"help* me please"',
            "27": '"help* me* please" or hulp*',
            "28": '"help me please*" or (hulp and halp)',
            "29": '"help me please" not (hulp and halp)',
            "30": '"help me please" hulp',
            "31": "help and hilp and not holp",
            "32": "help hilp not holp",
            "33": "help hilp and not holp",
            "34": "*lp and halp",
            "35": "*신은 and 어떠세요",
        }

        texts_matcheswith = {
            "halp thinks he needs help": [
                "25", "22", "20", "21", "11", "17", "16", "23", "34", "1",
                "0", "5", "7", "6", "9", "8",
            ],
            "he needs halp": ["24", "25", "20", "11", "10", "12", "34", "6"],
            "help": ["25", "20", "12", "17", "16", "1", "0", "5", "6"],
            "help hilp": [
                "25", "22", "20", "32", "21", "12", "17", "16", "19", "31",
                "23", "1", "0", "5", "4", "7", "6", "9", "8", "33",
            ],
            "help me please hulp": [
                "30", "25", "27", "20", "13", "12", "15", "14", "17", "16",
                "19", "18", "23", "29", "1", "0", "3", "2", "5", "4", "6", "9",
            ],
            "helper": ["20", "10", "12", "16"],
            "hulp hilp": [
                "25", "27", "20", "21", "10", "12", "14", "17", "19", "23",
                "1", "5", "4", "7", "6", "9",
            ],
            "nothing": ["25", "10", "12"],
            "안녕하세요, 당신은 어떠세요?": ["10", "12", "25", "35"],
        }
        # fmt: on

        all_ok = True
        for text, matches in texts_matcheswith.items():
            _matches = []
            for _id, expr in exprs.items():
                if self.match(text, expr):
                    _matches.append(_id)

            test_passed = sorted(matches) == sorted(_matches)
            if test_passed:
                print("Passed", repr(text))
            else:
                print("Failed", repr(text), "expected", matches, "matched", _matches)

            all_ok = all_ok and test_passed

        # Tests for non western characters, should fail with
        # pyparsing.exceptions.ParseException under the previous
        # configuration
        non_western_exprs = {
            "0": "*",
            "1": "ヿ",  # Edge character
            "2": "亀",  # Character in CJK block
            "3": "ヿ or 亀",
            "4": "ヿ and 亀",
            "5": "not ヿ"
        }

        non_western_texts_matcheswith = {
            "안녕하세요, 당신은 어떠세요?": ["0", "5"],
            "ヿ": ["0", "1", "3"],
            "亀": ["0", "2", "3", "5"],
            "亀 ヿ": ["0", "1", "2", "3", "4"],
        }

        for text, matches in non_western_texts_matcheswith.items():
            _matches = []
            for _id, expr in non_western_exprs.items():
                if self.match(text, expr):
                    _matches.append(_id)

            test_passed = sorted(matches) == sorted(_matches)
            if test_passed:
                print("Passed", repr(text))
            else:
                print("Failed", repr(text), "expected", matches, "matched", _matches)

            all_ok = all_ok and test_passed

        return all_ok


def main():
    if ParserTest().Test():
        print("All tests OK")
    else:
        print("One or more tests FAILED")
        raise Exception("One or more tests FAILED")


if __name__ == "__main__":
    main()
