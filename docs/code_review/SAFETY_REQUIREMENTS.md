# Safety-Critical Code Review Requirements

## Purpose
This document outlines mandatory safety review requirements for robotics code that could affect robot behavior, human safety, or system integrity.

---

## When Safety Review is Required

Safety review is **MANDATORY** for any change that:

1. Modifies hardware abstraction layer (`src/hardware/`)
2. Changes robot API validation logic (`src/robot_api/`)
3. Affects safety constraints or limits
4. Modifies emergency stop functionality
5. Changes planner collision detection
6. Affects MetaClaw execution safety
7. Modifies world state that could affect safety decisions
8. Any change flagged by author as safety-related

---

## Safety Review Process

### Pre-Submission Requirements
Before submitting a PR with safety implications:

1. **Safety Impact Assessment** - Document potential failure modes
2. **Test Case Identification** - Add tests for safety scenarios
3. **Rollback Plan** - Document how to revert if issues arise
4. **Monitoring Plan** - Identify how issues will be detected

### Review Checklist

#### Failure Mode Analysis
- [ ] Identified all potential failure modes
- [ ] Assessed severity of each failure mode
- [ ] Documented recovery procedures for each failure
- [ ] Emergency stop covers identified failures

#### Safety Constraints
- [ ] All hardcoded limits documented with units
- [ ] Limits validated against hardware specifications
- [ ] Constraint violations produce safe behavior
- [ ] Constraints tested in simulation first

#### Emergency Procedures
- [ ] Emergency stop tested and verified
- [ ] Timeout values appropriate for each operation
- [ ] Hardware failures detected and handled
- [ ] Graceful degradation documented

#### Testing Requirements
- [ ] Unit tests for all safety-critical paths
- [ ] Integration tests for safety scenarios
- [ ] Simulation tests before hardware deployment
- [ ] Edge case testing complete

---

## Critical Safety Rules (Non-Negotiable)

### Absolute Prohibitions
1. **NEVER** allow direct hardware access without abstraction
2. **NEVER** bypass validation in robot API
3. **NEVER** allow MetaClaw to execute unverified skills
4. **NEVER** remove emergency stop functionality
5. **NEVER** skip safety checks for "performance"

### Mandatory Practices
1. All robot commands MUST go through validation
2. All hardware access MUST use abstraction layer
3. All skill execution MUST be interruptible
4. All state changes MUST be atomic
5. All external input MUST be sanitized

---

## Safety Review Severity Levels

### Critical (Must Fix Before Merge)
- Emergency stop bypass/breakage
- Missing validation on robot commands
- Direct hardware access outside abstraction
- Missing timeout on hardware operations
- MetaClaw bypass of safety checks

### High (Should Fix Before Merge)
- Insufficient error handling for hardware failures
- Missing sensor validation
- Race conditions in state management
- Incomplete rollback procedures

### Medium (Fix Within Sprint)
- Missing logging for safety events
- Incomplete error messages
- Insufficient test coverage for edge cases

---

## Safety Documentation Requirements

### For Each Safety-Critical Change

```markdown
## Safety Impact Assessment

**Change Description:** [Brief description]

**Potential Failure Modes:**
- [Failure mode 1]
- [Failure mode 2]

**Affected Components:**
- [Component 1]
- [Component 2]

**Severity:** [Critical/High/Medium]

**Mitigation:**
- [How this is handled]

**Testing:**
- [How this was tested]

**Rollback:**
- [How to revert if needed]

**Monitoring:**
- [How issues will be detected]
```

---

## Review Sign-Off Requirements

Based on ARCHITECTURE.md Section "Review Requirements":

| Component | Reviews Required | Special Requirements |
|-----------|------------------|---------------------|
| IRobotAPI implementations | 2+ reviewers | Must test with RobotSimulator |
| Skill implementations | 2+ reviewers | Must validate against schema |
| Safety-critical code | 2+ reviewers | Must include safety analysis |
| MetaClaw adapter | 2+ reviewers | Must verify isolation |

| Change Type | Required Sign-offs |
|-------------|-------------------|
| Hardware layer | Code Reviewer + Robotics Engineer + Safety Owner |
| Safety constraints | Code Reviewer + Safety Owner |
| MetaClaw safety | Code Reviewer + MetaClaw Engineer + Safety Owner |
| Emergency stop | Code Reviewer + Robotics Engineer + Safety Owner + Team Lead |
| Skill implementations | Code Reviewer + Skill Designer + Robotics Engineer |

### Special Review Requirements

**IRobotAPI Implementations:**
- Must be tested with RobotSimulator before approval
- All methods must be implemented: `move_joints`, `move_pose`, `move_linear`, `set_gripper`, `get_world_state`, `execute_skill`, `stop`
- Joint/velocity limits must be enforced
- Emergency stop must function correctly

**Skill Implementations:**
- Must validate against SkillSchema (name, description, inputs, preconditions, effects, safety_constraints)
- Skills CANNOT directly control motors - must use IRobotAPI
- Skills CANNOT access raw sensors - must use WorldState only
- Must validate preconditions before execution

**MetaClaw Adapter:**
- Must verify isolation from direct hardware access
- MetaClaw CANNOT directly execute unverified skills
- Skill execution flow: MetaClaw -> Planner -> Skill Layer -> Robot API -> Hardware
- New/modified skills require: safety validation, Code Reviewer review, integration testing

---

## Known Safety-Critical Patterns

### Safe Robot Command Flow
```
User Input → Validation → Safety Check → API → Hardware Abstraction → Hardware
```

### Safe MetaClaw Skill Execution
```
Skill Proposal → Validation → Safety Sandbox → Skill Designer Review → Verified Execution
```

### Prohibited Patterns
- Direct function calls to hardware layer from planner
- Bypassing robot_api validation
- MetaClaw direct hardware access
- Hardcoded safety limits without documentation
- Commented-out safety checks

---

## Incident Response

If safety issues are discovered post-deployment:

1. **IMMEDIATELY** notify team lead and safety owner
2. **DO NOT** attempt to fix without safety review
3. **DOCUMENT** all details of the incident
4. **ROLLBACK** to last known safe state if needed
5. **REVIEW** how the issue was missed in review process
