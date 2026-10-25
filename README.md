# ffmpeg-docker
Installation of FFmpeg for use in a VFX pipeline.

Compiled using these instructions:
https://trac.ffmpeg.org/wiki/CompilationGuide/Centos

## Building with docker
```docker build -t vfx/ffmpeg .```

## Running image in an interactive bash shell
```docker run -it --entrypoint='bash' vfx/ffmpeg```

## Project documentation

- [Mission](docs/MISSION.md): purpose, architecture, and quality expectations.
- [Roadmap](docs/ROADMAP.md): phase status and the next planned work.
- [Git workflow](docs/GIT.md): branches, worktree safety, and signed commits.
- [Implementation log](docs/IMPLEMENTATION.md): decisions and validation history.
- [Source provenance](docs/SOURCE_PROVENANCE.md): locked archive identities and checksum evidence.
- [Build environment](docs/BUILD_ENVIRONMENT.md): fixed OS packages, toolchain, CPU baselines, and Docker build tools.
- [Agent guidance](AGENTS.md): project orientation and working loop.

The project playbook is set up. [Build verification](docs/plans/02-build-verification.md)
is the next planned phase; this setup has not verified that the image builds or runs.
