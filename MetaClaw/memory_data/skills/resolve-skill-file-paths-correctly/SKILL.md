---
name: resolve-skill-file-paths-correctly
description: When looking up skill files for execution, use the correct workspace-relative path and verify the skill exists before reading.
category: agentic
---

## Resolve Skill File Paths Correctly

1. Skills should be located relative to the current workspace root, NOT using `../` navigation outside it.
2. Use the standard skill lookup path: `{workspace}/skills/{skill-name}/SKILL.md`
3. Before reading a skill file, verify it exists using a glob or list operation.
4. If the exact skill path is unknown, search using `find` within the workspace directory only.
5. If no matching skill is found, report the failure clearly and suggest available alternatives.

**Example:**
bash
# Correct approach
ls {workspace}/skills/conduct-lab-tour/
# If not found, search:
find {workspace}/skills -name "*.md" | grep -i temi


**Anti-pattern:** Using `../Desktop/...` paths that resolve outside the workspace, causing ENOENT errors and incorrect skill discovery.
