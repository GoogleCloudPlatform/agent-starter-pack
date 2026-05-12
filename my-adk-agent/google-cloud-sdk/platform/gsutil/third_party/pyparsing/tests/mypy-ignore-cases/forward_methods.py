import pyparsing as pp

# first, some basic validation: forward is a ParserElement, so is Literal
# MatchFirst([Forward(), Literal(...)]) should also be okay
e: pp.ParserElement = pp.Forward()
e = pp.Literal()
e = pp.MatchFirst([pp.Forward(), pp.Literal("hi there")])
# confirm that it isn't returning Any because it cannot be assigned to a str
x: str = pp.Forward() | pp.Literal("oops")  # type: ignore[assignment]

# confirm that `Forward.__or__` has the right behavior
e = pp.Forward() | pp.Literal("nice to meet you")
# and that it isn't returning Any because it cannot be assigned to an int
y: int = pp.Forward() | pp.Literal("oops")  # type: ignore[assignment]
