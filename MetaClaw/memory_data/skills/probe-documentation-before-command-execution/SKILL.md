---
name: probe-documentation-before-command-execution
description: Use when exploring tool or system capabilities. Always check built-in help/docs (--help, -h, README) before using exec commands to discover functionality.
category: automation
---

## Probe Documentation Before Executing Discovery Commands

When you need to understand what tools, commands, or capabilities are available, consult documentation first.

**Step-by-step:**
1. Check if the tool has `--help` or `-h`: `openclaw tools --help`
2. Look for README or docs: `ls *.md` in relevant directories
3. Only if docs are insufficient, use targeted `exec` calls
4. Avoid multiple consecutive `exec` calls for discovery

**Anti-pattern:** Running multiple `exec` calls like `openclaw tools list | grep` then `openclaw --help | grep` then `ls .env*` in sequence without consulting docs first. Each exec call is expensive and may expose file contents unnecessarily.

**Better pattern:**
bash
openclaw tools --help  # Get overview
# Then if specific tool needed:
openclaw tools feishu --help


**Anti-pattern:** Blind grep through output before understanding the structure.
