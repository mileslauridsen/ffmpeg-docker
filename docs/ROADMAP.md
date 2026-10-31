# Roadmap

This is the high-level direction for ffmpeg-docker. Detailed execution belongs in the linked plans; recorded decisions belong in [IMPLEMENTATION.md](IMPLEMENTATION.md).

## Planning Index

- [Phase 1: Project playbook](plans/01-project-playbook.md): establish project orientation, workflow, and planning documents.
- [Phase 2: Build verification](plans/02-build-verification.md): establish whether the existing image builds and runs, then address demonstrated failures.
- [Phase 3: Small image and deterministic dependencies](plans/03-small-deterministic-image.md): lock build inputs, minimize the runtime and media capabilities, and automate size and reproducibility checks.

## Current Direction

- The project playbook is adopted. Phase 2 acceptance is complete: CentOS 7 failed on both ARM64 and amd64, while the Debian 13 replacement builds and passes the recorded runtime checks on both `linux/amd64` and `linux/arm64`. Phase 3 locks sources and build inputs, minimizes runtime components, documents the tested media contract, and automates validation; local cold-build pairs pass while hosted Actions confirmation remains pending.
- Establish a measured baseline before selecting a replacement base image, updating codec versions, or changing supported platforms.
- Use the Phase 2 evidence to execute the five modernization tasks in Phase 3. Phase 3 is in progress with locked sources and build environment; its modernization plan records the handoff from the unbuildable legacy recipe.
- Retain the two-stage build model and direct FFmpeg CLI workflow.
- Track further work in the phase plans rather than maintaining a duplicate backlog.

## Development Loops

```text
documentation: inspect repository -> update project documents -> check links and consistency
build: define compatibility -> inspect dependencies -> build -> inspect tools -> encode and probe -> record evidence
```

## Phase Status

| Phase | Status | Plan | Outcome |
| --- | --- | --- | --- |
| 1. Project playbook | complete | [Plan](plans/01-project-playbook.md) | Project guidance, workflow, mission, roadmap, plans, and log adopted. |
| 2. Build verification | complete | [Plan](plans/02-build-verification.md) | CentOS 7 package-repository failures and successful Debian replacement verification are recorded for both architectures; acceptance review complete. |
| 3. Small image and deterministic dependencies | in progress | [Plan](plans/03-small-deterministic-image.md) | Tasks 1–5 cold-build checks are complete for both targets; hosted CI execution remains pending. Generic CPU baselines remain provisional. |

## Assumptions

- Initial use remains a locally built Docker image; no registry publication or release automation is configured in this setup.
- The selected image targets are `linux/amd64` and `linux/arm64`. The tested media profiles and explicit exclusions are documented in [MEDIA_SUPPORT.md](MEDIA_SUPPORT.md).
- The original recipe mixed versioned archives, unpinned repositories, and an FFmpeg snapshot; replacement source inputs and OS package resolution are pinned to recorded identities.
- Docker Desktop's ARM64 Linux daemon is available. Both images build and pass the recorded CLI and H.264 smoke checks on that engine; native production workers for each architecture have not been used for validation.
