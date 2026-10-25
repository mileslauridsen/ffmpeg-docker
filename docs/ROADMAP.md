# Roadmap

This is the high-level direction for ffmpeg-docker. Detailed execution belongs in the linked plans; recorded decisions belong in [IMPLEMENTATION.md](IMPLEMENTATION.md).

## Planning Index

- [Phase 1: Project playbook](plans/01-project-playbook.md): establish project orientation, workflow, and planning documents.
- [Phase 2: Build verification](plans/02-build-verification.md): establish whether the existing image builds and runs, then address demonstrated failures.
- [Phase 3: Small image and deterministic dependencies](plans/03-small-deterministic-image.md): lock build inputs, minimize the runtime and media capabilities, and automate size and reproducibility checks.

## Current Direction

- The project playbook is adopted. Build verification has started; CentOS 7 failed on both ARM64 and amd64. The replacement Debian 13 image builds and passes H.264 smoke tests on both `linux/amd64` and `linux/arm64`; phase 3 Tasks 1 and 2 lock sources and build inputs for both targets.
- Establish a measured baseline before selecting a replacement base image, updating codec versions, or changing supported platforms.
- Use phase 2 evidence to execute the five modernization tasks in phase 3. Phase 2 remains incomplete; phase 3 is in progress with locked sources and build environment. The modernization plan defines a handoff when the legacy build cannot proceed reasonably.
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
| 2. Build verification | in progress | [Plan](plans/02-build-verification.md) | CentOS 7 package-repository failures recorded for both architectures; amd64 and arm64 replacement builds and smoke checks pass; broader capability matrix remains. |
| 3. Small image and deterministic dependencies | in progress | [Plan](plans/03-small-deterministic-image.md) | Tasks 1 and 2 are complete for amd64 and arm64; runtime minimization, media capabilities, and automated checks remain. |

## Assumptions

- Initial use remains a locally built Docker image; no registry publication or release automation is configured in this setup.
- The selected image targets are `linux/amd64` and `linux/arm64`. Required media profiles still need to be established in phase 3, Task 4.
- The original recipe mixed versioned archives, unpinned repositories, and an FFmpeg snapshot; replacement source inputs and OS package resolution are pinned to recorded identities.
- Docker Desktop's ARM64 Linux daemon is available. Both images build and pass the recorded CLI and H.264 smoke checks on that engine; native production workers for each architecture have not been used for validation.
