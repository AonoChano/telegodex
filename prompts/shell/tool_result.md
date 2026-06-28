---
name: tool_result
role: system
description: Shell execution result template. Placeholders filled in at runtime.
placeholders: "{tool}, {command}, {exit_code}, {timed_out}, {output}"
used_by: core/orchestrator/shell_pipeline.py build_tool_result_message()
         core/orchestrator/chat_tools.py build_tool_result_message()
---

Telegodex tool result:
tool: {tool}
command: {command}
exit_code: {exit_code}
timed_out: {timed_out}
{output}
Use this result to answer the user. If it failed, explain the failure and propose the next step.
