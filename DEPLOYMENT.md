# Stardew Agent 从零部署指南

本文面向没有参与开发的人，目标是在 **macOS + Steam + Stardew Valley** 上把
CyberJu / Stardew Agent 跑起来。

所有命令以当前仓库实际代码为准。当前可用的部署方式是 **Terraform + Docker**
（在宿主机本地构建镜像），不要求用户 clone / build HelloStardew 的 C# 源码。

---

## 1. 架构总览

```text
Stardew Valley
  └─ SMAPI
       └─ HelloStardew (GitHub Release v0.1.0)
            └─ HTTP API 监听 :8788 (BindAddress "+")

Docker / Terraform
  ├─ stardew-postgres       :15432 -> 5432   # LangGraph checkpoint
  ├─ stardew-mcp-server     :8001            # MCP Streamable HTTP
  │    └─ 调 HelloStardew: http://host.docker.internal:8788
  └─ stardew-agent          :8000            # FastAPI
       ├─ 调 MCP:   http://mcp:8001/mcp
       ├─ 调 DB:    postgres:5432/stardew
       └─ 调 LLM:   https://api.deepseek.com
```

HelloStardew 的 `AgentEndpoint` 默认是 `http://127.0.0.1:8000/chat`，正好指向
Terraform 发布到宿主机 8000 端口的 agent。

---

## 2. 环境要求

| 项目 | 要求 | 说明 |
| --- | --- | --- |
| macOS | 当前开发环境为 macOS | 命令按 macOS + Steam 路径编写 |
| CPU | Apple Silicon / Intel 均可 | 本项目的 Docker 镜像和 Terraform 均无架构相关分支；Docker Desktop 会自动选择 arm64 / amd64 |
| Steam + Stardew Valley | 已安装并能正常启动 | 路径见下文 |
| SMAPI | 4.0.0 或更高 | HelloStardew 的 `MinimumApiVersion` 是 `4.0.0` |
| Docker Desktop | 已安装并启动 | agent / MCP / Postgres 都跑在 Docker 里 |
| Terraform | 已安装 | 当前没有 docker-compose 文件，编排用 Terraform |
| Git | 已安装 | 用于 clone `stardew-agent` 和 `stardew-mcp-server` |
| Python | 宿主机**不需要** | 依赖装在 Docker 镜像内 |
| PostgreSQL | 宿主机**不需要** | Postgres 由 Terraform 启动在 Docker 里 |

### 安装 Docker Desktop

从 https://www.docker.com/products/docker-desktop/ 下载安装，启动后确认：

```bash
docker version
```

### 安装 Terraform

推荐官方安装器或 Homebrew：

```bash
brew install hashicorp/tap/terraform
terraform version
```

### 安装 Git

macOS 一般自带；如果没有：

```bash
xcode-select --install
```

---

## 3. 安装 Stardew Valley + SMAPI

1. 在 Steam 中安装 Stardew Valley，并先正常启动一次，让 Steam 生成游戏目录。
2. 到 https://smapi.io 下载 SMAPI。
3. 解压后运行 `install on Mac.command`，按提示选择 Stardew Valley 目录并安装。
4. 安装器通常会配置 Steam 启动选项，使“开始游戏”直接通过 SMAPI 启动。
   如果没配置，可以手动运行：

```bash
STARDEW_DIR="$HOME/Library/Application Support/Steam/steamapps/common/Stardew Valley/Contents/MacOS"
"$STARDEW_DIR/StardewModdingAPI"
```

---

## 4. 安装 HelloStardew（GitHub Release，不 clone 源码）

1. 下载 Release `v0.1.0`：

```bash
curl -LO https://github.com/HeptaneL/HelloStardew/releases/download/v0.1.0/HelloStardew.0.1.0.zip
unzip HelloStardew.0.1.0.zip
```

2. 把解压出的 `HelloStardew` 文件夹放进 SMAPI 的 `Mods` 目录：

```bash
STARDEW_DIR="$HOME/Library/Application Support/Steam/steamapps/common/Stardew Valley/Contents/MacOS"
mkdir -p "$STARDEW_DIR/Mods"
cp -R HelloStardew "$STARDEW_DIR/Mods/"
```

