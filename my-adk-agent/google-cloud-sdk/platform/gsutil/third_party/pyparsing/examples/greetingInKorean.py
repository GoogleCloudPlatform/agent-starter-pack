#
# greetingInKorean.py
#
# Demonstration of the parsing module, on the prototypical "Hello, World!" example
#
# Copyright 2004-2016, by Paul McGuire
#
from pyparsing import Word, pyparsing_unicode as ppu

korean_chars = ppu.한국어.alphas
korean_word = Word(korean_chars, min=2)

# define grammar
greet = korean_word + "," + korean_word + "!"

# input string
hello = "안녕, 여러분!"  # "Hello, World!" in Korean

# parse input string
print(greet.parse_string(hello))
