# coding=utf-8
import imp
import sys

from modules.virtual_machine import VirtualMachine


def run_python_file(filename):
    """Run a python file as if it were the main program on the command line.
    `filename` is the path to the file to execute.
    """
    old_main_mod = sys.modules['__main__']
    main_mod = imp.new_module('__main__')  # Create a module to serve as __main__
    sys.modules['__main__'] = main_mod
    main_mod.__builtins__ = sys.modules['builtins']

    with open(filename, 'r') as f:
        source = f.read()

    if not source or source[-1] != '\n':
        source += '\n'  # `compile` needs the last line to be clean
    code = compile(source, filename, "exec")

    vm = VirtualMachine()
    vm.run_code(code, global_names=main_mod.__dict__)
