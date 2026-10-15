# WereWolf 项目说明

WereWolf 是一个基于 Python 的 AI 狼人杀对局引擎。项目当前聚焦于 CLI 运行的 8 人标准局：由多个 LLM Agent 扮演狼人、预言家、女巫、猎人和平民，在信息隔离的前提下完成夜间行动、白天发言、投票放逐、猎人触发和胜负裁决。

项目的核心目标是先跑通完整对局流程，再在此基础上扩展复盘、评测、批量对局、Web 观战和 Agent 自优化能力。

## 当前能力

- 支持 8 人标准配置：2 狼人、1 预言家、1 女巫、1 猎人、3 平民
- 支持完整阶段流转：夜晚、白天讨论、白天投票、猎人触发、游戏结束
- 支持角色专属行动：
  - 狼人夜间协商并击杀目标
  - 预言家查验玩家身份
  - 女巫使用解药或毒药
  - 猎人死亡后可开枪
  - 所有存活玩家白天发言与投票
- 支持按角色过滤信息，避免 Agent 看到越权内容
- 支持 OpenAI 兼容接口调用 LLM，并要求模型返回 JSON 行动
- 支持结构化事件日志，单局结束后写入 `data/logs/<game_id>.json`
- 提供随机决策的 `MockAgent`，便于后续测试或脱离 LLM 调试

## 技术栈

- Python 3.11+
- asyncio
- OpenAI SDK 兼容接口
- PyYAML
- python-dotenv
- structlog
- pytest / pytest-asyncio

`requirements.txt` 中还预留了 FastAPI、WebSocket、SSE、httpx 等依赖，方便后续扩展 Web 服务和实时观战。

## 目录结构

```text
WereWolf/
├── configs/
│   └── game.yaml              # 游戏角色与规则配置
├── data/
│   └── logs/                  # 对局事件日志（运行产物，不入库）
├── scripts/
│   └── run_game.py            # CLI 单局运行入口
├── src/
│   ├── agents/                # Agent 决策层
│   │   ├── base_agent.py      # LLM Agent
│   │   └── mock_agent.py      # 随机 Mock Agent
│   ├── comm/
│   │   └── info_filter.py     # 信息隔离与玩家视角生成
│   ├── engine/                # 游戏引擎核心
│   │   ├── action_handler.py  # 行动执行
│   │   ├── actions.py         # 行动类型与合法性校验
│   │   ├── config_loader.py   # YAML 配置加载
│   │   ├── events.py          # 事件总线
│   │   ├── game_factory.py    # 对局创建与角色分配
│   │   ├── manager.py         # 游戏主循环
│   │   ├── phases.py          # 阶段流转
│   │   ├── state.py           # 核心状态模型
│   │   └── win_checker.py     # 胜负判断
│   ├── llm/
│   │   └── provider.py        # OpenAI 兼容 LLM Provider
│   ├── observability/
│   │   └── logger.py          # 事件日志落盘
│   ├── prompts/               # 各角色 system prompt
│   └── utils/
│       └── prompt_loader.py   # Prompt YAML 加载
├── tests/                     # 测试目录，目前仅有包结构
├── .env.example               # 环境变量模板，复制为 .env 后填写
├── .gitignore
└── requirements.txt
```

## 快速开始

### 1. 创建虚拟环境

```bash
python -m venv .venv
```

Windows PowerShell：

```powershell
.\.venv\Scripts\Activate.ps1
```

macOS / Linux：

```bash
source .venv/bin/activate
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 配置 LLM 环境变量

项目通过 `.env` 读取 OpenAI 兼容接口配置。仓库中提供了模板，复制一份再填写即可：

```bash
cp .env.example .env
```

```env
API_KEY=你的 API Key
BASE_URL=你的 OpenAI 兼容接口地址
MODEL=deepseek-v4-pro
```

`MODEL`、`API_KEY`、`BASE_URL` 会在 `src/llm/provider.py` 中被读取。如果使用标准 OpenAI 接口，也可以按 OpenAI SDK 的兼容方式填写。

`.env` 已在 `.gitignore` 中，不会被提交到仓库。

### 4. 运行单局游戏

```bash
python scripts/run_game.py
```

运行后会在终端输出每个阶段的行动、发言、投票和死亡结果。游戏结束时会将结构化日志保存到：

```text
data/logs/<game_id>.json
```

## 游戏配置

默认配置位于 `configs/game.yaml`：

```yaml
game:
  roles:
    werewolf: 2
    seer: 1
    witch: 1
    hunter: 1
    villager: 3

  win_conditions:
    werewolf: "存活狼人数 >= 存活好人数"
    villager: "所有狼人被放逐或死亡"

  wolf_negotiation:
    max_rounds: 3
    consensus_timeout: true
