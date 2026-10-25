# Debian 13 (Trixie) multi-platform index pinned to sha256:62bd423a.
FROM debian:trixie-slim@sha256:62bd423aeee912639ca8ee681c2b762cb3e25137e0a92b20be455898a9f034ad AS compile-image

ENV PATH="/root/bin:${PATH}"
COPY build /build

# Install the compiler and tools required by the locked source builds.
RUN apt-get update && \
    apt-get install -y --no-install-recommends autoconf automake bzip2 ca-certificates \
        cmake g++ gcc gpgv gnupg2 libfreetype6-dev libtool make pkg-config \
        python3 xz-utils zlib1g-dev && \
    rm -rf /var/lib/apt/lists/* && \
    mkdir -p ~/ffmpeg_sources/downloads

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

RUN apt-get update && \
    apt-get install -y --no-install-recommends bash && \
    rm -rf /var/lib/apt/lists/* && \
    printf '%s\n' 'export PATH="/root/bin:$PATH"' > /etc/profile.d/ffmpeg-path.sh

COPY --from=compile-image /root/bin /root/bin
ENV PATH=/root/bin:$PATH
