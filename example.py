#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import asyncio
import p5.aiogoldsrcrcon


async def _coroutine():
    async with p5.aiogoldsrcrcon.Connection(address = ("hlds.host.address.example.com", 27015), password = "super-secret-rcon-password") as _connection:
        await _connection.open()
        _response = await _connection.execute(command = "status")
        print(_response.strip())

asyncio.get_event_loop().run_until_complete(asyncio.wait_for(_coroutine(), timeout = 3))
