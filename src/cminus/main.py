"""Module 6 - CLI / menu / pipeline driver.  Owner: unassigned."""
import argparse

from cminus import __version__


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="cminus", description="C-Minus: C subset to Python compiler")
    ap.add_argument("--version", action="version", version=f"cminus {__version__}")
    ap.parse_args(argv)
    print("C-Minus: pipeline not wired up yet.")
    return 0
