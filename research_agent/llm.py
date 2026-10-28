# llm.py - Gemini function-calling wrapper + fake model for testing

import os
from dataclasses import dataclass, field
from typing import Protocol

DEFAULT_MODEL = os.getenv("AGENT_MODEL", "gemini-3.8-flash")


@dataclass
class ModelResponse:
    text: str = ""
    tool_calls: list[dict] = field(default_factory=list)
    raw: object = None  # provider-specific content, forwarded on next call


class ChatModel(Protocol):
    def decide(self, system: str, messages: list[dict], tools: list) -> ModelResponse: ...


class GeminiModel:
    """Wraps Gemini with manual tool execution (no auto function calling)."""

    def __init__(self, model: str = DEFAULT_MODEL):
        from google import genai
        self.model = model
        self.client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

    def decide(self, system: str, messages: list[dict], tools: list) -> ModelResponse:
        from google.genai import types

        config = types.GenerateContentConfig(
            system_instruction=system,
            temperature=0.0,
            automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
        )

        if tools:
            config.tools = [
                types.Tool(function_declarations=[
                    types.FunctionDeclaration(
                        name=t.name,
                        description=t.description,
                        parameters_json_schema=t.params_schema,
                    )
                    for t in tools
                ])
            ]

        resp = self.client.models.generate_content(
            model=self.model,
            contents=self._build_contents(messages),
            config=config,
        )

        content = resp.candidates[0].content
        calls = [
            {"name": fc.name, "args": dict(fc.args or {})}
            for fc in (resp.function_calls or [])
        ]
        text = "".join(p.text for p in (content.parts or []) if getattr(p, "text", None))
        return ModelResponse(text=text.strip(), tool_calls=calls, raw=content)

    @staticmethod
    def _build_contents(messages: list[dict]) -> list:
        """Convert our message format to Gemini's Content objects."""
        from google.genai import types

        contents = []
        tool_results = []

        for m in messages:
            # Accumulate tool results into a single user turn (Gemini's format)
            if m["role"] == "tool":
                tool_results.append(
                    types.Part.from_function_response(
                        name=m["name"], response={"result": m["result"]}
                    )
                )
                continue

            # Flush any pending tool results before the next message
            if tool_results:
                contents.append(types.Content(role="user", parts=list(tool_results)))
                tool_results.clear()

            if m["role"] == "user":
                contents.append(
                    types.Content(role="user", parts=[types.Part.from_text(text=m["text"])])
                )
            elif m.get("raw") is not None:
                contents.append(m["raw"])
            else:
                # Reconstruct assistant message
                parts = []
                if m.get("text"):
                    parts.append(types.Part.from_text(text=m["text"]))
                for c in m.get("tool_calls", []):
                    parts.append(types.Part(
                        function_call=types.FunctionCall(name=c["name"], args=c["args"])
                    ))
                contents.append(types.Content(role="model", parts=parts))

        # Flush trailing tool results
        if tool_results:
            contents.append(types.Content(role="user", parts=list(tool_results)))

        return contents


class FakeModel:
    """Returns pre-scripted responses. For tests only."""

    def __init__(self, script: list[ModelResponse], repeat_last: bool = False):
        self.script = list(script)
        self.repeat_last = repeat_last
        self.calls: list[dict] = []

    def decide(self, system: str, messages: list[dict], tools: list) -> ModelResponse:
        self.calls.append({"messages": list(messages), "tools": [t.name for t in tools]})
        if len(self.script) > 1 or not self.repeat_last:
            return self.script.pop(0) if self.script else ModelResponse()
        return self.script[0]
