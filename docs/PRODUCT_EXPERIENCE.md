---
title: Product Experience
category: product
last_updated: 2026-07-13
relevance: high
summary: Final user-facing experience and interaction principles for Telegodex
related: [README.md, USAGE.md, ARCHITECTURE.md, QUICKSTART.md]
---

# Product Experience

## Startup Platform Behavior

The bot should take responsibility for Telegram-side configuration that can be changed through the Bot API. The user should not have to return to BotFather every time the project adds, removes, or renames a slash command. On startup, Telegodex should synchronize the command menu automatically, so the Telegram client shows the same commands the current code can actually handle.

Platform settings that cannot be changed through the Bot API should be detected and explained early. If Telegram reports that private-chat Threaded Mode is not enabled for the bot, Telegodex should warn configured admins during startup and tell them to enable it in BotFather. This warning should not stop the bot from running, because ordinary chat, forum-group workflows, and debugging may still be useful.

The warning must be precise. Private-chat Threaded Mode is not the same thing as forum supergroup topics. Forum groups still need Topics enabled on the group and bot admin permissions for topic management. Startup checks should help the user understand the missing platform setting without pretending that one Telegram switch controls every workbench surface.

本文描述 Telegodex 最终应该给用户的使用效果。它不解释内部模块怎么写，不要求开发者按某个类名或某个函数去实现，也不替代架构文档。它只回答一个问题：用户从拿到 Bot，到在 Telegram 里控制 AI、Codex 和后续更多 CLI Agent 时，眼前应该看到什么，手上应该怎么操作，心里应该怎么理解。

开发者读这个文件时，要把它当成产品体验的基准。代码可以换方案，模块可以迁移，命令可以扩展，具体实现可以重构，但用户看到的逻辑不能乱。Codex 的对话就应该是 Codex 的对话，普通 AI 的对话就应该是普通 AI 的对话。用户开在某个 forum topic 里的工作上下文，不应该因为代码找不到绑定就悄悄落进另一个 AI Provider。用户需要被问清楚：是在这里创建新的 Codex 会话，还是取消这次操作。

## 概述

Telegodex 是 Telegram Workbench。用户不是只想找一个会聊天的 Bot，也不是只想把几个 API key 拼在一起。用户希望把手机上的 Telegram 变成一个可以远程控制电脑上 Codex CLI 和其它 CLI AI 工作流的界面。普通 AI 对话、Codex 项目会话、Shell 命令、文件传输、审批、状态面板、Codex 自身的长期运行状态，都应该像在一个工作台里自然发生，而不是像一堆散落的 slash command。

用户启动 Telegodex 后，最基础的体验是：在 Telegram 里和不同 AI 服务商聊天，切换模型，保留上下文，收到富文本回复。更完整的体验是：用户在论坛群聊里给每个项目或每个任务开 topic，把 Codex 会话绑定到 topic 上，然后在这个 topic 里像使用一个远程开发工作间一样发消息、看输出、点审批按钮、接收运行结果、停止长任务、查看状态。

普通 Bot 私聊要一直可用。它适合问答、翻译、总结、轻量代码解释、模型切换、配置检查、查看运行状态。完整 Workbench 建议放在 Telegram forum group 里使用，因为 Telegram 的 topic 能天然承载多个项目、多个任务和多个上下文。用户把一个 topic 理解成一个工作间。AI chat topic 是 AI chat 的工作间，Codex topic 是 Codex 的工作间，未来 Claude Code 或 Shell session 也应该按同样的直觉放进各自的工作间。

用户不应该需要知道很多内部术语。用户应该能靠眼前的提示判断当前在哪里、正在和谁说话、这个话题绑定了什么、是否有任务在跑、下一步能点哪个按钮。命令可以存在，因为命令适合高级用户和应急场景。但常见动作应该通过按钮、面板、提示消息和自动识别来完成。

## 产品边界

Codex 不是 Telegodex 内部实现的 Agent，也不是普通 AI Provider 的一种。Codex 是独立的外部 CLI/runtime 进程。Telegodex 的职责是把 Telegram 变成 Codex 的移动控制界面：创建或绑定 topic、恢复 thread、显示历史和输出、转发审批、展示状态、处理停止和重试。

