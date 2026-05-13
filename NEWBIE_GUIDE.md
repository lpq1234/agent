# 新人上手指南（本仓库）

这份指南给第一次接触本项目的同学，帮助你快速建立整体心智模型。

## 1. 先看全局：这是一个“可运行 Agent + 教学拆解”的双轨仓库

仓库主要分成两大块：

1. `agent/` 与根目录 `agent.py`：可直接运行的完整 Agent 系统。
2. `build-agent-example/`：从 step01 到 step08 的渐进式教学版本（每步都有 code + doc）。

建议把它理解为：
- **主线工程**（`agent/`）告诉你“实战如何组织”。
- **教学分步**（`build-agent-example/`）告诉你“能力如何一步步长出来”。

## 2. 主线工程结构（重点）

### 2.1 入口与主循环
- `agent.py`：极简入口。
- `agent/loop.py`：组件装配 + REPL 主循环。
- `agent/runner.py`：单轮 `messages.create`、tool_use 循环、并发安全工具调度。

### 2.2 三层记忆
- `agent/memory.py`：记忆存储接口/实现。
- `agent/compactor.py`：触发压缩后，把旧对话提炼成情景记忆并更新长期记忆。
- `agent/telemetry.py`：token 统计与压缩阈值判断。

> 关键理解：不是“把所有聊天都塞给模型”，而是通过压缩与归档把上下文成本降下来。

### 2.3 Prompt 组装与模板
- `agent/context.py`：把系统身份、技能信息、长期记忆等拼成最终 system prompt。
- `templates/`：
  - `SOUL.md`：人格与边界。
  - `USER.md`：用户偏好。
  - `templates/agent/*.md`：主 Agent 模板片段。
  - `templates/subagents/*.md`：子代理身份模板。

### 2.4 工具系统
- `agent/tools/registry.py` / `base.py` / `schema.py`：工具注册与协议。
- `agent/tools/`：内置工具（shell、web、filesystem、search、skills）。
- 特殊工具：
  - `todo.py`：任务规划 `update_todos`。
  - `dispatch.py`：子代理派遣 `dispatch_subagent`。

### 2.5 Skills 与子代理
- `agent/skills.py` + `skills/*/SKILL.md`：按需加载技能文本。
- `agent/subagents/registry.py` + `agent/subagents/spec.py`：子代理类型、能力白名单和运行约束。

## 3. 新人必须优先搞懂的 6 件事

1. **单轮 Tool Use 闭环**：模型发起 tool_use -> 本地执行 -> 回填 tool_result -> 继续推理。
2. **历史与压缩机制**：什么时候压缩、压缩后保留什么、如何避免上下文爆炸。
3. **Todo 规划约束**：为什么只允许一个 `in_progress`。
4. **子代理隔离**：子代理有独立 history，只回传总结，主上下文保持干净。
5. **并发执行边界**：并发发生在 runner 工具层，不是独立“并发 API”。
6. **Skill 触发时机**：为什么要按需加载而不是预加载全部技能。

## 4. 推荐学习路径（7 天版）

### Day 1：跑起来
- 建环境并跑 `python agent.py`。
- 跑 `step01`、`step02`，体会“单次调用 -> 循环对话”。

### Day 2：多轮上下文
- 看 `step03_history.py` 与文档。
- 亲自打印 messages，确认历史如何影响回答。

### Day 3：系统提示词与角色
- 看 `step04_system_prompt.py`。
- 改 system prompt 做 2~3 组 A/B 对比。

### Day 4：工具调用
- 看 `step05_tool_use.py`。
- 自己增加一个只读工具（例如读取本地时间/文件摘要）。

### Day 5：技能系统
- 看 `step06_skills.py` 与 `skills/*/SKILL.md`。
- 试着创建一个极简技能（例如“代码评审检查清单”）。

### Day 6：任务规划
- 看 `step07_plan_todolist.py`。
- 关注状态流转正确性（pending/in_progress/completed）。

### Day 7：子代理
- 看 `step08_subagent.py`。
- 设计一个“并发派遣 + 汇总”的任务，观察主 history 的简化效果。

## 5. 实战协作建议

- **先读再改**：先用只读方式梳理调用链，再做改动。
- **小步提交**：一个 commit 只做一件事，便于回滚。
- **优先补文档**：改行为就同步更新相关说明。
- **关注可观测性**：任何新增机制都尽量可日志化、可验证。
- **避免一次塞满能力**：Agent 架构最怕“复杂度瞬间爆炸”，保持最小可行迭代。

## 6. 你可以立刻做的 3 个练习

1. 给 `step05_tool_use.py` 增加一个“只读目录树（限制深度）”工具。
2. 给 `step07` 增加一个非法状态迁移校验并提示原因。
3. 在 `step08` 里写一个“多子代理分工读取文档并汇总”的 demo 任务。

完成这 3 个练习后，你会对本仓库最核心的工程能力（工具、规划、子代理）有扎实理解。