3. 确认目录结构（`manifest.json` 和 `HelloStardew.dll` 必须直接在 `HelloStardew` 下）：

```text
Mods/
└─ HelloStardew/
   ├─ manifest.json
   ├─ HelloStardew.dll
   └─ i18n/
      ├─ default.json
      └─ zh.json
```

4. 首次通过 SMAPI 启动游戏后，会自动生成
   `Mods/HelloStardew/config.json`。生成内容默认 `BindAddress` 为 `"+"`。

> GMCM（Generic Mod Config Menu）是可选依赖，不装也能运行；它只提供游戏内
> 修改配置的界面，不是 Agent 启动的硬依赖。

---

## 5. 配置 HelloStardew

配置文件路径（Steam 默认安装）：

```text
~/Library/Application Support/Steam/steamapps/common/Stardew Valley/Contents/MacOS/Mods/HelloStardew/config.json
```

默认内容：

```json
{
  "BindAddress": "+",
  "Port": 8788,
  "EnableSpouseConversation": true,
  "InitiateTypedDialogueKey": "LeftAlt",
  "AgentEndpoint": "http://127.0.0.1:8000/chat",
  "AgentTimeoutSeconds": 30,
  "OfferTypedResponse": true
}
```

| 字段 | 默认值 | 是否必须修改 | 说明 |
| --- | --- | --- | --- |
| `BindAddress` | `+` | 否 | `+` 表示接受任意 Host，Docker 里的 MCP 才能通过 `host.docker.internal` 访问。若改成 `127.0.0.1`，Docker 部署会连不上 |
| `Port` | `8788` | 否 | 若被占用，改这里，并同步改 `terraform.tfvars` 的 `stardew_api_url` |
| `EnableSpouseConversation` | `true` | 否 | NPC/配偶 AI 对话总开关 |
| `InitiateTypedDialogueKey` | `LeftAlt` | 否 | 按住此键点击村民输入自定义对话 |
| `AgentEndpoint` | `http://127.0.0.1:8000/chat` | 否 | 指向 agent。Terraform 默认发布 8000 端口，无需改 |
| `AgentTimeoutSeconds` | `30` | 否 | 调 agent 的超时秒数 |
| `OfferTypedResponse` | `true` | 否 | 是否提供“自己打字”选项 |

> 没有安装 GMCM 时，手动改 `config.json` 后需要**重启游戏**才生效。
> 使用 GMCM 修改则在关闭菜单时立即生效。

---

## 6. 配置 DeepSeek API

Terraform 部署**只读取 `terraform.tfvars`**，不读取 `.env`。

```bash
cd ~/stardew/stardew-agent/terraform
cp terraform.tfvars.example terraform.tfvars
```

编辑 `terraform.tfvars`，至少填写：

```hcl
openai_api_key = "sk-..."
```

可选：

```hcl
model    = "deepseek-flash"
base_url = "https://api.deepseek.com"
```

说明：

- 不要把 API Key 写进仓库或 `.env.example`。
- `terraform.tfvars` 已被 `terraform/.gitignore` 忽略。
- 如果 Key 为空，agent 容器会在导入 `ChatOpenAI` 时报
  `OpenAIError: Missing credentials` 并反复重启。

---

## 7. 获取 Agent 与 MCP Server 代码

Terraform 会从**本地相邻目录**构建镜像，因此两个仓库必须放在同一父目录下：

```text
~/stardew/
├─ stardew-agent/
└─ stardew-mcp-server/
```

执行：

```bash
mkdir -p ~/stardew
cd ~/stardew
git clone https://github.com/HeptaneL/stardew-agent.git
git clone https://github.com/HeptaneL/stardew-mcp-server.git
```

> 这是当前实现的一个硬约束：`terraform/mcp.tf` 用
> `../../stardew-mcp-server` 作为 Docker build context。如果两个仓库不是
> 兄弟目录，`terraform apply` 会在构建 MCP 镜像时失败。

---

## 8. 用 Terraform 启动 Postgres + MCP Server + Agent

```bash
cd ~/stardew/stardew-agent/terraform
cp terraform.tfvars.example terraform.tfvars
# 编辑 terraform.tfvars，至少填 openai_api_key

terraform init
terraform apply
```

