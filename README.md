# 简单工作流 MVP — 代码审查流程

多 Agent 协作的代码审查工作流：**编码 → 审查 → 修复 → 复审（循环）→ 通过**

自研轻量工作流引擎，支持顺序执行、条件分支、循环，无需第三方框架。

## 快速开始

```bash
python run_demo.py              # 使用内置 Mock LLM，无需 API Key
python main.py                  # 完整 CLI 入口
python main.py --requirement "写一个判断回文的函数"
python main.py -v               # 详细日志
```

## 工作流程

```
CodingAgent → ReviewAgent → (有问题?) → FixAgent → ReviewAgent → (通过?) → 完成
                                        ↑                         ↓
                                        └────── 循环 ─────────────┘
```

1. **CodingAgent**：根据需求生成代码
2. **ReviewAgent**：审查代码，有问题 → 请求修改，没问题 → 通过
3. **FixAgent**：根据审查意见修复代码，回到 ReviewAgent 复审

## 项目结构

```
core/       # 工作流引擎（编排、状态管理、消息传递）
agents/     # 三个 Agent（编码、审查、修复）
llm/        # LLM 客户端（Mock + OpenAI）
tests/      # 测试（20 个，全部通过）
main.py     # CLI 入口
run_demo.py # 快速演示
```

## 核心特性

- **流程控制**：顺序执行、条件分支、循环、最大迭代次数防死循环
- **Agent 通信**：结构化 Message + 共享 WorkflowState，全程记录消息日志
- **可扩展**：继承 `BaseAgent` 实现 `run()` 即可添加新 Agent
- **LLM 灵活**：内置 Mock LLM 开箱即用，也支持 OpenAI 兼容 API

## 运行测试

```bash
python tests/test_workflow.py
```

## 使用真实 LLM

```bash
pip install -r requirements.txt
set OPENAI_API_KEY=sk-xxx
python main.py
```
