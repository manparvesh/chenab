# coding=utf-8
import collections
import dis
import operator
import sys

from modules.frame import Frame
from modules.function import Function
from modules.virtual_machine_error import VirtualMachineError

Block = collections.namedtuple("Block", "type, handler, stack_height")


class VirtualMachine(object):
    def __init__(self):
        self.frames = []  # The call stack of frames.
        self.current_frame = None  # The current frame.
        self.return_value = None
        self.last_exception = None

    # Frame manipulation
    def make_frame(self, code, callargs={}, global_names=None, local_names=None):
        """
        make frame
        :rtype: object
        """
        if global_names is not None and local_names is not None:
            local_names = global_names
        elif self.frames:
            global_names = self.current_frame.global_names
            local_names = {}
        else:
            global_names = local_names = {
                '__builtins__': __builtins__,
                '__name__': '__main__',
                '__doc__': None,
                '__package__': None,
            }
        local_names.update(callargs)
        frame = Frame(code, global_names, local_names, self.current_frame)
        return frame

    def push_frame(self, frame):
        """
        push frame to frame stack
        :param frame:
        """
        self.frames.append(frame)
        self.current_frame = frame

    def pop_frame(self):
        """
        pop frame from stack
        """
        self.frames.pop()
        if self.frames:
            self.current_frame = self.frames[-1]
        else:
            self.current_frame = None

    # Jumping through bytecode
    def jump(self, jump):
        """
        Move the bytecode pointer to `jump`, so it will execute next.
        """
        self.current_frame.last_instruction = jump

    def run_code(self, code, global_names=None, local_names=None):
        """
        An entry point to execute code using the virtual machine.
        """
        frame = self.make_frame(code, global_names=global_names, local_names=local_names)

        self.run_frame(frame)

    def parse_byte_and_args(self):
        """
        parses arguments and groups them
        :return:
        """
        frame = self.current_frame
        opoffset = frame.last_instruction
        byteCode = frame.code_obj.co_code[opoffset]
        frame.last_instruction += 1
        byte_name = dis.opname[byteCode]
        if byteCode >= dis.HAVE_ARGUMENT:
            argument = frame.code_obj.co_code[
                       frame.last_instruction:frame.last_instruction + 2]  # index into the bytecode
            frame.last_instruction += 2  # advance the instruction pointer
            arg_val = argument[0] + (argument[1] << 8)
            if byteCode in dis.hasconst:  # Look up a constant
                argument = frame.code_obj.co_consts[arg_val]
            elif byteCode in dis.hasname:  # Look up a name
                argument = frame.code_obj.co_names[arg_val]
            elif byteCode in dis.haslocal:  # Look up a local name
                argument = frame.code_obj.co_varnames[arg_val]
            elif byteCode in dis.hasjrel:  # Calculate a relative jump
                argument = frame.last_instruction + arg_val
            else:
                argument = arg_val
            argument = [argument]
        else:
            argument = []

        return byte_name, argument

    def dispatch(self, byte_name, argument):
        """
        Dispatch by bytename to the corresponding methods.
        Exceptions are caught and set on the virtual machine.
        """

        # When later unwinding the block stack,
        # we need to keep track of why we are doing it.
        why = None
        try:
            bytecode_fn = getattr(self, 'byte_%s' % byte_name, None)
            if bytecode_fn is None:
                if byte_name.startswith('UNARY_'):
                    self.unaryOperator(byte_name[6:])
                elif byte_name.startswith('BINARY_'):
                    self.binaryOperator(byte_name[7:])
                else:
                    raise VirtualMachineError(
                        "unsupported bytecode type: %s" % byte_name
                    )
            else:
                why = bytecode_fn(*argument)
        except:
            # deal with exceptions encountered while executing the op.
            self.last_exception = sys.exc_info()[:2] + (None,)
            why = 'exception'

        return why

    def manage_block_stack(self, why):
        """
        manage block stack and send to appropriate jump calls
        depending on the type of code block we're processing
        :param why:
        :return:
        """
        block = self.current_frame.block_stack[-1]

        if block.type == 'loop' and why == 'continue':
            self.jump(self.return_value)
            why = None
            return why

        self.current_frame.pop_block()
        current_exc = self.current_frame.unwind_block(block)
        if current_exc is not None:
            self.last_exception = current_exc

        if block.type == 'loop' and why == 'break':
            self.jump(block.handler)
            why = None

        elif block.type in ['setup-except', 'finally'] and why == 'exception':
            self.current_frame.push_block('except-handler')
            exctype, value, tb = self.last_exception
            self.current_frame.push(tb, value, exctype)
            self.current_frame.push(tb, value, exctype)  # yes, twice
            self.jump(block.handler)
            why = None

        elif block.type == 'finally':
            if why in ('return', 'continue'):
                self.current_frame.push(self.return_value)
            self.current_frame.push(why)
            self.jump(block.handler)
            why = None

        return why

    def run_frame(self, frame):
        """
        Run a frame until it returns (somehow).
        Exceptions are raised, the return value is returned.
        """
        self.push_frame(frame)
        while True:
            byte_name, argument = self.parse_byte_and_args()

            why = self.dispatch(byte_name, argument)

            # Deal with any block management we need to do
            while why and frame.block_stack:
                why = self.manage_block_stack(why)

            if why:
                break

        self.pop_frame()

        if why == 'exception':
            exc, val, tb = self.last_exception
            e = exc(val)
            e.__traceback__ = tb
            raise e

        return self.return_value

    ## Stack manipulation

    def byte_LOAD_CONST(self, const):
        """
        load constant into current frame
        :param const:
        """
        self.current_frame.push(const)

    def byte_POP_TOP(self):
        """
        pop top from frame
        """
        self.current_frame.pop()

    def byte_DUP_TOP(self):
        """
        add duplicate value of top value into the current frame
        """
        self.current_frame.push(self.current_frame.top())

    ## Names
    def byte_LOAD_NAME(self, name):
        """
        load a name into local_names of current frame
        :param name:
        """
        frame = self.current_frame
        if name in frame.local_names:
            val = frame.local_names[name]
        elif name in frame.global_names:
            val = frame.global_names[name]
        elif name in frame.builtin_names:
            val = frame.builtin_names[name]
        else:
            raise NameError("name '%s' is not defined" % name)
        self.current_frame.push(val)

    def byte_STORE_NAME(self, name):
        """
        store value of a local variable from current frame
        :param name:
        """
        self.current_frame.local_names[name] = self.current_frame.pop()

    def byte_DELETE_NAME(self, name):
        """
        delete name from current frame
        :param name:
        """
        del self.current_frame.local_names[name]

    def byte_LOAD_FAST(self, name):
        """
        load variable value from current frame
        :param name:
        """
        if name in self.current_frame.local_names:
            val = self.current_frame.local_names[name]
        else:
            raise UnboundLocalError(
                "local variable '%s' referenced before assignment" % name
            )
        self.current_frame.push(val)

    def byte_STORE_FAST(self, name):
        """
        store value of local variable in current frame
        :param name:
        """
        self.current_frame.local_names[name] = self.current_frame.pop()

    def byte_LOAD_GLOBAL(self, name):
        """
        load global variable value from global names list or builtins
        :param name:
        """
        f = self.current_frame
        if name in f.global_names:
            val = f.global_names[name]
        elif name in f.builtin_names:
            val = f.builtin_names[name]
        else:
            raise NameError("global name '%s' is not defined" % name)
        f.push(val)

    ## Operators

    UNARY_OPERATORS = {
        'POSITIVE': operator.pos,
        'NEGATIVE': operator.neg,
        'NOT': operator.not_,
        'INVERT': operator.invert,
    }

    def unaryOperator(self, op):
        """
        apply unary operator to value from top of stack and push back
        :param op:
        """
        x = self.current_frame.pop()
        self.current_frame.push(self.UNARY_OPERATORS[op](x))

    BINARY_OPERATORS = {
        'POWER': pow,
        'MULTIPLY': operator.mul,
        'FLOOR_DIVIDE': operator.floordiv,
        'TRUE_DIVIDE': operator.truediv,
        'MODULO': operator.mod,
        'ADD': operator.add,
        'SUBTRACT': operator.sub,
        'SUBSCR': operator.getitem,
        'LSHIFT': operator.lshift,
        'RSHIFT': operator.rshift,
        'AND': operator.and_,
        'XOR': operator.xor,
        'OR': operator.or_,
    }

    def binaryOperator(self, op):
        """
        apply binary operator to value from top of stack and push back
        :param op:
        """
        x, y = self.current_frame.pop_n(2)
        self.current_frame.push(self.BINARY_OPERATORS[op](x, y))

    COMPARE_OPERATORS = [
        operator.lt,
        operator.le,
        operator.eq,
        operator.ne,
        operator.gt,
        operator.ge,
        lambda x, y: x in y,
        lambda x, y: x not in y,
        lambda x, y: x is y,
        lambda x, y: x is not y,
        lambda x, y: issubclass(x, Exception) and issubclass(x, y),
    ]

    def byte_COMPARE_OP(self, opnum):
        """
        apply comparison operator to value from top of stack and push back
        :param opnum:
        """
        x, y = self.current_frame.pop_n(2)
        self.current_frame.push(self.COMPARE_OPERATORS[opnum](x, y))

    ## Attributes and indexing

    def byte_LOAD_ATTR(self, attr):
        """
        load attribute
        :param attr:
        """
        obj = self.current_frame.pop()
        val = getattr(obj, attr)
        self.current_frame.push(val)

    def byte_STORE_ATTR(self, name):
        """
        store an attributes
        :param name:
        """
        val, obj = self.current_frame.pop_n(2)
        setattr(obj, name, val)

    def byte_STORE_SUBSCR(self):
        """
        store subscr
        """
        val, obj, subscr = self.current_frame.pop_n(3)
        obj[subscr] = val

    ## Building

    def byte_BUILD_TUPLE(self, count):
        """
        build tuple
        :param count:
        """
        elts = self.current_frame.pop_n(count)
        self.current_frame.push(tuple(elts))

    def byte_BUILD_LIST(self, count):
        """
        build list from `count` values in stack
        :param count:
        """
        elts = self.current_frame.pop_n(count)
        self.current_frame.push(elts)

    def byte_BUILD_MAP(self, size):
        """
        build a map. size is not needed here
        :param size:
        """
        self.current_frame.push({})

    def byte_STORE_MAP(self):
        """
        store map into current frame
        """
        the_map, val, key = self.current_frame.pop_n(3)
        the_map[key] = val
        self.current_frame.push(the_map)

    def byte_UNPACK_SEQUENCE(self, count):
        """
        unpack a sequence from the stack
        :param count:
        """
        seq = self.current_frame.pop()
        for x in reversed(seq):
            self.current_frame.push(x)

    def byte_BUILD_SLICE(self, count):
        """
        build a slice of a string
        :param count:
        """
        if count == 2:
            x, y = self.current_frame.pop_n(2)
            self.current_frame.push(slice(x, y))
        elif count == 3:
            x, y, z = self.current_frame.pop_n(3)
            self.current_frame.push(slice(x, y, z))
        else:  # pragma: no cover
            raise VirtualMachineError("Strange BUILD_SLICE count: %r" % count)

    def byte_LIST_APPEND(self, count):
        """
        append to list
        :param count:
        """
        val = self.current_frame.pop()
        the_list = self.current_frame.stack[-count]  # peek
        the_list.append(val)

    ## Jumps

    def byte_JUMP_FORWARD(self, jump):
        """
        jump forward
        :param jump:
        """
        self.jump(jump)

    def byte_JUMP_ABSOLUTE(self, jump):
        """
        jump absolute
        :param jump:
        """
        self.jump(jump)

    def byte_POP_JUMP_IF_TRUE(self, jump):
        """
        jump if popped value is true
        :param jump:
        """
        val = self.current_frame.pop()
        if val:
            self.jump(jump)

    def byte_POP_JUMP_IF_FALSE(self, jump):
        """
        jump if popped value is false
        :param jump:
        """
        val = self.current_frame.pop()
        if not val:
            self.jump(jump)

    def byte_JUMP_IF_TRUE_OR_POP(self, jump):
        """
        jump if true, else pop
        :param jump:
        """
        val = self.current_frame.top()
        if val:
            self.jump(jump)
        else:
            self.current_frame.pop()

    def byte_JUMP_IF_FALSE_OR_POP(self, jump):
        """
        jump if false, else pop
        :param jump:
        """
        val = self.current_frame.top()
        if not val:
            self.jump(jump)
        else:
            self.current_frame.pop()

    ## Blocks

    def byte_SETUP_LOOP(self, dest):
        """
        setup a loop
        :param dest:
        """
        self.current_frame.push_block('loop', dest)

    def byte_GET_ITER(self):
        """
        get iterator
        """
        self.current_frame.push(iter(self.current_frame.pop()))

    def byte_FOR_ITER(self, jump):
        """
        byte for iterator
        :param jump:
        """
        iterobj = self.current_frame.top()
        try:
            v = next(iterobj)
            self.current_frame.push(v)
        except StopIteration:
            self.current_frame.pop()
            self.jump(jump)

    def byte_BREAK_LOOP(self):
        """
        break a loop
        :return:
        """
        return 'break'

    def byte_CONTINUE_LOOP(self, destination):
        """
        continue a loop
        :param destination:
        :return: 
        """
        # This is a trick with the return value.
        # While unrolling blocks, continue and return both have to preserve
        # state as the finally blocks are executed.  For continue, it's
        # where to jump to, for return, it's the value to return.  It gets
        # pushed on the stack for both, so continue puts the jump destination
        # into return_value.
        self.return_value = destination
        return 'continue'

    def byte_SETUP_EXCEPT(self, dest):
        """
        `except` setup
        :param dest:
        """
        self.current_frame.push_block('setup-except', dest)

    def byte_SETUP_FINALLY(self, dest):
        """
        `finally` setup
        :param dest:
        """
        self.current_frame.push_block('finally', dest)

    def byte_POP_BLOCK(self):
        """
        pop a block
        """
        self.current_frame.pop_block()

    def byte_RAISE_VARARGS(self, argc):
        """
        raise variable arguments
        :param argc:
        :return:
        """
        cause = exc = None
        if argc == 2:
            cause = self.current_frame.pop()
            exc = self.current_frame.pop()
        elif argc == 1:
            exc = self.current_frame.pop()
        return self.do_raise(exc, cause)

    def do_raise(self, exc, cause):
        """
        raise helper method
        :param exc:
        :param cause:
        :return:
        """
        if exc is None:  # reraise
            exc_type, val, tb = self.last_exception

        elif type(exc) == type:  # As in `raise ValueError`
            exc_type = exc
            val = exc()  # Make an instance.
        elif isinstance(exc, BaseException):
            # As in `raise ValueError('foo')`
            exc_type = type(exc)
            val = exc
        else:
            return 'exception'  # failure

        self.last_exception = exc_type, val, val.__traceback__
        return 'exception'

    def byte_POP_EXCEPT(self):
        """
        pop except
        """
        block = self.current_frame.pop_block()
        if block.type != 'except-handler':
            raise Exception("popped block is not an except handler")
        current_exc = self.current_frame.unwind_block(block)
        if current_exc is not None:
            self.last_exception = current_exc

    ## Functions

    def byte_MAKE_FUNCTION(self, argc):
        """
        make a function
        :param argc:
        """
        name = self.current_frame.pop()
        code = self.current_frame.pop()
        defaults = self.current_frame.pop_n(argc)
        globs = self.current_frame.global_names
        fn = Function(name, code, globs, defaults, None, self)
        self.current_frame.push(fn)

    def byte_CALL_FUNCTION(self, arg):
        """
        call a function
        :param arg:
        """
        lenKw, lenPos = divmod(arg, 256)  # KWargs not supported in byterun
        posargs = self.current_frame.pop_n(lenPos)

        func = self.current_frame.pop()
        return_value = func(*posargs)
        self.current_frame.push(return_value)

    def byte_RETURN_VALUE(self):
        """
        return value
        :return:
        """
        self.return_value = self.current_frame.pop()
        return "return"

    ## Importing

    def byte_IMPORT_NAME(self, name):
        """
        import name
        :param name:
        """
        level, fromlist = self.current_frame.pop_n(2)
        frame = self.current_frame
        self.current_frame.push(__import__(name, frame.global_names, frame.local_names, fromlist, level))

    def byte_IMPORT_FROM(self, name):
        """
        import from
        :param name:
        """
        mod = self.current_frame.top()
        self.current_frame.push(getattr(mod, name))

    ## And the rest...
    def byte_LOAD_BUILD_CLASS(self):
        """
        build a class
        """
        self.current_frame.push(__build_class__)

    def byte_STORE_LOCALS(self):
        """
        store locals
        """
        self.current_frame.local_names = self.current_frame.pop()
