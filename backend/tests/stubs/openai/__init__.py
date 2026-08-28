"""
Minimal stand-in for the `openai` package, just enough to exercise
utils/llm.py's Groq code path in tests without a real network call or API
key. Not a real dependency -- see tests/stubs/README.md.
"""

import json


class _Delta:
    def __init__(self, content):
        self.content = content


class _StreamChoice:
    def __init__(self, content):
        self.delta = _Delta(content)


class _StreamChunk:
    def __init__(self, content):
        self.choices = [_StreamChoice(content)]


class _Function:
    def __init__(self, name, arguments):
        self.name = name
        self.arguments = json.dumps(arguments) if isinstance(arguments, dict) else arguments


class _ToolCall:
    def __init__(self, call_id, name, arguments):
        self.id = call_id
        self.type = "function"
        self.function = _Function(name, arguments)


class _Message:
    def __init__(self, content=None, tool_calls=None):
        self.content = content
        self.tool_calls = tool_calls


class _Choice:
    def __init__(self, content=None, tool_calls=None):
        self.message = _Message(content=content, tool_calls=tool_calls)


class _CompletionResponse:
    def __init__(self, content=None, tool_calls=None):
        self.choices = [_Choice(content=content, tool_calls=tool_calls)]


# Tests can push scripted responses here to control exactly what the
# "model" decides to do next, call by call -- e.g.
#   TOOL_CALL_SCRIPT.append({"tool_calls": [("search_document", {"query": "x"})]})
#   TOOL_CALL_SCRIPT.append({"content": "final answer text"})
# Cleared automatically per-test via the `client` fixture's fresh module
# reload (this list lives on a freshly-imported module each test).
TOOL_CALL_SCRIPT = []


class _Completions:
    def create(self, model, messages, temperature=0.0, stream=False, tools=None):
        if tools is not None:
            if TOOL_CALL_SCRIPT:
                step = TOOL_CALL_SCRIPT.pop(0)
                if "tool_calls" in step:
                    calls = [
                        _ToolCall(f"call_{i}", name, args)
                        for i, (name, args) in enumerate(step["tool_calls"])
                    ]
                    return _CompletionResponse(tool_calls=calls)
                return _CompletionResponse(content=step.get("content", "stub answer"))
            # No script left -- default to ending the loop so tests that
            # don't care about the exact trace still terminate.
            return _CompletionResponse(content="stub final answer")

        stub_reply = "stub answer"
        if stream:
            def gen():
                for word in stub_reply.split(" "):
                    yield _StreamChunk(word + " ")
            return gen()
        return _CompletionResponse(content=stub_reply)


class _Chat:
    def __init__(self):
        self.completions = _Completions()


class OpenAI:
    def __init__(self, api_key=None, base_url=None):
        self.api_key = api_key
        self.base_url = base_url
        self.chat = _Chat()
