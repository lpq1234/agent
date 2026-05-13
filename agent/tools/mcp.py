from __future__ import annotations

import json
import os
import subprocess
from dataclasses import dataclass
from typing import Any

from .base import Tool
from .schema import ObjectSchema, StringSchema, tool_parameters_schema


@dataclass(frozen=True)
class MCPServerConfig:
    name: str
    command: str
    args: tuple[str, ...]
    env: dict[str, str]


@dataclass(frozen=True)
class MCPToolSpec:
    server: str
    tool: str
    name: str
    description: str


def _encode_msg(payload: dict[str, Any]) -> bytes:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    return f"Content-Length: {len(body)}\r\n\r\n".encode("ascii") + body


def _iter_messages(blob: bytes):
    cursor = 0
    marker = b"\r\n\r\n"
    while cursor < len(blob):
        idx = blob.find(marker, cursor)
        if idx < 0:
            return
        header = blob[cursor:idx].decode("ascii", errors="ignore")
        length = None
        for line in header.split("\r\n"):
            if line.lower().startswith("content-length:"):
                length = int(line.split(":", 1)[1].strip())
                break
        if length is None:
            return
        start = idx + len(marker)
        end = start + length
        if end > len(blob):
            return
        yield json.loads(blob[start:end].decode("utf-8"))
        cursor = end


class MCPClient:
    def __init__(self, cfg: MCPServerConfig):
        self.cfg = cfg

    def call(self, method: str, params: dict[str, Any] | None = None, timeout: int = 30) -> dict[str, Any]:
        reqs = [
            {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2024-11-05", "capabilities": {}, "clientInfo": {"name": "agent", "version": "0.1"}}},
            {"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}},
            {"jsonrpc": "2.0", "id": 2, "method": method, "params": params or {}},
        ]
        payload = b"".join(_encode_msg(r) for r in reqs)

        env = os.environ.copy()
        env.update(self.cfg.env)
        proc = subprocess.Popen(
            [self.cfg.command, *self.cfg.args],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
        )
        out, err = proc.communicate(payload, timeout=timeout)
        if proc.returncode not in (0, None):
            raise RuntimeError(err.decode("utf-8", errors="ignore")[:500])
        for msg in _iter_messages(out):
            if msg.get("id") == 2:
                return msg
        raise RuntimeError("no response for requested id")


class MCPCallTool(Tool):
    name = "mcp_call"
    read_only = True

    def __init__(self, *, servers: dict[str, MCPServerConfig]):
        self._servers = servers

    @property
    def description(self) -> str:
        if not self._servers:
            return "调用 MCP server 工具（未配置服务器，请设置 MCP_SERVERS_JSON）"
        return f"调用 MCP server 工具，可用 servers: {', '.join(sorted(self._servers))}"

    @property
    def parameters(self) -> dict:
        return tool_parameters_schema(
            server=StringSchema("MCP server 名称", enum=sorted(self._servers.keys()) or None),
            tool=StringSchema("远端 tool 名称"),
            arguments=ObjectSchema("远端 tool 参数", properties={}, required=[]),
        )

    def execute(self, *, server: str, tool: str, arguments: dict[str, Any]) -> str:
        cfg = self._servers.get(server)
        if cfg is None:
            return f"Error: unknown MCP server '{server}'"
        client = MCPClient(cfg)
        try:
            msg = client.call("tools/call", {"name": tool, "arguments": arguments or {}})
        except Exception as exc:
            return f"Error: MCP call failed: {exc}"
        if "error" in msg:
            return f"Error: MCP call failed: {msg['error']}"
        return json.dumps(msg.get("result", {}), ensure_ascii=False, indent=2)


class MCPProxyTool(Tool):
    read_only = True

    def __init__(self, *, spec: MCPToolSpec, server_cfg: MCPServerConfig):
        self._spec = spec
        self._cfg = server_cfg

    @property
    def name(self) -> str:
        return self._spec.name

    @property
    def description(self) -> str:
        return self._spec.description

    @property
    def parameters(self) -> dict:
        return tool_parameters_schema(arguments=ObjectSchema("传给 MCP 工具的参数", properties={}, required=[]))

    def execute(self, *, arguments: dict[str, Any]) -> str:
        client = MCPClient(self._cfg)
        try:
            msg = client.call("tools/call", {"name": self._spec.tool, "arguments": arguments or {}})
        except Exception as exc:
            return f"Error: MCP call failed: {exc}"
        if "error" in msg:
            return f"Error: MCP call failed: {msg['error']}"
        return json.dumps(msg.get("result", {}), ensure_ascii=False, indent=2)


def load_mcp_servers() -> dict[str, MCPServerConfig]:
    raw = os.environ.get("MCP_SERVERS_JSON", "").strip()
    if not raw:
        return {}
    data = json.loads(raw)
    servers: dict[str, MCPServerConfig] = {}
    for name, cfg in data.items():
        if not isinstance(cfg, dict) or "command" not in cfg:
            continue
        servers[name] = MCPServerConfig(
            name=name,
            command=str(cfg["command"]),
            args=tuple(str(x) for x in cfg.get("args", [])),
            env={str(k): str(v) for k, v in cfg.get("env", {}).items()},
        )
    return servers


def build_mcp_tools() -> list[Tool]:
    servers = load_mcp_servers()
    tools: list[Tool] = [MCPCallTool(servers=servers)]

    for server_name, cfg in servers.items():
        client = MCPClient(cfg)
        try:
            msg = client.call("tools/list", {})
        except Exception:
            continue
        result = msg.get("result", {})
        for item in result.get("tools", []):
            remote_name = item.get("name")
            if not remote_name:
                continue
            local_name = f"mcp_{server_name}_{str(remote_name).replace('-', '_')}"
            desc = item.get("description") or f"MCP proxy for {server_name}:{remote_name}"
            tools.append(MCPProxyTool(
                spec=MCPToolSpec(server=server_name, tool=remote_name, name=local_name, description=desc),
                server_cfg=cfg,
            ))
    return tools
