# Implementation Log

Record decisions that change project direction, specifications, runtime behavior, tests, validation, dependencies, deployment, or architecture. Link to plans rather than duplicating their details.

## 2026-10-25: Minimize Runtime Contents (Initial Capability Set)

Request:

- Complete phase 3 Task 3 for the `linux/amd64` and `linux/arm64` images.

Decision:

- Build an explicit runtime artifact directory containing only `ffmpeg`, `ffprobe`, and collected license/notice files. Preserve Bash and the pinned Debian runtime base. Keep diagnostic copies in the compile stage, outside the final image, and explicitly strip the shipped executables.
- Compare the existing dynamic-linked build with a fully static FFmpeg link on both architectures. Select the shared candidate as the initial runtime: it has the smaller compressed transfer size on both platforms, and is also smaller by total image bytes on amd64. The static arm64 image is 309,358 bytes smaller uncompressed, but 495,964 bytes larger compressed.
- Retain the full configured codec set because Task 4 has not yet established which media capabilities may be removed. The initial selection is provisional until Task 4's matrix is tested and Task 3 is repeated.

Affected areas:

- Dockerfile, license collection helper, phase 3 plan, and this log.

Validation and measurements:

| Platform / candidate | Image identity | Total image bytes (`docker image inspect`) | Gzip `docker image save` bytes | ffmpeg / ffprobe bytes |
| --- | --- | ---: | ---: | ---: |
| amd64 baseline (`task2-amd64`) | `sha256:3c5962bbeca8509f17864a054d7f956ecdb07ae4e2cbb25c058edd05c4905262` | 257,143,506 | 69,003,608 | 45,223,256 / 45,010,104 |
| amd64 shared (`task3-shared-amd64`) | `sha256:6ded3e9d913bef8c34d7c9cc2b97ed263114baffc342566dda46d270452e06f2` | 244,556,814 | 65,916,674 | 45,223,256 / 45,010,104 |
| amd64 static (`task3-static-amd64`) | `sha256:84d0ff0438059ef3201b3d39fa07e0f4e546c0c36a4dca9f6b1296590f76a67e` | 245,297,566 | 66,704,327 | 45,215,232 / 45,010,368 |
| arm64 baseline (`task2-arm64`) | `sha256:f725177a158679cdc35b4ce9026a8803a7348c6edf582fb444a91c2d2dd385d5` | 259,989,041 | 69,747,762 | 35,536,112 / 35,339,392 |
| arm64 shared (`task3-shared-arm64`) | `sha256:f7906e15be0f47aa973959cc2879ff91b342ed827feec28a8d68e69cc47383ac` | 247,988,492 | 66,773,180 | 35,536,112 / 35,339,392 |
| arm64 static (`task3-static-arm64`) | `sha256:7b340590e42495f0a553cdc3042fda56d413b92ae1b1f5ea496390c263545ce1` | 247,679,134 | 67,269,144 | 35,150,152 / 34,953,512 |

- Compared to baseline, the selected shared image reduces total image bytes by 12,586,692 (4.9%) on amd64 and 12,000,549 (4.6%) on arm64; gzip transfer bytes fall by 3,086,934 (4.5%) and 2,974,582 (4.3%), respectively.
- Baseline layer history included `/root/bin` at 100 MB (amd64) and 80.2 MB (arm64), containing FFmpeg, FFprobe, NASM, ndisasm, x264, and LAME. The selected images contain only FFmpeg and FFprobe in `/root/bin` (90.2 MB amd64, 70.9 MB arm64) and 340 kB of license/notice files. The pinned Debian base and Bash remain.
- `ldd` on shared executables resolved all dynamic libraries. FFmpeg required the system loader plus libc, libm, zlib, bzip2, libmvec, libgcc_s, and libstdc++; FFprobe had the corresponding resolved set (the amd64 FFprobe did not need libgcc_s). Static executables report `not a dynamic executable`. No missing libraries were reported.
- The static x265 link initially failed because x265's pkg-config metadata requested `-lgcc_s`, for which the pinned Debian builder has no static archive. The static-only build removes that token; static builds then completed. Static linking reduced arm64 executable size modestly but increased compressed image size on both platforms.
- On both architectures, mounted-media H.264 read/write roundtrips passed; FFprobe confirmed H.264, 128x128, 24 fps, and 1 second. FFmpeg and FFprobe report version 8.1.3, Bash login access resolves both, and NASM, ndisasm, x264, LAME, gcc, and g++ are absent from runtime.
- License collection found 23 notice files across FFmpeg and the nine locked source dependencies. The build retains the Debian CA certificates and system runtime data. Fonts and any additional capability-specific data are not yet classified because Task 4's media matrix is undefined.
- `git diff --check` passed. Binary stripping is applied in the artifact assembly step; current binary sizes match the pre-task builds for shared candidates, indicating the upstream install output was already stripped. Static candidates are slightly smaller due to link contents, not an additional stripping reduction.

