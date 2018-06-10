import click

from modules import __main__


@click.group(invoke_without_command=True)
@click.argument('file_name', nargs=1)
def cli(file_name):
    """
    Simple Python interpreter written in Python 3.5

    Implementation based on content from the book "500 lines or less"
    """
    __main__.run_python_file(file_name)
