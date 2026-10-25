# Implementation Log

Record decisions that change project direction, specifications, runtime behavior, tests, validation, dependencies, deployment, or architecture. Link to plans rather than duplicating their details.

## 2026-10-25: Begin Dependency Locking

Request:

- Start the first task in phase 3: lock FFmpeg and every source dependency behind a verified fetch helper.

Decision:

- Add a versioned archive lock and a Python 2/3-compatible helper that verifies SHA-256, verifies signed releases against pinned key fingerprints, and extracts sources only after verification.
- Replace the Dockerfile's FFmpeg snapshot, floating repository clones, and unverified source URLs with the lock-driven fetch. Select FFmpeg 8.1.3 and pinned source versions/commit for the configured integrations.
- Remove Yasm as redundant for the selected NASM assembler path. Verify libvpx's `--as=nasm` support and compatibility during build verification.
- Record checksum provenance and explicitly leave build compatibility and VFX media-profile validation pending.

Affected areas:

- Dockerfile, dependency lock, source fetch helper, pinned FFmpeg release key, phase plan, README, and source provenance documentation.

Validation:

- Downloaded and hashed all ten locked source archives; FFmpeg and libvorbis detached signatures verified with pinned fingerprints. x265 and Opus digests matched publisher pages; libogg and libvorbis digests matched Xiph SHA256SUMS.
- Source archive extraction roots were inspected and matched the lock manifest.
- The helper verified and extracted all ten cached source archives, including the FFmpeg detached signature. A deliberately corrupted NASM digest was rejected. A fresh NASM HTTPS fetch succeeded and matched its locked digest.
- Python syntax compilation and `git diff --check` passed. The deliberately incorrect NASM digest returned failure before extraction.
- Docker Desktop reported an ARM64 Linux engine. `docker build --progress=plain -t vfx/ffmpeg:locked .` failed at the CentOS 7 `yum update` step: the configured mirrorlist could not be resolved and no base URL was available for `aarch64`. The build did not reach source fetching or compilation, so this is evidence that the current CentOS 7 recipe cannot build in this environment, not evidence about source compatibility.

Follow-up:

- Signature/provenance audit is complete for materials found. Source compatibility was subsequently verified for the amd64 target; see the following entry. Broader media profiles remain for Task 4, and phase 2 remains in progress.

## 2026-10-25: Verify Locked Sources On linux/amd64

Request:

- Complete the first phase 3 task after selecting `linux/amd64` as the target platform.

Decision:

- Replace the unusable CentOS 7 build/runtime bases with Debian 13 Trixie pinned to multi-platform index digest `sha256:62bd423aeee912639ca8ee681c2b762cb3e25137e0a92b20be455898a9f034ad`.
- Add the explicit build tools needed by the locked sources, including Python 3, CA certificates, `gpgv`, and `xz-utils`. Update the fetch helper to work without Python's removed `distutils` module and retry transient downloads up to three attempts.
- Keep all currently configured codec integrations. No broader media profile has been established; Task 4 will define that contract.

Affected areas:

- Dockerfile, source fetch helper, phase 2 and phase 3 plans, roadmap, and provenance documentation.

Validation:

- `docker build --platform=linux/amd64 --progress=plain -t vfx/ffmpeg:locked-amd64 .` completed. It fetched and verified all ten locked archives, verified FFmpeg and Vorbis signatures, and compiled FFmpeg 8.1.3 with GCC 14.2.0.
- Final image identity after restoring Bash login behavior: `linux/amd64`, `sha256:4c3ae6bd024b9e7a92c499b73fc5b12b621cceb7cfec213aef03f413f84daa68`.
- FFmpeg and FFprobe both start as version 8.1.3. Encoder inventory includes libx264, libx265, libfdk_aac, libmp3lame, libopus, libvorbis, and libvpx-backed VP8/VP9 encoders.
- A mounted one-second 128x128, 24 fps H.264 test encode succeeded; FFprobe confirmed H.264, 128x128, 24 fps, and 1.000 seconds. The documented `bash -lc` invocation resolves both `ffmpeg` and `ffprobe` after adding their path to the login profile.
- `git diff --check`, helper Python syntax compilation, successful fetch/extraction, and the negative checksum test passed.

Follow-up:

- Complete the remaining build-environment locking in Task 2, including immutable package repository resolution. Define broader media profiles in Task 4. Phase 2's current validation is recorded; retain its in-progress status until the agreed capability requirements are represented in the full matrix.

## 2026-10-25: Verify Locked Sources On linux/arm64

Request:

- Expand Task 1 to support and validate `linux/arm64` alongside the previously selected amd64 target.

Decision:

