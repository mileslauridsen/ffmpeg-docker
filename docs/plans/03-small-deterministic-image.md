# Plan: Small Image And Deterministic Dependencies

## Goal

Produce the smallest measured FFmpeg runtime image that meets the documented VFX requirements, with exact source and build-environment versions and automated checks against dependency drift and size regressions.

## Current State

- The Dockerfile separates compilation and runtime stages and now uses a digest-pinned Debian 13 Trixie base for amd64 and arm64 targets.
- FFmpeg and its nine source dependencies now have immutable identities, archive checksums, and signature checks where available.
- Debian package resolution and the builder toolchain are snapshot-pinned for amd64 and arm64; see [build environment](../BUILD_ENVIRONMENT.md).
- The runtime now copies only `ffmpeg` and `ffprobe` from an explicit artifact directory, plus source license notices. NASM, codec CLI tools, headers, archives, sources, and build caches stay out of the final image.
- Shared and fully static candidates were measured again with the Task 4 media set. Shared linking remains smaller by compressed OCI archive size on both architectures. The default build enables FFmpeg's size optimization; SIMD and threading remain enabled.
- No automated size, dependency-lock, or reproducibility checks exist.

## Decisions And Boundaries

- This is a planned engineering phase. Creating this document does not implement or validate a new image.
- Start with the evidence and requirements from [build verification](02-build-verification.md). Attempt the existing recipe before modernization; do not spend unlimited effort restoring obsolete infrastructure solely for comparison.
- If the baseline cannot build, record the failing command and why modernization is necessary. Keep phase 2 incomplete, explicitly record the handoff in both plans and the log, and establish the first working locked build as the size baseline.
- Preserve the `vfx/ffmpeg` tag, direct CLI invocation, and required media behavior unless a documented decision revises them.
- Preserve Bash access in the initial replacement runtime. A shell-free production image requires a recorded compatibility decision and updated mission, README, and tests; a separate debug target is an option.
- Choose exact versions, target platforms, runtime contents, and numeric size budgets from evidence during execution. No arbitrary version or size target is selected here.
- Treat deterministic dependency selection, identical executable bytes, and identical image digests as separate claims, each requiring its own evidence.
- Registry publication, GPU support, and job orchestration remain outside this phase.

## Execution Order

1. Capture baseline evidence and a required-capability matrix through phase 2.
2. Complete task 1 and task 2 together to establish a working build with locked sources and environment.
3. Complete task 3 using the initial capability set; compare runtime candidates before choosing one.
4. Complete task 4, then repeat task 3's size comparison because codec selection can change the best linking strategy.
5. Complete task 5. Create focused validation scripts alongside earlier tasks and reuse them in CI.

For each task, record commands, target platform, results, and unresolved issues in [IMPLEMENTATION.md](../IMPLEMENTATION.md). Keep task checkboxes and phase status current. Follow [GIT.md](../GIT.md) and preserve unrelated local edits.

## Work Plan

### Task 1: Lock FFmpeg And Every Source Dependency

Deliverable: `build/dependencies.lock.json` and a build helper that consumes it as the single source of archive identities. NASM is retained; Yasm is removed as a redundant assembler input for this recipe.

See [locked source provenance](../SOURCE_PROVENANCE.md) for the current pin rationale and verification evidence.

- [x] 1. Inventory FFmpeg, x264, x265, FDK AAC, LAME, Opus, Ogg, Vorbis, libvpx, NASM, and Yasm, including dependencies introduced by the replacement build. Yasm was only selected to assemble libvpx and is removed in favor of NASM; libvpx's NASM assembler path was exercised successfully in both architecture builds.
- [x] 2. Confirm the selected exact releases or full commit hashes are compatible with the replacement build environment and required media profiles. Record selection rationale and media compatibility; never resolve branch heads or moving snapshots during an ordinary build. All locked sources compiled for `linux/amd64` and `linux/arm64` with Debian 13 Trixie and GCC 14.2.0; FFmpeg configured all currently enabled external codec integrations, the expected encoders are present, and a one-second H.264 encode/probe passed on each architecture. Broader VFX media profiles were defined and tested in Task 4.
- [x] 3. Record each selected dependency's version or commit, source URL, archive SHA-256, and relevant patches. Store patches in the repository so their contents are reviewable.
- [x] 4. Establish checksum provenance. Verify upstream release signatures where available using an identified signing-key fingerprint; document how sources without signatures were checked. FFmpeg and libvorbis detached signatures were verified; publisher checksums and locally computed hashes are distinguished in the provenance record.
- [x] 5. Implement download and extraction from the manifest, preferring HTTPS and failing on HTTP errors or checksum mismatches. Ensure no source is extracted or compiled before verification succeeds.
- [x] 6. Remove duplicate version definitions and all floating source retrieval from the Dockerfile. Pin source submodules too, if any selected dependency requires them.
- [x] 7. Exercise a successful fetch and a deliberately incorrect checksum. Document the controlled process for changing a dependency lock and rerunning its compatibility checks.

