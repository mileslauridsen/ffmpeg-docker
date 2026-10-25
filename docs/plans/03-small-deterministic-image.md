# Plan: Small Image And Deterministic Dependencies

## Goal

Produce the smallest measured FFmpeg runtime image that meets the documented VFX requirements, with exact source and build-environment versions and automated checks against dependency drift and size regressions.

## Current State

- The Dockerfile separates compilation and runtime stages and now uses a digest-pinned Debian 13 Trixie base for amd64 and arm64 targets.
- FFmpeg and its nine source dependencies now have immutable identities, archive checksums, and signature checks where available.
- Debian package resolution and the builder toolchain are snapshot-pinned for amd64 and arm64; see [build environment](../BUILD_ENVIRONMENT.md).
- The runtime copies all of `/root/bin`, including installed assembler tools, rather than an explicit runtime artifact set.
- Configured encoders and one H.264 workflow have been verified. Broader required media profiles, runtime linkage, and image sizes remain unmeasured.
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
- [x] 2. Confirm the selected exact releases or full commit hashes are compatible with the replacement build environment and required media profiles. Record selection rationale and media compatibility; never resolve branch heads or moving snapshots during an ordinary build. All locked sources compiled for `linux/amd64` and `linux/arm64` with Debian 13 Trixie and GCC 14.2.0; FFmpeg configured all currently enabled external codec integrations, the expected encoders are present, and a one-second H.264 encode/probe passed on each architecture. Broader VFX media profiles remain for Task 4 because the project has not defined them yet.
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

- [ ] 1. Measure the current working baseline: total uncompressed image bytes, compressed transfer size when available, executable sizes, and layer contents. Record platform and image identity with every result.
- [ ] 2. Inspect executable dependencies with ELF inspection tools in the builder. Enumerate required loaders, shared libraries, certificates, fonts, and other data from the capability matrix; do not infer full static linkage from pkg-config flags.
- [ ] 3. Create an explicit output directory containing only `ffmpeg`, `ffprobe`, required runtime dependencies, and required notices. Exclude NASM, Yasm, codec CLI tools, headers, static archives, sources, and build caches.
- [ ] 4. Build a minimal shared-library runtime candidate and a fully static candidate where supported by the selected libraries. If a candidate is infeasible, record the failing evidence rather than claiming a size comparison.
- [ ] 5. Strip shipping binaries while retaining diagnostic artifacts outside the runtime image. Measure the total image; account for duplicated library code in separate static executables.
- [ ] 6. Test mounted-media reads and writes, both command-line tools, required runtime data, and Bash access. For a shell-free candidate, resolve the documented Bash compatibility decision before selecting it as production output.
- [ ] 7. Select the smallest passing candidate, record the comparison and rejected alternatives, and copy only its verified artifacts into the final stage. Repeat after task 4.

Completion evidence: a before/after table using consistent size metrics, a runtime-content inventory, passing runtime checks, and no compiler or assembler tools in the production image.

### Task 4: Define And Minimize Media Capabilities

Deliverable: `docs/MEDIA_SUPPORT.md`, explicit FFmpeg configuration, and representative media tests.

- [ ] 1. Define a capability matrix covering required input/output formats, codecs, filters, protocols, bit depths, alpha handling, image sequences, and supported platforms. Record representative user workflows and expected outputs.
- [ ] 2. Map every requirement to FFmpeg components and external libraries. Classify the currently enabled codecs as required or optional; record any intentional support removal before implementing it.
- [ ] 3. Set `--disable-autodetect` and explicitly enable required external integrations. Disable unused programs and documentation while retaining `ffmpeg` and `ffprobe`.
- [ ] 4. Evaluate `--disable-everything` with explicit component enables. Include required demuxers, muxers, parsers, bitstream filters, protocols, filters, and test-only generators where needed; verify behavior rather than relying solely on encoder listings.
- [ ] 5. Remove unnecessary external dependencies from the build and lock manifest only after their capabilities are deliberately excluded. Recheck the resulting configuration and required license notices.
- [ ] 6. Compare `--enable-small` against the ordinary optimized build on representative workloads. Record encoding time, output correctness, and image-size differences; retain SIMD and threading unless evidence supports changing them.
- [ ] 7. Run the complete capability matrix and publish the resulting support contract. Repeat runtime-size measurements with the final capability set and update README usage.

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

Tasks 1 and 2 are complete for `linux/amd64` and `linux/arm64`. Task 2 uses provisional generic CPU baselines pending production-worker inventory; CI is not configured. Broader VFX media profiles remain undefined and are assigned to Task 4. The CentOS 7 baseline failed at package setup on both architectures; phase 2 remains in progress. See the implementation log.

Last updated: 2026-10-25
