"""
Tool calling interface for Gemini Live voice sessions.
Allows any AI Agent to expose tools and functions to the voice session.
"""

from __future__ import annotations

import inspect
import json
import logging
from typing import Callable, Dict, Any, Optional, List, Union
from pydantic import BaseModel
from google.genai import types

logger = logging.getLogger(__name__)

TYPE_MAP = {
    str: "string",
    int: "integer",
    float: "number",
    bool: "boolean",
    list: "array",
    dict: "object",
}


def python_type_to_json_type(py_type: Any) -> str:
    """Map standard Python types to JSON schema types."""
    return TYPE_MAP.get(py_type, "string")


def inspect_callable_to_declaration(fn: Callable[..., Any], name: Optional[str] = None, description: Optional[str] = None) -> types.FunctionDeclaration:
    """
    Introspects a standard Python function and generates a Gemini FunctionDeclaration.
    """
    func_name = name or fn.__name__
    func_doc = description or inspect.getdoc(fn) or f"Execute {func_name}"
    
    sig = inspect.signature(fn)
    properties: Dict[str, Any] = {}
    required: List[str] = []

    for param_name, param in sig.parameters.items():
        if param_name in ("self", "cls"):
            continue

        param_type = "string"
        if param.annotation != inspect.Parameter.empty:
            param_type = python_type_to_json_type(param.annotation)

        properties[param_name] = {
            "type": param_type,
            "description": f"Parameter {param_name}",
        }

        if param.default == inspect.Parameter.empty:
            required.append(param_name)

    schema = {
        "type": "object",
        "properties": properties,
        "required": required,
    }

    return types.FunctionDeclaration(
        name=func_name,
        description=func_doc,
        parameters_json_schema=schema,
    )


class VoiceTool:
    """Represents an executable tool exposed to Gemini Live."""

    def __init__(
        self,
        handler: Callable[..., Any],
        name: Optional[str] = None,
        description: Optional[str] = None,
        declaration: Optional[types.FunctionDeclaration] = None,
    ) -> None:
        self.handler = handler
        self.name = name or getattr(handler, "__name__", "custom_tool")
        self.description = description or inspect.getdoc(handler) or ""
        self.declaration = declaration or inspect_callable_to_declaration(
            handler, name=self.name, description=self.description
        )

    async def execute(self, args: Dict[str, Any]) -> Any:
        """Executes the tool handler with provided arguments, with resilient parameter binding."""
        # Check signature
        try:
            sig = inspect.signature(self.handler)
            has_var_keyword = any(
                p.kind == inspect.Parameter.VAR_KEYWORD for p in sig.parameters.values()
            )
            
            clean_args = dict(args)
            
            # Smart aliasing for common synonym discrepancies (e.g. city -> location)
            for param_name, param in sig.parameters.items():
                if param_name not in clean_args:
                    if param_name == "location" and "city" in clean_args:
                        clean_args["location"] = clean_args["city"]
                    elif param_name == "city" and "location" in clean_args:
                        clean_args["city"] = clean_args["location"]
                    elif param_name == "query" and "expression" in clean_args:
                        clean_args["query"] = clean_args["expression"]
                    elif param_name == "expression" and "query" in clean_args:
                        clean_args["expression"] = clean_args["query"]

            # Filter out unexpected keyword arguments if handler doesn't take **kwargs
            if not has_var_keyword:
                valid_params = set(sig.parameters.keys())
                filtered_args = {k: v for k, v in clean_args.items() if k in valid_params}
            else:
                filtered_args = clean_args

            if inspect.iscoroutinefunction(self.handler):
                return await self.handler(**filtered_args)
            return self.handler(**filtered_args)
        except Exception as e:
            if inspect.iscoroutinefunction(self.handler):
                return await self.handler(**args)
            return self.handler(**args)


class ToolRegistry:
    """
    Manages available tools, schema generation for Gemini Live,
    and dispatching incoming tool calls.
    """

    def __init__(self) -> None:
        self._tools: Dict[str, VoiceTool] = {}

    def register(
        self,
        func_or_tool: Union[Callable[..., Any], VoiceTool, Any],
        name: Optional[str] = None,
        description: Optional[str] = None,
    ) -> VoiceTool:
        """
        Register a function, VoiceTool, or agent tool (including LangChain tools).
        """
        if isinstance(func_or_tool, VoiceTool):
            self._tools[func_or_tool.name] = func_or_tool
            return func_or_tool

        # Check for LangChain tool
        if hasattr(func_or_tool, "name") and hasattr(func_or_tool, "description") and hasattr(func_or_tool, "run"):
            tool_name = name or func_or_tool.name
            tool_desc = description or func_or_tool.description
            
            # Use args_schema if present
            schema = None
            if hasattr(func_or_tool, "args_schema") and func_or_tool.args_schema:
                schema = func_or_tool.args_schema.model_json_schema()

            async def lc_handler(**kwargs):
                if hasattr(func_or_tool, "arun"):
                    return await func_or_tool.arun(kwargs)
                return func_or_tool.run(kwargs)

            declaration = types.FunctionDeclaration(
                name=tool_name,
                description=tool_desc,
                parameters_json_schema=schema or {"type": "object", "properties": {}},
            )
            v_tool = VoiceTool(handler=lc_handler, name=tool_name, description=tool_desc, declaration=declaration)
            self._tools[tool_name] = v_tool
            return v_tool

        if callable(func_or_tool):
            v_tool = VoiceTool(handler=func_or_tool, name=name, description=description)
            self._tools[v_tool.name] = v_tool
            return v_tool

        raise ValueError(f"Unsupported tool type: {type(func_or_tool)}")

    def get_tool(self, name: str) -> Optional[VoiceTool]:
        return self._tools.get(name)

    def to_gemini_tools(self) -> Optional[List[types.Tool]]:
        """Exports registered tools into Gemini Live types.Tool format."""
        if not self._tools:
            return None
        declarations = [tool.declaration for tool in self._tools.values()]
        return [types.Tool(function_declarations=declarations)]

    async def execute_tool(self, name: str, call_id: str, args: Dict[str, Any]) -> types.FunctionResponse:
        """
        Executes a registered tool and formats the response for Gemini Live.
        """
        tool = self.get_tool(name)
        if not tool:
            err_msg = f"Tool '{name}' is not registered."
            logger.error(err_msg)
            return types.FunctionResponse(
                id=call_id,
                name=name,
                response={"error": err_msg},
            )

        try:
            logger.info(f"Executing tool '{name}' with args: {args}")
            result = await tool.execute(args)
            # Ensure JSON serializable structure
            if not isinstance(result, (dict, list, str, int, float, bool, type(None))):
                if hasattr(result, "dict"):
                    result = result.dict()
                elif hasattr(result, "model_dump"):
                    result = result.model_dump()
                else:
                    result = str(result)

            payload = {"result": result} if not isinstance(result, dict) else result
            return types.FunctionResponse(
                id=call_id,
                name=name,
                response=payload,
            )
        except Exception as e:
            logger.error(f"Error executing tool '{name}': {e}", exc_info=True)
            return types.FunctionResponse(
                id=call_id,
                name=name,
                response={"error": str(e)},
            )
