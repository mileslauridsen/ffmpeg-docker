# Git Workflow

This document defines Git conventions for ffmpeg-docker.

The local primary branch is `main` and tracks `origin/main`. GitHub's default branch and the local `origin/HEAD` reference both point to `main`.

## Branch Naming

Use short, lowercase, hyphenated task names with these prefixes:

- `feature/`: new behavior or capabilities.
- `hotfix/`: urgent fixes to an established working image.
- `planning/`: project direction and design work.
- `docs/`: documentation-only work.
- `maintenance/`: dependency, build, and tooling maintenance.

Examples: `docs/project-playbook`, `maintenance/verify-ffmpeg-build`.

## Branch Creation And Worktree Safety

Create a focused branch before a new task group when starting from a clean worktree:

```sh
git switch -c maintenance/verify-ffmpeg-build
```

For a dirty worktree, inspect staged and unstaged changes before deciding how to isolate new work. Preserve existing edits and staging; do not automatically stash, reset, or carry unrelated changes into a commit. The initial playbook adoption started on the existing checkout because templates and a Dockerfile edit were already present; that branch was subsequently renamed from `master` to `main`.

Keep each branch focused on one task group. Inspect the actual staged diff before committing. Do not commit or push as a side effect of a documentation or implementation request unless requested.

## Commit Signing

Repository policy: signed commits are required, matching the effective `commit.gpgsign=true` configuration observed during setup. Signing itself has not been tested.

Resolve signing failures before committing. An unsigned exception requires an authorized maintainer's explicit approval for that commit.

## Documentation And Change Records

Update [IMPLEMENTATION.md](IMPLEMENTATION.md) when a change affects direction, architecture, runtime behavior, dependencies, validation, deployment, or feature scope. Correcting a typo or link alone does not require an entry.

Update the relevant phase plan and roadmap when scope or phase status changes. Retain completed plans as history.

## Before Finishing

- Review the diff and preserve unrelated changes and staging.
- Run the checks appropriate to the change and record what actually ran.
- Report the branch, commit or review state, and remaining limitations.
