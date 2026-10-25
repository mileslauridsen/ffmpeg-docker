# Plan: Project Playbook

## Goal

Give maintainers and agents a project-specific entry point, working conventions, and an evidence-based plan for further development.

## Current State

- The repository contains a Dockerfile, brief usage instructions, and reusable playbook templates.
- At adoption, the templates were already staged and a Dockerfile formatting edit was present.

## Decisions And Boundaries

- Adopt the templates into root `AGENTS.md` and `docs/`, retaining the reusable originals.
- Document the existing recipe separately from future verification and improvements.
- Preserve all pre-existing edits and staging. This phase changes documentation only.
- Use signed commits for future commits, consistent with the effective Git configuration; create no commit during setup.

## Work Plan

### 1. Establish Project Documents

- Add agent guidance, mission, Git policy, roadmap, phase plans, and an implementation log.
- Replace template prompts with repository-specific facts and explicit unknowns.

### 2. Connect And Validate

- Link the project documents from the README and link plans from the roadmap.
- Check local Markdown links, unresolved template prompts, and whitespace errors in the changed documents.
- Review Git status and confirm the Dockerfile edit and staged templates are preserved.

## Validation

- Inspect the Dockerfile, README, templates, and effective commit-signing configuration.
- Run local documentation link and placeholder checks and `git diff --check`.
- No image build or runtime test is needed to validate this documentation-only adoption.

## Acceptance Criteria

- All six playbook document types are adopted with project-specific content.
- Agent guidance and the README lead to the relevant project documents.
- Build verification is documented as planned work, with runnable checks and observable acceptance criteria.
- Existing user changes and staging are preserved.

## Status

Status: complete

Last updated: 2026-10-25
