# Automated Linting Rules Configuration

## Overview
This document defines linting and static analysis configuration for the project.

---

## Python Linting Configuration (`.python-lint`)

### Required Tools
- `ruff` - Fast Python linter (primary)
- `mypy` - Type checking
- `bandit` - Security vulnerabilities
- `pyright` - Additional type checking

### Configuration File: `pyproject.toml`

```toml
[tool.ruff]
line-length = 100
target-version = "py39"
select = [
    "E",      # pycodestyle errors
    "W",      # pycodestyle warnings
    "F",      # pyflakes
    "I",      # isort
    "N",      # pep8-naming
    "UP",     # pyupgrade
    "S",      # bandit security
    "B",      # flake8-bugbear
    "C4",     # flake8-comprehensions
    "DTZ",    # flake8-datetimez
    "T10",    # flake8-debugger
    "ISC",    # flake8-implicit-str-concat
]
ignore = [
    "S101",   # bandit: assert (used in tests)
    "B017",   # bugbear: assertRaises with exc info
]

[tool.ruff.per-file-ignores]
"tests/*" = ["S101", "B017"]
"MetaClaw/*" = ["S101"]

[tool.mypy]
python_version = "3.9"
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true
disallow_incomplete_defs = true
check_untyped_defs = true
strict_optional = true
warn_redundant_casts = true
warn_unused_ignores = true

[tool.bandit]
targets = ["src/", "MetaClaw/"]
exclude = ["tests/", "*.pyc", "__pycache__"]
```

---

## TypeScript Linting Configuration

### Required Tools
- `eslint` - JavaScript/TypeScript linter
- `typescript` - Type checking
- `prettier` - Code formatting

### Configuration File: `.eslintrc.json`

```json
{
  "root": true,
  "parser": "@typescript-eslint/parser",
  "plugins": ["@typescript-eslint", "security"],
  "extends": [
    "eslint:recommended",
    "plugin:@typescript-eslint/recommended",
    "plugin:security/recommended"
  ],
  "rules": {
    "no-console": "warn",
    "no-debugger": "error",
    "security/no-eval": "error",
    "security/new-cap": "warn",
    "@typescript-eslint/explicit-module-boundary-types": "error",
    "@typescript-eslint/no-explicit-any": "warn",
    "@typescript-eslint/no-unused-vars": ["error", { "argsIgnorePattern": "^_" }]
  },
  "ignorePatterns": ["dist/", "node_modules/", "*.js"]
}
```

### Configuration File: `.prettierrc`

```json
{
  "semi": true,
  "singleQuote": true,
  "tabWidth": 2,
  "trailingComma": "es5",
  "printWidth": 100
}
```

---

## Pre-Commit Hooks

Configuration File: `.pre-commit-config.yaml`

```yaml
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.4.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-added-large-files
      - id: check-merge-conflict

  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.1.6
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.7.1
    hooks:
      - id: mypy
        additional_dependencies: [types-all]
```

---

## CI/CD Integration

### GitHub Actions: `.github/workflows/lint.yml`

```yaml
name: Lint and Type Check

on: [push, pull_request]

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.9'

      - name: Install dependencies
        run: |
          pip install ruff mypy bandit

      - name: Run Ruff
        run: ruff check src/ MetaClaw/

      - name: Run Ruff (autofix)
        run: ruff format --check src/ MetaClaw/

      - name: Run Mypy
        run: mypy src/ MetaClaw/

      - name: Run Bandit
        run: bandit -r src/ MetaClaw/

  frontend-lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '18'

      - name: Install dependencies
        run: |
          npm install eslint @typescript-eslint/parser

      - name: Run ESLint
        run: npx eslint frontend/src/

      - name: Run Prettier
        run: npx prettier --check frontend/src/
```

---

## Running Linters Locally

### Python
```bash
# Install dependencies
pip install ruff mypy bandit

# Run all linters
ruff check src/ MetaClaw/
ruff format --check src/ MetaClaw/
mypy src/ MetaClaw/
bandit -r src/ MetaClaw/

# Auto-fix issues
ruff check --fix src/ MetaClaw/
ruff format src/ MetaClaw/
```

### TypeScript
```bash
# Install dependencies
npm install

# Run all linters
npm run lint
npm run format:check
```

---

## IDE Integration

### VS Code Settings: `.vscode/settings.json`

```json
{
  "python.linting.enabled": true,
  "python.linting.ruffEnabled": true,
  "python.formatting.provider": "ruff",
  "typescript.preferences.importModuleSpecifier": "relative",
  "[python]": {
    "editor.defaultFormatter": "charliermarsh.ruff",
    "editor.formatOnSave": true
  },
  "[typescript]": {
    "editor.defaultFormatter": "esbenp.prettier-vscode",
    "editor.formatOnSave": true
  }
}
```

---

## Violation Severity Levels

| Tool | Rule | Severity | Description |
|------|------|----------|-------------|
| ruff | S101 | Error | Use of `assert` detected |
| ruff | E501 | Warning | Line too long |
| ruff | F401 | Error | Unused import |
| mypy | strict | Error | Missing type annotations |
| bandit | B413 | Error | Blacklist: pickle |
| bandit | S301 | Error | Pickle deserialization |
| eslint | no-console | Warning | Console statement |
| eslint | security/no-eval | Error | Use of eval() |
