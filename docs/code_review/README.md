# Code Review Documentation

This directory contains the complete code review framework for the OpenClaw Robot Learning Project.

## Contents

| Document | Description |
|----------|-------------|
| [CHECKLIST.md](CHECKLIST.md) | Comprehensive review checklist for all changes |
| [REVIEW_CRITERIA.md](REVIEW_CRITERIA.md) | Layer-specific review criteria and severity levels |
| [SAFETY_REQUIREMENTS.md](SAFETY_REQUIREMENTS.md) | Mandatory safety review requirements |
| [LINTING.md](LINTING.md) | Automated linting and static analysis configuration |
| [REVIEW_TEMPLATE.md](REVIEW_TEMPLATE.md) | Template for requesting code reviews |

## Quick Start

### For Authors

1. **Before submitting a PR:**
   - Review [CHECKLIST.md](CHECKLIST.md)
   - Complete safety assessment if applicable
   - Run linting (`ruff check . && ruff format --check .`)
   - Ensure all tests pass

2. **When requesting review:**
   - Fill out [REVIEW_TEMPLATE.md](REVIEW_TEMPLATE.md)
   - Assign appropriate reviewers per [REVIEW_CRITERIA.md](REVIEW_CRITERIA.md)
   - Address all checklist items

### For Reviewers

1. **Review process:**
   - Start with [CHECKLIST.md](CHECKLIST.md)
   - Reference [REVIEW_CRITERIA.md](REVIEW_CRITERIA.md) for layer-specific criteria
   - For safety-critical changes, consult [SAFETY_REQUIREMENTS.md](SAFETY_REQUIREMENTS.md)

2. **Approval criteria:**
   - All critical issues resolved
   - No blocking concerns
   - Safety review passed (if applicable)

## Safety First

**REMINDER:** This project involves robotics hardware. Always prioritize safety over performance or feature delivery.

- All robot commands MUST go through validation layers
- NEVER bypass safety checks
- MetaClaw MUST NOT execute unverified skills
- Emergency stop functionality MUST always be available

## Contact

For questions about the review process, contact the Code Reviewer team member.
