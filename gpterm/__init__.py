"""Interact with LLMs, and use them in the terminal."""

__version__ = "0.0.2"

import click

from gpterm import chat


@click.command()
@click.option("--model", default="gpt-3.5-turbo", help="The model to use.")
@click.argument("args", nargs=-1)
def main(model, args):
    initial_message = " ".join(args)
    chat.chat(model=model, initial_message=initial_message or None)
