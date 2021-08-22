#!/usr/bin/env python3
# -*- coding: utf-8 -*-

def _private():
    from . import entry_point as _entry_point

    class _Result(object):
        entry_point = _entry_point

    return _Result


_private = _private()
try: _private.entry_point()
finally: del _private
