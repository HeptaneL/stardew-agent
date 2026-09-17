# Stardew Agent

把 LLM Agent 接进[星露谷物语](https://www.stardewvalley.net/)：村民和配偶的对话
当场生成，农场助手能查你这一天的真实存档。

不是套壳聊天框 —— Agent 通过 MCP 读实时游戏状态，回复写回游戏里的对话框和聊天框。

## 游戏内交互

按住 `Alt` 点击你的配偶，输入你想说的话，她当场给你几个可选回复：

https://github.com/user-attachments/assets/9047a6b1-f1a6-4d09-a007-448b909d4657

<img width="1512" alt="配偶对话" src="https://github.com/user-attachments/assets/21f76ce8-45a5-457c-b8f6-31d2affad136" />

在聊天框里敲 `cj 今天该做什么？`，CyberJu 会先查一遍你的存档再回答：

<img width="1512" height="982" alt="CyberJu 聊天框" src="https://github.com/user-attachments/assets/faab78a1-07a7-4616-9588-1b2b0d851a11" />

三个入口：

| 入口 | 怎么触发 | 回答是谁 |
| --- | --- | --- |
| 农场助手 | 聊天框输入 `cj <消息>` | CyberJu，可以用全部工具查存档 |
| 配偶 | 按住 `Alt` 点击你的配偶 | 配偶人格 + 配偶技能文档 |
| 村民 | 按住 `Alt` 点击任意村民 | 该村民人格 + 村民技能文档 |

回复走 ValleyTalk 的线路格式：`- ` 开头的一行是角色说的话，`% ` 开头的几行是
玩家可选的回复。模组解析这个格式并渲染成游戏原生的对话窗，所以玩家看到的是
星露谷本来的 UI，不是外挂窗口。

## Agentic RAG：检索由 Agent 决定

这是这个项目最想讲清楚的一件事：**上下文该由谁来决定。**

常见做法是工程师把上下文收集齐，拼成一个巨大的 prompt 再喂给模型：

```text
工程师收集上下文 ──► 拼成一个巨大的 prompt ──► LLM ──► 台词
```

这里把「检索」本身交还给 Agent，做成一次工具调用：

```text
环境 ──► Agent ──► 自己决定要查什么 ──► 工具 ──► 观察 ──► 推理 ──► 台词 / 行动
```

区别在于检索的**时机、内容和次数**都不是预先固定的。Agent 在 ReAct 循环里
（`agents/villager.py`）先看问题，需要查就调工具，看到结果再决定要不要继续查 ——
不需要查就直接回答，需要就查几次，而不是把可能用得上的信息一次性灌进去。

落在代码上是几处：

- **prompt 里没有一个字符的游戏状态。** `persona.py` 只拼接三样东西 —— 角色文档、
  技能文档、格式约定，全是稳定不变的内容。今天几号、季节、天气、农夫在哪、
  关系如何，一律不在 prompt 里。
- **工具白名单是对「这个人会去打听什么」的建模。** `CHARACTER_TOOLS`
  （`mcp_client.py:16`）给村民和配偶的，是一个真正住在山谷里的人会去问的东西 ——
  日期和今天的事件、自己的家庭、与农夫和镇上其他人的关系、农夫现在在哪、
  最近做了什么。日历和生日查询留给 CyberJu，因为它的工作是安排一天。
- **检索是 Agent 自己发起的工具调用。** `read_character_profile`（`tools.py:112`）
  由模型决定何时调、查谁：33 位村民各自一份文档，文件名就是主键，所以 `Evelyn`、
  `evelyn`、`艾芙琳` 都能落到同一份内容上。
- **状态永远新鲜。** 状态是每次请求现查的，不会出现 prompt 里固化着上一周存档
  状态的情况。文档也一样，每次请求重新读盘，改完不用重启。

这样做的收益是：新增一位村民只是多一个 Markdown 文件，不必再写一份上下文采集
逻辑；同一个角色换一种模式只换技能文档；上下文开销随这次对话实际需要增长，
而不是随游戏状态可能涉及的范围增长。

要让「按需检索」成立，环境一侧必须先有可查询的接口，而不能只把状态拼成一段
文字丢出来。这条链路的三段都是本项目的组成部分：

| 部分 | 角色 |
| --- | --- |
| [HelloStardew](https://github.com/HeptaneL/HelloStardew) | 游戏侧。读取游戏状态、暴露 HTTP API、把回复写回游戏 |
| 本仓库（`stardew-agent`） | 提示词里的稳定人设 + 自己决定要查什么的 Agent |
| [stardew-skills](https://github.com/HeptaneL/stardew-skills) | 角色与技能文档的独立仓库，本仓库里的文档最初来自这里 |

设计上刻意让 MCP 只返回事实（日期、关系、位置、最近活动），不做解释，解释留给
Agent —— 这也是为什么三个 Agent 共用一个薄薄的 MCP 层，而人格、记忆、推理全部
留在 Python 这一侧。

## 记忆机制

记忆挂在 LangGraph 的 checkpointer 上，由 `thread_id` 定位。

**一次对话的上下文。** 每次请求带一个 `thread_id`，LangGraph 用它作为 checkpoint
的 key（`api.py:72`）：

```python
config = {"configurable": {"thread_id": request.thread_id}}
```

系统提示词只在线程的第一轮发送（`api.py:92`）—— 之后模型看到的是这个线程累积
的消息历史，人设不必每轮重复。同一线程内 Agent 记得自己查过什么、说过什么，
所以「那 Haley 喜欢什么来着」这类追问不需要重新推理一遍。

**每个 (角色, 模式) 一份独立的图。** `character_agents` 按 `(kind, character)`
缓存编译好的图（`api.py:40`、`api.py:57`），每个图自带 checkpointer：

```python
character_agents[(kind, character)] = await _AGENT_FACTORIES[kind]()
```

这条设计有个具体的理由：同一位村民在一个存档里是配偶、在另一个存档里是邻居时，
两份对话历史必须互不干扰，否则「你是我妻子」会渗进邻居那条线里。分开缓存图的
时候，模式隔离是结构上成立的，不靠提示词去提醒模型。

存档和 `thread_id` 的对应关系由游戏侧决定，同一个存档带上同一串 `thread_id`
重放请求，就能接着上次的上下文继续聊。

## 三个 Agent

三者共用同一个 ReAct 图结构，区别只在工具集和技能文档。

### CyberJu —— 农场助手

CyberJu 是工具最全的那个。它在回答之前通过 MCP 工具读实时游戏状态，所以给出的
建议基于农场当天真实发生的事。

- 图：`src/stardew_agent/agents/butler.py`
- 提示词：`src/stardew_agent/prompts.py` 中的 `CYBERJU_PROMPTS`，每种语言一份
- 游戏内：聊天框输入 `cj <消息>`
- 工具：全部 12 个 MCP 工具 + `read_character_profile`
- 风格：简洁、沉稳，1–3 个短条目

可用的 MCP 工具：

```text
get_current_date        get_todays_events       get_week_birthdays
get_birthdays_on_day    get_events_on_day       get_month_calendar
get_household           get_relationship        get_current_state
get_recent_activity     get_recent_events       check_health
```

除了 MCP 工具，CyberJu 还带一个本地工具 `read_character_profile`
（`src/stardew_agent/tools.py:112`），用来查某位村民的角色文档 —— 身份、兴趣、
人际关系。所以「艾芙琳喜欢什么礼物」这类问题，它会自己去读 `evelyn.md`，而不是
凭印象回答。这个工具留在 Python 这一侧，是因为文档装在 Agent 里，MCP Server
那个独立进程从来看不到它们。

工具接收的是名字，不是文件名，所以 `Evelyn`、`evelyn`、`艾芙琳` 都能找到
`evelyn.md`：先按文件名匹配（`tools.py:84`），匹配不上再逐份文档比对首行标题
（`tools.py:88`），因此模型不必先知道中文名对应的英文文件名。名字只用来比对
已经列出的文档、不参与拼路径，所以它也没法走出 `assets/`。`language` 参数决定
读哪一份译文，按农夫当前的语言来给；不给的话，用名字是哪份文档给的（`艾芙琳`
来自 `zh/`）作为线索。

### 配偶（Spouse）—— 活起来的对话

配偶 Agent 把农夫配偶原本写死的对话换成当场生成的台词。它保留角色的性格，
但不再被限制在事先写好的那几句里。

它同样是一个会用工具的 Agent，只是比 CyberJu 收得更紧：白名单就是上面那 6 个
`CHARACTER_TOOLS`（`mcp_client.py:16`），和一个真正住在山谷里的人会去打听的
信息范围一致。

- 图：`src/stardew_agent/agents/spouse.py`
- 提示词：由 `src/stardew_agent/persona.py` 从角色文档和技能文档组装
- 游戏内：按住 `Alt` 点击你的配偶，输入你想说的话，她会给出几个可选回复
- 风格：一到两句自然的句子，不使用 Markdown

### 村民（Villager）—— 其他所有人也一样

村民 Agent 对**其他所有村民**做的事，和配偶 Agent 对农夫配偶做的事一样：
把写死的对话换成当场生成的台词，同时保留角色的性格与他/她和农夫之间真实的
关系。

它与配偶 Agent 共用同一份工具白名单和同一种回复格式，图结构也完全一样，
唯一的区别是系统提示词里的技能文档 —— 所以一个角色只需要写一次，两种模式下
都能见到。

走哪条路是模组的决定，不是 Agent 的决定：模组在每次请求里都会带上 `is_spouse`，
因为只有它能看到农夫是否和这个人结了婚，光看名字看不出来。

- 图：`src/stardew_agent/agents/villager.py`
- 提示词：`src/stardew_agent/persona.py` 中的 `villager_prompt`
- 游戏内：按住 `Alt` 点击任意村民
- 风格：一到两句自然的句子，不使用 Markdown

鹈鹕镇全部 33 位村民都已有角色文档，且每人都配有中英两份：

```
abigail   alex     caroline  clint    demetrius  dwarf    elliott
emily     evelyn   george    gus      haley      harvey   jas
jodi      kent     krobus    leah     lewis      linus    marnie
maru      pam      penny     pierre   robin      sam      sandy
sebastian shane    vincent   willy    wizard
```

也就是说，游戏里对**任何**一位村民按住 `Alt` 说话都能走通。`krobus` 一并覆盖，
作为同居室友时同样由模组通过 `is_spouse` 标记。

## 人格（Persona）的组装方式

一份提示词由三块相互独立的东西拼成，顺序是 角色 → 技能 → 格式约定
（`persona.py:128`），让输出约定离生成发生的地方最近：

| 层次 | 位置 | 回答的问题 |
| --- | --- | --- |
| 角色 | `src/stardew_agent/assets/character/<name>.md` | 这个人是谁 —— 身份、兴趣、人际关系 |
| 技能 | `src/stardew_agent/assets/skills/<skill>/SKILL.md` | 不管你是谁，在这个模式下该怎么表现 |
| 格式约定 | `prompts.py` 中的 `DIALOGUE_FORMAT_CONTRACTS` | 如何输出模组能解析的回复 |

拆成三块是为了正交：新增一位村民只是多一份角色文档，不需要碰代码；新增一种
模式（比如「节日里的村民」）只是多一份技能文档，33 位角色立刻都能用。现在有
33 份角色文档 × 2 个技能（`skills/spouse/`、`skills/villagers/`），具体搭配
哪一个是每次请求按 `is_spouse` 决定的。

角色文档的结构化也是为检索服务的 —— `## Interests`、`## Important Relationships`
这样的固定小节，让 Agent 读进来之后能按问题取用其中一段，而不是把整份文档
当成一段散文。

### 添加一位角色

1. 新增 `src/stardew_agent/assets/character/<name>.md`，文件名用 NPC 的内部名
   （小写）。`Haley` 会去找 `haley.md`。
2. 在游戏里和他/她说话 —— 作为配偶，或者作为普通村民都行。

不需要改代码 —— `POST /chat` 能解析任何有文档的名字，没有文档的返回 `404`。
要加一种语言，就把翻译后的文档放在以该语言命名的目录里，和英文原文并列
（`assets/character/zh/haley.md`）。

## 语言

每种语言有一套自己的提示词，不做翻译。消息用什么语言发过来，回复就用什么
语言回去，因为提示词本身就是用那种语言写的：

```text
中文输入 ──► 中文提示词 ──► agent ──► 中文输出
English in ──► English prompt ──► agent ──► English out
```

请求里带 `"language": "zh"`，中文那一套就会贯穿始终：CyberJu 提示词、角色
文档、技能文档、格式约定。只看主语言子标签（`prompts.py:21`），所以 `zh`、
`zh-CN`、`zh-Hans` 和 `zh-TW` 都解析为 `zh`。没有自己那一套的语言一律回落到
英文，英文也是默认值。

直接用中文写回复，而不是先写英文再渲染一遍，这才是重点。一个角色的口吻属于
这个角色本身；用中文写的措辞读起来是那个角色，而不是别人台词的忠实副本。这
也顺带让一次中文回复只需一次模型调用。

几个细节：

- 翻译文档是英文原件的兄弟文件，放在以语言命名的目录下
  （`assets/character/zh/haley.md`）。每份文档各自解析，缺翻译时会回落到英文
  并打一条 warning，所以一个角色可以先在一种语言上线，之后再补翻译。
- 一个线程的历史是它当初用的那种语言。中途换语言不会重写之前的轮次，而系统
  提示词只在线程的第一轮发送，所以想换语言就开一个新的 `thread_id`。
- 唯一不随语言改变的是线路格式。模组靠 `- ` 和 `% ` 解析回复，所以两套提示词
  用的是同一组 ASCII 标记，中文约定里也明确写了这一点 —— 否则模型写中文时会
  顺手用全角的 `－` 和 `％`，模组认不出来。
- 中文那一套是参照游戏自带的中文文本和 ValleyTalk 的 `i18n/zh.json` 写的，所以
  名称和语气与中文玩家在游戏里读到的保持一致 —— 鹈鹕镇是 Pelican Town，农夫是
  the farmer，花舞节是 Flower Dance。

模组会按**游戏当前语言**（`LocalizedContentManager.CurrentLanguageCode`）在每次
请求里带上 `language`，所以中文玩家在游戏里直接就能拿到中文回复，不需要额外
配置，也不会和游戏支持的语言列表脱节。

## 架构

```text
                    Stardew Valley
                         │
                       SMAPI
                         │
                  HelloStardew  ──────────────┐
                         │                    │
                    HTTP API                  │ POST /chat
                    :8788                     │ :8000
                         │                    │
                    MCP Server                │
                         │                    │
                       MCP                    │
                         │                    │
              ┌──────────▼──────────┐         │
              │    Stardew Agent    │         │
              │                     │         │
              │     LangGraph       │◄────────┘
              │     LangChain       │
              │        LLM          │
              └─────────────────────┘
```

两个方向：

- **游戏 → Agent：** 模组把游戏状态通过 HTTP API 暴露出来，MCP Server 把它
  包装成工具。三个 Agent 都会调用这些工具 —— CyberJu 用全部，配偶和村民用
  共用的那一部分 —— 让自己说的话基于真实的农场。
- **Agent → 游戏：** 模组向 Agent 的 `/chat` 发请求，再把回复写回游戏
  （CyberJu 写进聊天框，配偶和村民写进对话窗）。

## 环境要求

- Python 3.12 与 [uv](https://docs.astral.sh/uv/)
- Stardew Valley（Steam 版），并安装
  [SMAPI](https://smapi.io/) 和
  [HelloStardew](https://github.com/HeptaneL/HelloStardew)
- `stardew-mcp-server`（会作为 MCP stdio server 自动拉起）
- 一个 OpenAI 兼容的 LLM API（默认 DeepSeek）

## 配置

把 `.env.example` 复制成 `.env` 并填好：

| 变量 | 说明 |
| --- | --- |
| `MODEL` | 模型名，例如 `deepseek-flash` |
| `BASE_URL` | OpenAI 兼容的 base URL，例如 `https://api.deepseek.com` |
| `OPENAI_API_KEY` | 上面那项的 API key |
| `STARDEW_MCP_PATH` | 存放 `stardew-mcp-server` 的目录 |
| `STARDEW_API_URL` | HelloStardew 的 HTTP API，例如 `http://127.0.0.1:8788` |

## 运行

```bash
uv sync

# 启动 agent API。模组期望它在 127.0.0.1:8000。
uv run uvicorn stardew_agent.api:app --host 127.0.0.1 --port 8000
```

然后带着模组启动游戏：

- **CyberJu：** 打开聊天框，输入 `cj 今天该做什么？`
- **配偶：** 按住 `Alt` 点击你的配偶，然后输入消息。
- **村民：** 按住 `Alt` 点击任意一位村民。

想确认 MCP Server 和模组的连接是否正常，运行：

```bash
uv run python -m stardew_agent.test_mcp
```

## API

`POST http://127.0.0.1:8000/chat`

| 字段 | 说明 |
| --- | --- |
| `character` | `CyberJu`，或任何有角色文档的 NPC 名字 |
| `message` | 玩家说的话 |
| `thread_id` | 这条消息属于哪次对话；见[记忆机制](#记忆机制) |
| `language` | `en`（默认）或 `zh`；决定用哪套提示词，见[语言](#语言) |
| `is_spouse` | 必填。这位 NPC 是不是农夫的配偶或室友；决定用哪个技能 |

`is_spouse` 故意不给默认值。默认成 `false` 会让农夫自己的配偶以村民人格作答，
这看起来只是有点不像本人，而不像一个 bug；缺字段则会直接返回 `422`。
`CyberJu` 也要带这个字段，但它先按名字匹配，然后忽略它。

### 用法示例

同一个接口的三种用法，区别只在 `character` 和 `is_spouse`。

**跟农场助手说话**（对应游戏里的聊天框）：

```bash
curl -s http://127.0.0.1:8000/chat \
  -H 'Content-Type: application/json' \
  -d '{
    "character": "CyberJu",
    "message": "今天该做什么？",
    "thread_id": "cyberju-day-3",
    "language": "zh",
    "is_spouse": false
  }'
```

```json
{
  "character": "CyberJu",
  "message": "今天有三件事值得优先处理：\n1. 花舞节今天举行，下午 9 点开始，别忘了去。\n2. 今天是海莉的生日，准备一份她喜欢的礼物。\n3. 温室里的作物可以收了。"
}
```

**跟一位普通村民说话**（`is_spouse: false`）：

```bash
curl -s http://127.0.0.1:8000/chat \
  -H 'Content-Type: application/json' \
  -d '{
    "character": "Abigail",
    "message": "今天下午你在做什么？",
    "thread_id": "abigail-day-3-1",
    "language": "zh",
    "is_spouse": false
  }'
```

```json
{
  "character": "Abigail",
  "message": "- 下午大概又要去矿洞里，最近在练剑。\n% 我也想去，几点出发？\n% 下矿小心点。\n% 你在练什么？"
}
```

**跟自己的配偶说话**（`is_spouse: true`，同一个角色，换一份技能文档）：

```bash
curl -s http://127.0.0.1:8000/chat \
  -H 'Content-Type: application/json' \
  -d '{
    "character": "Haley",
    "message": "今天下午你在做什么？",
    "thread_id": "haley-spring-12",
    "language": "zh",
    "is_spouse": true
  }'
```

### 回复格式

以 `- ` 开头的那一行是角色说的话，以 `% ` 开头的几行是玩家可以选的回复。
CyberJu 则用普通散文作答，因为它的回复进的是聊天框而不是对话窗。

模型不会总是乖乖听话，所以 `format_dialogue_reply`（`api.py:133`）不信任原始
输出，而是从里面挑出真正带格式的行重建一遍：多说的开场白会丢掉，换行断句会
接回去，包裹的引号（中英文都算）会剥掉。模型完全无视格式时，回落到清理过的
原文，玩家至少还能看到台词。

### 错误

未知角色返回 `404`（`detail` 是找不到的那份文档路径），缺 `is_spouse` 返回 `422`：

```json
{"detail": "No persona document at /path/to/stardew-agent/src/stardew_agent/assets/character/leo.md"}
```

## 项目结构

```text
src/stardew_agent/
├── api.py            # FastAPI /chat 分发入口
├── agents/
│   ├── butler.py     # CyberJu —— 带全部 MCP 工具的 ReAct 循环
│   ├── spouse.py     # 配偶 —— 带 MCP 工具子集的 ReAct 循环
│   └── villager.py   # 村民 —— 同一份子集，另一个技能
├── assets/
│   ├── character/    # 这个人是谁，每个 NPC 一份（33 位村民）
│   │   └── zh/       #   ...以及同样这些文件，按语言分目录
│   └── skills/       # 在这个模式下该怎么表现，每个模式一个目录
│       ├── spouse/zh/
│       └── villagers/zh/
├── persona.py        # 读取角色 + 技能，组装提示词
├── prompts.py        # CYBERJU_PROMPTS、DIALOGUE_FORMAT_CONTRACTS，按语言
├── mcp_client.py     # MCP stdio 客户端 + CHARACTER_TOOLS 白名单
├── tools.py          # 本地工具：read_character_profile 读取角色文档
├── model.py          # LLM 客户端
└── config.py         # .env 配置
```

## 致谢

特别感谢 [ValleyTalk](https://github.com/dandm1/ValleyTalk)（作者 dandm1，LGPL v3）。
这个项目在两个方面大量参考了它：

- **游戏内的对话交互。** 打字输入、对话窗、可选回复这一整套交互方式参考了
  ValleyTalk 的实现，回复里 `- ` 表示角色说的话、`% ` 表示玩家可选的回复，也是
  直接沿用它的约定 —— 这条约定从游戏侧一路贯穿到这里的提示词和解析代码。
- **角色文档。** 33 份 `character/*.md` 在编写时参考了它
  `ContentPack/assets/bio/` 下的角色传记，中文文案则参照游戏自带的中文文本与它的
  中文翻译。

没有它，这里会从零开始摸一遍星露谷的对话系统。

还要感谢 [SMAPI](https://smapi.io/)（Pathoschild）、Harmony，以及
[Stardew Valley](https://www.stardewvalley.net/) 的作者 ConcernedApe。
