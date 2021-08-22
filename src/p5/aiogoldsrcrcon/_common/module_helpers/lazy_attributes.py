#!/usr/bin/env python3
# -*- coding: utf-8 -*-

if "__main__" != __name__:
    def _private():
        def _make_base():
            import sys
            import typing
            import inspect

            from . import import_module as _import_module

            class _Types(object):
                Factory = typing.Callable
                ModuleName = str
                Dictionary = typing.Dict[typing.Union[str, type(None)], typing.Union[Factory, type(None)]]

            class _ValidateAndMake(object):
                @staticmethod
                def module_name(value: typing.Union[type(None), _Types.ModuleName], make_default: typing.Callable):
                    if value is None: return make_default()
                    assert(isinstance(value, _Types.ModuleName) and bool(value) and (not value.startswith(".")))
                    return value

                @classmethod
                def dictionary(cls, value: typing.Union[type(None), _Types.Dictionary], make_default: typing.Callable):
                    if value is None: return make_default()
                    _collector = {_key: cls.__factory(key = _key, value = _value) for _key, _value in dict(value).items()}
                    for _key, _value in make_default().items(): _collector.setdefault(_key, _value)
                    return _collector

                @staticmethod
                def __factory(key: typing.Union[str, type(None)], value: typing.Union[_Types.Factory, type(None)]):
                    if key is None:
                        if value is None: return None
                    else: assert(isinstance(key, str) and bool(key) and (1 == len(key.split("."))))
                    _parameters = inspect.signature(value).parameters
                    _parameters_count = len(_parameters)
                    if 1 > _parameters_count: return lambda module, name: value()
                    if 2 > _parameters_count:
                        _parameter = next(iter(_parameters.values()))
                        if _parameter.VAR_KEYWORD == _parameter.kind: return lambda module, name: value(module = module, name = name)
                        if _parameter.VAR_POSITIONAL == _parameter.kind: return lambda module, name: value(name)
                        _parameter = _parameter.name
                        if "name" == _parameter: return lambda module, name: value(name = name)
                        if "module" == _parameter: return lambda module, name: value(module = module)
                        return lambda module, name: value()
                    if 3 > _parameters_count: return lambda module, name: value(module = module, name = name)
                    raise ValueError("unsupported signature")

            class _Meta(type):
                dictionary: _Types.Dictionary = None
                module_name: _Types.ModuleName = None

                @property
                def get(cls): return cls.__getter

                def __init__(cls, *args, **kwargs):
                    super().__init__(*args, **kwargs)

                    import inspect

                    _module_name = _ValidateAndMake.module_name(value = cls.module_name, make_default = lambda: cls.__module__)
                    _module = sys.modules[_module_name]

                    def _make_default_dictionary():
                        # noinspection PyUnusedLocal
                        def _factory(module: type(_module), name: str):
                            # noinspection PyCallingNonCallable
                            return _import_module(name = "{}.{}".format(_module_name, name))
                        return {None: _factory}

                    _dictionary = _ValidateAndMake.dictionary(value = cls.dictionary, make_default = _make_default_dictionary)

                    try: _default_factory = _dictionary[None]
                    except KeyError: _default_factory = None

                    _recursion_protector = set()

                    def _getter(name: str):
                        assert(isinstance(name, str) and bool(name))
                        assert(1 == len(name.split(".")))
                        if name in _recursion_protector:
                            try: raise RuntimeError("recursion rejected")
                            finally: raise AttributeError(name)
                        _recursion_protector.add(name)
                        try:
                            _factory = _dictionary.get(name, _default_factory)
                            if _factory is None: raise AttributeError(name)
                            return _factory(module = _module, name = name)
                        finally: _recursion_protector.remove(name)

                    cls.__module = _module
                    cls.__getter = _getter

            # noinspection PyShadowingNames
            class _Result(metaclass = _Meta):
                Types = _Types

            return _Result

        _Base = _make_base()

        def _make_class(**kwargs):
            _valid_keys = {"dictionary", "module_name"}
            for _key in kwargs.keys():
                if not (_key in _valid_keys): raise ValueError("unknown argument: {}".format(_key))

            def _make_dictionary():
                try: return kwargs["dictionary"]
                except KeyError: pass
                return Base.dictionary

            def _make_module_name():
                try: return kwargs["module_name"]
                except KeyError: pass
                import inspect
                _frame = inspect.stack()[2]
                _module = inspect.getmodule(_frame[0])
                return _module.__name__

            # noinspection PyShadowingNames
            class _Result(Base):
                dictionary = _make_dictionary()
                module_name = _make_module_name()

            return _Result

        def _make_getter(**kwargs):
            if not ("module_name" in kwargs):
                import inspect
                _frame = inspect.stack()[2]
                _module = inspect.getmodule(_frame[0])
                kwargs["module_name"] = _module.__name__

            _class = _make_class(**kwargs)
            _class.get.keys = _class.dictionary.keys() if isinstance(_class.dictionary, dict) else tuple()
            return _class.get

        class _Result(object):
            Base = _Base
            make_class = _make_class
            make_getter = _make_getter

        return _Result

    _private = _private()
    Base = _private.Base
    make_class = _private.make_class
    make_getter = _private.make_getter
    del _private