首次 `apply` 会：

1. 拉取 `postgres:16-alpine`；
2. 本地构建 `stardew-mcp-server:latest`；
3. 本地构建 `stardew-agent:latest`；
4. 创建三个容器并等待健康检查通过。

关键变量（都有默认值，通常不需要改）：

| 变量 | 默认值 | 说明 |
| --- | --- | --- |
| `openai_api_key` | 空 | **必须填** |
| `model` | `deepseek-flash` | OpenAI 兼容模型名 |
| `base_url` | `https://api.deepseek.com` | OpenAI 兼容 API 地址 |
| `stardew_api_url` | `http://host.docker.internal:8788` | MCP 容器访问 HelloStardew 的地址 |
| `agent_port` | `8000` | agent 宿主机端口 |
| `mcp_port` | `8001` | MCP 宿主机端口 |
| `postgres_port` | `15432` | Postgres 宿主机端口 |
| `postgres_user` / `postgres_password` / `postgres_db` | `stardew` / `stardew` / `stardew` | 仅容器内部使用 |

确认三个容器都 healthy：

```bash
docker ps --filter name=stardew
```

期望输出包含：

```text
stardew-agent         Up ... (healthy)   0.0.0.0:8000->8000/tcp
stardew-mcp-server    Up ... (healthy)   0.0.0.0:8001->8001/tcp
stardew-postgres      Up ... (healthy)   0.0.0.0:15432->5432/tcp
```

停止 / 销毁：

```bash
terraform destroy
```

---

## 9. 启动 Stardew + SMAPI + HelloStardew

```bash
STARDEW_DIR="$HOME/Library/Application Support/Steam/steamapps/common/Stardew Valley/Contents/MacOS"
"$STARDEW_DIR/StardewModdingAPI"
```

或在 Steam 中点击“开始游戏”（若 SMAPI 安装器已配置启动选项）。

SMAPI 控制台出现类似输出即表示 HelloStardew 已加载：

```text
Calendar API ready. Try: curl http://127.0.0.1:8788/health
```

载入存档后，除 `/health` 外的接口才会返回真实游戏数据；未载入存档时这些接口
会返回 `503 no_save_loaded`。

---

## 10. 端到端验证

按顺序验证：

### 10.1 HelloStardew

```bash
curl http://127.0.0.1:8788/health
```

期望返回 JSON，且 `"ok": true`。

### 10.2 三个容器

```bash
docker ps --filter name=stardew
```

### 10.3 MCP 容器能否访问 HelloStardew

```bash
docker exec stardew-mcp-server python -c "import urllib.request; print(urllib.request.urlopen('http://host.docker.internal:8788/health', timeout=5).status)"
```

期望输出 `200`。

### 10.4 Agent API（CyberJu）

```bash
curl -s http://127.0.0.1:8000/chat \
  -H 'Content-Type: application/json' \
  -d '{"character":"CyberJu","message":"今天天气怎么样？","thread_id":"guide-test-1","language":"zh","is_spouse":false}'
```

期望返回 200，`message` 为 CyberJu 的回答。若存档未载入，回答会说明拿不到
游戏状态，但 HTTP 状态仍是 200。

### 10.5 游戏内验证

- 聊天框输入 `cj 今天该做什么？`，CyberJu 应读取存档并回答。
- 按住 `Alt` 点击任意村民，输入一句话，应得到带可选回复的对话。

---

## 11. 常见问题

### HelloStardew API 无法连接 / 容器返回 404

```bash
curl http://127.0.0.1:8788/health
```

- 宿主机 curl 都失败：游戏 / SMAPI / HelloStardew 没启动或端口不对。
- 宿主机 curl 成功，但 MCP 容器返回 404：检查 `config.json` 的
  `BindAddress` 是否为 `"+"`。如果不是，改成 `"+"` 后重启游戏。
- 如果之前手动改过 `config.json`，没有 GMCM 时不会热生效，必须重启游戏。

### 8788 端口被占用

1. 改 `Mods/HelloStardew/config.json` 的 `Port`，例如 `8789`。
2. 改 `terraform.tfvars`：

