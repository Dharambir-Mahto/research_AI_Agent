"""
Pytest configuration for automatically running async test functions without external plugins.
"""

import asyncio
import inspect
import pytest


def pytest_pyfunc_call(pyfuncitem):
    """Automatically run async def test functions using asyncio.run."""
    test_function = pyfuncitem.obj
    if inspect.iscoroutinefunction(test_function):
        args = {
            arg: pyfuncitem.funcargs[arg]
            for arg in pyfuncitem._fixtureinfo.argnames
            if arg in pyfuncitem.funcargs
        }
        asyncio.run(test_function(**args))
        return True
    return None
