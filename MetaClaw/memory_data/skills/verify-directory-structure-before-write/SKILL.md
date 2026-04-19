---
name: verify-directory-structure-before-write
description: When instructed to write or append to a file, always verify the parent directory exists before attempting the write operation.
category: automation
---

## Verify Directory Structure Before Write

1. Parse the target file path from the request.
2. Check if the parent directory exists using `os.path.isdir()` or equivalent.
3. If the directory does not exist, create it first with `mkdir -p` or equivalent before writing.
4. Only then proceed with the file write/append operation.
5. If the file itself doesn't exist, create it (do not fail with ENOENT).

**Example:**
bash
# Before writing to /Users/dongtingxiao/.openclaw/workspace/memory/2026-04-18.md
mkdir -p /Users/dongtingxiao/.openclaw/workspace/memory
# Then write the file


**Anti-pattern:** Calling `write` on a file path whose parent directory hasn't been verified to exist, causing ENOENT errors.