普通多 Provider AI chat 是辅助能力。它适合在同一个 Telegram 环境里快速问问题、翻译、总结、解释代码片段，避免用户为了一个小问题切换 App。但它不能抢占产品主轴，也不能伪装成 Codex。普通 AI chat 的上下文和 Codex thread 必须隔离。

当 Codex 自身支持后台运行、子代理、任务派发或 thread resume 时，Telegodex 应该呈现这些 Codex-owned 能力，而不是自己实现一个竞争性的 TaskHub、Cron/Webhook/Heartbeat 自动化系统或 `/tasks` 任务引擎。Telegram 端只负责让用户看见、审批、停止、恢复和定位这些 Codex 状态。

## 第一次配置和启动

用户先在自己的机器上准备 `.env`。用户需要配置从 BotFather 得到的 `TELEGRAM_BOT_TOKEN`，并配置至少一个 AI 服务商的 key。用户可以只配置 DeepSeek，也可以配置 OpenAI、Anthropic、Google、Qwen、Kimi、GLM、ERNIE，或通过自定义 Provider 接入本地和自托管服务。用户不需要一开始理解所有 Provider 的细节，只要知道至少有一个服务商可用，Bot 就能启动并回复普通 AI 消息。

用户运行 `python run.py` 后，后端会显示启动过程。用户会看到配置检查、Bot token 检查、可用 Provider、数据库位置、管理员用户、Codex 可执行文件检测、Codex app-server 启动结果等日志。启动成功时，用户看到类似 `Telegodex 启动成功` 的消息。这个时刻对用户很重要，因为它表示 Telegram 端已经可以开始交互。如果配置错误，日志应该直接告诉用户错在哪里，比如缺少 Bot token、没有配置任何 Provider、数据库无法初始化、Codex 找不到可执行文件。用户不应该在 Telegram 里盲等。

启动横幅里的版本号应该和项目版本一致。用户在命令行看到的版本、项目文件里的版本、变更记录里提到的版本，应该互相对得上。用户不应该看到代码已经是新版本，但启动横幅还写旧版本。版本号的意义不是让用户研究发布流程，而是让用户在截图、反馈、多人协作时能说清楚自己运行的是哪一版。

用户第一次给 Bot 发 `/start` 或 `/开始` 时，Bot 会创建或刷新用户记录，然后发出一个主菜单消息。主菜单不是一段长说明，而是一条可操作的面板消息。面板里应该有清楚的按钮，例如 `系统配置`、`运行状态`、`提供商设置`、`Codex菜单`、`语言设置`、`开启新对话`、`管理会话`、`帮助`。用户点按钮后，最好原地更新这条面板，而不是刷出一堆碎消息。短状态可以用 Telegram 的浮窗提示，重要结果和错误才留在聊天记录里。

用户在主菜单里点 `运行状态`，应该看到 Bot 是否在线、数据库是否正常、当前启用哪些 Provider、Codex daemon 是否已启动、当前版本号、最近一次错误的摘要。用户点 `提供商设置`，应该看到当前 Provider、当前模型、可切换的模型、temperature 等常用选项。用户不需要先背命令，再去猜某个 Provider 是否配置成功。

## 普通 Bot 私聊

用户可以直接在 Bot 私聊里发一句话，比如“帮我总结这段文字”或“把这段英文翻译成中文”。如果用户没有显式进入 Codex、Shell 或其它 Agent 模式，这条消息就按普通 AI chat 处理。Bot 会使用当前选择的 Provider 和模型，把用户消息加入当前普通对话上下文，然后返回 Telegram Rich Message。

普通 AI chat 的回复应该利用 Telegram 原生富文本能力。代码要显示成代码块，表格要显示成表格，数学公式要保留 LaTeX，折叠内容要放进 details，引用和列表要清楚。用户不应该收到一段被转义字符弄乱的 Markdown，也不应该看到公式被替换成难以复制的 Unicode 符号。

普通 AI chat 可以在私聊中持续上下文。用户发完一个问题，继续追问“详细一点”“换成日语”“给我代码版本”，Bot 应该知道这是同一段普通 AI 对话。用户点 `开启新对话` 或发送 `/new` 后，Bot 才开启新的普通对话。用户点 `管理会话` 时，应该看到当前普通对话、历史对话和可恢复选项。