Completion evidence: every built source maps to a manifest entry; amd64 and arm64 image builds fetched and verified all locked identities; a checksum mismatch stops before extraction; every configured external encoder is present; the H.264 runtime smoke test passed on both architectures.

### Task 2: Pin The Build Environment

Deliverable: a documented, locked builder environment and explicit target-platform configuration.

- [x] 1. Select `linux/amd64` and `linux/arm64`, with generic x86-64-v1 and ARMv8-A baselines. Production worker inventory is not available yet; confirm these provisional baselines against the actual VFX workers before deployment.
- [x] 2. Pin Debian 13 Trixie by multi-platform image digest and record the amd64 and arm64 manifest identities.
- [x] 3. Pin Debian package repositories to the `20261025T000000Z` snapshot and lock the full package closure for each target architecture.
- [x] 4. Remove unrestricted updates and record exact package, compiler, linker, assembler, CMake, libc, and build-tool versions in build metadata.
- [x] 5. Set generic per-architecture compiler flags and FFmpeg `--cpu=generic`; preserve runtime CPU detection.
- [x] 6. Pin the Dockerfile frontend and BuildKit image by digest. Record the Buildx version and supported local build commands; CI is not configured in this repository yet.
- [x] 7. Run two independent `--no-cache` builds for each architecture and compare source, package, base-image, and toolchain identities. Build output bytes are not claimed to be reproducible by this task.

Completion evidence: two clean builds each of `linux/amd64` and `linux/arm64` used identical source, base-image, package, and toolchain identities. Both architecture images pass FFmpeg/FFprobe startup and a one-second H.264 encode/probe. Production worker CPU inventories and CI remain follow-up items; the selected generic baselines are provisional.

### Task 3: Minimize Runtime Contents

Deliverable: a measured runtime choice and an explicit artifact-copy policy.

- [x] 1. Measure the working baseline and both runtime candidates: total image bytes, gzip-compressed `docker image save` size, executable sizes, and layer contents. Record platform and image identity with every result in the implementation log.
- [x] 2. Inspect runtime linkage using `ldd` on each architecture and verify static candidates report no dynamic executable. The shared runtime uses Debian's loader and resolved shared libraries; runtime data requirements were reviewed against the Task 4 capability matrix.
- [x] 3. Create an explicit output directory containing only `ffmpeg`, `ffprobe`, and collected source license notices. Exclude NASM, codec CLI tools, headers, static archives, sources, and build caches.
- [x] 4. Build and compare shared and fully static runtime candidates for both architectures. The static x265 link needed removal of an unavailable `-lgcc_s` pkg-config token; the resulting builds and runtime checks passed.
- [x] 5. Strip shipping binaries and retain diagnostic copies in the compile stage outside the runtime image. Compare total image sizes for shared and static links; the small static executable reduction does not offset its larger compressed image transfer.
- [x] 6. Test mounted-media reads and writes, both command-line tools, H.264 output properties, absence of build tools, and Bash access on amd64 and arm64. The final media matrix and mounted-file/pipe behavior were checked in Task 4.
- [x] 7. Repeat the shared/static comparison for the final capability set, record the measurements and selected linking strategy, and copy only verified runtime artifacts into the final stage. The shared build has the smaller compressed OCI archive on both architectures; measurements are in the implementation log.

Completion evidence: initial and final shared/static measurements, runtime-content inventory, passing media checks, and no compiler or assembler tools in the production image are recorded in the implementation log.

### Task 4: Define And Minimize Media Capabilities

Deliverable: `docs/MEDIA_SUPPORT.md`, explicit FFmpeg configuration, and representative media tests.

- [x] 1. Define the capability matrix covering common VFX input/output formats, codecs, filters, protocols, bit depths, alpha handling, image sequences, and both target platforms. The user selected preservation of current codecs plus common VFX formats; representative workflows and expected outputs are in [media support](../MEDIA_SUPPORT.md).
- [x] 2. Map the candidate workflows to FFmpeg components and external libraries in the support matrix. Keep all currently configured external codec integrations; broader default FFmpeg components are candidates for removal only where not required by the matrix.
- [x] 3. Add `--disable-autodetect`, explicitly enable the locked codec integrations, and disable unused programs, docs, network access, and capture devices while retaining `ffmpeg` and `ffprobe`.
- [x] 4. Evaluate `--disable-everything` with explicit component enables. Include required demuxers, muxers, parsers, bitstream filters, protocols, and filters; generate redistributable fixtures outside the runtime image because generator/capture devices are excluded. Verify behavior rather than relying solely on encoder listings.
- [x] 5. Audit external dependencies against the selected matrix and remove dependencies only when their capabilities are deliberately excluded. All currently locked external codec libraries remain required by the selected scope; the configured license notices were retained and reviewed.
- [x] 6. Compare `--enable-small` against the ordinary optimized build on representative workloads. On amd64, the 1080p 10-second H.264 medium-preset encode had a 1.484-second ordinary median and a 1.435-second size-optimized median; both produced 1920×1080, 24 fps, 10-second H.264 output. The size-optimized image was 15,107,264 bytes smaller by `docker image inspect` on amd64 and 12,178,196 bytes smaller on arm64. ARM64 encode output correctness passed; only amd64 performance was timed. Retain SIMD and threading.
- [x] 7. Run the representative capability matrix on both targets, publish the resulting support contract, and update README usage. Representative workflow checks passed on both targets and the support contract and operator instructions are published.

