# Review Criteria by Layer

## Overview
This document defines specific review criteria for each architectural layer of the robot control system.

---

## Layer 1: Hardware Abstraction (`src/hardware/`)

### Purpose
Provides low-level interface to robot hardware and simulation environment.

### Review Criteria

| Category | Criteria | Severity |
|----------|----------|----------|
| **Safety** | All hardware operations have timeout protection | Critical |
| **Safety** | Simulation mode mirrors real hardware behavior exactly | Critical |
| **Safety** | Emergency stop always available and tested | Critical |
| **Correctness** | Sensor readings calibrated and validated | High |
| **Correctness** | Motor commands bounded within safe limits | Critical |
| **Reliability** | Hardware failure detection and reporting | High |
| **Maintainability** | Clear abstraction between simulation and real hardware | Medium |

### Key Files to Review
- `src/hardware/simulator.py` - Simulation engine
- `src/hardware/__init__.py` - Interface definitions

---

## Layer 2: Robot API (`src/robot_api/`)

### Purpose
High-level API for robot control, enforcing safety constraints and validation.

### Review Criteria

| Category | Criteria | Severity |
|----------|----------|----------|
| **Safety** | Every command validated before execution | Critical |
| **Safety** | Safety constraints checked on all operations | Critical |
| **Safety** | Emergency stop is atomic and immediate | Critical |
| **Correctness** | State machine transitions are valid | High |
| **Correctness** | Command sequencing is preserved | High |
| **Robustness** | Timeout and retry logic appropriate | Medium |
| **API Design** | Interface matches specification | High |
| **API Design** | Error responses are informative | Medium |

### Key Files to Review
- `src/robot_api/robot_api.py` - Main API implementation
- `src/robot_api/__init__.py` - Public interface

---

## Layer 3: Planner (`src/planner/`)

### Purpose
Mission planning, path planning, and task coordination.

### Review Criteria

| Category | Criteria | Severity |
|----------|----------|----------|
| **Safety** | Plans validated before execution | Critical |
| **Safety** | Collision avoidance implemented | Critical |
| **Safety** | Resource limits enforced | High |
| **Correctness** | Planning algorithms produce valid plans | High |
| **Correctness** | Plan execution respects constraints | High |
| **Performance** | Planning time within acceptable bounds | Medium |
| **Recoverability** | Failed plans can be rolled back | High |

---

## Layer 4: Skill System (`src/skill/`)

### Purpose
Skill abstraction layer supporting MetaClaw continual learning.

### Review Criteria

| Category | Criteria | Severity |
|----------|----------|----------|
| **Safety** | Skill parameters validated before execution | Critical |
| **Safety** | Skill execution can be interrupted | Critical |
| **Safety** | MetaClaw cannot bypass safety checks | Critical |
| **Isolation** | Skills are isolated from each other | High |
| **Correctness** | Skill schemas are versioned | Medium |
| **Integration** | MetaClaw integration follows approved patterns | High |

### Key Files to Review
- `src/skill/skill_schemas.py` - Skill definitions
- MetaClaw integration points

---

## Layer 5: Shared/Interfaces (`src/shared/`)

### Purpose
Common interfaces, world state, and shared utilities.

### Review Criteria

| Category | Criteria | Severity |
|----------|----------|----------|
| **Consistency** | Interfaces used consistently across layers | High |
| **Thread Safety** | World state access is thread-safe | Critical |
| **Abstraction** | No layer violations | High |
| **Events** | Event publishing follows patterns | Medium |

### Key Files to Review
- `src/shared/interfaces.py` - Interface definitions
- `src/shared/world_state.py` - World state management

---

## MetaClaw Integration (`MetaClaw/`)

### Purpose
Continual learning and skill evolution.

### Review Criteria

| Category | Criteria | Severity |
|----------|----------|----------|
| **Safety** | OpenClaw API never called directly | Critical |
| **Safety** | Learned skills validated before execution | Critical |
| **Safety** | Policy updates sandboxed | Critical |
| **Isolation** | MetaClaw cannot directly control hardware | Critical |
| **Learning** | Learning bounds respected | High |
| **Memory** | Memory operations are recoverable | High |

### Key Files to Review
- `MetaClaw/metaclaw/` - Core MetaClaw implementation
- `MetaClaw/metaclaw/memory/` - Memory management
- Integration adapters

---

## Frontend (`frontend/`)

### Purpose
User interface for monitoring and control.

### Review Criteria

| Category | Criteria | Severity |
|----------|----------|----------|
| **Security** | No direct robot control commands | Critical |
| **Security** | API calls authenticated | High |
| **Correctness** | State display matches robot state | High |
| **Usability** | Error states handled gracefully | Medium |
| **Performance** | UI responsive under load | Medium |

---

## Test Coverage Requirements

| Layer | Minimum Coverage |
|-------|-----------------|
| Hardware | 80% |
| Robot API | 90% |
| Planner | 80% |
| Skill System | 85% |
| Shared | 85% |
| MetaClaw | 75% |
| Frontend | 70% |

---

## Complexity Thresholds

| Metric | Maximum |
|--------|---------|
| Cyclomatic complexity per function | 10 |
| Lines per function | 50 |
| Lines per module | 500 |
| Import depth | 5 |

---

## Required Reviewers by Change Type

| Change Type | Required Reviewers |
|-------------|--------------------|
| Hardware layer | Code Reviewer + Robotics Engineer |
| Safety constraints | Code Reviewer + Safety Owner |
| MetaClaw integration | Code Reviewer + MetaClaw Engineer |
| API changes | Code Reviewer + Backend Engineer |
| Frontend changes | Code Reviewer + Frontend Engineer |
| Skill system | Code Reviewer + Skill Designer |
| Any safety-critical | Code Reviewer + Safety Review |