普通 AI chat 和 Codex chat 的上下文必须分开。用户在普通 AI 里讨论写作，在 Codex topic 里修代码，两个上下文不能混在一起。用户切换 Provider 时，也应该尽量保留每个 Provider 自己的上下文。用户从 DeepSeek 切到另一个 Provider，不应该无缘无故污染 Codex 的 thread，也不应该让 Codex 去读取普通 AI 的历史当成项目上下文。

## 为什么完整功能建议用论坛群聊

Telegodex 支持直接在 Bot 私聊里使用，但私聊更适合普通 AI chat 和轻量管理。完整的 Workbench，尤其是 Codex、Shell、文件传输、审批、多个项目并行、长期上下文，建议放在 Telegram forum group 里使用。

用户需要自己创建一个群聊，把自己配置好 token 的 Bot 拉进去。用户打开群详情，进入管理界面，开启 Topics。群聊变成 forum group 后，用户可以给不同项目开不同 topic。一个 topic 可以叫 `Codex - Telegodex`，另一个可以叫 `AI - 文档讨论`，再另一个可以叫 `Shell - 部署机器`。用户不需要把所有工作挤在一个聊天流里。

用户给 Bot 配管理员权限时，体验应该直接。Bot 需要能创建 topic、管理 topic、删除自己产生的过期选项消息、置顶重要面板、在必要时清理临时消息。用户可以勾选 `Change group info`、`Delete Messages`、`Ban users`、`Manage Topics`、`Pin messages`，如果图省事也可以给全部权限。产品和代码都必须守住边界：这些权限是为了让工作台顺畅，不是为了做和用户意图无关的管理动作。开发者写任何会影响群成员、删除用户内容、封禁用户、改群名的行为，都应该有非常明确的用户触发和保护。

用户把 Bot 拉进群聊后，可以在群里 `@你的Bot` 随便发一条消息。后端日志会显示群聊 ID。更好的体验是，Bot 私聊会主动给管理员发一条绑定请求消息，告诉用户检测到哪个群、群名是什么、Group ID 是多少、是否要把这个群绑定为 Workbench 群。消息里带 `同意绑定` 和 `拒绝` 按钮。这个消息应该有时效，比如 10 分钟。用户 10 分钟内没操作，按钮消失，消息内容变成“绑定请求已失效，请在群里重新 @Bot 触发”。用户不应该面对一个永远有效的旧绑定按钮。

另一种配置方式也应该支持。用户可以在 Bot 私聊里打开 `/start` 主菜单，进入 `系统配置`，点击 `设置 Group ID`。Bot 发一条提示消息，让用户回复这条消息并粘贴 Group ID。用户发出 Group ID 后，Bot 校验格式和权限，成功后回复绑定完成。用户从日志或绑定请求里复制 Group ID，都应该能走通这条路径。

## 主菜单和面板

用户和 Telegodex 的大部分管理动作都应该从一条主菜单面板开始。这个面板不是网页后台的替代品，但它要承担手机端最常用的控制入口。用户打开 Bot 私聊，发送 `/start`，就能看到它。用户在群聊里需要配置或查看状态，也应该能通过按钮跳回私聊面板完成敏感操作。

主菜单应该保持短而清楚。用户看到 `系统配置`，知道这是 Bot token 之外的运行配置和群聊绑定。用户看到 `运行状态`，知道能检查 Provider、Codex daemon、数据库、版本。用户看到 `提供商设置`，知道能切换当前普通 AI Provider 和模型。用户看到 `Codex菜单`，知道能管理 Codex 会话、启动新 topic、查看当前 thread。用户看到 `管理会话`，知道能看普通 AI 对话和不同工作流会话。

用户点按钮后，面板可以原地变化。比如用户点 `Codex菜单`，同一条消息变成 Codex 面板，按钮换成 `新建 Codex Topic`、`当前会话状态`、`会话列表`、`切换工作目录`、`返回主菜单`。用户点 `返回主菜单`，面板再变回主菜单。Telegram 聊天记录不应该被十几条菜单消息刷屏。

