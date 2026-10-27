# syntax=docker/dockerfile:1.7.1@sha256:a57df69d0ea827fb7266491f2813635de6f17269be881f696fbfdf2d83dda33e

# Debian 13 (Trixie) multi-platform index pinned to sha256:62bd423a.
FROM debian:trixie-slim@sha256:62bd423aeee912639ca8ee681c2b762cb3e25137e0a92b20be455898a9f034ad AS compile-image

ARG TARGETARCH
ENV PATH="/root/bin:${PATH}"
COPY build /build

# Use the immutable Debian archive state and install the exact, architecture-specific package closure.
RUN set -eu; \
    test "$TARGETARCH" = amd64 -o "$TARGETARCH" = arm64; \
    rm -f /etc/apt/sources.list.d/debian.sources /etc/apt/sources.list; \
    cp /build/apt/sources.list /etc/apt/sources.list; \
    apt-get update -o Acquire::Retries=3 -o Acquire::http::Timeout=30; \
    apt-get install -y --no-install-recommends $(tr '\n' ' ' < "/build/apt/builder-${TARGETARCH}.packages"); \
    python3 /build/verify_apt_lock.py "$TARGETARCH"; \
    rm -rf /var/lib/apt/lists/* && \
    mkdir -p ~/ffmpeg_sources/downloads

# Compile generic x86-64-v1 or ARMv8-A code. FFmpeg and the codecs retain runtime CPU dispatch.
RUN set -eu; \
    case "$TARGETARCH" in \
        amd64) CPU_FLAGS='-march=x86-64 -mtune=generic' ;; \
        arm64) CPU_FLAGS='-march=armv8-a -mtune=generic' ;; \
    esac; \
    printf '#!/bin/sh\nexec /usr/bin/gcc %s "$@"\n' "$CPU_FLAGS" > /usr/local/bin/ffmpeg-gcc; \
    printf '#!/bin/sh\nexec /usr/bin/g++ %s "$@"\n' "$CPU_FLAGS" > /usr/local/bin/ffmpeg-g++; \
    chmod 755 /usr/local/bin/ffmpeg-gcc /usr/local/bin/ffmpeg-g++
ENV CC=/usr/local/bin/ffmpeg-gcc
ENV CXX=/usr/local/bin/ffmpeg-g++

# Fetch only locked source archives; the helper verifies each digest and the FFmpeg signature before extraction.
RUN python3 -u /build/fetch_sources.py --all \
    --output-dir ~/ffmpeg_sources/downloads \
    --extract-dir ~/ffmpeg_sources

# Install NASM
RUN cd ~/ffmpeg_sources/nasm && \
	./configure --prefix="$HOME/ffmpeg_build" --bindir="$HOME/bin" && \
	make && \
	make install && \
	hash -r

# Install libx264
RUN cd ~/ffmpeg_sources/x264 && \
	./configure --prefix="$HOME/ffmpeg_build" --bindir="$HOME/bin" --enable-static && \
	make && \
	make install && \
	hash -r

# Install libx265
RUN cd ~/ffmpeg_sources/x265/build/linux && \
	cmake -G "Unix Makefiles" -DCMAKE_INSTALL_PREFIX="$HOME/ffmpeg_build" -DENABLE_SHARED:bool=off ../../source && \
	make && \
	make install

# Install libfdk_aac
RUN cd ~/ffmpeg_sources/fdk-aac && \
	autoreconf -fiv && \
	./configure --prefix="$HOME/ffmpeg_build" --disable-shared && \
	make && \
	make install

# Install libmp3lame
RUN cd ~/ffmpeg_sources/lame && \
	./configure --prefix="$HOME/ffmpeg_build" --bindir="$HOME/bin" --disable-shared --enable-nasm && \
	make && \
	make install

# Install libopus
RUN cd ~/ffmpeg_sources/opus && \
	./configure --prefix="$HOME/ffmpeg_build" --disable-shared && \
	make && \
	make install

# libogg
RUN cd ~/ffmpeg_sources/libogg && \
	./configure --prefix="$HOME/ffmpeg_build" --disable-shared && \
	make && \
	make install

# Install libvorbis
RUN cd ~/ffmpeg_sources/libvorbis && \
	./configure --prefix="$HOME/ffmpeg_build" --with-ogg="$HOME/ffmpeg_build" --disable-shared && \
	make && \
	make install

# Install libvpx
RUN cd ~/ffmpeg_sources/libvpx && \
	./configure --prefix="$HOME/ffmpeg_build" --disable-examples --disable-unit-tests --enable-vp9-highbitdepth --as=nasm && \
	make && \
	make install

# Install ffmpeg
ARG EXTRA_LDEXEFLAGS=""
ARG ENABLE_SMALL=1
RUN set -eu; \
    if [ "$EXTRA_LDEXEFLAGS" = "-static" ]; then \
        sed -i 's/-lgcc_s//g' "$HOME/ffmpeg_build/lib/pkgconfig/x265.pc"; \
    fi; \
    if [ "$ENABLE_SMALL" = 1 ]; then SMALL_FLAG=--enable-small; \
    elif [ "$ENABLE_SMALL" = 0 ]; then SMALL_FLAG=; \
    else echo "ENABLE_SMALL must be 0 or 1" >&2; exit 2; fi; \
    cd ~/ffmpeg_sources/ffmpeg && \
	PATH="$HOME/bin:$PATH" PKG_CONFIG_PATH="$HOME/ffmpeg_build/lib/pkgconfig" ./configure \
  --prefix="$HOME/ffmpeg_build" \
  --cpu=generic \
  --pkg-config-flags="--static" \
  --extra-cflags="-I$HOME/ffmpeg_build/include" \
  --extra-ldflags="-L$HOME/ffmpeg_build/lib" \
  --extra-ldexeflags="$EXTRA_LDEXEFLAGS" \
  --extra-libs=-lpthread \
  --extra-libs=-lm \
  --bindir="$HOME/bin" \
  --disable-autodetect \
  --disable-programs \
  --enable-ffmpeg \
  --enable-ffprobe \
  --disable-doc \
  --enable-zlib \
  --disable-avdevice \
  --disable-indevs \
  --disable-outdevs \
  --disable-network \
  --disable-everything \
  --enable-demuxer=aiff \
  --enable-demuxer=avi \
  --enable-demuxer=concat \
  --enable-demuxer=flac \
  --enable-demuxer=image2 \
  --enable-demuxer=image2pipe \
  --enable-demuxer=matroska \
  --enable-demuxer=mov \
  --enable-demuxer=mp3 \
  --enable-demuxer=mxf \
  --enable-demuxer=ogg \
  --enable-demuxer=wav \
  --enable-decoder=aac \
  --enable-decoder=dnxhd \
  --enable-decoder=dpx \
  --enable-decoder=exr \
  --enable-decoder=ffv1 \
  --enable-decoder=flac \
  --enable-decoder=h264 \
  --enable-decoder=hevc \
  --enable-decoder=libvpx_vp8 \
  --enable-decoder=libvpx_vp9 \
  --enable-decoder=mjpeg \
  --enable-decoder=mp3 \
  --enable-decoder=opus \
  --enable-decoder=pcm_s16be \
  --enable-decoder=pcm_s16le \
  --enable-decoder=pcm_s24be \
  --enable-decoder=pcm_s24le \
  --enable-decoder=pcm_s32be \
  --enable-decoder=pcm_s32le \
  --enable-decoder=png \
  --enable-decoder=prores \
  --enable-decoder=tiff \
  --enable-decoder=vorbis \
  --enable-decoder=vp8 \
  --enable-decoder=vp9 \
  --enable-encoder=aac \
  --enable-encoder=dnxhd \
  --enable-encoder=dpx \
  --enable-encoder=exr \
  --enable-encoder=ffv1 \
  --enable-encoder=flac \
  --enable-encoder=libfdk_aac \
  --enable-encoder=libmp3lame \
  --enable-encoder=libopus \
  --enable-encoder=libvorbis \
  --enable-encoder=libx264 \
  --enable-encoder=libx265 \
  --enable-encoder=libvpx_vp8 \
  --enable-encoder=libvpx_vp9 \
  --enable-encoder=mjpeg \
  --enable-encoder=pcm_s16le \
  --enable-encoder=pcm_s16be \
  --enable-encoder=pcm_s24le \
  --enable-encoder=pcm_s24be \
  --enable-encoder=pcm_s32le \
  --enable-encoder=pcm_s32be \
  --enable-encoder=png \
  --enable-encoder=prores_ks \
  --enable-encoder=tiff \
  --enable-filter=alphaextract \
  --enable-filter=alphamerge \
  --enable-filter=anull \
  --enable-filter=aformat \
  --enable-filter=aresample \
  --enable-filter=atrim \
  --enable-filter=colorspace \
  --enable-filter=concat \
  --enable-filter=crop \
  --enable-filter=fps \
  --enable-filter=format \
  --enable-filter=lut \
  --enable-filter=lut3d \
  --enable-filter=null \
  --enable-filter=overlay \
  --enable-filter=pad \
  --enable-filter=scale \
  --enable-filter=setpts \
  --enable-filter=setparams \
  --enable-filter=tonemap \
  --enable-filter=trim \
  --enable-filter=volume \
  --enable-muxer=aiff \
  --enable-muxer=flac \
  --enable-muxer=image2 \
  --enable-muxer=image2pipe \
  --enable-muxer=matroska \
  --enable-muxer=mov \
  --enable-muxer=mp3 \
  --enable-muxer=mp4 \
  --enable-muxer=mxf \
  --enable-muxer=ogg \
  --enable-muxer=wav \
  --enable-muxer=webm \
  --enable-bsf=aac_adtstoasc \
  --enable-bsf=h264_mp4toannexb \
  --enable-bsf=hevc_mp4toannexb \
  --enable-bsf=null \
  --enable-bsf=vp9_superframe \
  --enable-bsf=vp9_superframe_split \
  --enable-parser=aac \
  --enable-parser=dnxhd \
  --enable-parser=h264 \
  --enable-parser=hevc \
  --enable-parser=mjpeg \
  --enable-parser=mpeg4video \
  --enable-parser=mpegvideo \
  --enable-parser=opus \
  --enable-parser=png \
  --enable-parser=vp8 \
  --enable-parser=vp9 \
  --enable-protocol=file \
  --enable-protocol=pipe \
  $SMALL_FLAG \
  --enable-gpl \
  --enable-libfdk_aac \
  --enable-libmp3lame \
  --enable-libopus \
  --enable-libvorbis \
  --enable-libvpx \
  --enable-libx264 \
  --enable-libx265 \
  --enable-nonfree || { tail -n 80 ffbuild/config.log; exit 1; }; \
	make && \
	make install && \
	hash -r

# Keep diagnostic binaries in the builder, but ship only the stripped FFmpeg CLI tools and source notices.
COPY scripts/collect_licenses.py /tmp/collect_licenses.py
RUN set -eu; \
    mkdir -p /root/ffmpeg_runtime/bin /root/ffmpeg_runtime/share/licenses /root/ffmpeg_diagnostics; \
    cp "$HOME/bin/ffmpeg" "$HOME/bin/ffprobe" /root/ffmpeg_diagnostics/; \
    cp "$HOME/bin/ffmpeg" "$HOME/bin/ffprobe" /root/ffmpeg_runtime/bin/; \
    for source in ffmpeg nasm x264 x265 fdk-aac lame opus libogg libvorbis libvpx; do \
        license_dir="/root/ffmpeg_runtime/share/licenses/$source"; \
        mkdir -p "$license_dir"; \
        python3 /tmp/collect_licenses.py "$HOME/ffmpeg_sources/$source" "$license_dir"; \
    done; \
    strip --strip-unneeded /root/ffmpeg_runtime/bin/ffmpeg /root/ffmpeg_runtime/bin/ffprobe

# Remove source trees and static build dependencies after capturing the runtime artifacts.
RUN rm -r ~/ffmpeg_sources ~/ffmpeg_build

FROM debian:trixie-slim@sha256:62bd423aeee912639ca8ee681c2b762cb3e25137e0a92b20be455898a9f034ad AS runtime-image

RUN test "$(dpkg-query -W -f='${Version}' bash)" = '5.2.37-2+b10' && \
    printf '%s\n' 'export PATH="/root/bin:$PATH"' > /etc/profile.d/ffmpeg-path.sh

COPY --from=compile-image /root/ffmpeg_runtime/bin /root/bin
COPY --from=compile-image /root/ffmpeg_runtime/share/licenses /usr/share/doc/ffmpeg-build/licenses
ENV PATH=/root/bin:$PATH
