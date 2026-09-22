import asyncio
import json
from typing import Dict, List, Optional

import pytest
from typing_extensions import Annotated, Doc

from dbgpt._private.pydantic import BaseModel, ConfigDict, Field

from ..base import BaseTool, FunctionTool, ToolParameter, tool
from ..pack import ToolPack


class TestBaseTool(BaseTool):
    @property
    def name(self):
        return "test_tool"

    @property
    def description(self):
        return "This is a test tool."

    @property
    def args(self):
        return {}

    def execute(self, *args, **kwargs):
        return "executed"

    async def async_execute(self, *args, **kwargs):
        return "async executed"


def test_base_tool():
    tool = TestBaseTool()
    assert tool.name == "test_tool"
    assert tool.description == "This is a test tool."
    assert tool.execute() == "executed"
    assert asyncio.run(tool.async_execute()) == "async executed"


def test_function_tool_sync() -> None:
    def two_sum(a: int, b: int) -> int:
        """Add two numbers."""
        return a + b

    ft = FunctionTool(name="sample", func=two_sum)
    assert ft.execute(1, 2) == 3
    with pytest.raises(ValueError):
        asyncio.run(ft.async_execute(1, 2))


@pytest.mark.asyncio
async def test_function_tool_async() -> None:
    async def sample_async_func(a: int, b: int) -> int:
        """Add two numbers asynchronously."""
        return a + b

    ft = FunctionTool(name="sample_async", func=sample_async_func)
    with pytest.raises(ValueError):
        ft.execute(1, 2)
    assert await ft.async_execute(1, 2) == 3


@pytest.mark.asyncio
async def test_function_tool_sync_with_args() -> None:
    def two_sum(a: int, b: int) -> int:
        """Add two numbers."""
        return a + b

    ft = FunctionTool(
        name="sample",
        func=two_sum,
        args={
            "a": {"type": "integer", "name": "a", "description": "The first number."},
            "b": {"type": "integer", "name": "b", "description": "The second number."},
        },
    )
    ft1 = FunctionTool(
        name="sample",
        func=two_sum,
        args={
            "a": ToolParameter(
                type="integer", name="a", description="The first number."
            ),
            "b": ToolParameter(
                type="integer", name="b", description="The second number."
            ),
        },
    )
    assert ft.description == "Add two numbers."
    assert ft.args.keys() == {"a", "b"}
    assert ft.args["a"].type == "integer"
    assert ft.args["a"].name == "a"
    assert ft.args["a"].description == "The first number."
    assert ft.args["a"].title == "A"
    dict_params = [
        {
            "name": "a",
            "type": "integer",
            "description": "The first number.",
            "required": True,
        },
        {
            "name": "b",
            "type": "integer",
            "description": "The second number.",
            "required": True,
        },
    ]
    json_params = json.dumps(dict_params, ensure_ascii=False)
    expected_prompt = (
        f"sample: Call this tool to interact with the sample API. What is the "
        f"sample API useful for? Add two numbers. Parameters: {json_params}"
    )
    pmt, info = await ft.get_prompt()
    pmt1, info1 = await ft1.get_prompt()
    assert pmt == expected_prompt
    assert pmt1 == expected_prompt
    assert ft.execute(1, 2) == 3
    with pytest.raises(ValueError):
        await ft.async_execute(1, 2)


def test_function_tool_sync_with_complex_types() -> None:
    @tool
    def complex_func(
        a: int,
        b: Annotated[int, Doc("The second number.")],
        c: Annotated[str, Doc("The third string.")],
        d: List[int],
        e: Annotated[Dict[str, int], Doc("A dictionary of integers.")],
        f: Optional[float] = None,
        g: str | None = None,
    ) -> int:
        """A complex function."""
        return (
            a + b + len(c) + sum(d) + sum(e.values()) + (f or 0) + (len(g) if g else 0)
        )

    ft: FunctionTool = complex_func._tool
    assert ft.description == "A complex function."
    assert ft.args.keys() == {"a", "b", "c", "d", "e", "f", "g"}
    assert ft.args["a"].type == "integer"
    assert ft.args["a"].description == "A"
    assert ft.args["b"].type == "Annotated"
    assert ft.args["b"].description == "The second number."
    assert ft.args["c"].type == "Annotated"
    assert ft.args["c"].description == "The third string."
    assert ft.args["d"].type == "array"
    assert ft.args["d"].description == "D"
    assert ft.args["e"].type == "object"
    assert ft.args["e"].description == "A dictionary of integers."
    assert ft.args["f"].type == "number"
    assert ft.args["f"].description == "F"
    assert ft.args["g"].type == "string"
    assert ft.args["g"].description == "G"


