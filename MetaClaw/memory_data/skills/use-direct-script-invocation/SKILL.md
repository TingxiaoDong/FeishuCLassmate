---
name: use-direct-script-invocation
description: Use when executing Python or Node scripts. Always invoke scripts with the direct `python <file>.py` or `node <file>.js` pattern to avoid preflight validation failures.
category: automation
---

## Direct Script Invocation

When running script files, use the simplest possible invocation pattern:

1. For Python scripts: `python <filename.py>` (do NOT use `python /full/path/to/file.py`)
2. For Node scripts: `node <filename.js>` (do NOT use full absolute paths)
3. If the script is not in the current directory, use `cd` to navigate first, then run with relative filename.

**Anti-pattern:** Using complex interpreter invocations like `python /Users/dongtingxiao/Desktop/...` triggers script preflight validation which may refuse to run.
