---
title: "🛠️ Codex 桥接"
order: 4
---

# Codex 桥接

Codex 桥接把 Telegodex 变成 **Codex CLI 的远程控制台**。它不是又一家
AI 服务商:Codex 以本地子进程方式运行,Telegodex 通过 JSON-RPC 驱动它,
把输出流式回传到 Telegram,并把每一条审批请求路由到你可以手机点按的
内联按钮上。

把它想象成一个远程终端:Codex 在你的机器上干重活,你在任何地方监督它。

---

## 它不是什么

Codex 桥接 **不是**模型服务商。它不调用 OpenAI 兼容的对话接口,而是在
本地启动 `codex app-server` 进程,通过 stdio 与之通信,并把它的智能体
能力(文件编辑、Shell 执行、技能调用)暴露给 Telegram。

| 维度 | AI 服务商 | Codex 桥接 |
|---|---|---|
| 运行位置 | 远程 API | 本地子进程 |
| 职责 | 对话补全 | 智能体工作、文件编辑、Shell |
| 传输 | HTTPS | stdio 上的 JSON-RPC |
| 审批 | 不适用 | Telegram 内联按钮 |

---

## 调用 Codex

基础命令是 `/codex <提示>`:

- 在私聊中,它启动一次独立的 Codex 回合。
- 在论坛超级群组中,使用 `/codex new` 创建并绑定一个全新的 Codex 话题。
  话题内的每条消息都会延续同一个 Codex 会话,无需再加 `/codex` 前缀。

Codex 绑定的话题是排他的——绝不会回退到普通 AI 对话。一个没有活跃线程的
历史 Codex 话题会提示你开启新会话或取消。

---

## 指令前缀

在 Codex 会话中,消息的首字符决定路由方式:

| 前缀 | 含义 | 示例 |
|---|---|---|
| `/` | 斜杠命令(Codex 技能) | `/status` |
| `!` | 原始 Shell 命令 | `!ls -la` |
| `@` | 文件路径查询 | `@src/main.py` |
| (无) | 普通自然语言提示 | `重构 auth 模块` |

通过前缀,你不用离开键盘就能告诉 Telegodex:"我要调用技能,而不是聊天"。

---

## 审批

当 Codex 想执行 Shell 命令或修改文件时,Telegodex 会把完整提案以
内联键盘形式展示:

- **✅ 同意** —— 让它执行
- **✅ 本会话内同意** —— 本会话内预批准类似动作
- **❌ 拒绝** —— 退回,让 Codex 调整策略

若你迟迟不响应,审批会自动超时,默认安全拒绝。超时时长可通过
`CODEX_APPROVAL_TIMEOUT` 配置。

---

## 流式输出

Codex 输出会边产生边流入对话:

1. Telegodex 打开一条草稿消息,token 到达即更新。
2. stderr 行单独上浮,你能看到告警与错误。
3. 回合结束时,最终 Markdown 通过富消息 API 重新渲染——表格、代码块、
   LaTeX 全部原生呈现。

每个活跃回合下方都会出现 **⏹ 停止** 内联按钮,点按即可中途打断 Codex。

---

## Shell 提案

`/shell` 命令让你用自然语言请 AI 提议一条 Shell 命令,然后一键通过
Codex 执行:

- `/shell 找出 logs 目录下的大文件` —— AI 提议,你批准
- `/shell !du -sh logs/*` —— 直接执行,跳过提议
- `/shell -- git status` —— 字面命令,不经过 AI

这是从"我想要这个结果"到"它已经在跑"的最短路径。

---

## 截图

`/screenshot` 捕获 Codex 当前所在终端窗口,并以图片形式发送。当你想
核对 Codex 此刻正在看什么——文件列表、编辑器状态、构建输出——而不
离开 Telegram 时使用它。

---

## 配置

Codex 桥接会从 `PATH` 与常见安装路径自动探测 `codex` 可执行文件。仅
在需要覆盖时设置以下环境变量:

| 变量 | 用途 |
|---|---|
| `CODEX_EXECUTABLE_PATH` | 强制指定 Codex 二进制路径 |
| `CODEX_DAEMON_AUTO_START` | 机器人启动时是否自动启动守护进程 |
| `CODEX_DAEMON_MAX_RESTARTS` | 子进程崩溃后的重启次数上限 |
| `CODEX_APPROVAL_TIMEOUT` | 审批自动拒绝前的秒数 |

守护进程是常驻的:一旦启动,跨回合持续运行,会话状态得以保留。
