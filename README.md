# Stardew Agent

一个实验性的 Agent 运行时，通过 MCP 把 AI Agent 接入
[星露谷物语](https://www.stardewvalley.net/)。

目标不是做一个聊天机器人，而是探索 Agent 如何感知并推理一个持续存在的
游戏环境。

目前包含三个 Agent，与 [HelloStardew](https://github.com/HeptaneL/HelloStardew)
SMAPI 模组配合，在 Steam 版游戏上运行。游戏状态通过 MCP *流入* Agent，
Agent 的回复再*流回*游戏。

## 主要创新：上下文管理中的渐进式披露

这个项目真正想验证的东西不是提示词写得好不好，而是 **Agent 的上下文该由谁来决定**。

常见的做法是让工程师替模型把上下文收集齐，拼成一份大提示词：

```text
工程师收集上下文 ──► 拼成一个巨大的 prompt ──► LLM ──► 台词
```

这里反过来：提示词里只有稳定的人设，会变的东西由 Agent 在需要时自己去拿。

```text
环境 ──► Agent ──► 自己决定需要什么 ──► MCP 工具 ──► 观察 ──► 推理 ──► 台词 / 行动
```

具体落在几处：

- **提示词里没有一个字符的游戏状态。** `persona.py` 只拼接三样东西 —— 角色文档、
  技能文档、格式约定，全都是稳定不变的内容。今天几号、季节、天气、农夫在哪、
  关系如何，一律不在提示词里。
- **工具白名单是对「这个人会去打听什么」的建模。** `CHARACTER_TOOLS`
  （`mcp_client.py`）给角色的，是一个真正住在山谷里的人会去问的东西，而不是所有
  可获取的信息；全部工具留给 CyberJu，因为它的工作是安排一天。
- **查什么、查几次，由 Agent 自己决定。** 每一轮都是一次 ReAct 循环
  （`agents/villager.py`）：不需要查询就直接回答，需要就多查几次 —— 而不是把所有
  可能用得上的信息一次性灌进去。
- **状态永远新鲜。** 状态是每次请求现查的，所以不会出现提示词里固化着上一周存档
  状态的情况。

这样做的收益是，新增一位村民只是多一个 Markdown 文件，不必再写一份上下文采集
逻辑；同一个角色换一种模式只换技能文档；上下文开销随这次对话实际需要增长，而
不是随游戏状态可能涉及的范围增长。

要让「按需获取」成立，环境一侧必须先有可查询的接口，而不能只把状态拼成一段
文字丢出来。这条链路的三段都是本项目的组成部分，各自负责一件事：

| 部分 | 角色 |
| --- | --- |
| [HelloStardew](https://github.com/HeptaneL/HelloStardew) | 游戏侧。读取游戏状态、暴露 HTTP API、把回复写回游戏 |
| 本仓库（`stardew-agent`） | 提示词里的稳定人设 + 自己决定要查什么的 Agent |
| [stardew-skills](https://github.com/HeptaneL/stardew-skills) | 角色与技能文档的实验空间，本仓库里的资产最初来自这里 |

换句话说，渐进式披露不是 Agent 单方面能做的事：游戏侧要「读得宽」，Agent 才能
「取得准」。设计上刻意让 MCP 只返回事实（日期、关系、位置、最近活动），不做
解释，解释留给 Agent —— 这也是为什么三个 Agent 共用一个薄薄的 MCP 层，而人格、
记忆、推理全部留在 Python 这一侧。

## Agent 组成

### CyberJu —— 农场助手

CyberJu 是一个会用工具的 Agent。它在回答之前通过 MCP 工具读取实时游戏状态
（日历、事件、生日、当前日期），所以给出的建议基于农场当天真实发生的事。

- 图：`src/stardew_agent/agents/butler.py`
- 提示词：`src/stardew_agent/prompts.py` 中的 `CYBERJU_PROMPTS`，每种语言一份
- 游戏内：在聊天框输入 `cj <消息>` 与它对话
- 风格：简洁、沉稳，1–3 个短条目

<img width="1512" height="982" alt="Screenshot 2026-09-12 at 5 16 55 PM" src="https://github.com/user-attachments/assets/faab78a1-07a7-4616-9588-1b2b0d851a11" />


### 配偶（Spouse）—— 活起来的对话

配偶 Agent 把农夫配偶原本写死的对话换成当场生成的台词。它保留角色的性格，
但不再被限制在事先写好的那几句里。

它同样是一个会用工具的 Agent，只是比 CyberJu 收得更紧：它只能查看一个真正
住在山谷里的人会去打听的东西 —— 日期和今天的事件、自己的家庭、自己与农夫
和镇上其他人的关系、农夫现在在哪、农夫最近做了什么。日历和生日查询留给
CyberJu，因为它的工作是安排一天，而不是过日子。这份白名单是
`src/stardew_agent/mcp_client.py` 里的 `CHARACTER_TOOLS`，与下面的村民 Agent
共用。

- 图：`src/stardew_agent/agents/spouse.py`
- 提示词：由 `src/stardew_agent/persona.py` 从角色文档和技能文档组装
- 游戏内：按住 `Alt` 点击你的配偶，输入你想说的话，她会给出几个可选回复
- 风格：一到两句自然的句子，不使用 Markdown

<img width="3024" height="1964" alt="image" src="https://github.com/user-attachments/assets/21f76ce8-45a5-457c-b8f6-31d2affad136" />


### 村民（Villager）—— 其他所有人也一样

村民 Agent 对**其他所有村民**做的事，和配偶 Agent 对农夫配偶做的事一样：
把写死的对话换成当场生成的台词，同时保留角色的性格与他/她和农夫之间真实的
关系。

它与配偶 Agent 共用同一份工具白名单和同一种回复格式。两者唯一的区别是系统
提示词里的技能文档，所以一个角色只需要写一次，两种模式下都能见到。

走哪条路是模组的决定，不是 Agent 的决定：模组在每次请求里都会带上
`is_spouse`，因为只有它能看到农夫是否和这个人结了婚，光看名字看不出来。

- 图：`src/stardew_agent/agents/villager.py`
- 提示词：`src/stardew_agent/persona.py` 中的 `villager_prompt`，由角色文档与
  `skills/villagers/SKILL.md` 组装
- 游戏内：按住 `Alt` 点击任意村民
- 风格：一到两句自然的句子，不使用 Markdown

### 当前覆盖情况

鹈鹕镇全部 33 位村民都已有角色文档，且每人都配有中英两份：

```
abigail   alex     caroline  clint    demetrius  dwarf    elliott
emily     evelyn   george    gus      haley      harvey   jas
jodi      kent     krobus    leah     lewis      linus    marnie
maru      pam      penny     pierre   robin      sam      sandy
sebastian shane    vincent   willy    wizard
```

也就是说，现在游戏里对**任何**一位村民按住 `Alt` 说话，都能走通，不再只限于
配偶和 Haley。`krobus` 一并覆盖，作为同居室友时同样由模组通过 `is_spouse`
标记。


## 人格（Persona）的组装方式

一份提示词由三块相互独立的东西拼成。把它们分开，才能在之后让一个技能套用到
别的角色上，也让同一个角色出现在不止一种模式里。

| 层次 | 位置 | 回答的问题 |
| --- | --- | --- |
| 角色 | `src/stardew_agent/assets/character/<name>.md` | 这个人是谁 —— 身份、兴趣、人际关系 |
| 技能 | `src/stardew_agent/assets/skills/<skill>/SKILL.md` | 不管你是谁，在这个模式下该怎么表现 |
| 格式约定 | `prompts.py` 中的 `DIALOGUE_FORMAT_CONTRACTS` | 如何输出模组能解析的回复 |

三者按 角色 → 技能 → 格式约定 的顺序拼接，让输出约定离生成发生的地方最近。

现在有 33 份角色文档，每份都可以与两个技能搭配 —— `skills/spouse/SKILL.md`
和 `skills/villagers/SKILL.md`。具体搭配哪一个是每次请求按 `is_spouse` 决定的，
见上文「村民（Villager）」。

这些文档最初来自
[stardew-skills](https://github.com/HeptaneL/stardew-skills) 仓库，那是一个独立
的实验空间。这里这份才是实际运行的版本，并且**不**与它保持同步 —— 要改就改
这里。

### 尚未接入：记忆

游戏工具已经落地，所以配偶技能里的 `## Use of Context` 现在描述的是她真的能
查到什么。但对话记忆还没有，那是另一回事：这些工具报告的是农场和这一天，而
不是你们俩上周对彼此说过什么。因此技能文档里仍然明确写着，她不记得之前的
对话。

同一线程（`thread_id`）内的一轮对话历史由 LangGraph 的 checkpointer 保留，
所以一次对话之内的上下文是连贯的；跨对话的长期记忆则还没有。等记忆存储落地
时，需要回头处理的正是 `assets/skills/spouse/SKILL.md` 里的
`## Relationship Continuity`，以及 `## Use of Context` 中那段关于不记得的
说明。

注意历史保存在进程内存里（`InMemorySaver`），重启服务即丢失。CyberJu 每次
请求都会新建一个 Agent，因此它本身不带对话记忆。

### 添加一位角色

1. 新增 `src/stardew_agent/assets/character/<name>.md`，文件名用 NPC 的内部名
   （小写）。`Haley` 会去找 `haley.md`。
2. 在游戏里和他/她说话 —— 作为配偶，或者作为普通村民都行。

不需要改代码 —— `POST /chat` 能解析任何有文档的名字，没有文档的返回 `404`。
两个技能都已经存在，所以新角色只要有了文档，两种模式下都立刻可用。

唯一的例外是模组根本不会发过来的名字，比如无法对话的 NPC，那种请求在到达
这里之前就已经失败了。

要加一种语言，就把翻译后的文档放在以该语言命名的目录里，和英文原文并列
（`assets/character/zh/haley.md`）。见[语言](#语言)。

这些 Markdown 每次请求都会重新读取，所以改完不用重启就生效。

## 语言

每种语言有一套自己的提示词，不做翻译。消息用什么语言发过来，回复就用什么
语言回去，因为提示词本身就是用那种语言写的：

```text
中文输入 ──► 中文提示词 ──► agent ──► 中文输出
English in ──► English prompt ──► agent ──► English out
```

请求里带 `"language": "zh"`，中文那一套就会贯穿始终：CyberJu 提示词、角色
文档、技能文档、格式约定。只看主语言子标签，所以 `zh`、`zh-CN`、`zh-Hans`
和 `zh-TW` 都解析为 `zh`。没有自己那一套的语言一律回落到英文，英文也是默认值。

直接用中文写回复，而不是先写英文再渲染一遍，这才是重点。一个角色的口吻属于
这个角色本身；用中文写的措辞读起来是那个角色，而不是别人台词的忠实副本。这
也顺带让一次中文回复只需一次模型调用。

有两点需要注意：

- 翻译文档是英文原件的兄弟文件，放在以语言命名的目录下
  （`assets/character/zh/haley.md`）。每份文档各自解析，缺翻译时会回落到英文
  并打一条 warning，所以一个角色可以先在一种语言上线，之后再补翻译。
- 一个线程的历史是它当初用的那种语言。中途换语言不会重写之前的轮次，而系统
  提示词只在线程的第一轮发送，所以用英文开的线程会一直用英文回答。想换语言
  就开一个新的 `thread_id`。

唯一不随语言改变的是线路格式。模组靠 `- ` 和 `% ` 解析回复，所以两套提示词
用的是同一组 ASCII 标记，中文约定里也明确写了这一点 —— 否则模型写中文时会
顺手用全角的 `－` 和 `％`，模组认不出来。

中文那一套是参照游戏自带的中文文本和 ValleyTalk 的 `i18n/zh.json` 写的，所以
名称和语气与中文玩家在游戏里读到的保持一致 —— 鹈鹕镇是 Pelican Town，农夫是
the farmer，花舞节是 Flower Dance。新增中文文档时请沿用这套词汇；提示词里
叫鹈鹕镇、角色文档里叫别的名字，读起来就像两款游戏。

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
| `thread_id` | 这条消息属于哪次对话；状态按线程保存（`CyberJu` 忽略它） |
| `language` | `en`（默认）或 `zh`；决定用哪套提示词，见[语言](#语言) |
| `is_spouse` | 必填。这位 NPC 是不是农夫的配偶或室友；决定用哪个技能 |

`character` 要么是 `CyberJu`（会用工具的助手），要么是有角色文档的 NPC 名字；
`is_spouse` 为 true 时以农夫配偶的身份回答，为 false 时以普通村民的身份回答。
名字对 `src/stardew_agent/assets/character/` 做大小写不敏感的匹配，未知名字返回
`404`。

`is_spouse` 故意不给默认值。默认成 `false` 会让农夫自己的配偶以村民人格作答，
这看起来只是有点不像本人，而不像一个 bug；缺字段则会直接返回 `422`。
`CyberJu` 也要带这个字段，但它先按名字匹配，然后忽略它。

Agent 按 `(is_spouse, character)` 组合缓存，所以同一位村民在一个存档里作为配偶
出现、在另一个存档里作为邻居时，会保留两份各自独立的历史。

### 用法示例

同一个接口的三种用法。区别只在 `character` 和 `is_spouse`。

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

**跟一位普通村民说话**（`is_spouse: false`，对应游戏里按住 `Alt` 点击村民）：

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

```json
{
  "character": "Haley",
  "message": "- 今天下午我都在镇上拍照，光线特别好。\n% 拍的什么？\n% 听起来很有意思。\n% 下次带我一起去。"
}
```

### 回复格式

回复里带着同样的 `character`，答案在 `message` 里。配偶与村民的回复是模组能
解析的对话格式：

```json
{
  "character": "Haley",
  "message": "- I spent most of the afternoon taking photos.\n% That sounds fun.\n% What did you take pictures of?\n% Tell me more."
}
```

以 `- ` 开头的那一行是角色说的话。以 `% ` 开头的几行是玩家可以选的回复，可以
没有。CyberJu 则用普通散文作答，因为它的回复进的是聊天框而不是对话窗。

换一种语言时结构不变，只是内容跟着变 —— 因为同一份约定是用那种语言给的，而
标记在两种语言里都是 ASCII。

### 错误

未知角色返回 `404`（`detail` 是找不到的那份文档路径），缺 `is_spouse` 返回
`422`：

```json
{"detail": "No persona document at /path/to/stardew-agent/src/stardew_agent/assets/character/leo.md"}
```

```json
{"detail": [{"type": "missing", "loc": ["body", "is_spouse"], "msg": "Field required", "input": {"character": "Haley", "message": "今天下午你在做什么？", "thread_id": "haley-spring-12", "language": "zh"}}]}
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
├── mcp_client.py     # MCP stdio 客户端 -> stardew-mcp-server
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

另：本仓库之外的 HelloStardew 与 stardew-skills 都是本项目自己的部分，见上文
「主要创新」，不在此列。

还要感谢 [SMAPI](https://smapi.io/)（Pathoschild）、Harmony，以及
[Stardew Valley](https://www.stardewvalley.net/) 的作者 ConcernedApe。
