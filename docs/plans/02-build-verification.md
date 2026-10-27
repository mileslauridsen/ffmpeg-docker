# Plan: Build Verification

## Goal

Establish and document a working build and runtime baseline for the FFmpeg image, addressing demonstrated failures with focused changes.

## Current State

- The initial Dockerfile used `centos:centos7`; its package repositories failed for ARM64 and amd64. The replacement build and runtime stages now use Debian 13 Trixie pinned by digest.
- Codec libraries and FFmpeg now use the pinned source manifest described in [phase 3](03-small-deterministic-image.md).
- The runtime stage copies only the verified FFmpeg executables and source notices. Shared-library requirements were inspected and the shared runtime was exercised on both target architectures.
- No automated build or media smoke checks are present.
- The Docker daemon and ARM64 Linux engine were reached on 2026-10-25. CentOS 7 builds failed at `yum update` for both ARM64 and amd64 because the configured mirrorlist/base URL was unavailable. The replacement Debian 13 builds completed for both architectures; see the [implementation log](../IMPLEMENTATION.md). Mounted H.264 encode/probe and login Bash checks passed on both.

## Decisions And Boundaries

- Establish the required host and target platform, codecs, and media profiles before selecting broad dependency changes.
- Preserve the documented image tag, direct CLI invocation, and shell access unless the plan records a deliberate revision.
- Diagnose build failures in order. Record changes to source locations, versions, base image, and runtime dependencies with their evidence.
- Defer registry publication, deployment automation, GPU encoding, and general pipeline orchestration.

## Work Plan

### 1. Capture The Baseline

- Check Docker daemon access and record host architecture, target platform, Docker version, and build inputs.
- Attempt the current build and capture the first actionable failure or resulting image identity.
- Record whether source revisions can be recovered; do not label the snapshot recipe reproducible.

### 2. Resolve Demonstrated Build And Runtime Failures

- Repair source retrieval, compiler compatibility, or runtime dependencies as evidence requires.
- Inspect `ffmpeg -version`, `ffprobe -version`, build configuration, and the encoder list in the resulting image.
- Confirm all configured codec integrations are present, or explicitly document and approve changes to the supported set.

### 3. Exercise Media And Document Usage

- Encode a short synthetic H.264 video in the container and inspect it with ffprobe.
- Exercise representative required audio and video codecs once media requirements are established.
- Verify writable mounted output and interactive Bash access.
- Update operator instructions and the implementation log with actual results and any unresolved limitations.

## Validation

Run from the repository root on the selected Docker platform. These commands are planned checks, not recorded results:

```sh
docker version
docker build --progress=plain -t vfx/ffmpeg .
docker image inspect vfx/ffmpeg
docker run --rm vfx/ffmpeg ffmpeg -version
docker run --rm vfx/ffmpeg ffprobe -version
docker run --rm vfx/ffmpeg ffmpeg -buildconf
docker run --rm vfx/ffmpeg ffmpeg -encoders
docker run --rm --entrypoint bash vfx/ffmpeg -lc 'command -v ffmpeg && command -v ffprobe'

mkdir -p /tmp/ffmpeg-docker-smoke
docker run --rm -v /tmp/ffmpeg-docker-smoke:/media -w /media \
  vfx/ffmpeg ffmpeg -y -f lavfi -i testsrc2=size=128x128:rate=24 \
  -t 1 -c:v libx264 -pix_fmt yuv420p smoke.mp4
docker run --rm -v /tmp/ffmpeg-docker-smoke:/media -w /media \
  vfx/ffmpeg ffprobe -v error -show_streams -show_format -of json smoke.mp4
```

Inspect the probe output for H.264 video, 128x128 dimensions, 24 fps, and approximately one second of media. Use a fresh output directory for independent runs. Adapt the mount path if the host cannot share `/tmp` with Docker.

## Acceptance Criteria

- An image builds on the documented target platform; build inputs, image identity, and commands are recorded.
- Both executables start without missing-library errors in the runtime stage.
- Configured encoders are available, with any intentional support changes documented.
- The synthetic encode succeeds and the probe output matches the expected stream properties.
- Mounted output and Bash invocation work; README instructions match verified behavior.
- Failures and deferred requirements remain explicit; a failed baseline attempt alone does not complete this phase.

## Status

Status: in progress

The targets are `linux/amd64` and `linux/arm64`; replacement builds, CLI startup, configured encoder inventory, mounted H.264 smoke tests, login Bash checks, and the phase 3 Task 4 representative media matrix passed on both. Phase 2 remains in progress pending an acceptance review of its legacy baseline and recorded replacement evidence.

Last updated: 2026-10-27
