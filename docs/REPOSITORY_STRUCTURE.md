# Repository Structure
## OpenClaw Robot Learning Project

## Directory Layout

```
/FeishuCLassmate
├── .git/                      # Git repository data
├── .gitignore                 # Git ignore patterns
├── .claude/                   # Claude agent config
├── docs/                      # Documentation
│   ├── GIT_WORKFLOW.md        # Branch strategy & workflow
│   └── REPOSITORY_STRUCTURE.md
├── src/                       # Core system source code
│   ├── hardware/              # Hardware abstraction layer (HAL)
│   │   └── ...
│   ├── robot_api/             # Robot control API layer
│   │   └── ...
│   ├── planner/               # Task planning layer
│   │   └── ...
│   ├── skill/                 # Skill system framework
│   │   └── ...
│   └── shared/                # Shared utilities & types
│       └── ...
├── backend/                    # FastAPI backend service
│   ├── api/                   # API routes
│   ├── models/                # Data models/schemas
│   ├── services/              # Business logic services
│   ├── db/                    # Database connections
│   └── requirements.txt       # Python dependencies
├── MetaClaw/                  # MetaClaw continual learning module
│   ├── benchmark/
│   ├── openclaw-metaclaw-memory/
│   ├── metaclaw/
│   ├── skill_bank/
│   ├── robot_skill_bank/
│   └── extensions/
├── frontend/                  # Frontend/UI
│   ├── css/
│   └── js/
├── tests/                     # Test suite
│   ├── unit/                  # Unit tests
│   │   └── layer_tests/
│   ├── integration/           # Integration tests
│   └── simulation/            # Simulation tests
└── README.md
```

## Branch Structure

```
main                         # Production (protected)
develop                      # Development integration (protected)
├── feature/arch-system-layers
├── feature/arch-interface-design
└── module/metaclaw
```

## Module Responsibilities

| Directory | Owner | Purpose |
|-----------|-------|---------|
| `src/hardware` | Robotics Engineer | Hardware abstraction layer |
| `src/robot_api` | Robotics Engineer | Robot control API |
| `src/planner` | Backend Engineer | Task planning |
| `src/skill` | Skill Designer | Skill system |
| `src/shared` | All | Shared utilities |
| `backend` | Backend Engineer | FastAPI backend service |
| `MetaClaw` | MetaClaw Engineer | Continual learning |
| `frontend` | Frontend Engineer | UI/Visualization |
| `tests` | Testing Engineer | Test coverage |

---

*Document Version: 1.0*
*Last Updated: 2026-04-17*
