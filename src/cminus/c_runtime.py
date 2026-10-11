"""Compatibility names for the canonical core runtime."""

from cminus.runtime import c_int_div as c_div, c_int_mod as c_mod, c_printf as printf

__all__ = ["c_div", "c_mod", "printf"]
