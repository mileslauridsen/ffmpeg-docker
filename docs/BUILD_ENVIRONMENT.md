# Build Environment Lock

This document records the fixed builder inputs for the amd64 and arm64 images. The machine running Docker is not used to select compiler optimizations.

## Operating System And Packages

- Builder and runtime: Debian GNU/Linux 13 (Trixie), pinned by the multi-platform index digest `sha256:62bd423aeee912639ca8ee681c2b762cb3e25137e0a92b20be455898a9f034ad`.
- Selected platform manifests: amd64 `sha256:4876fdea29cac1a33a3195f1eb1952feb1fca7dd6dd00be3e2f1879cf20d34d2`; arm64 `sha256:a66b19aa552f595b4ab276c6b4f9b24fa4546632c5ecd88cccdced4a6866323a`.
- APT reads only the Debian `trixie` and `trixie-security` `main` suites at snapshot `20261025T000000Z`. The exact requested packages and transitive closure are versioned in `build/apt/builder-{amd64,arm64}.packages`; complete installed package manifests are in `build/apt/resolved-{amd64,arm64}.packages`.
- `build/verify_apt_lock.py` compares the installed package set against the per-platform manifest and fails the image build on any difference. APT verifies Debian's signed repository metadata and package checksums. The snapshot endpoint is HTTP because the initial minimal base does not yet contain the CA bundle; repository signature verification remains enabled.
- The runtime base already contains Bash `5.2.37-2+b10`; the Dockerfile checks this exact version and does not run APT in the runtime stage.
- `build/toolchain.lock.json` records the base, snapshot, package versions, compiler and assembler, CPU baselines, Dockerfile frontend, and BuildKit identities.

## CPU Targets

Task 2 uses generic portable targets until deployment worker CPU details are available:

- `linux/amd64`: x86-64-v1, compiled with `-march=x86-64 -mtune=generic`.
- `linux/arm64`: ARMv8-A, compiled with `-march=armv8-a -mtune=generic`.

The Dockerfile uses BuildKit's `TARGETARCH` value to choose the flags and rejects other architectures. FFmpeg's `--cpu=generic` selects the generic minimum, while runtime CPU detection remains enabled. Do not add `-march=native` or tune from the Docker host. Confirm these baselines against production workers before changing them.

## Docker Build Tools

- Dockerfile frontend: `docker/dockerfile:1.7.1`, pinned in the Dockerfile to index digest `sha256:a57df69d0ea827fb7266491f2813635de6f17269be881f696fbfdf2d83dda33e`.
- BuildKit: `moby/buildkit:v0.33.1`, pinned to index digest `sha256:cec9f139f45e93c5c69c60f8b07cfad9f43f4ef6b6a6cd917527fea5ff2e3dea`.
- Buildx CLI: `v0.37.2` is the version used for this validation. The local Docker Engine is `29.8.2` and includes BuildKit `v0.33.1`.
- `.github/workflows/ci.yml` is configured to run cached image builds and runtime/media checks on pull requests and `main`. A weekly schedule and manual run perform two isolated `--no-cache` builds per architecture, compare shipping binary/library hashes and canonical root-filesystem content/metadata, and report Docker config and manifest digest equality separately. Hosted workflow execution has not yet occurred.
- CI actions are pinned by full commit SHA in the workflow and recorded in `build/toolchain.lock.json`. CI uses native `ubuntu-24.04` amd64 and `ubuntu-24.04-arm` ARM64 runners, plus the pinned Buildx CLI `v0.37.2` and BuildKit image above.

Create and inspect a builder using the pinned BuildKit image:

```sh
docker buildx create --name ffmpeg-pinned --driver docker-container \
  --driver-opt image=moby/buildkit:v0.33.1@sha256:cec9f139f45e93c5c69c60f8b07cfad9f43f4ef6b6a6cd917527fea5ff2e3dea
docker buildx inspect ffmpeg-pinned --bootstrap
```

Build each platform explicitly. `--load` imports the selected single-platform image into the local Docker image store:

```sh
docker buildx build --builder ffmpeg-pinned --platform=linux/amd64 --build-arg SOURCE_DATE_EPOCH=0 --load \
  -t vfx/ffmpeg:locked-amd64 .
docker buildx build --builder ffmpeg-pinned --platform=linux/arm64 --build-arg SOURCE_DATE_EPOCH=0 --load \
  -t vfx/ffmpeg:locked-arm64 .
```

For clean-input comparisons, repeat each command with `--no-cache`. The source archive manifest, Debian package manifest, image base digest, and toolchain lock must match between runs.

## Automated Validation

Run static lock validation on a host with Python 3:

```sh
python3 scripts/validate_lock.py
```

After building an image for one platform, check its version, configure flags, runtime linkage, contents, and size budget, then run representative media conversions:

```sh
python3 scripts/validate_image.py --image vfx/ffmpeg:local-amd64 --platform linux/amd64
python3 scripts/smoke_media.py --image vfx/ffmpeg:local-amd64 --platform linux/amd64
```

Use the corresponding ARM64 image and `--platform linux/arm64` for the ARM64 run. To compare two isolated cold builds, use the pinned Buildx builder:

```sh
python3 scripts/reproducible_build.py \
  --builder ffmpeg-pinned \
  --platform linux/amd64 \
  --metadata /tmp/ffmpeg-repro-amd64.json
```

Image size is measured with `docker image inspect .Size` and checked against [the per-platform budgets](../build/image-size-budgets.json). These budgets are guardrails based on the Task 4 optimized images; revise them deliberately when the capability set or pinned base changes.
