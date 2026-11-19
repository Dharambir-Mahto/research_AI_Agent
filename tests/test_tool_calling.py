"""
Tests for ToolRegistry, VoiceTool, and schema inspection.
"""

import pytest
from gemini_voice.tools import ToolRegistry, VoiceTool


def multiply_numbers(a: int, b: int) -> int:
    """Multiplies two integers."""
    return a * b


async def async_fetch_info(topic: str) -> str:
    """Fetches info about a topic asynchronously."""
    return f"Details about {topic}"


async def test_tool_registration_and_execution():
    registry = ToolRegistry()
    registry.register(multiply_numbers)
    registry.register(async_fetch_info)

    # 1. Check schemas
    gemini_tools = registry.to_gemini_tools()
    assert gemini_tools is not None
    assert len(gemini_tools) == 1
    declarations = gemini_tools[0].function_declarations
    assert len(declarations) == 2

    decl_names = [d.name for d in declarations]
    assert "multiply_numbers" in decl_names
    assert "async_fetch_info" in decl_names

    # 2. Test execution of sync tool
    res1 = await registry.execute_tool("multiply_numbers", "call_1", {"a": 6, "b": 7})
    assert res1.response == {"result": 42}

    # 3. Test execution of async tool
    res2 = await registry.execute_tool("async_fetch_info", "call_2", {"topic": "Gemini Live"})
    assert res2.response == {"result": "Details about Gemini Live"}


async def test_tool_parameter_aliasing_and_filtering():
    def get_weather(location: str) -> str:
        """Weather tool."""
        return f"Weather in {location}"

    registry = ToolRegistry()
    registry.register(get_weather)

    # Calling with 'city' alias instead of 'location'
    res = await registry.execute_tool("get_weather", "call_3", {"city": "Berlin", "extra_param": 123})
    assert res.response == {"result": "Weather in Berlin"}


async def test_unregistered_tool():
    registry = ToolRegistry()
    res = await registry.execute_tool("nonexistent", "call_x", {})
    assert "error" in res.response