- Reuse the same digest-pinned Debian 13 Trixie base and architecture-neutral source lock. Build FFmpeg and its locked codec dependencies natively for ARM64.
- Keep Task 1 complete for both image targets. Package snapshot and toolchain pinning remain Task 2 work; broader media profiles remain Task 4 work.

Affected areas:

- Phase 2 and phase 3 plan status, roadmap, source provenance, and this implementation log.

Validation:

- `docker build --platform=linux/arm64 --progress=plain -t vfx/ffmpeg:locked-arm64 .` completed, verifying all ten locked archives and compiling FFmpeg 8.1.3 with GCC 14.2.0. FFmpeg emitted non-fatal compiler warnings in upstream sources including RV60, VLC, VVC, and WMA code.
- Final image identity: `linux/arm64`, `sha256:102e8fd0d115bed0eceafdac1c4e93d192440de7cceeee595798444e09b76a94`.
- FFmpeg and FFprobe start as version 8.1.3; login Bash resolves both executables. Configured external encoders are present.
- A mounted one-second 128x128, 24 fps H.264 test encode succeeded; FFprobe confirmed H.264, 128x128, 24 fps, and 1.000 seconds.

Follow-up:

- Complete the remaining build-environment locking in Task 2, including immutable package repository resolution. Define broader media profiles in Task 4. Native production workers for both architectures have not been used for validation.

## 2026-10-25: Plan Image Modernization

Request:

- Turn the five repository-review recommendations into a planning file with ordered steps for an implementing agent.

Decision:

- Add [phase 3](plans/03-small-deterministic-image.md) with tasks for source locking, build-environment locking, runtime minimization, explicit media capabilities, and automated size/reproducibility checks.
- Specify prerequisites, task dependencies, deliverables, completion evidence, and acceptance criteria. Keep exact versions and numeric size budgets pending measurement.
- Preserve the existing compatibility contracts while requiring an explicit decision before choosing a shell-free runtime or removing media support.
- Keep phase 2 as the baseline investigation; document a handoff if legacy build failures make modernization necessary without calling that investigation complete.

Affected areas:

- New phase plan, roadmap index and status, and this log. Runtime code remains unchanged.

Validation:

- Checked local Markdown links, unresolved template prompts, whitespace, and plan/roadmap status consistency.
- No Docker build or modernization task was executed for this planning-only change.

Follow-up:

- Execute baseline verification and the ordered modernization tasks, recording actual measurements and updating task status as work completes.

## 2026-10-25: Synchronize GitHub Branch Rename

Request:

- Update the local checkout after the maintainer renamed the branch on GitHub.

Decision:

- Fetch with pruning, set `main` to track `origin/main`, and refresh `origin/HEAD` from GitHub's default branch.
- Update the Git workflow to reflect the completed migration.

Validation:

- Fetch discovered `origin/main` and removed the stale `origin/master` tracking reference.
- Upstream configuration succeeded; `git remote set-head origin -a` confirmed `origin/HEAD` points to `main`.
- Existing staged and working-tree changes were preserved; no commit or push was made.

Follow-up:

- None for this checkout.

## 2026-10-25: Rename Local Primary Branch

Request:

- Rename `master` to `main`.

Decision:

- Rename the local branch to `main`, preserving its commit, staged changes, and working-tree edits.
- Update the Git workflow to reflect the new name. Remote branches and the hosting default remain unchanged; `main` still tracks `origin/master`.

Validation:

- Confirmed `git branch --show-current` reports `main`, its commit remains `2928ab9`, and Git status preserves the existing changes and staging.

Follow-up:

- Remote branch publication and hosting default migration remain separate work if requested.

## 2026-10-25: Adopt Project Playbook

Request:

- Set up this repository using the documents in `templates/project-playbook`.

Decision:

- Adopt root agent guidance and project-specific documents under `docs/`, preserving the reusable templates.
- Complete [playbook adoption](plans/01-project-playbook.md) and define [build verification](plans/02-build-verification.md) as the next planned phase.
- Require signed commits consistent with the effective `commit.gpgsign=true` configuration. Signing has not been exercised.
- Preserve the existing `master` checkout, staged templates, and unstaged Dockerfile formatting edit; do not commit or publish during setup.

Affected areas:

- `AGENTS.md`, README navigation, mission, roadmap, Git workflow, phase plans, and this log.
- Build and runtime behavior are unchanged by this adoption.

Validation:

- Inspected repository files, source templates, Git status, the existing Dockerfile diff, and effective signing configuration.
- Checked local Markdown links, unresolved template prompts in adopted documents, and Git whitespace validation.
- Docker CLI presence was confirmed. Docker daemon access, image builds, runtime linking, and media conversion were not tested in this documentation phase.

Follow-up:

- Execute the build verification phase to establish platform requirements and build/runtime evidence before broader modernization.
