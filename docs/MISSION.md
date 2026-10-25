# Mission

Provide a containerized FFmpeg command-line environment for visual effects artists and pipeline developers to convert, encode, and inspect media without installing its build dependencies on every workstation or worker.

The intended outcome is an image whose supported codecs, build inputs, and runtime behavior are documented and verified. The existing recipe is the starting point; reproducibility and runtime compatibility have not yet been demonstrated in this setup.

## Development Loop

```text
define media and codec requirements -> update build recipe -> build image -> verify tools and media output -> document operation -> repeat
```

- Keep usage simple: build an image and invoke FFmpeg commands against mounted media.
- Preserve documented command usage and codec support unless a change explicitly revises those expectations.
- Make dependency versions and validation evidence traceable.
- Keep build tools and source trees out of the final runtime stage.
- Record failures with the failing build step or command and enough environment details to reproduce them.

## Engineering Model

- `Dockerfile`: a CentOS 7 compilation stage builds FFmpeg and codec libraries; a separate CentOS 7 runtime stage receives `/root/bin` and adds it to `PATH`.
- Codec configuration: x264, x265, libvpx, FDK AAC, LAME MP3, Opus, and Vorbis are enabled by the recipe. Actual availability must be checked in a built image.
- `README.md`: operator entry point for build commands, invocation, and documentation links.
- `docs/`: mission, direction, execution plans, Git policy, and decision history.
- `templates/project-playbook/`: reusable source templates, retained separately from the adopted project documents.

Media enters and leaves through caller-supplied mounts. No application server, job scheduler, or automated media pipeline is implemented here.

## Quality Bar

- Keep the `vfx/ffmpeg` image tag used by the documented examples unless deliberately revised.
- Preserve direct command invocation and interactive Bash access.
- Validate Dockerfile changes with an image build, tool inspection, and a small synthetic-media encode and probe. Record platform and image identity with results.
- Do not claim a fully static executable, a reproducible build, or successful runtime linking without evidence.
- Explicitly review supported codecs and distribution requirements before publishing an image built with the current GPL and nonfree configuration.
