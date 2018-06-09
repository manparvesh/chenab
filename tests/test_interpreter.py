import unittest

from src.interpreter import Interpreter


class MyTestCase(unittest.TestCase):
    def test_interpreter(self):
        import sys
        from io import StringIO

        saved_stdout = sys.stdout
        try:
            out = StringIO()
            sys.stdout = out

            what_to_execute = {
                "instructions": [("LOAD_VALUE", 0),  # the first number
                                 ("LOAD_VALUE", 1),  # the second number
                                 ("ADD_TWO_VALUES", None),
                                 ("PRINT_ANSWER", None)],
                "numbers": [7, 5]}

            interpreter = Interpreter()
            interpreter.run_code(what_to_execute)

            output = out.getvalue().strip()
            self.assertEqual('12', output)

            out = StringIO()
            sys.stdout = out
            what_to_execute = {
                "instructions": [("LOAD_VALUE", 0),
                                 ("LOAD_VALUE", 1),
                                 ("ADD_TWO_VALUES", None),
                                 ("LOAD_VALUE", 2),
                                 ("ADD_TWO_VALUES", None),
                                 ("PRINT_ANSWER", None)],
                "numbers": [7, 5, 8]}

            interpreter.run_code(what_to_execute)

            output = out.getvalue().strip()
            self.assertEqual('20', output)
        finally:
            sys.stdout = saved_stdout


if __name__ == '__main__':
    unittest.main()
