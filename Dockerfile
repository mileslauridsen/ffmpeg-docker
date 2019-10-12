#Download base image centos 7
FROM centos:centos7 AS compile-image

ENV PATH="/root/bin:${PATH}"

# Update software repository
# Install dependencies
# Make source directory
RUN	yum -y update && yum clean all && \
	yum -y install autoconf automake bzip2 cmake freetype-devel gcc gcc-c++ git libtool make mercurial pkgconfig zlib-devel hg && \
	mkdir ~/ffmpeg_sources

# Install NASM
RUN cd ~/ffmpeg_sources && \
	curl -O -L http://www.nasm.us/pub/nasm/releasebuilds/2.13.02/nasm-2.13.02.tar.bz2 && \
	tar xjvf nasm-2.13.02.tar.bz2 && \
	cd nasm-2.13.02 && \
	./autogen.sh && \
	./configure --prefix="$HOME/ffmpeg_build" --bindir="$HOME/bin" && \
	make && \
	make install && \
	cd ../ && \
	rm -r nasm* && \
	yum erase nasm && hash -r

# Install Yasm
RUN cd ~/ffmpeg_sources && \
	curl -O -L http://www.tortall.net/projects/yasm/releases/yasm-1.3.0.tar.gz && \
	tar xzvf yasm-1.3.0.tar.gz && \
	cd yasm-1.3.0 && \
	./configure --prefix="$HOME/ffmpeg_build" --bindir="$HOME/bin" && \
	make && \
	make install && \
	cd ../ && \
	rm -r yasm*

# Install libx264
RUN cd ~/ffmpeg_sources && \
	yum -y remove nasm && hash -r && \
	git clone --depth 1 http://git.videolan.org/git/x264 && \
	cd x264 && \
	./configure --prefix="$HOME/ffmpeg_build" --bindir="$HOME/bin" --enable-static && \
	make && \
	make install && \
	cd ../ && \
	rm -r x264*

# Install libx265
RUN cd ~/ffmpeg_sources && \
	hg clone https://bitbucket.org/multicoreware/x265 && \
	cd ~/ffmpeg_sources/x265/build/linux && \
	cmake -G "Unix Makefiles" -DCMAKE_INSTALL_PREFIX="$HOME/ffmpeg_build" -DENABLE_SHARED:bool=off ../../source && \
	make && \
	make install && \
	cd ~/ffmpeg_sources && \
	rm -r x265*

# Install libfdk_aac
RUN cd ~/ffmpeg_sources && \
	git clone --depth 1 https://github.com/mstorsjo/fdk-aac && \
	cd fdk-aac && \
	autoreconf -fiv && \
	./configure --prefix="$HOME/ffmpeg_build" --disable-shared && \
	make && \
	make install && \
	rm -r fdk-aac*

# Install libmp3lame
RUN cd ~/ffmpeg_sources && \
	curl -O -L http://downloads.sourceforge.net/project/lame/lame/3.100/lame-3.100.tar.gz && \
	tar xzvf lame-3.100.tar.gz && \
	cd lame-3.100 && \
	./configure --prefix="$HOME/ffmpeg_build" --bindir="$HOME/bin" --disable-shared --enable-nasm && \
	make && \
	make install && \
	cd ../ && \
	rm -r lame*

# Install libopus
RUN cd ~/ffmpeg_sources && \
	curl -O -L https://archive.mozilla.org/pub/opus/opus-1.2.1.tar.gz && \
	tar xzvf opus-1.2.1.tar.gz && \
	cd opus-1.2.1 && \
	./configure --prefix="$HOME/ffmpeg_build" --disable-shared && \
	make && \
	make install && \
	cd ../ && \
	rm -r opus*

# libogg
RUN cd ~/ffmpeg_sources && \
	curl -O -L http://downloads.xiph.org/releases/ogg/libogg-1.3.3.tar.gz && \
	tar xzvf libogg-1.3.3.tar.gz && \
	cd libogg-1.3.3 && \
	./configure --prefix="$HOME/ffmpeg_build" --disable-shared && \
	make && \
	make install && \
	cd ../ && \
	rm -r libogg*

# Install libvorbis
RUN cd ~/ffmpeg_sources && \
	curl -O -L http://downloads.xiph.org/releases/vorbis/libvorbis-1.3.5.tar.gz && \
	tar xzvf libvorbis-1.3.5.tar.gz && \
	cd libvorbis-1.3.5 && \
	./configure --prefix="$HOME/ffmpeg_build" --with-ogg="$HOME/ffmpeg_build" --disable-shared && \
	make && \
	make install && \
	cd ../ && \
	rm -r libvorbis*

# Install libvpx
RUN cd ~/ffmpeg_sources && \
	git clone --depth 1 https://chromium.googlesource.com/webm/libvpx.git && \
	cd libvpx && \
	./configure --prefix="$HOME/ffmpeg_build" --disable-examples --disable-unit-tests --enable-vp9-highbitdepth --as=yasm && \
	make && \
	make install && \
	cd ../ && \
	rm -r libvpx*

# Install ffmpeg
RUN cd ~/ffmpeg_sources && \
	curl -O -L https://ffmpeg.org/releases/ffmpeg-snapshot.tar.bz2 && \
	tar xjvf ffmpeg-snapshot.tar.bz2 && \
	cd ffmpeg && \
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
	cd ../ && \
	rm -r ffmpeg* && \
	hash -r

# Remove source directory and clean yum
RUN	rm -r ~/ffmpeg_sources && \
    rm -r ~/ffmpeg_build && \
	yum -y remove cmake gcc gcc-c++ git make mercurial hg && \
	yum -y clean all && \
	rm -rf /var/cache/yum

FROM centos:centos7 AS runtime-image

COPY --from=compile-image /root/bin /root/bin
ENV PATH=/root/bin:$PATH
