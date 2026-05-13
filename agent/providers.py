from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Protocol

import anthropic


@dataclass
class LLMUsage:
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_input_tokens: int = 0
    cache_creation_input_tokens: int = 0


@dataclass
class LLMResponse:
    content: list[dict[str, Any]]
    stop_reason: str
    usage: LLMUsage


class LLMProvider(Protocol):
    def create_message(self, *, model: str, max_tokens: int, system: str | None = None,
                       tools: list[dict] | None = None, messages: list[dict]) -> LLMResponse: ...


class AnthropicProvider:
    def __init__(self, *, api_key: str, base_url: str | None = None):
        self.client = anthropic.Anthropic(api_key=api_key, base_url=base_url)

    def create_message(self, *, model: str, max_tokens: int, system: str | None = None,
                       tools: list[dict] | None = None, messages: list[dict]) -> LLMResponse:
        resp = self.client.messages.create(
            model=model,
            max_tokens=max_tokens,
            system=system,
            tools=tools,
            messages=messages,
        )
        blocks = []
        for b in resp.content:
            if b.type == "text":
                blocks.append({"type": "text", "text": b.text})
            elif b.type == "tool_use":
                blocks.append({"type": "tool_use", "id": b.id, "name": b.name, "input": b.input})
        usage = LLMUsage(
            input_tokens=getattr(resp.usage, "input_tokens", 0) or 0,
            output_tokens=getattr(resp.usage, "output_tokens", 0) or 0,
            cache_read_input_tokens=getattr(resp.usage, "cache_read_input_tokens", 0) or 0,
            cache_creation_input_tokens=getattr(resp.usage, "cache_creation_input_tokens", 0) or 0,
        )
        return LLMResponse(content=blocks, stop_reason=resp.stop_reason or "end_turn", usage=usage)


class OpenAIProvider:
    def __init__(self, *, api_key: str, base_url: str | None = None):
        from openai import OpenAI
        self.client = OpenAI(api_key=api_key, base_url=base_url)

    def create_message(self, *, model: str, max_tokens: int, system: str | None = None,
                       tools: list[dict] | None = None, messages: list[dict]) -> LLMResponse:
        oa_msgs = _to_openai_messages(messages, system)
        oa_tools = [_to_openai_tool(t) for t in (tools or [])]
        resp = self.client.chat.completions.create(
            model=model,
            messages=oa_msgs,
            tools=oa_tools or None,
            tool_choice="auto" if oa_tools else None,
            max_tokens=max_tokens,
        )
        msg = resp.choices[0].message
        blocks: list[dict[str, Any]] = []
        if msg.content:
            blocks.append({"type": "text", "text": msg.content})
        for tc in msg.tool_calls or []:
            args = tc.function.arguments or "{}"
            parsed = json.loads(args) if isinstance(args, str) else args
            blocks.append({"type": "tool_use", "id": tc.id, "name": tc.function.name, "input": parsed})

        stop_reason = "tool_use" if (msg.tool_calls and len(msg.tool_calls) > 0) else "end_turn"
        usage = LLMUsage(
            input_tokens=getattr(resp.usage, "prompt_tokens", 0) or 0,
            output_tokens=getattr(resp.usage, "completion_tokens", 0) or 0,
        )
        return LLMResponse(content=blocks, stop_reason=stop_reason, usage=usage)


def _to_openai_tool(t: dict) -> dict:
    return {
        "type": "function",
        "function": {
            "name": t["name"],
            "description": t.get("description", ""),
            "parameters": t.get("input_schema", {"type": "object", "properties": {}}),
        },
    }


def _to_openai_messages(messages: list[dict], system: str | None) -> list[dict]:
    out: list[dict] = []
    if system:
        out.append({"role": "system", "content": system})
    for m in messages:
        role = m.get("role")
        content = m.get("content")
        if role == "user" and isinstance(content, str):
            out.append({"role": "user", "content": content})
            continue
        if role == "assistant" and isinstance(content, list):
            text_parts = [b.get("text", "") for b in content if isinstance(b, dict) and b.get("type") == "text"]
            tool_calls = []
            for b in content:
                if isinstance(b, dict) and b.get("type") == "tool_use":
                    tool_calls.append({
                        "id": b.get("id"),
                        "type": "function",
                        "function": {"name": b.get("name"), "arguments": json.dumps(b.get("input", {}), ensure_ascii=False)},
                    })
            msg: dict[str, Any] = {"role": "assistant", "content": "\n".join([t for t in text_parts if t]) or None}
            if tool_calls:
                msg["tool_calls"] = tool_calls
            out.append(msg)
            continue
        if role == "user" and isinstance(content, list):
            for b in content:
                if isinstance(b, dict) and b.get("type") == "tool_result":
                    out.append({
                        "role": "tool",
                        "tool_call_id": b.get("tool_use_id"),
                        "content": str(b.get("content", "")),
                    })
    return out
