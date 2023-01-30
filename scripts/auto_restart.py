#!/usr/bin/env python
"""
Script to restart services automatically on python file changes.
"""
import shlex
import sys

from watchfiles import PythonFilter, run_process


def restart_message(*args, **kwargs):
    print("Files changed; restarting...")


if __name__ == "__main__":
    command = " ".join((shlex.quote(arg) for arg in sys.argv[1:]))
    run_process(".", target=command, step=500, callback=restart_message, watch_filter=PythonFilter())
