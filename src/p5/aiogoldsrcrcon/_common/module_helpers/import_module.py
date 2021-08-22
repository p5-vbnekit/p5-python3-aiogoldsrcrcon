#!/usr/bin/env python3
# -*- coding: utf-8 -*-

if "__main__" != __name__:
    def _private():
        import sys
        import importlib

        _this_module = sys.modules[__name__]
        def _execute(*args, **kwargs): return importlib.import_module(*args, **kwargs)

        class _Callable(_this_module.__class__):
            def __call__(self, *args, **kwargs): return _execute(*args, **kwargs)

        _this_module.__class__ = _Callable

        class _Result(object):
            execute = _execute

        return _Result

    _private = _private()
    execute = _private.execute
    del _private