如果某个操作只需要告诉用户“已保存”“已取消”“无变化”，Bot 可以用短暂浮窗。比如用户点了当前已经启用的 Provider，Bot 弹出“已经在使用 DeepSeek”。如果某个操作会改变长期状态，Bot 应该在聊天里留一条简短确认。比如用户绑定了新的 forum group，Bot 要留下“已绑定到群 X，Group ID: Y”。

## 普通 AI topic

用户可以在 forum group 里创建一个普通 AI topic，用来和普通 Provider 聊天。这个 topic 可以叫 `AI - 翻译`、`AI - 资料整理`、`AI - 头脑风暴`。用户在 topic 里提到 Bot 或按群聊配置发送消息，Bot 应该把它当成普通 AI chat。

普通 AI topic 的上下文属于普通 AI。用户在这个 topic 里问 DeepSeek、OpenAI 或其它 Provider，Bot 应该把这个 topic 的 `message_thread_id` 当成隔离边界。用户在另一个 topic 里问别的问题，不应该串到这里。用户在同一个 topic 里连续追问，Bot 应该保留这里的普通 AI 上下文。

普通 AI topic 不应该被 Codex handler 抢走。即使这个 forum group 里同时存在 Codex topic，只要当前 topic 没有绑定 Codex，也不是历史 Codex topic，用户发来的普通消息就应该进入普通 AI chat。用户不会理解“因为 Bot 里装了 Codex，所以所有 topic 都被 Codex 检查后丢弃”。检查可以存在，但结果必须符合用户直觉：普通 AI topic 继续普通 AI，Codex topic 继续 Codex。

## Codex topic

用户想在 Telegram 里控制 Codex 时，入口是在 forum group 里创建一个 Codex topic。用户可以发送 `/codex new`，也可以发送 `/codex resume <thread-id>` 恢复已有 Codex thread，或在 Codex 菜单里点 `新建 Codex Topic`。Bot 会创建一个新的 forum topic，名字可以包含 `Codex`、项目名、短 thread 标识或当前工作目录提示。创建或恢复完成后，Bot 会把这个 topic 和对应 Codex 会话绑定。

用户进入这个 Codex topic 后，不应该每句话都写 `/codex`。这个 topic 已经是 Codex 的工作间，用户直接发“检查一下登录逻辑”“运行测试”“修复这个失败”，Bot 就应该把消息送给 Codex。用户需要的是像在 Codex CLI 里继续同一个 thread 一样的感觉，只是输入和输出发生在 Telegram。

Codex topic 的上下文必须属于 Codex。它不能在找不到当前活动绑定时悄悄落到普通 AI chat。用户看到 topic 名、历史消息和之前的 Codex 输出，会认定这里是 Codex 工作区。如果后端发现这个 topic 曾经是 Codex topic，但当前找不到活动 thread，Bot 应该发一条选项消息，问用户是在这个 topic 创建新的 Codex 会话，还是取消。用户不点按钮时，默认效果应该是取消，也就是不做任何事。

这个选项消息应该替换旧选项。用户在同一个 Codex topic 里连续发消息，Bot 不应该留下多条互相矛盾的“创建或取消”按钮。Bot 应该删除这个 topic 下旧的同类选项消息，生成一条新的提问选项消息。用户点击 `创建新的 Codex 会话` 后，这个 topic 重新绑定 Codex。用户点击 `取消` 后，Bot 不把那条用户消息交给普通 AI，也不创建 Codex，会话保持未绑定状态。

普通 AI 对话不能接管 Codex topic。原因很简单：Codex 没有提供让用户手动替换历史上下文的接口，用户也不应该承担整理混乱上下文的成本。一个 Codex topic 如果突然由普通 AI 回复，用户会以为 Codex 看到了之前的项目状态，实际却没有。这个错觉比直接提示用户重新创建会话更糟。

用户可以在 Codex topic 里查看状态。Bot 应该能告诉用户当前 thread、工作目录、是否有 turn 正在运行、最近一次输出时间、是否有待审批请求。用户可以点 `状态`，也可以发 `/codex status`。状态消息不要太长，但要足够定位问题。用户看到状态后，应该知道现在是“可以继续发消息”“正在执行命令”“等待我审批”“daemon 不可用”“thread 已丢失需要重建”。

