# Code Review Request Template

Use this template when requesting code review for any changes.

---

## Pull Request Review Request

### Basic Information

**PR Title:**
> [Brief description of change]

**PR Link:**
> [URL to pull request]

**Reviewer(s) Requested:**
> [List requested reviewers]

**Related Issue/Ticket:**
> [Reference to issue tracker]

**Type of Change:**
> - [ ] Bug fix
> - [ ] New feature
> - [ ] Refactoring
> - [ ] Documentation
> - [ ] Safety-critical change
> - [ ] MetaClaw integration
> - [ ] Other: ____________

---

### Change Summary

**What does this change do?**
> [Description of functionality]

**Why is this change needed?**
> [Business/technical justification]

**How does it work?**
> [Technical explanation]

---

### Affected Components

**Layers modified:**
> - [ ] Hardware Abstraction (`src/hardware/`)
> - [ ] Robot API (`src/robot_api/`)
> - [ ] Planner (`src/planner/`)
> - [ ] Skill System (`src/skill/`)
> - [ ] Shared (`src/shared/`)
> - [ ] MetaClaw (`MetaClaw/`)
> - [ ] Frontend (`frontend/`)
> - [ ] Tests (`tests/`)

**Related modules:**
> [List specific files/modules affected]

---

### Safety Impact Assessment

**Does this change affect safety?**  Yes / No

If yes, complete the following:

**Potential failure modes:**
> [List potential failure modes]

**Safety constraints affected:**
> [List any safety constraints modified]

**Mitigation measures:**
> [How failures are prevented/handled]

**Testing performed:**
> - [ ] Unit tests pass
> - [ ] Integration tests pass
> - [ ] Simulation tests pass
> - [ ] Manual testing performed
> - [ ] Safety review completed

**Rollback plan:**
> [How to revert if issues arise]

---

### Breaking Changes

**Does this change introduce breaking changes?**  Yes / No

If yes, describe:
> [Description of breaking changes]

**Migration steps required:**
> [Steps to migrate existing code/data]

---

### Review Checklist

*For submitter: ensure all items are addressed before requesting review*

- [ ] Code follows style guidelines
- [ ] Tests added/updated for all changes
- [ ] Documentation updated if needed
- [ ] No hardcoded credentials/secrets
- [ ] All CI checks passing locally
- [ ] Related issues/tickets referenced
- [ ] Breaking changes documented
- [ ] Safety impact assessed (if applicable)

---

### Additional Notes

> [Any additional context for reviewers]

---

### For Reviewer Use

**Review completed:**  Yes / No / Partially

**Issues found:**
> [List of issues requiring resolution]

**Approval status:**
> - [ ] Approved
> - [ ] Approved with comments
> - [ ] Changes requested
> - [ ] Blocking concerns

**Reviewer signature:** _________________

**Date:** _________________

---

## Safety Review Request (If Applicable)

*Complete this section for any safety-critical changes*

**Safety reviewer assigned:**
> [Name of safety reviewer]

**Safety impact level:**
> - [ ] Critical - Must address before any deployment
> - [ ] High - Should address before merge
> - [ ] Medium - Address within sprint

**Safety concerns:**
> [List specific safety concerns]

**Safety approval:**  Yes / No / Pending

**Safety reviewer signature:** _________________

**Date:** _________________

---

## MetaClaw Integration Review (If Applicable)

*Complete this section for MetaClaw-related changes*

**MetaClaw engineer review:**  Yes / No / N/A

**Skill verification completed:**  Yes / No / N/A

**Learning bounds respected:**  Yes / No / N/A

**Notes:**
> [MetaClaw-specific review notes]

**MetaClaw engineer signature:** _________________

**Date:** _________________
