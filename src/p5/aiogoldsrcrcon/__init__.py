#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
asyncio rcon client for GoldSrc engine

There's 2 parts
1. python library (p5.aiogoldsrcrcon)
2. executable python script (p5-aiogoldsrcrcon[.exe]) with cli and interactive interface
"""

if "__main__" != __name__:
    def _private():
        from . _common import module_helpers as _module_helpers_module

        class _Result(object):
            module_getter = _module_helpers_module.lazy_attributes.make_getter(dictionary = {
                "entry_point": lambda module: getattr(module, "_entry_point").execute,
                "Connection": lambda module: module.connection.Class
            })

        return _Result

    _private = _private()
    def __getattr__(name: str): return _private.module_getter(name = name)

    __all__ = _private.module_getter.keys
    __date__ = None
    __author__ = None
    __version__ = None
    __credits__ = None
    _fields = tuple()
    __bases__ = tuple()
