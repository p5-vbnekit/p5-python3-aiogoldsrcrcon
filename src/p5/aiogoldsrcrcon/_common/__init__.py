#!/usr/bin/env python3
# -*- coding: utf-8 -*-

if "__main__" != __name__:
    def _private():
        from . import module_helpers as _module_helpers_module

        class _Result(object):
            module_getter = _module_helpers_module.lazy_attributes.make_getter()

        return _Result

    _private = _private()
    def __getattr__(name: str): return _private.module_getter(name = name)
