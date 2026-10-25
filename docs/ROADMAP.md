# Roadmap

This is the high-level direction for ffmpeg-docker. Detailed execution belongs in the linked plans; recorded decisions belong in [IMPLEMENTATION.md](IMPLEMENTATION.md).

## Planning Index

- [Phase 1: Project playbook](plans/01-project-playbook.md): establish project orientation, workflow, and planning documents.
- [Phase 2: Build verification](plans/02-build-verification.md): establish whether the existing image builds and runs, then address demonstrated failures.

## Current Direction

- The project playbook is adopted. The next planned engineering phase is build verification; it has not started.
- Establish a measured baseline before selecting a replacement base image, updating codec versions, or changing supported platforms.
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
| 2. Build verification | planned | [Plan](plans/02-build-verification.md) | Build and runtime baseline with documented failures or successful validation. |

## Assumptions

- Initial use remains a locally built Docker image; no registry publication or release automation is configured in this setup.
- The intended deployment platform and required media profiles still need to be established during build verification.
- The current recipe mixes versioned archives, unpinned repositories, and an FFmpeg snapshot; it does not define reproducible inputs.
- A Docker CLI is installed on the setup host. Daemon availability, image build success, and runtime behavior have not been checked.
