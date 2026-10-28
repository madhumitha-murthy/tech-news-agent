"""
research_agent/llm.py — The model that decides what to do next.

The agent talks to the model through one method, decide(). Given the
conversation so far and the available tools, the model either asks for tool
calls or gives a final answer. GeminiModel uses Gemini function calling;
FakeModel replays a script so tests never call an API.

Message format used throughout the agent:
    {"role": "user", "text": "..."}
    {"role": "assistant", "text": "...", "tool_calls": [{"name": ..., "args": {...}}]}
    {"role": "tool", "name": "...", "result": <any JSON-serialisable value>}
"""

import os
from dataclasses import dataclass, field
from typing import Protocol

DEFAULT_MODEL = os.getenv("AGENT_MODEL", "gemini-2.0-flash")


@dataclass
class ModelTurn:
    text: str = ""
    tool_calls: list[dict] = field(default_factory=list)  # [{"name": ..., "args": {...}}]
    raw: object = None  # provider-specific message, resent as-is on the next call


class ChatModel(Protocol):
    def decide(self, system: str, messages: list[dict], tools: list) -> ModelTurn: ...


class GeminiModel:
    """Gemini with function calling. Our code runs the tools, not the SDK."""

    def __init__(self, model: str = DEFAULT_MODEL):
        from google import genai

        self.model = model
        self.client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

    def decide(self, system: str, messages: list[dict], tools: list) -> ModelTurn:
        from google.genai import types

        config = types.GenerateContentConfig(
            system_instruction=system,
            temperature=0.0,
            # We run tools ourselves so every call can be validated and traced.
            automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
        )
        if tools:
            config.tools = [
                types.Tool(
                    function_declarations=[
                        types.FunctionDeclaration(
                            name=t.name,
                            description=t.description,
                            parameters_json_schema=t.parameters,
                        )
                        for t in tools
                    ]
                )
            ]

        response = self.client.models.generate_content(
            model=self.model, contents=self._to_contents(messages), config=config
        )
        content = response.candidates[0].content
        calls = [{"name": fc.name, "args": dict(fc.args or {})} for fc in (response.function_calls or [])]
        text = "".join(p.text for p in (content.parts or []) if getattr(p, "text", None))
        return ModelTurn(text=text.strip(), tool_calls=calls, raw=content)

    @staticmethod
    def _to_contents(messages: list[dict]) -> list:
        from google.genai import types

        contents, pending_results = [], []

        def flush_results():
            if pending_results:
                contents.append(types.Content(role="user", parts=list(pending_results)))
                pending_results.clear()

        for m in messages:
            if m["role"] == "tool":
                pending_results.append(
                    types.Part.from_function_response(name=m["name"], response={"result": m["result"]})
                )
                continue
            flush_results()
            if m["role"] == "user":
                contents.append(types.Content(role="user", parts=[types.Part.from_text(text=m["text"])]))
            elif m.get("raw") is not None:
                contents.append(m["raw"])  # keeps any provider metadata intact
            else:
                parts = [types.Part.from_text(text=m["text"])] if m.get("text") else []
                parts += [
                    types.Part(function_call=types.FunctionCall(name=c["name"], args=c["args"]))
                    for c in m.get("tool_calls", [])
                ]
                contents.append(types.Content(role="model", parts=parts))
        flush_results()
        return contents


class FakeModel:
    """Replays a fixed list of ModelTurns. Used in tests and for dry runs."""

    def __init__(self, script: list[ModelTurn], repeat_last: bool = False):
        self.script = list(script)
        self.repeat_last = repeat_last
        self.calls: list[dict] = []  # what the agent sent, for assertions

    def decide(self, system: str, messages: list[dict], tools: list) -> ModelTurn:
        self.calls.append({"messages": list(messages), "tools": [t.name for t in tools]})
        if len(self.script) > 1 or not self.repeat_last:
            return self.script.pop(0) if self.script else ModelTurn(text="")
        return self.script[0]
