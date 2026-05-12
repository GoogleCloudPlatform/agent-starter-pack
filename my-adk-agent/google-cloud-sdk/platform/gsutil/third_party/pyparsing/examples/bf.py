# bf.py
#
# Brainf*ck interpreter demo
#
# BF instructions (symbols):
#   + - increment value at the current pointer
#   - - decrement value at the current pointer
#   > - increment pointer
#   < - decrement pointer
#   , - input new byte value, store at the current pointer
#   . - output the byte at the current pointer
#   [] - evaluate value at current pointer, if nonzero, execute all statements in []'s and repeat
#
import pyparsing as pp

# define the basic parser

# define Literals for each symbol in the BF langauge
PLUS, MINUS, GT, LT, INP, OUT, LBRACK, RBRACK = pp.Literal.using_each("+-<>,.[]")

# use a pyparsing Forward for the recursive definition of an instruction that can
# itself contain instructions
instruction_expr = pp.Forward().set_name("instruction")

# define a LOOP expression for the instructions enclosed in brackets; use a
# pyparsing Group to wrap the instructions in a sub-list
LOOP = pp.Group(LBRACK + instruction_expr[...] + RBRACK)

# use '<<=' operator to insert expression definition into existing Forward
instruction_expr <<= PLUS | MINUS | GT | LT | INP | OUT | LOOP

program_expr = instruction_expr[...].set_name("program")

# ignore everything that is not a BF symbol
ignore_chars = pp.Word(pp.printables, exclude_chars="+-<>,.[]")
program_expr.ignore(ignore_chars)


class BFEngine:
    """
    Brainf*ck execution environment, with a memory array and pointer.
    """
    def __init__(self, memory_size: int = 1024):
        self._ptr = 0
        self._memory_size = memory_size
        self._memory = [0] * self._memory_size

    @property
    def ptr(self):
        return self._ptr

    @ptr.setter
    def ptr(self, value):
        self._ptr = value % self._memory_size

    @property
    def at_ptr(self):
        return self._memory[self._ptr]

    @at_ptr.setter
    def at_ptr(self, value):
        self._memory[self._ptr] = value % 256

    def output_value_at_ptr(self):
        print(chr(self.at_ptr), end="")

    def input_value(self):
        input_char = input() or "\0"
        self.at_ptr = ord(input_char[0])

    def reset(self):
        self._ptr = 0
        self._memory[:] = [0] * self._memory_size

    def dump_state(self):
        for i in range(30):
            print(f"{self._memory[i]:3d} ", end="")
        print()

        if self.ptr < 30:
            print(f" {'    ' * self.ptr}^")


# define executable classes for each instruction

class Instruction:
    """Abstract class for all instruction classes to implement."""
    def __init__(self, tokens):
        self.tokens = tokens

    def execute(self, bf_engine: BFEngine):
        raise NotImplementedError()


class IncrPtr(Instruction):
    def execute(self, bf_engine: BFEngine):
        bf_engine.ptr += 1


class DecrPtr(Instruction):
    def execute(self, bf_engine: BFEngine):
        bf_engine.ptr -= 1


class IncrPtrValue(Instruction):
    def execute(self, bf_engine: BFEngine):
        bf_engine.at_ptr += 1


class DecrPtrValue(Instruction):
    def execute(self, bf_engine: BFEngine):
        bf_engine.at_ptr -= 1


class OutputPtrValue(Instruction):
    def execute(self, bf_engine: BFEngine):
        bf_engine.output_value_at_ptr()


class InputPtrValue(Instruction):
    def execute(self, bf_engine: BFEngine):
        bf_engine.input_value()


class RunInstructionLoop(Instruction):
    def __init__(self, tokens):
        super().__init__(tokens)
        self.instructions = self.tokens[0][1:-1]

    def execute(self, bf_engine: BFEngine):
        while bf_engine.at_ptr:
            for i in self.instructions:
                i.execute(bf_engine)


# add parse actions to all BF instruction expressions
PLUS.add_parse_action(IncrPtrValue)
MINUS.add_parse_action(DecrPtrValue)
GT.add_parse_action(IncrPtr)
LT.add_parse_action(DecrPtr)
OUT.add_parse_action(OutputPtrValue)
INP.add_parse_action(InputPtrValue)
LOOP.add_parse_action(RunInstructionLoop)


@program_expr.add_parse_action
def run_program(tokens):
    bf = BFEngine()
    for t in tokens:
        t.execute(bf)
    print()

if __name__ == '__main__':

    # generate railroad diagram
    import contextlib

    with contextlib.suppress(Exception):
        program_expr.create_diagram("bf_diagram.html")

    # execute an example BF program
    hw = "+[-->-[>>+>-----<<]<--<---]>-.>>>+.>>..+++[.>]<<<<.+++.------.<<-.>>>>+."
    program_expr.parse_string(hw)
