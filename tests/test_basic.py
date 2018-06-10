# coding=utf-8
from unittest import TestCase

from click.testing import CliRunner

from chenab import cli


class TestSample(TestCase):
    """
        Sample Test
    """

    def __init__(self, methodName='runTest'):
        super(TestSample, self).__init__()
        self.runner = CliRunner()

    def runTest(self):
        result = self.runner.invoke(cli, ['tests/sample_python_codes/hello_world.py'])
        output_string = str(result.output.encode('ascii', 'ignore').decode("utf-8"))
        self.assertEqual(0, result.exit_code)
        self.assertEqual("Hello world!\n", output_string)
