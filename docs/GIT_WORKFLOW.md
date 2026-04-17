# Git Workflow & Branch Strategy
## OpenClaw Robot Learning Project

---

## 1. Branch Structure

```
main                    # Production-ready code (protected)
develop                 # Integration branch for features (protected)
├── feature/*           # Feature development branches
├── release/*           # Release preparation branches
└── hotfix/*            # Emergency production fixes
```

### Branch Naming Conventions (Per ARCHITECTURE.md)

| Branch Type | Pattern | Example |
|-------------|---------|---------|
| Feature | `feature/{layer}-{name}` | `feature/skill-grasp-implementation` |
| Bug Fix | `fix/{layer}-{issue}` | `fix/robot-api-collision-detection` |
| Refactor | `refactor/{component}` | `refactor/skill-base-class` |
| Docs | `docs/{topic}` | `docs/api-reference` |
| Module | `module/<name>` | `module/metaclaw` |
| Release | `release/v<major.minor.patch>` | `release/v1.0.0` |
| Hotfix | `hotfix/{layer}-{issue}` | `hotfix/skill-precondition-bug` |

---

## 2. Module Organization

```
OpenClaw Robot Learning
├── src/                    # Core system (layered architecture)
│   ├── hardware/           # Hardware abstraction layer
│   ├── robot_api/          # Robot control API
│   ├── planner/            # Task planning layer
│   ├── skill/              # Skill system
│   └── shared/             # Shared utilities
├── backend/                # FastAPI backend service
│   ├── api/                # API routes
│   ├── models/             # Data models/schemas
│   ├── services/           # Business logic services
│   ├── db/                 # Database connections
│   └── requirements.txt    # Python dependencies
├── MetaClaw/               # MetaClaw continual learning
├── frontend/               # UI and visualization
├── tests/                  # Test suite
│   ├── unit/
│   ├── integration/
│   └── simulation/
└── docs/                   # Documentation
```

---

## 3. Workflow Rules

### Commit Message Format (Per ARCHITECTURE.md)
```
{type}({layer}): {description}

[optional body with details]

[optional footer with ticket/issue]
```

**Types**: feat, fix, refactor, docs, test, chore
**Layer**: planner, skill, robot-api, hardware, shared, backend, metaclaw

**Examples**:
```
feat(skill): implement grasp skill with force control

fix(robot-api): correct joint limit validation

test(hardware): add collision detection tests
```

### Merge Strategy
- **Feature branches** → Merge via Pull Request to `develop`
- **Release branches** → Merge to `main` AND `develop` after QA
- **Hotfix branches** → Merge to `main` AND `develop` immediately
- **No fast-forward merges** → Always create merge commit

### Pull Request Requirements (Per ARCHITECTURE.md)

| Component | Reviews Required | Special Requirements |
|-----------|------------------|---------------------|
| IRobotAPI implementations | 2+ | Must test with RobotSimulator |
| Skill implementations | 2+ | Must validate against schema |
| Safety-critical code | 2+ | Must include safety analysis |
| MetaClaw adapter | 2+ | Must verify isolation |
| Other components | 1+ | All tests must pass |

**General Requirements:**
1. All tests passing
2. No merge conflicts
3. Proper branch naming per convention
4. Descriptive PR description

---

## 4. Release Tagging

### Tag Structure (Per ARCHITECTURE.md)

**Phase/Layer tags:**
```
v{phase}.{layer}-{description}
```

**Examples**:
- `v0.1-planner` - Planner layer complete
- `v0.2-skill` - Skill layer complete
- `v0.3-robot-api` - Robot API complete
- `v0.4-integration` - Full system integration

**Full release tags:**
```
v<major>.<minor>.<patch>[-<prerelease>]
```

**Examples**:
- `v1.0.0` - Initial production release
- `v1.0.0-alpha` - Alpha release
- `v1.0.0-rc1` - Release candidate

### Release Process
1. Create release branch: `release/v<x.y.z>` or per module
2. Final testing and bug fixes
3. Tag: `git tag -a v<x.y.z> -m "Release v<x.y.z>"`
4. Merge to `main` and `develop`
5. Push tags: `git push origin --tags`

---

## 5. Conflict Resolution

### Steps
1. Pull latest from target branch
2. Merge target into your feature branch
3. Resolve conflicts locally
4. Run tests to verify
5. Push and update PR

### Prevention
- Rebase frequently on `develop`
- Communicate with team before large changes
- Use small, focused commits

---

## 6. Protected Branches

| Branch | Protection Rules |
|--------|------------------|
| `main` | No direct push, PR required, reviews required |
| `develop` | No direct push, PR required, linear history preferred |

---

## 7. Phase Branches

### Phase 1 (Architecture & Core) ✅
```
develop
├── feature/planner-system-layers      # System layer definitions
├── feature/skill-interface-design     # Interface contracts
├── feature/robot-api-core             # Core Robot API
├── feature/skill-framework             # Skill system framework
├── feature/backend-api-structure      # Backend FastAPI service
└── module/metaclaw                     # MetaClaw module
```

### Phase 2 (Integration & Composite Skills)
```
develop
├── feature/integration-testing         # End-to-end integration testing
├── feature/composite-skills            # Composite skills (approach_and_grasp, pick_and_place)
├── feature/skill-tracking-panel        # Skill execution tracking panel
└── ...
```

---

*Document Version: 2.2 - Phase 2 branches renamed*
*Last Updated: 2026-04-17*
