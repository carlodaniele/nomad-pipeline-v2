# Nomad Pipeline v2

Adapter-first, CMS-agnostic pipeline that converts Telegram audio, optional images, and optional context text into AI-generated, publish-ready content.

## Goals

- Keep orchestration logic in `core/`.
- Keep CMS integrations in `adapters/`.
- Enforce a shared contract in `docs/contracts/`.
- Automate structure and contract checks in GitHub Actions.

## Initial Structure

- `core/` platform-agnostic orchestration logic.
- `adapters/wordpress/` WordPress Ability adapter.
- `adapters/astro/` Astro publishing adapter.
- `docs/contracts/` versioned schemas and examples.
- `scripts/ci/` local validation scripts.
- `.github/workflows/` CI automation.

## Quick Start

```bash
bash scripts/ci/validate-structure.sh
bash scripts/ci/validate-contract.sh
bash scripts/pipeline/dry-run.sh
```