def test_function_tool_sync_with_args_schema() -> None:
    class ArgsSchema(BaseModel):
        a: int = Field(description="The first number.")
        b: int = Field(description="The second number.")
        c: Optional[str] = Field(None, description="The third string.")
        d: List[int] = Field(description="Numbers.")

    @tool(args_schema=ArgsSchema)
    def complex_func(a: int, b: int, c: Optional[str] = None) -> int:
        """A complex function."""
        return a + b + len(c) if c else 0

    ft: FunctionTool = complex_func._tool
    assert ft.description == "A complex function."
    assert ft.args.keys() == {"a", "b", "c", "d"}
    assert ft.args["a"].type == "integer"
    assert ft.args["a"].description == "The first number."
    assert ft.args["b"].type == "integer"
    assert ft.args["b"].description == "The second number."
    assert ft.args["c"].type == "string"
    assert ft.args["c"].description == "The third string."
    assert ft.args["d"].type == "array"
    assert ft.args["d"].description == "Numbers."


def test_tool_decorator() -> None:
    @tool(description="Add two numbers")
    def add(a: int, b: int) -> int:
        """Add two numbers."""
        return a + b

    assert add(1, 2) == 3
    assert add._tool.name == "add"
    assert add._tool.description == "Add two numbers"


def test_function_tool_opt_in_schema_validation_is_structured_and_pre_execution() -> (
    None
):
    calls = []

    class ArgsSchema(BaseModel):
        model_config = ConfigDict(extra="forbid")

        quarter: str = Field(pattern=r"^20\d{2}Q[1-4]$", description="Quarter")
        top_n: int = Field(default=5, ge=1, le=20, description="Top N")

    @tool(args_schema=ArgsSchema, validate_args=True)
    def analyze(quarter: str, top_n: int = 5) -> dict:
        """Analyze one quarter."""

        calls.append((quarter, top_n))
        return {"quarter": quarter, "top_n": top_n}

    invalid = analyze(quarter="2026-Q2", top_n=0)

    assert invalid["status"] == "error"
    assert invalid["error"]["code"] == "invalid_arguments"
    assert invalid["error"]["retryable"] is True
    assert {item["field"] for item in invalid["error"]["details"]} == {
        "quarter",
        "top_n",
    }
    assert calls == []
    extra = ToolPack([analyze]).execute(
        resource_name="analyze", quarter="2026Q2", unexpected=True
    )
    assert extra["error"]["code"] == "invalid_arguments"
    assert extra["error"]["details"][0]["field"] == "unexpected"
    assert calls == []
    assert analyze(quarter="2026Q2", top_n=3) == {
        "quarter": "2026Q2",
        "top_n": 3,
    }
    assert calls == [("2026Q2", 3)]


def test_function_tool_prompt_preserves_json_schema_constraints() -> None:
    class ArgsSchema(BaseModel):
        quarter: str = Field(pattern=r"^20\d{2}Q[1-4]$", description="Quarter")
        top_n: int = Field(default=5, ge=1, le=20, description="Top N")

    @tool(args_schema=ArgsSchema)
    def analyze(quarter: str, top_n: int = 5) -> None:
        """Analyze one quarter."""

        return None

    assert analyze._tool.args["quarter"].constraints == {"pattern": r"^20\d{2}Q[1-4]$"}
    assert analyze._tool.args["top_n"].constraints == {
        "maximum": 20,
        "minimum": 1,
    }
    prompt, _ = asyncio.run(analyze._tool.get_prompt(lang="zh"))
    assert '"pattern": "^20\\\\d{2}Q[1-4]$"' in prompt
    assert '"minimum": 1' in prompt
    assert '"maximum": 20' in prompt


@pytest.mark.asyncio
async def test_tool_decorator_async() -> None:
    @tool
    async def async_add(a: int, b: int) -> int:
        """Asynchronously add two numbers."""
        return a + b

    assert await async_add(1, 2) == 3
