# coding=utf-8
import inspect
import types


def make_cell(value):
    """
        Create a real Python closure and grab a cell.
    """
    fn = (lambda x: lambda: x)(value)
    return fn.__closure__[0]


class Function(object):
    """
        Create a realistic function object, defining the things the interpreter expects.
        function—invoking the __call__ method—creates a new Frame object and starts running it
    """
    __slots__ = [
        'func_code',
        'func_name',
        'func_defaults',
        'func_globals',
        'func_locals',
        'func_dict',
        'func_closure',
        '__name__',
        '__dict__',
        '_vm',
        '_func',
    ]

    def __init__(self, name, code, globs, defaults, closure, vm):
        self._vm = vm
        self.func_code = code
        self.func_name = self.__name__ = name or code.co_name
        self.func_defaults = tuple(defaults)
        self.func_globals = globs
        self.func_locals = self._vm.frame.f_locals
        self.__dict__ = {}
        self.func_closure = closure
        self.__doc__ = code.co_consts[0] if code.co_consts else None

        # Sometimes, we need a real Python function.  This is for that.
        kw = {
            'argdefs': self.func_defaults,
        }
        if closure:
            kw['closure'] = tuple(make_cell(0) for _ in closure)
        self._func = types.FunctionType(code, globs, **kw)

    def __call__(self, *args, **kwargs):
        """
        when calling a new function, create and return a Frame object
        :param args:
        :param kwargs:
        """
        calling_arguments = inspect.getcallargs(self._func, *args, **kwargs)
        # Use callargs to provide a mapping of arguments: values to pass into the new frame.
        frame = self._vm.make_frame(
            self.func_code, calling_arguments, self.func_globals, {}
        )
        return self._vm.run_frame(frame)
