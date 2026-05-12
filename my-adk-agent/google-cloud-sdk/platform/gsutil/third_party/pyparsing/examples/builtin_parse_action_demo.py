#
#  builtin_parse_action_demo.py
#  Copyright, 2012 - Paul McGuire
#
#  Simple example of using builtin functions as parse actions.
#

import pyparsing as pp
ppc = pp.common

# make an expression that will match a list of ints (which
# will be converted to actual ints by the parse action attached
# to integer)
nums = ppc.integer[...]


test = "2 54 34 2 211 66 43 2 0"
print(test)

# try each of these builtins as parse actions
for fn in (sum, max, min, len, sorted, reversed, list, tuple, set, any, all):
    if fn is reversed:
        # reversed returns an iterator, we really want to show the list of items
        fn = lambda x: list(reversed(x))

    # show how each builtin works as a free-standing parse action
    print(fn.__name__, nums.set_parse_action(fn).parse_string(test))
