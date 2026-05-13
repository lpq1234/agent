# Windows 启动指南

> 适用于 Windows 10/11 + PowerShell。

## 1) 安装与环境

1. 安装 Python 3.10+（勾选 `Add python.exe to PATH`）。
2. 在项目根目录执行：

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
```

## 2) 配置 `.env`

### Anthropic

```env
LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=你的key
ANTHROPIC_BASE_URL=
```

### OpenAI（原生格式）

```env
LLM_PROVIDER=openai
OPENAI_API_KEY=你的key
OPENAI_BASE_URL=
```

## 3) 启动

```powershell
python agent.py
```

## 4) Windows 下命令差异提示

- `run_command` 在 Windows 下通过系统 shell 执行命令；
- 常见替换：
  - `ls` -> `dir`
  - `cat file` -> `type file`
  - `grep x file` -> `findstr x file`

## 5) MCP 可选配置（Windows）

在 `.env` 中配置 `MCP_SERVERS_JSON`，例如：

```env
MCP_SERVERS_JSON={"fs":{"command":"npx","args":["-y","@modelcontextprotocol/server-filesystem","."]}}
```

要求：
- `command` 对应程序在 Windows 可执行（如 `npx`、`node`、`python`、`.exe`）。
- 若命令可执行但调用失败，先在 PowerShell 直接运行该命令定位问题。
