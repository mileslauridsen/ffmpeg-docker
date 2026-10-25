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
RUN cd ~/ffmpeg_sources/ffmpeg && \
	PATH="$HOME/bin:$PATH" PKG_CONFIG_PATH="$HOME/ffmpeg_build/lib/pkgconfig" ./configure \
  --prefix="$HOME/ffmpeg_build" \
  --cpu=generic \
  --pkg-config-flags="--static" \
  --extra-cflags="-I$HOME/ffmpeg_build/include" \
  --extra-ldflags="-L$HOME/ffmpeg_build/lib" \
  --extra-libs=-lpthread \
  --extra-libs=-lm \
  --bindir="$HOME/bin" \
  --enable-gpl \
  --enable-libfdk_aac \
  --enable-libmp3lame \
  --enable-libopus \
  --enable-libvorbis \
  --enable-libvpx \
  --enable-libx264 \
  --enable-libx265 \
  --enable-nonfree && \
	make && \
	make install && \
	hash -r

# Remove source directory and clean yum
RUN rm -r ~/ffmpeg_sources ~/ffmpeg_build

FROM debian:trixie-slim@sha256:62bd423aeee912639ca8ee681c2b762cb3e25137e0a92b20be455898a9f034ad AS runtime-image

RUN test "$(dpkg-query -W -f='${Version}' bash)" = '5.2.37-2+b10' && \
    printf '%s\n' 'export PATH="/root/bin:$PATH"' > /etc/profile.d/ffmpeg-path.sh

COPY --from=compile-image /root/bin /root/bin
ENV PATH=/root/bin:$PATH
