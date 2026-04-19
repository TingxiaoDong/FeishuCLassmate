---
name: batch-search-before-reading
description: Use when repeatedly searching for the same or related strings across multiple grep/read commands. Consolidate into a single comprehensive search to avoid redundant queries and session loss.
category: automation
---

## Batch Search Strategy for Codebase Investigations

1. Before making multiple searches, list ALL terms you need to find in one command.
2. Use `grep -E "term1|term2|term3"` to search multiple patterns simultaneously.
3. If reading multiple files, use `cat file1 file2 file3` instead of separate read calls.
4. After one failed search, check if the terms appeared in other files before doing another search.
5. Cache results in your context—don't re-search for information you've already found.

**Example:**
Instead of:

grep "appToken" file.ts
grep "BITABLE" config.ts
grep "tableId" setup.ts

Do:
bash
grep -rE "appToken|BITABLE|tableId" ~/path/src --include="*.ts" | head -50


**Anti-pattern:** Running 5 separate grep commands when one piped grep with multiple patterns would suffice.