Follow-up:

- Define and test the required media/data matrix in Task 4, then repeat runtime size, linkage, and mounted-media validation. Do not treat the current shared selection as final until that comparison is complete.

## 2026-10-25: Pin The Build Environment

Request:

- Complete phase 3 Task 2 for the amd64 and arm64 targets.

Decision:

- Pin Debian 13 Trixie to multi-platform index `sha256:62bd423aeee912639ca8ee681c2b762cb3e25137e0a92b20be455898a9f034ad`, record both platform manifest identities, and resolve package installation from Debian snapshot `20261025T000000Z`.
- Lock the complete installed package sets and versions per platform. The runtime stage uses Bash from the pinned base and does not perform package installation.
- Select provisional generic CPU baselines: x86-64-v1 for amd64 (`-march=x86-64 -mtune=generic`) and ARMv8-A for arm64 (`-march=armv8-a -mtune=generic`). FFmpeg uses `--cpu=generic` and keeps runtime CPU detection enabled. Production worker CPU inventory remains a follow-up.
- Pin the Dockerfile frontend and BuildKit image by digest, and document the Buildx version and local multi-platform commands. This repository has no CI workflow; CI pinning will be applied when CI is introduced.

Affected areas:

- Dockerfile, per-platform APT package lists and resolved manifests, APT verifier, toolchain lock, build-environment guide, README, phase 3 plan, roadmap, and this log.

Validation:

- Created a Buildx builder using `moby/buildkit:v0.33.1` pinned to index digest `sha256:cec9f139f45e93c5c69c60f8b07cfad9f43f4ef6b6a6cd917527fea5ff2e3dea`; bootstrap reported BuildKit v0.33.1 with amd64 and arm64 support.
- Completed two independent `--no-cache` builds for each target. Resolved package manifest hashes were stable: amd64 `c29676accb29e3cb1d4bf5538e9fbb1e457618eb91f20bbf486863a08a91d5c0` (208 packages); arm64 `96c84483a3eb10214008e4b1e72a890773fad6779002b97f596be8c1f2562800` (207 packages). Source lock hash: `9ba39352cc780ddf78427adcf44b78e6c9f540c66c099955bedae33fd9341724`; toolchain lock hash: `357d6ada8e729f4928626becfc8e359a7caafee47ea2023586cf065b3058871a`.
- Build image identities were amd64 `sha256:3c5962bbeca8509f17864a054d7f956ecdb07ae4e2cbb25c058edd05c4905262` and repeat `sha256:dff728a842310d6a290a6815a518621167710514690d2b70764b1848ff7ac373`; arm64 `sha256:f725177a158679cdc35b4ce9026a8803a7348c6edf582fb444a91c2d2dd385d5` and repeat `sha256:2581e6731c76dcca03feac689fc5174446acc81f4e3ebc9315e709731beb1518`.
- FFmpeg and FFprobe report 8.1.3 on both platforms. On each architecture, a one-second 128x128, 24 fps H.264 smoke encode succeeded and FFprobe confirmed codec, dimensions, frame rate, and duration. The two amd64 clean builds emitted non-fatal upstream compiler warnings; neither build failed.
- `git diff --check`, Python syntax parsing for the APT verifier, and JSON parsing of the toolchain lock passed. Build output bytes and image-digest equality are not claimed by Task 2.

Follow-up:

- Confirm the provisional CPU baselines against actual production workers. Pin CI build tooling when a CI workflow is added. Continue with runtime minimization in Task 3, media capabilities in Task 4, and automated checks in Task 5.

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