## Codex 私聊模式

All、Bot 私聊和普通 topic 可以作为 Codex topic 的入口，但不作为 Codex turn 的运行面。用户在这些位置发送 `/codex new` 或 `/codex resume <thread-id>` 时，Bot 应该创建新的 Codex 专属 topic；普通 `/codex <prompt>` 应提示用户先进入 Codex topic。

用户在私聊里用 Codex 时，Bot 应该明确显示当前会话状态。比如第一次启动时提示“已创建新的 Codex 会话”，恢复旧 thread 时提示“正在恢复上次 Codex 会话”，新建时提示“已开始新的 Codex 会话”。用户如果想切换工作目录，可以通过 Codex 菜单或命令完成。用户不应该在私聊里不知不觉追加到一个很久以前的 Codex thread。

私聊里普通 AI chat 和 Codex chat 也要分开。用户直接发普通消息时，进入普通 AI。用户发 `/codex` 或在 Codex 面板里操作时，进入 Codex。用户不应该因为上一条消息用了 Codex，下一条普通闲聊也自动进入 Codex，除非界面清楚显示当前处于 Codex 模式并提供退出方式。

## Codex 输出

用户给 Codex 发消息后，Bot 应该尽快给出可见反馈。最轻的反馈可以是用户消息上的 reaction，也可以是一条 draft Rich Message。用户应该知道 Codex 已收到消息、正在思考、正在读文件、正在编辑、正在执行命令，还是已经完成。

Codex 的回答应该流式显示。用户不应该等很久只看到空白。长回答可以不断更新 draft，最终再沉淀成一条完整 Rich Message。命令输出也应该进入同一个可见流里。用户让 Codex 运行测试时，应该看到测试命令开始、输出逐步出现、最后显示退出码和摘要。

Codex 的 reasoning 或中间状态可以折叠。用户需要知道 Codex 没卡住，但不一定想让思考过程占满屏幕。适合的体验是用 `<details>` 把思考摘要收起来，默认只露出“思考过程”或“运行中”的简短标题。最终答案要清楚，代码块要能复制，diff 要能看懂。

Codex 失败时不能伪装成功。用户应该看到失败状态和错误摘要。比如上下文太长、使用额度受限、命令失败、审批超时、daemon 断开，Bot 都应该说清楚。失败消息应该告诉用户下一步该做什么：重试、开启新会话、缩短输入、检查配置、重新启动 Bot，或点某个按钮恢复。

## 审批

当 Codex 想执行命令或修改文件时，用户会收到审批消息。审批消息应该出现在对应 Codex topic 里，而不是跑到群聊主频道，也不是跑到 Bot 私聊里让用户找不到。用户在哪里发起 Codex 工作，审批就应该在哪里出现。

审批消息要让用户能判断风险。命令审批要显示要执行的命令、工作目录、触发原因和可选决策。文件修改审批要显示文件路径和 diff 摘要。用户不应该看到“unknown file”然后被要求盲点同意。可选按钮应该跟实际可用决策一致，比如只允许本次同意、允许本会话、拒绝、取消，就只显示这些按钮。

审批有超时。用户长时间不点，Bot 应该自动拒绝，并在原审批消息上显示已超时。用户回来看时，能知道这次操作已经不会继续执行。用户如果仍想执行，可以重新发消息或让 Codex 重试。

用户点审批按钮后，Bot 应该给出即时反馈。短反馈可以是浮窗“已批准”“已拒绝”。审批消息本身也应该变成最终状态，避免用户和协作者重复点击。多人在同一个 topic 工作时，大家应该能看见某个审批已经被处理。

## Shell 和工具控制

用户可以在工作流里执行 shell 命令。高级用户可以用 `!` 前缀直接发原始命令。普通用户可以用自然语言说“运行测试”“列出最近修改的文件”“查看当前目录”。最终体验里，自然语言命令不应该直接静默执行。Bot 应该给出一个候选命令，并显示 `运行`、`编辑`、`取消`。

危险命令必须先确认。用户发出删除、格式化、覆盖、清理这类命令时，Bot 应该拦住并明确说明风险。用户点击确认后才执行。这个确认要在当前 topic 里完成，并且要有超时和取消。

