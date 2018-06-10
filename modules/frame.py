import collections

Block = collections.namedtuple("Block", "type, handler, stack_height")


class Frame(object):
    """
    collection of attributes with no methods
    the attributes include the code object created by the compiler;
    the local, global, and builtin namespaces; a reference to the previous frame;
    a data stack; a block stack; and the last instruction executed
    """

    def __init__(self, code_object, global_names, local_names, previous_frame):
        self.code_obj = code_object
        self.global_names = global_names
        self.local_names = local_names
        self.prev_frame = previous_frame
        self.stack = []

        if previous_frame:
            self.builtin_names = previous_frame.builtin_names
        else:
            self.builtin_names = local_names['__builtins__']
            if hasattr(self.builtin_names, '__dict__'):
                self.builtin_names = self.builtin_names.__dict__

        self.last_instruction = 0
        self.block_stack = []

    """
    Data stack manipulation
    """

    def top(self):
        """
        top
        :return:
        """
        return self.stack[-1]

    def pop(self):
        """
        pop
        :return:
        """
        return self.stack.pop()

    def push(self, *values):
        """
        push
        :param values:
        """
        self.stack.extend(values)

    def pop_n(self, n):
        """Pop a number of values from the value stack.
        A list of `n` values is returned, the deepest value first.
        """
        if n:
            ret = self.stack[-n:]
            self.stack[-n:] = []
            return ret
        else:
            return []

    # Block stack manipulation
    def push_block(self, b_type, handler=None):
        """
        push block
        :param b_type:
        :param handler:
        """
        stack_height = len(self.stack)
        self.block_stack.append(Block(b_type, handler, stack_height))

    def pop_block(self):
        """
        pop block
        :return:
        """
        return self.block_stack.pop()

    def unwind_block(self, block):
        """Unwind the values on the data stack when a given block is finished."""
        if block.type == 'except-handler':
            offset = 3
        else:
            offset = 0

        while len(self.stack) > block.stack_height + offset:
            self.pop()

        if block.type == 'except-handler':
            traceback, value, exctype = self.pop_n(3)
            return exctype, value, traceback
