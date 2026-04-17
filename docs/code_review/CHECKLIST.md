# Code Review Checklist

## General Requirements (All Layers)

### Code Quality
- [ ] Code follows PEP 8 style guidelines (Python) / ESLint rules (TypeScript)
- [ ] No hardcoded credentials, API keys, or secrets
- [ ] No placeholder/TODO comments without issue tracking
- [ ] Proper error handling with meaningful error messages
- [ ] No commented-out code blocks
- [ ] Consistent naming conventions throughout
- [ ] Functions/modules have clear, single responsibility

### Documentation
- [ ] Public APIs have docstrings
- [ ] Complex logic has inline comments explaining "why" not "what"
- [ ] README updated if adding new modules/dependencies
- [ ] Type hints present for Python code
- [ ] Interface contracts documented

### Testing
- [ ] Unit tests added/updated for changed code
- [ ] Test coverage maintained or improved
- [ ] All tests pass locally before PR submission
- [ ] Integration tests added for multi-layer changes

### Security
- [ ] No direct robot hardware access outside abstraction layers
- [ ] Input validation on all external data
- [ ] No SQL injection vulnerabilities
- [ ] No exposed sensitive endpoints
- [ ] Proper authentication/authorization checks

---

## Layer-Specific Requirements

### Layer 1: Hardware Abstraction (`src/hardware/`)
- [ ] All hardware access goes through defined interface
- [ ] Simulation mode available for all hardware operations
- [ ] Safety limits enforced at hardware level
- [ ] Error handling for hardware failures
- [ ] No direct motor/sensor commands without validation
- [ ] RobotSimulator available for testing IRobotAPI implementations

### Layer 2: Robot API (`src/robot_api/`)
- [ ] All commands validated before forwarding to hardware
- [ ] Safety constraints checked on every command
- [ ] Proper timeout handling for all operations
- [ ] State machine transitions are atomic
- [ ] Emergency stop functionality verified
- [ ] Joint/velocity limits enforced per ARCHITECTURE.md
- [ ] IRobotAPI interface fully implemented: move_joints, move_pose, move_linear, set_gripper, get_world_state, execute_skill, stop

### Layer 3: Planner (`src/planner/`)
- [ ] Path planning considers safety constraints
- [ ] Collision detection implemented
- [ ] Resource limits enforced
- [ ] Plan validation before execution
- [ ] Rollback capability for failed plans
- [ ] SkillRequest properly formatted per interface contract
- [ ] MetaClaw integration follows isolation requirements

### Layer 4: Skill System (`src/skill/`)
- [ ] Skill schemas validated before loading
- [ ] Skill isolation prevents cross-contamination
- [ ] MetaClaw integration follows approved patterns
- [ ] Skill parameters sanitized
- [ ] Skill execution can be interrupted safely
- [ ] Skill schema enforced: name, description, inputs, preconditions, effects, safety_constraints
- [ ] Skills CANNOT directly control motors - must use IRobotAPI
- [ ] Skills CANNOT access raw sensors - must use WorldState only
- [ ] Preconditions validated before execution

### Layer 5: Shared/Interfaces (`src/shared/`)
- [ ] Interface changes are backward compatible
- [ ] World state updates are thread-safe
- [ ] No circular dependencies between modules
- [ ] Event publishing follows established patterns
- [ ] TypedDicts match ARCHITECTURE.md definitions

### MetaClaw Integration (`MetaClaw/`)
- [ ] OpenClaw API accessed only through defined adapter
- [ ] Memory operations validated before execution
- [ ] Policy updates sandboxed and validated
- [ ] No direct skill execution without verification
- [ ] Continual learning bounds respected
- [ ] MetaClaw CANNOT bypass safety checks (CRITICAL RULE)
- [ ] Execution flow enforced: MetaClaw -> Planner -> Skill -> Robot API -> Hardware

### Frontend (`frontend/`)
- [ ] No direct robot control commands from UI
- [ ] API calls go through backend abstraction
- [ ] User input sanitized
- [ ] Error states handled gracefully

---

## Pull Request Requirements
- [ ] PR description explains the "why" of the change
- [ ] Related issue/ticket referenced
- [ ] Breaking changes clearly documented
- [ ] Migration steps provided if needed
- [ ] Reviewer assigned appropriately (see REVIEW_CRITERIA.md for layer-specific requirements)
- [ ] All CI checks pass
- [ ] At least 1 approval from Code Reviewer or relevant domain owner

## Safety-Critical Review (Additional Requirements)
For changes affecting robot behavior, safety, or MetaClaw execution:
- [ ] Safety impact assessment documented
- [ ] Failure mode analysis completed
- [ ] Emergency stop scenarios tested
- [ ] Safety reviewer explicitly approved
- [ ] Rollback plan documented
- [ ] Monitoring/alerting in place for production