命令运行时，用户应该能停止。Codex 或 Shell 正在跑时，topic 里可以出现临时控制条，按钮包括 `Stop`、`Live`、`Last Reply`、`Status`。用户不想用按钮，也可以用 `/stop`、`/live`、`/last`、`/status`。按钮和命令是同一件事的两个入口，不应该有一边能做、一边做不了的差异。

Live 视图应该让用户知道长任务还活着。用户点 `Live` 后，Bot 可以定期刷新终端状态或输出摘要。用户点 `Stop` 后，Live 停止。Live 不应该无限刷新刷屏，也不应该在任务结束后继续更新。

## 文件发送和目录浏览

用户可以让 Bot 从工作目录发送文件。用户发 `/send path/to/file`，Bot 检查路径是否在允许范围内、文件是否存在、大小是否合适、是否命中敏感文件规则。安全通过后，Bot 把文件发到当前聊天或 topic。

用户不记得文件名时，可以发 `/send` 打开目录浏览。Bot 用内联按钮显示当前目录的文件和子目录，支持上一页、下一页、上一级。用户点文件名，Bot 发送文件。用户点目录名，Bot 进入目录。这个体验应该像一个轻量文件选择器，不需要用户在手机上输入很长路径。

敏感文件不能被发送。`.env`、密钥、证书、数据库、日志、被 gitignore 排除的文件，都应该被保护。用户请求发送这些文件时，Bot 应该拒绝并说明原因。拒绝消息要短，但不能含糊。用户应该知道是路径越界、文件太大、命中敏感规则，还是没有权限。

## 会话管理

用户需要能查看当前有哪些会话。普通 AI 会话、Codex 会话、未来的 Claude Code 会话，以及 Codex/CLI runtime 自身暴露的运行状态，都应该有一个清楚的管理入口。用户点 `管理会话` 后，看到活跃会话列表、最近更新时间、所在 chat/topic、当前 Provider 或外部 runtime、是否正在运行。

用户可以开启新普通对话，也可以开启新 Codex topic。两者不是同一个动作。`开启新对话` 对普通 AI 有意义，`新建 Codex Topic` 对 Codex 有意义。界面文案要让用户知道自己正在创建哪一种上下文。

用户可以归档或结束会话。归档后，旧会话不再接收新消息，但历史仍可查看。用户在旧 Codex topic 里继续发消息时，Bot 应该提示这个 topic 已归档，并提供创建新 Codex 会话或取消，而不是自动恢复一个用户以为已经结束的工作。

未来如果出现命名会话能力，它应该服务于 Telegram topic 和外部 Codex thread 的绑定、别名和恢复，而不是在 Bot 内部创建一套与 Codex 无关的 Agent 上下文。topic 仍然是 Telegram 里最直观的工作间；命名只应该帮助用户找到、恢复或重命名工作间。

## 长时间运行的 Codex 工作

用户会希望把长时间工作留给 Codex 执行，同时继续在 Telegram 里观察状态。比如“跑完整测试，失败时总结原因”或“继续这个重构，等需要审批时提醒我”。这类工作应该优先由 Codex 或对应外部 CLI runtime 自己管理。Telegodex 不应该另起一个 Bot-owned TaskHub 来冒充 Codex 的后台任务系统。

当 Codex 暴露长期运行、后台工作、子代理或任务派发状态时，结果应该回到发起它的 Codex topic。Telegram 端需要显示任务是否还活着、最近输出、是否等待审批、是否失败、能否停止或恢复。用户不需要关心这些状态来自 Codex app-server、Codex CLI 还是未来某个官方接口；但用户必须知道这仍然是 Codex 的工作，不是普通 AI chat 的工作。

如果 Codex 暂时没有提供某种后台能力，Telegodex 应该诚实地呈现当前 turn 的运行状态，而不是自己发明 `/tasks`、Cron、Webhook、Heartbeat 或子代理系统来绕过它。未来若增加相关入口，命名也应该指向 Codex-owned 状态，例如“Codex 活动”或“当前 Codex 运行”，而不是暗示 Bot 有独立任务引擎。

## 多人协作

