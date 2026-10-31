# ffmpeg-docker
FFmpeg command-line tools for VFX and media conversion workflows. The supported codec and format contract is documented in [Media Support](docs/MEDIA_SUPPORT.md).

## Build

Create the pinned BuildKit builder described in [Build Environment](docs/BUILD_ENVIRONMENT.md), then build for one target:

```sh
docker buildx build --builder ffmpeg-pinned --platform=linux/amd64 --build-arg SOURCE_DATE_EPOCH=0 --load -t vfx/ffmpeg .
```

Use `--platform=linux/arm64` for the ARM64 image.

## Run

Invoke the CLI directly and mount media into the container:

```sh
docker run --rm -v "$PWD/media:/media" vfx/ffmpeg ffmpeg -i /media/input.mov /media/output.mp4
```

## Running image in an interactive bash shell
```docker run -it --entrypoint='bash' vfx/ffmpeg```

## Project documentation

- [Mission](docs/MISSION.md): purpose, architecture, and quality expectations.
- [Roadmap](docs/ROADMAP.md): phase status and the next planned work.
- [Git workflow](docs/GIT.md): branches, worktree safety, and signed commits.
- [Implementation log](docs/IMPLEMENTATION.md): decisions and validation history.
- [Source provenance](docs/SOURCE_PROVENANCE.md): locked archive identities and checksum evidence.
- [Build environment](docs/BUILD_ENVIRONMENT.md): fixed OS packages, toolchain, CPU baselines, and Docker build tools.
- [Media support](docs/MEDIA_SUPPORT.md): tested formats, codecs, workflows, and explicit exclusions.
- [Automated validation](docs/BUILD_ENVIRONMENT.md#automated-validation): lock, runtime, media, size-budget, and cold-build checks.
- [Agent guidance](AGENTS.md): project orientation and working loop.

The project roadmap and task state are in [docs/ROADMAP.md](docs/ROADMAP.md). Task 4's representative workflow evidence and known limits are recorded in [docs/MEDIA_SUPPORT.md](docs/MEDIA_SUPPORT.md) and [docs/IMPLEMENTATION.md](docs/IMPLEMENTATION.md).
