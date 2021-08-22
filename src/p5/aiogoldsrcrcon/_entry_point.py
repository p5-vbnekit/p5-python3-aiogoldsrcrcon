#!/usr/bin/env python3
# -*- coding: utf-8 -*-

if "__main__" != __name__:
    def _private():
        import io
        import os
        import sys
        import typing
        import atexit
        import asyncio
        import argparse

        from . import connection as _connection_module

        _interactive_capability = sys.stdin.isatty() and sys.stderr.isatty()

        async def _coroutine(address: str, password: str, verbose: bool, transaction_timeout: typing.Optional[float], response_sink: typing.Callable):
            async with _connection_module.make(address = address, password = password) as _connection:
                await _connection.open()

                if transaction_timeout is None:
                    def _execute_command(command: str): return _connection(command = command)
                else:
                    assert isinstance(transaction_timeout, float) and (0 < transaction_timeout)
                    def _execute_command(command: str): return asyncio.wait_for(_connection(command = command), timeout = transaction_timeout)

                _response = await _execute_command(command = "wait")
                try: assert _response is None
                except AssertionError:
                    _response = tuple([_response for _response in [_response.strip() for _response in _response.splitlines()] if _response])
                    if 1 == len(_response): _response = f"unexpected server response: {_response[0]}"
                    else:
                        with io.StringIO() as _stream:
                            print(f"unexpected server response:", file = _stream)
                            for _response in _response: print(f"> {_response}", file = _stream)
                            _response = _stream.getvalue()
                    raise ConnectionError(_response)

                if verbose:
                    print("udp client initialized for \"{}:{}\"".format(*address), flush = True, file = sys.stderr)
                    if _interactive_capability: print("type your commands here, or press Ctrl+C for exit", flush = True, file = sys.stderr)

                while True:
                    try: _command = input()
                    except EOFError: break
                    _command = _command.strip()
                    if not _command: continue
                    if verbose: print(f"sending request, command: {_command}", flush = True, file = sys.stderr)
                    _response = await _execute_command(command = _command)
                    response_sink(response = ("" if _response is None else _response))
                    if verbose: print("request/response transaction finished", flush = True, file = sys.stderr)

        def _parse_address(source: str):
            assert isinstance(source, str) and bool(source)
            assert source == source.strip()
            source = source.split(":")
            if 1 == len(source): _host, _port = source[0], 27015
            else:
                _host, _port = ":".join(source[:-1]), int(source[-1])
                assert (0 <= _port) and (65536 > _port)
            assert _host == _host.strip()
            assert bool(_host)
            return _host, _port

        def _make_response_sink(verbose: bool, original_stdout: bool):
            assert isinstance(verbose, bool)
            assert isinstance(original_stdout, bool)

            _actions = []

            def _decorator(delegate: typing.Callable): _actions.append(delegate)

            if verbose:
                @_decorator
                def _action(response: str):
                    response = tuple([response.strip() for response in response.strip().splitlines()])
                    if 1 == len(response): print(f"server response: {response[0]}", flush = True, file = sys.stderr)
                    elif response:
                        print(f"server response:", flush = True, file = sys.stderr)
                        for response in response: print(f"> {response}", flush = True, file = sys.stderr)

            if not (verbose and sys.stdout.isatty()):
                if original_stdout:
                    @_decorator
                    def _action(response: str):
                        if (response): print(response, end = "", flush = True, file = sys.stdout)

                else:
                    @_decorator
                    def _action(response: str):
                        for response in [response.strip() for response in response.strip().splitlines()]: print(response, flush = True, file = sys.stdout)

            del _decorator

            def _result(response: str):
                assert isinstance(response, str)
                for _action in _actions: _action(response = response)

            return _result

        def _make_arguments_parser():
            _result = argparse.ArgumentParser(
                prog = f"{sys.executable} -m {__package__}" if "__main__.py" == os.path.basename(sys.argv[0]) else None,
                description = "python3 asyncio rcon client for GoldSrc engine"
            )
            _result.add_argument("-a", "--address", type = str, help = "server address (aka rcon_address): host[:port]")
            _result.add_argument("-p", "--password", type = str, help = "server password (aka rcon_password)")
            _result.add_argument("-t", "--transaction-timeout", type = float, default = +0.0e+0, help = "transaction timeout in seconds, 0 for infinite")
            _result.add_argument("-o", "--original-stdout", action = "store_true", help = "don't stip server responses for stdout")
            _result.add_argument("-q", "--quiet", action = "store_true", help = "brief output, less interactivity and verbosity - suitable for automation")
            return _result

        def _execute():
            _arguments_parser = _make_arguments_parser()
            _help_message = _arguments_parser.format_help()

            def _parse_arguments():
                _arguments, _argv = _arguments_parser.parse_known_args()
                if _argv: raise ValueError("unrecognized arguments: %s" % " ".join(_argv))
                return _arguments

            try:
                _parsed_arguments = _parse_arguments()
                _address = _parse_address(source = _parsed_arguments.address) if _parsed_arguments.address else None
                _password = _parsed_arguments.password
                _quiet = _parsed_arguments.quiet
                _original_stdout = _parsed_arguments.original_stdout
                _transaction_timeout = _parsed_arguments.transaction_timeout
                assert isinstance(_transaction_timeout, float)
                if 0 == _transaction_timeout: _transaction_timeout = None
                else: assert 0 < _transaction_timeout

            except BaseException as _exception:
                if not (isinstance(_exception, SystemExit) and (0 == _exception.code)):
                    def _at_exit_handler(): print(_help_message, flush = True, file = sys.stderr)
                    atexit.register(_at_exit_handler)
                    del _at_exit_handler
                raise

            del _arguments_parser, _parsed_arguments

            _verbose = not _quiet

            if _verbose and _interactive_capability:
                if not (1 < len(sys.argv)): print(_help_message, flush = True, file = sys.stderr)

                _exit_without_waiting = False

                def _at_exit_handler():
                    if _exit_without_waiting: return
                    _prompt_state = False

                    try:
                        if "nt" == os.name:
                            import msvcrt
                            _prompt_state = True
                            print("press any key for exit", end = "", flush = True, file = sys.stderr)
                            msvcrt.getch()
                            return

                        import termios
                        _descriptor = sys.stdin.fileno()

                        try:
                            _old_tty_attributes = termios.tcgetattr(_descriptor)
                            _new_tty_attributes = termios.tcgetattr(_descriptor)
                            _new_tty_attributes[3] = _new_tty_attributes[3] & ~termios.ICANON & ~termios.ECHO
                            termios.tcsetattr(_descriptor, termios.TCSANOW, _new_tty_attributes)
                        except termios.error: return

                        _prompt_state = True
                        print("press any key for exit", end = "", flush = True, file = sys.stderr)

                        try: sys.stdin.read(1)
                        except IOError: pass
                        finally: termios.tcsetattr(_descriptor, termios.TCSAFLUSH, _old_tty_attributes)
                    finally:
                        if _prompt_state: print("", flush = True, file = sys.stderr)

                atexit.register(_at_exit_handler)
                del _at_exit_handler

            try:
                if _address is None:
                    if _interactive_capability: print("server address is not specified with cli interface (--address), enter it: ", end = "", flush = True, file = sys.stderr)
                    else: print("server address is not specified with cli interface (--address) and will be obtained from pipe stdin", flush = True, file = sys.stderr)
                    try: _address = input()
                    except BaseException:
                        if _interactive_capability: print("", flush = True, file = sys.stderr)
                        raise
                    if _address: _address = _address.strip()
                    else:
                        _address = "localhost:27015"
                        print(f"using default server address: {_address}", flush = True, file = sys.stderr)
                    _address = _parse_address(source = _address)

                if _password is None:
                    if _interactive_capability:
                        import getpass
                        print("server password is not specified with cli interface (--password), enter it: ", end = "", flush = True, file = sys.stderr)
                        try: _password = getpass.getpass(prompt = "")
                        except BaseException:
                            print("", flush = True, file = sys.stderr)
                            raise
                    else:
                        print("server password is not specified with cli interface (--password) and will be obtained from pipe stdin", flush = True, file = sys.stderr)
                        _password = input()

                asyncio.get_event_loop().run_until_complete(_coroutine(
                    address = _address, password = _password, verbose = _verbose, transaction_timeout = _transaction_timeout,
                    response_sink = _make_response_sink(verbose = _verbose, original_stdout = _original_stdout)
                ))

            except KeyboardInterrupt: _exit_without_waiting = True

        class _Result(object):
            execute = _execute

        return _Result

    _private = _private()
    try: execute = _private.execute
    finally: del _private
