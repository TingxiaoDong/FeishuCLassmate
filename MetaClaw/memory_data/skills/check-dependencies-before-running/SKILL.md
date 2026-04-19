---
name: check-dependencies-before-running
description: Use when about to run Node.js/npm commands in a project directory. Verify dependencies and module availability first to avoid MODULE_NOT_FOUND failures.
category: automation
---

## Pre-Execution Dependency Verification

1. Before `npm run`, `node script.ts`, or `require()` calls, verify:
   - `package.json` exists in the current directory
   - `node_modules/` folder exists
   - Required packages are in `node_modules/` (quick `ls node_modules | grep <pkg>`)
2. For missing modules, run `npm install` before executing.
3. Check Node.js version compatibility if modules fail to load.
4. If errors persist, run `npm ls` to show dependency tree and identify conflicts.

**Example verification:**
bash
ls package.json node_modules/ 2>/dev/null || echo "MISSING DEPS"
npm list 2>&1 | head -20


**Anti-pattern:** Running `node script.ts` without first confirming `node_modules` contains all required packages.