Completion evidence: every required workflow passes, enabled capabilities match the documented matrix, and size savings and performance tradeoffs are measured. No required VFX feature is silently removed.

### Task 5: Automate Size And Reproducibility Checks

Deliverable: reusable validation scripts, CI checks, and recorded release/build metadata.

- [ ] 1. Turn the phase 2 smoke checks and capability matrix into scripts that assert expected stream properties and exit unsuccessfully on mismatches. Use synthetic or redistributable fixtures with fixed identities.
- [ ] 2. Add checks for lock-manifest completeness, checksum rejection, exact FFmpeg and dependency identities, runtime linkage, and absence of build tools. Inspect runtime artifacts from the builder when the final image lacks a shell.
- [ ] 3. Add CI build jobs for each supported platform, using pinned actions and toolchain identities. Exercise cold builds as well as ordinary cached builds.
- [ ] 4. Measure final image size with the same metric as task 3 and set a numeric per-platform budget from the measured result. Fail the check on an unreviewed budget overrun; report transfer size separately when available.
- [ ] 5. Build the same revision twice in isolated work directories without reusing compiled artifacts. Compare the hashes of all shipping executables and shared libraries, and publish a useful difference report on failure.
- [ ] 6. Resolve byte differences by controlling build timestamps, `SOURCE_DATE_EPOCH` where supported, source paths, locale, timezone, archive order, and embedded metadata. Do not label differing binary hashes reproducible merely because versions match.
- [ ] 7. Separately compare image content and image digests. Normalize layer/config timestamps and account for provenance metadata if image-digest reproducibility is claimed. Report this separately from binary reproducibility.
- [ ] 8. Record lock identities, target platform, configure flags, artifact hashes, image size, and media-test results as CI artifacts. Document local reproduction and dependency-update commands.

Completion evidence: CI catches an invalid checksum, a missing required capability, a version mismatch, and an image-size overrun. Two independent builds produce identical shipping-binary hashes per platform; image-digest equality is reported separately.

## Validation

- During planning adoption: check Markdown links, unresolved template prompts, whitespace, and consistency with the roadmap. No Dockerfile change or build is part of creating this plan.
- During execution: reuse the commands in [phase 2](02-build-verification.md), then extend validation with each task's completion evidence.
- Keep logs for failed experiments as well as successful builds. Do not invent a baseline size when the legacy recipe cannot build.
- Verify direct CLI invocation, mounted output, required media properties, CPU compatibility, runtime data, and the documented shell/debug workflow on each supported platform.

## Acceptance Criteria

- All five tasks are complete, with measured results linked from the implementation log.
- Every source and build dependency has an immutable identity; builds verify downloaded source contents before use.
- The final runtime is the smallest tested candidate that satisfies the agreed support contract, with a measured size budget and explicit runtime contents.
- Required media workflows pass without missing libraries or accidental host dependencies.
- CI enforces dependency identities, media behavior, and size budgets; independent builds produce matching shipping-binary hashes for the same platform.
- Any remaining image-digest differences are documented without claiming byte-identical images.
- README, mission, support documentation, roadmap, and validation instructions describe the implemented behavior, including any deliberate compatibility changes.

## Reference Guidance

- [Docker build best practices](https://docs.docker.com/build/building/best-practices/): image pinning and build-stage separation.
- [Docker base images](https://docs.docker.com/build/building/base-images/): minimal runtimes and scratch dependencies.
- [FFmpeg downloads](https://www.ffmpeg.org/download.html): release archives and signature verification.
- [FFmpeg configure options](https://github.com/FFmpeg/FFmpeg/blob/master/configure): capability and size controls; consult the selected locked release during implementation.

## Status

Status: in progress

Tasks 1–4 are complete for `linux/amd64` and `linux/arm64`; Task 3's final runtime comparison selects shared linking, and `--enable-small` is enabled by default. Task 2 uses provisional generic CPU baselines pending production-worker inventory; CI is not configured. Task 5 automation remains. The CentOS 7 baseline failed at package setup on both architectures; phase 2 remains in progress. See the implementation log.

Last updated: 2026-10-27
