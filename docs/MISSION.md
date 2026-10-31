# Mission

Provide a containerized FFmpeg command-line environment for visual effects artists and pipeline developers to convert, encode, and inspect media without installing its build dependencies on every workstation or worker.

The intended outcome is an image whose supported codecs, build inputs, and runtime behavior are documented and verified. The supported media contract is recorded in [MEDIA_SUPPORT.md](MEDIA_SUPPORT.md); representative workflows have been built and exercised on both target architectures. Two independent cold builds now match on runtime binaries, canonical rootfs content and metadata, image config, and manifest for both targets. A pinned CI workflow is configured to build and inspect each target; the push-triggered hosted checks passed on both targets. The hosted scheduled/manual cold-reproducibility job has not run yet.

## Development Loop

```text
define media and codec requirements -> update build recipe -> build image -> verify tools and media output -> document operation -> repeat
```

- Keep usage simple: build an image and invoke FFmpeg commands against mounted media.
- Preserve documented command usage and the support contract unless a change explicitly revises those expectations.
- Make dependency versions and validation evidence traceable.
- Keep build tools and source trees out of the final runtime stage.
- Record failures with the failing build step or command and enough environment details to reproduce them.

## Engineering Model

- `Dockerfile`: a Debian 13 Trixie compilation stage builds pinned FFmpeg and codec sources; a separate digest-pinned runtime stage receives only `ffmpeg`, `ffprobe`, and collected source notices.
- Codec configuration: an explicit `--disable-everything` component set retains the documented VFX and audio workflows on CPU-only `linux/amd64` and `linux/arm64` images. See [MEDIA_SUPPORT.md](MEDIA_SUPPORT.md) for scope, tested properties, and limitations.
- `README.md`: operator entry point for build commands, invocation, and documentation links.
- `docs/`: mission, direction, execution plans, Git policy, and decision history.
- `templates/project-playbook/`: reusable source templates, retained separately from the adopted project documents.

Media enters and leaves through caller-supplied mounts. No application server, job scheduler, or automated media pipeline is implemented here.

## Quality Bar

- Keep the `vfx/ffmpeg` image tag used by the documented examples unless deliberately revised.
- Preserve direct command invocation and interactive Bash access.
- Validate Dockerfile changes with an image build, tool inspection, and representative media encodes/probes on both target platforms. Record platform and image identity with results.
- Do not claim a fully static executable, a reproducible build, or successful runtime linking without evidence.
- Explicitly review supported codecs and distribution requirements before publishing an image built with the current GPL and nonfree configuration.