```

目前 `config_loader.py` 主要读取 `roles` 并生成 `GameConfig`。阶段时长、胜负条件文本和狼人协商配置已经写在 YAML 中，但部分字段还未接入引擎逻辑。

## 核心流程

```text
创建游戏
  ↓
随机分配角色
  ↓
NIGHT 夜晚
  ├── 狼人协商击杀
  ├── 预言家查验
  └── 女巫救人 / 毒人 / 空过
  ↓
夜晚死亡结算
  ↓
DAY_DISCUSS 白天讨论
  └── 存活玩家依次发言
  ↓
DAY_VOTE 白天投票
  └── 统计票数并放逐最高票玩家
  ↓
HUNTER_TRIGGER 猎人触发，可选
  ↓
胜负判断
  ↓
进入下一轮或结束游戏
```

胜负规则在 `src/engine/win_checker.py` 中实现：

- 狼人全部死亡：好人阵营胜利
- 存活狼人数大于等于存活好人数：狼人阵营胜利
- 其他情况：游戏继续

## 关键模块说明

### GameManager

`src/engine/manager.py` 是游戏主控，负责：

- 创建所有玩家 Agent
- 根据当前阶段调用对应处理函数
- 构造每个玩家的可见视角
- 请求 Agent 决策
- 校验并执行行动
- 发布事件
- 推进阶段
- 游戏结束后保存日志

### GameState

`src/engine/state.py` 是引擎的核心状态模型，保存：

- 玩家列表与角色
- 当前阶段、轮次、行动序号
- 存活玩家与死亡玩家
- 夜间击杀、女巫毒杀、投票放逐
- 发言记录、投票记录、狼人私聊记录
- 预言家查验历史
- 最终胜者

### Action / ActionHandler

`src/engine/actions.py` 定义行动类型和合法性校验，`src/engine/action_handler.py` 负责真正修改状态。

当前支持的行动包括：

- `kill`
- `check`
- `save`
- `poison`
- `nothing`
- `speak`
- `vote`
- `abstain`
- `shoot`

### InfoFilter

`src/comm/info_filter.py` 根据玩家角色生成 `PlayerView`：

- 所有人可见：阶段、轮次、存活玩家、近期发言、死亡历史
- 女巫可见：解药 / 毒药状态、当晚被刀目标
- 预言家可见：历史查验结果
- 狼人可见：狼队友 ID、狼人夜间私聊内容

### BaseAgent

`src/agents/base_agent.py` 使用角色 prompt 和玩家视角调用 LLM。模型必须返回标准 JSON，例如：

```json
{
  "thought": "推理过程",
  "action": "vote",
  "target_id": 3,
  "speech_content": "我认为 3 号发言前后矛盾。"
}
```

Agent 会保留最近 20 条记忆，并在输出解析失败时最多重试 3 次。

### EventBus / GameLogger

`src/engine/events.py` 提供发布订阅机制，`src/observability/logger.py` 订阅所有事件并保存 JSON 日志。当前日志主要记录：

- 行动执行
- 玩家发言
- 投票
- 狼人击杀
- 女巫毒杀
- 玩家出局
- 猎人开枪

## Prompt 体系

角色 prompt 位于 `src/prompts/`：

```text
seer.yaml
witch.yaml
hunter.yaml
villager.yaml
werewolf.yaml
```

每个 prompt 都描述该角色的阵营、能力、胜利条件、策略建议和 JSON 输出格式。修改这些文件可以快速调整不同角色的行为风格。

## 当前状态与待完善点

- `tests/` 目录目前只有包结构，尚未补充实际测试用例
- `configs/game.yaml` 中的阶段时长、胜负条件文本、狼人协商配置尚未完全接入配置加载
- `MockAgent` 已实现，但当前 `GameManager` 默认使用 `BaseAgent`
- `requirements.txt` 中包含 Web 后端依赖，但当前仓库尚未实现 FastAPI 服务
- CLI 输出依赖终端编码，Windows 下如出现中文乱码，可优先确认终端 UTF-8 设置
- `BaseAgent` 中目标 ID 当前按 1 到 8 做了范围约束，若改成非 8 人局，需要同步调整

## 后续扩展方向

- 补充引擎单元测试：行动校验、阶段流转、胜负判断、女巫与猎人边界情况
- 增加 Mock 模式启动参数，方便不调用 LLM 跑通对局
- 增加批量对局脚本，统计不同 prompt 或模型的胜率
- 将 YAML 中更多规则参数接入 `GameConfig`
- 增加复盘报告生成，对 JSON 日志做可读化分析
- 接入 FastAPI + WebSocket，实现实时观战界面
- 引入评测指标，例如发言质量、投票命中率、阵营胜率、角色存活轮次

