# ffmpeg-docker
Installation of FFmpeg for use in a VFX pipeline.

Compiled using these instructions:
https://trac.ffmpeg.org/wiki/CompilationGuide/Centos

## Building with docker
```docker build -t vfx/ffmpeg .```

## Running image in an interactive bash shell
```docker run -it --entrypoint='bash' vfx/ffmpeg```
