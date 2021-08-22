#!/usr/bin/env python3
# -*- coding: utf-8 -*-

if "__main__" != __name__:
    def _private():
        import re
        import typing
        import asyncio

        class _Stream(object):
            async def write(self, data: bytes): raise NotImplementedError()
            async def read(self, size: int): raise NotImplementedError()
            async def close(self): raise NotImplementedError()

        class _Buffer(object):
            state = property(lambda self: self.__state)
            exception = property(lambda self: self.__exception)

            def open(self):
                assert self.__state is None
                self.__state = True
                if self.__event is not None: self.__event.set()

            def close(self):
                self.__state = False
                if self.__event is not None: self.__event.set()

            def put_data(self, data: bytes):
                assert isinstance(data, bytes) and bool(data)
                if not self.__state:
                    assert self.__state is False
                    return
                self.__data.append(data)
                if self.__event is not None: self.__event.set()

            def put_exception(self, exception: BaseException):
                assert isinstance(exception, BaseException)
                if self.__exception is not None: return
                self.__state = False
                self.__exception = exception
                if self.__event is not None: self.__event.set()

            async def get_data(self, size: int = None):
                if size is None:
                    async with self.__lock:
                        if not await self.__wait_data():
                            if self.__exception: raise self.__exception
                            return None
                        _data = bytes().join(self.__data)
                        self.__data.clear()
                        return _data
                assert isinstance(size, int) and (0 < size)
                _data = []
                async with self.__lock:
                    while 0 < size:
                        if not await self.__wait_data(): break
                        _size = len(self.__data[0])
                        if _size <= size:
                            _data.append(self.__data.pop(0))
                            if not await self.__wait(): return None
                            size -= _size
                        else:
                            _data.append(self.__data[0][:size])
                            self.__data[0] = self.__data[0][size:]
                            size = 0
                if _data: return bytes().join(_data)
                if self.__exception: raise self.__exception
                return None

            async def wait_connection(self):
                async with self.__lock:
                    assert not self.__data
                    if self.__state: return
                    if self.__event is None: self.__event = asyncio.Event()
                    await self.__event.wait()
                    self.__event = None
                    if self.__state: return
                    assert self.__state is False
                    if self.__exception: raise self.__exception
                    raise EOFError()

            def __init__(self):
                super().__init__()
                self.__data = []
                self.__lock = asyncio.Lock()
                self.__event = None
                self.__state = None
                self.__exception = None

            async def __wait_data(self):
                if self.__data: return True
                if self.__state is False: return False
                if self.__event is None: self.__event = asyncio.Event()
                await self.__event.wait()
                self.__event = None
                if self.__data: return True
                assert self.__state is False
                return False

        async def _make_stream(host: str, port: int, password: str, loop: asyncio.BaseEventLoop):
            _buffer = _Buffer()

            class _Protocol(asyncio.DatagramProtocol):
                def connection_made(self, transport):
                    super().connection_made(transport)
                    _buffer.open()

                def datagram_received(self, data, address):
                    super().datagram_received(data, address)
                    _buffer.put_data(data = data)

                def error_received(self, exception):
                    super().error_received(exception)
                    if exception is None: _buffer.close(EOFError())
                    else: _buffer.put_exception(exception = exception)

                def connection_lost(self, exception):
                    super().connection_lost(exception)
                    if exception is None: _buffer.close()
                    else: _buffer.put_exception(exception = exception)

            _transport, _protocol = await loop.create_datagram_endpoint(
                protocol_factory = lambda: _Protocol(),
                remote_addr = (host, port)
            )

            try:
                await _buffer.wait_connection()

                class _Result(_Stream):
                    async def read(self, size: int = None): return await _buffer.get_data(size=size)

                    async def write(self, data):
                        if not _buffer.state:
                            if _buffer.exception: raise _buffer.exception
                            raise EOFError()
                        _transport.sendto(data)
                        if not _buffer.state:
                            if _buffer.exception: raise _buffer.exception
                            raise EOFError()

                    async def close(self):
                        try: _transport.close()
                        finally: _buffer.close()

                return _Result()

            except BaseException:
                _transport.close()
                raise

        class _Communicator(object):
            async def __call__(self, command: str):
                assert isinstance(command, str)
                command = command.strip()
                assert bool(command)
                await self.__stream.write(self.__protocol.challenge_request)
                _response = await self.__stream.read()
                assert self.__protocol.expected_minimal_challenge_response_length <= len(_response)
                assert _response.endswith(self.__protocol.expected_challenge_response_parts[1])
                assert _response.startswith(self.__protocol.expected_challenge_response_parts[0])
                _response = _response[self.__protocol.expected_challenge_response_part_lengths[0]:-self.__protocol.expected_challenge_response_part_lengths[1]]
                assert self.__protocol.expected_challenge_id_pattern.match(_response) is not None
                await self.__stream.write(self.__protocol.main_request_parts[0] + _response + self.__protocol.main_request_parts[1] + command.encode() + self.__protocol.main_request_parts[2])
                _response = await self.__stream.read()
                assert _response.endswith(self.__protocol.expected_response_tail)
                assert _response.startswith(self.__protocol.expected_response_magic)
                _response = _response[self.__protocol.expected_response_magic_length:-self.__protocol.expected_response_tail_length].decode()
                return _response or None

            def __init__(self, stream: _Stream, password: str):
                assert isinstance(stream, _Stream)
                assert isinstance(password, str)
                super().__init__()

                _protocol_magic = self.__Protocol.magic

                class _Protocol(self.__Protocol):
                    main_request_parts = _protocol_magic + b"rcon ", (f" \"{password}\" ").encode(), b" \0"

                self.__stream = stream
                self.__protocol = _Protocol

            class __Protocol(object):
                magic = b"\xff\xff\xff\xff"
                challenge_request = magic + b"challenge rcon\n\0"
                expected_response_magic = magic + b"l"
                expected_response_magic_length = len(expected_response_magic)
                expected_response_tail = b"\x00\x00"
                expected_response_tail_length = len(expected_response_tail)
                expected_minimal_challenge_id_length = 1
                expected_challenge_id_pattern = re.compile(("^[0-9]+$").encode())
                expected_challenge_response_parts = magic + b"challenge rcon ", b"\n\x00"
                expected_challenge_response_part_lengths = tuple([len(_part) for _part in expected_challenge_response_parts])
                expected_minimal_challenge_response_length = expected_challenge_response_part_lengths[0] + expected_minimal_challenge_id_length + expected_challenge_response_part_lengths[1]

        def _parse_address(source: typing.Iterable):
            _host, _port = source
            assert isinstance(_host, str)
            _host = _host.strip()
            assert bool(_host)
            assert isinstance(_port, int) and (0 <= _port) and (65536 > _port)
            return _host, _port

        class _Class(object):
            "A class used to represent an Connection"

            host = property(lambda self: self.__host)
            port = property(lambda self: self.__port)
            loop = property(lambda self: self.__loop)
            address = property(lambda self: self.__address)
            password = property(lambda self: self.__password)

            async def execute(self, command: str):
                """
                Execute rcon command

                Connection should be opened before
                """
                try:
                    assert isinstance(self.__stream, _Stream)
                    assert isinstance(self.__communicator, _Communicator)
                except AssertionError: raise ConnectionError("not opened")
                return await self.__communicator(command = command)

            async def open(self, address: typing.Iterable = None, password: str = None):
                """
                Open connection
                
                Parameters
                ----------
                address : typing.Iterable, optional
                    server address [aka rcon_address], should be a pair (host: str, port: int)
                    default value is specified in the constructor if it's not None
                    
                password : str, optional
                    server password [aka rcon_password], should be a str
                    default value is specified in the constructor if it's not None
                """
                if address is None:
                    assert self.__address is not None
                    _host, _port = self.__address
                else: _host, _port = _parse_address(source = address)
                if password is None: _password = "" if self.__password is None else self.__password
                else:
                    assert isinstance(password, str)
                    _password = password
                try: assert self.__stream is None
                except AssertionError: raise ConnectionError("opened already")
                _loop = asyncio.get_running_loop() if self.__loop is None else self.__loop
                assert isinstance(_loop, asyncio.BaseEventLoop)
                _stream = await _make_stream(host = _host, port = _port, password = _password, loop = _loop)
                try: _communicator = _Communicator(stream = _stream, password = _password)
                except BaseException:
                    await _stream.close()
                    raise
                self.__stream, self.__communicator = _stream, _communicator

            async def close(self):
                "Close connection"
                try: assert isinstance(self.__stream, _Stream)
                except AssertionError: raise ConnectionError("not opened")
                _stream = self.__stream
                self.__stream = self.__communicator = None
                await _stream.close()

            async def __aenter__(self): return self

            async def __aexit__(self, exception_type, exception_value, exception_traceback):
                "Automatically closes connection if it was opened before"
                if self.__stream is None: return
                return await self.close()

            async def __call__(self, command: str):
                "does same as `execute()` method"
                return await self.execute(command = command)

            def __init__(self, address: typing.Iterable = None, password: str = None, loop: asyncio.BaseEventLoop = None):
                """
                Constructor

                Parameters
                ----------
                address : typing.Iterable, optional
                    default server address [aka rcon_address] for `open()` method

                password : str, optional
                    default server password [aka rcon_password] for `open()` method

                loop : asyncio event loop, optional
                """

                if address is None: _address, _host, _port = None, None, None
                else:
                    _address = _parse_address(source = address)
                    _host, _port = _address
                if password is not None: assert isinstance(password, str)
                _password = password
                if loop is None: _loop = None
                else:
                    assert isinstance(loop, asyncio.BaseEventLoop)
                    _loop = loop
                super().__init__()
                self.__host = _host
                self.__port = _port
                self.__loop = _loop
                self.__stream = None
                self.__address = _address
                self.__password = _password
                self.__communicator = None

        class _Result(object):
            Class = _Class

        return _Result

    _private = _private()
    try: Class = _private.Class
    finally: del _private

    def make(*args, **kwargs): return Class(*args, **kwargs)