Telegodex 要支持多人在同一个 forum group 里协作。用户 A 创建 Codex topic，用户 B 在里面继续提问，审批消息和输出都留在这个 topic。团队成员看到同一条历史，就能理解当前工作进度。

多人协作时，Bot 要避免制造不确定性。某个 topic 绑定了 Codex，就一直是 Codex，除非用户明确归档或重建。某个 topic 是普通 AI，就一直是普通 AI，除非用户明确把它绑定到某个 Agent。Bot 不应该因为一个用户发了某个命令，就让整个 topic 的语义变得模糊。

权限和敏感操作要尊重管理员设置。不是所有群成员都应该能改系统配置、切换全局 Provider、绑定 Group ID、审批高风险命令。普通消息可以开放给更多人，配置和危险操作可以限制给管理员或允许列表。用户被拒绝时，Bot 应该告诉他没有权限，而不是装作没收到。

## 错误和恢复

用户遇到错误时，Bot 要讲人话。Provider key 错误、Provider 网络失败、模型名不可用、Telegram draft 不支持、Codex daemon 未启动、Codex thread 恢复失败、审批超时、文件发送被拒绝，每一种错误都应该尽量给出下一步。

如果 draft 不可用，Bot 应该降级到普通消息编辑或最终消息发送。用户不需要知道 Telegram API 哪个能力不可用，只需要看到消息没有丢。如果某个 peer 不支持 draft，Bot 应该记住，不要每次都尝试失败再刷日志。

如果 Codex daemon 崩溃，Bot 应该尝试恢复，并在状态面板里显示恢复结果。恢复失败时，用户应该看到“Codex 暂不可用”，而不是普通 AI 突然接管 Codex topic。Codex 暂不可用就是 Codex 暂不可用，不能用别的 Provider 冒充。

如果 Bot 重启，已有会话应该尽量恢复。普通 AI 会话继续普通 AI。Codex topic 恢复到对应 thread。恢复成功时可以给轻提示。恢复失败时，要问用户创建新会话还是取消。用户不应该因为重启丢失 topic 语义。

## 语言和文案

用户可以在语言设置里切换界面语言。命令可以保持英文，但按钮和提示要尽量用用户选择的语言。中文用户看到中文按钮，日本语用户看到日本语按钮，英文用户看到英文按钮。错误消息和审批消息也应该跟随语言设置。

文案要短，但不能含糊。`失败了` 不够。`Provider 请求失败，请检查 API key、base URL 或模型名` 更有用。`没有绑定` 不够。`这个 topic 曾经是 Codex topic，但当前没有活动 Codex 会话。要在这里创建新的 Codex 会话吗？` 更符合用户理解。

界面里不要用内部实现词吓用户。用户不需要知道某个 handler、bucket、transport、JSON-RPC queue 的细节。可以说“当前 Codex 会话”“当前工作目录”“当前 topic”“当前 Codex 运行”。只有在调试面板、日志或开发者文档里才展示内部标识。

## 开发时不能偏离的直觉

一个 Telegram topic 对用户来说就是一个上下文容器。用户在 topic 里看到的历史，决定了用户认为自己正在和谁对话。代码的路由必须尊重这个直觉。

Codex topic 应该只进入 Codex。找不到当前 thread 时，问用户创建新的 Codex 会话还是取消。取消就是不做事。用户不点按钮，也等同不做事。

普通 AI topic 应该进入普通 AI。它没有绑定 Codex，也不是历史 Codex topic，就不要被 Codex 拦住。

普通 AI、Codex、Shell、未来的 Claude Code 都应该有各自上下文。跨 Provider 或跨外部 runtime 的切换可以在同一个 Workbench 里发生，但不能偷偷共享彼此的历史。

主菜单、状态面板、审批消息、控制条、错误提示，都要帮助用户判断当前状态。用户能从 Telegram 里看懂发生了什么，就不会去猜日志，也不会把一个上下文误当成另一个上下文。

开发者改代码时，如果某个改动会让 Codex topic 回落普通 AI，会让普通 AI topic 被 Codex 吃掉，会让审批消息跑出当前 topic，会让启动版本和项目版本不一致，会让用户看不到 Codex 长时间运行状态，就应该先停下来重新设计。产品体验以本文为准。
