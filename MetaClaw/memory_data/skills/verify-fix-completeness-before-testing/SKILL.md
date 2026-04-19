---
name: verify-fix-completeness-before-testing
description: Use after making code fixes to verify the change is complete and logically sound before running tests, preventing wasted test cycles on incomplete fixes.
category: automation
---

## Verify Fix Completeness Before Testing

1. **Review the entire modified function/block** end-to-end, not just the edited lines
2. **Check for downstream dependencies**: verify all callers use the fix correctly
3. **Validate data flow**: ensure inputs/outputs are correctly transformed
4. **Run static checks** (syntax, type hints, linters) before executing runtime tests
5. **Document expected behavior** in a comment before testing

python
# Before testing LOCATION_NAMES fix, verify:
# 1. resolve_location() handles all keys correctly
# 2. All callers pass normalized lowercase keys
# 3. Chinese output format matches Temi API expectations


**Anti-pattern:** Editing one line and immediately running tests without confirming the fix addresses the root cause holistically.