```hcl
stardew_api_url = "http://host.docker.internal:8789"
```

3. `terraform apply`，重启游戏。

### BindAddress 应该是什么

- Terraform / Docker 部署：必须是 `"+"`。
- 仅在宿主机本地跑 MCP（stdio）且不经过 Docker：`"127.0.0.1"` 也可以。
- 不要用 `"0.0.0.0"`：`HttpListener` 不支持，会报 `The request is not supported`。

### SMAPI 找不到 mod

确认结构：

```text
Mods/HelloStardew/manifest.json
Mods/HelloStardew/HelloStardew.dll
```

常见错误是解压后多套了一层：

```text
Mods/HelloStardew/HelloStardew/manifest.json   # 错误
```

把内层 `HelloStardew` 文件夹移到 `Mods/` 下。

### MCP Server 无法启动

```bash
docker logs stardew-mcp-server
```

- 端口 `8001` 被占用：改 `terraform.tfvars` 的 `mcp_port`。
- `STARDEW_API_URL` 不通：先按 10.3 验证。

### DeepSeek API Key 错误

```bash
docker logs stardew-agent
```

- 看到 `OpenAIError: Missing credentials`：`openai_api_key` 没填。
- 看到 401 / auth 错误：Key 不正确或已失效。
- 改 `terraform.tfvars` 后重新 `terraform apply`。

### PostgreSQL 无法连接

```bash
docker logs stardew-postgres
docker logs stardew-agent
```

- 宿主机已有 5432 端口：Terraform 默认用 `15432`，一般不会冲突。
- 如果 `15432` 也被占用，改 `postgres_port` 后 `terraform apply`。
- 数据库卷损坏时，可以清空后重建：

```bash
terraform destroy
docker volume rm stardew-postgres-data
terraform apply
```

### LangGraph checkpoint 初始化失败

Agent 启动时会自动建表；失败通常是因为 Postgres 还没就绪或连不上。Terraform
已经用健康检查和 `depends_on` 保证顺序，正常情况下不需要手动处理。若仍失败，
看 `docker logs stardew-agent` 里的 `PoolTimeout` / `Connection refused`，按
“PostgreSQL 无法连接”排查。

### macOS 权限问题

按住 `Alt` 点击村民没反应时，检查：

- 系统设置 → 隐私与安全性 → 辅助功能，允许终端 / Steam /
  StardewModdingAPI。
- 键盘监听可能需要“输入监控”权限。

### Steam / Stardew 路径问题

默认路径：

```text
~/Library/Application Support/Steam/steamapps/common/Stardew Valley/Contents/MacOS
```

如果不是 Steam 版或自定义过库目录，用实际游戏目录替换上述路径。`Mods` 就在
`Contents/MacOS` 下。

---

## 附：宿主机手动运行（非 Terraform，可选）

以下命令仅用于调试或不用 Docker 的场景。宿主机手动运行 agent 时仍需要一个
可达的 PostgreSQL（可以用 Terraform 启动的 `localhost:15432`，也可以自建）。
若使用 Terraform，则忽略本附录。

### MCP Server（stdio，默认）

```bash
cd ~/stardew/stardew-mcp-server
uv sync
STARDEW_API_URL=http://127.0.0.1:8788 uv run stardew-mcp-server
```

### MCP Server（Streamable HTTP）

```bash
cd ~/stardew/stardew-mcp-server
uv sync
MCP_TRANSPORT=streamable-http \
MCP_HOST=127.0.0.1 \
MCP_PORT=8001 \
MCP_HTTP_PATH=/mcp \
STARDEW_API_URL=http://127.0.0.1:8788 \
uv run stardew-mcp-server
```

### Agent（宿主机）

需要宿主机 Python 3.12+、uv，以及一个可达的 PostgreSQL。

```bash
cd ~/stardew/stardew-agent
cp .env.example .env
# 编辑 .env
uv sync
uv run uvicorn stardew_agent.api:app --host 127.0.0.1 --port 8000
```

`.env` 必填项：`MODEL`、`BASE_URL`、`OPENAI_API_KEY`、`DATABASE_URL`。
`STARDEW_MCP_TRANSPORT=stdio` 时还需要 `STARDEW_MCP_PATH`。
