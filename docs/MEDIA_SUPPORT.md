# Media Support Contract

## Scope

This is the phase 3 Task 4 support contract based on the selected direction: keep the current codec integrations and support common VFX conversion workflows. It targets the CPU-only `linux/amd64` and `linux/arm64` images with generic x86-64-v1 and ARMv8-A baselines. It does not promise hardware acceleration, real-time capture/playback, ACES compliance, deep EXR, or every format FFmpeg can recognize.

Workflow validation used generated media fixtures on both target architectures. The fixtures were generated outside the runtime image because lavfi and other capture devices are intentionally disabled. This validates selected representative profiles; it does not establish interoperability with every variant of each container or codec.

## Required Workflows

| Workflow | Required input and output | Required media behavior | Validation |
| --- | --- | --- | --- |
| Review movie | Read MP4; write H.264 video and AAC audio in MP4 | 8-bit 4:2:0 H.264; verify frame rate, dimensions, and duration | Passed on amd64 and arm64: 64×64, 24 fps, H.264/AAC, 1.002 s |
| High-quality delivery | Read MXF; write DNxHD/DNxHR in MXF; write ProRes 422 HQ in MOV | 10-bit 4:2:2 output; verify frame rate and dimensions | Passed on both: 1920×1080, 24 fps, DNxHD `yuv422p10le`; ProRes `yuv422p10le` |
| Alpha master | Read RGBA OpenEXR or PNG; write ProRes 4444 in MOV | Preserve alpha through input, encoding, and decode | Passed on both: ProRes 4444 stream `yuva444p12le`; extracted alpha was non-opaque (8-bit range 127–127) for EXR and PNG sources |
| HDR/high-bit-depth sequence | Read/write numbered OpenEXR, DPX, PNG, and TIFF sequences | OpenEXR half/float RGB(A); DPX 10/12-bit RGB; verify frame count and numbering | Passed on both: two-frame EXR and PNG sequences, DPX sequence round trip, EXR half→float, DPX 10/12-bit, TIFF output. HDR colorimetric fidelity was not tested. |
| Web delivery | Read MP4; write VP8 or VP9 with Opus in WebM; read WebM | Verify frame rate, dimensions, duration, and VP9 10-bit output | Passed on both: VP8 8-bit and VP9 `yuv420p10le`, 128×128 at 24 fps, 1.01 s, with Opus; WebM input decode passed |
| Audio transcode | Read WAV, AIFF, FLAC, Ogg, MP4, and Matroska audio; write PCM WAV/AIFF, FLAC, AAC, MP3, Opus, or Vorbis | Verify sample rate, channel count, and representative duration | Passed on both: WAV/AIFF/FLAC/Ogg read/write paths, MP3 and Vorbis output, Opus in WebM, AAC in MP4; 48 kHz mono fixture |
| Basic conform/filtering | Read MP4 or image inputs; scale, crop, pad, set frame rate, convert colorspace, composite/extract alpha, apply 1D/3D LUT or tone-map, trim/concat | Verify output dimensions and duration for representative operations | Passed on both: crop/pad/fps/colorspace/1D LUT, 3D LUT, overlay, alpha extraction, tone-map, trim, and concat. |

### Containers, Sequences, And Protocols

- Movie input: MOV/QuickTime, MP4, MXF, Matroska, WebM, and AVI (AVI was tested as an input fixture).
- Movie output: MOV/QuickTime, MP4, MXF, Matroska, and WebM.
- Audio containers: WAV, AIFF, FLAC, and Ogg.
- Image sequences: OpenEXR, DPX, PNG, TIFF, and JPEG through the image2 demuxer/muxer.
- File access: mounted local files and standard input/output pipes. Network protocols and capture devices are not part of this container's support contract.

### Codec And Component Mapping

| Capability | FFmpeg component or library | Required direction |
| --- | --- | --- |
| H.264 / AVC | Native decoder; `libx264` encoder | Decode and encode |
| H.265 / HEVC | Native decoder; `libx265` encoder | Decode and encode; current x265 build accepts 8-bit input pixel formats only (verified with an 8-bit encode/decode round trip) |
| VP8 / VP9 | `libvpx` encoders/decoders | Decode and encode |
| Apple ProRes | Native `prores` decoder and `prores_ks` encoder | Decode and encode, including 10-bit 4:2:2 and 4:4:4:4 alpha output |
| DNxHD / DNxHR | Native `dnxhd` decoder and encoder | Decode and encode, including 10-bit output |
| FFV1 and uncompressed video | Native FFmpeg components | Decode and encode for lossless/interchange workflows; FFV1 10-bit Matroska output and decode passed |
| OpenEXR, DPX, PNG, TIFF, JPEG | Native image codecs and image2 sequence support | Read and write; alpha and high-bit-depth support as listed above |
| AAC | Native decoder/encoder and the currently configured FDK AAC encoder | Decode and encode |
| MP3 | Native decoder and `libmp3lame` encoder | Decode and encode |
| Opus | Native decoder and `libopus` encoder | Decode and encode |
| Vorbis | Native decoder and `libvorbis` encoder | Decode and encode |
| PCM and FLAC | Native FFmpeg components | Decode and encode; little- and big-endian PCM formats are enabled for WAV and AIFF |

The current configure flags include `--enable-nonfree` for FDK AAC alongside GPL-licensed x264/x265. The resulting image is for local use until distribution rights are reviewed. Removing FDK AAC or changing the licensing posture requires an explicit decision and updated support tests.

### Explicitly Outside This Contract

These current FFmpeg defaults are optional for the selected local VFX workflows and may be disabled: AV1, broadcast/game/legacy codecs not listed above, subtitle codecs and rendering, font-based `drawtext`, camera/audio capture and output devices, hardware-acceleration APIs, and network protocols. The application receives media through mounted files and pipes. These exclusions do not prevent adding a workflow later; a new requirement must add a matrix row and representative test before its components are enabled.

## Baseline Inventory And Known Limits

Task 3 images for amd64 and arm64 listed the same selected encoder integrations: `libx264`, `libx265`, `libvpx`, `libvpx-vp9`, `libfdk_aac`, `libmp3lame`, `libopus`, and `libvorbis`. They also listed native ProRes, DNxHD, FFV1, OpenEXR, DPX, PNG, TIFF, and image2 components; MOV, MP4, MXF, Matroska, WebM, AVI, WAV, AIFF, FLAC, and Ogg support; and filters including scale, crop, pad, fps, colorspace, overlay, alphaextract, alphamerge, lut, lut3d, and tonemap.

The following capability limits are visible in the built image's encoder help output:

- `libx265` advertises 8-bit pixel formats only. Do not claim 10-bit HEVC encoding unless a later build changes and tests the x265 configuration.
- `prores_ks` advertises `yuv422p10le`, `yuv444p10le`, and `yuva444p10le` output formats. A tested 4444 MOV decodes as `yuva444p12le`; non-opaque alpha survived.
- `dnxhd` advertises 10-bit 4:2:2, 10-bit 4:4:4, and 10-bit GBR formats.
- `libvpx-vp9` advertises 10-bit and 12-bit pixel formats, including alpha variants.

## Configure Policy And Validation Limits

The build explicitly disables autodetection, enables only the required external libraries, retains `ffmpeg` and `ffprobe`, and disables unused programs, documentation, network access, and capture devices. It uses `--disable-everything` with explicit demuxer, muxer, decoder, encoder, parser, bitstream-filter, protocol, and filter enables. `--enable-small` is enabled by default based on the measured size and encode comparison; SIMD and threading remain enabled. No currently configured codec dependency was removed because each is represented by the selected support contract.

The desired protocol set is `file` and `pipe`; the concat demuxer is enabled for explicit file lists, while the concat URL protocol is not required. The desired component set excludes network protocols, hardware APIs, device capture, and subtitle rendering unless a documented workflow requires one.

## Representative Tests

Manual representative tests ran on both target platforms. Fixtures were generated outside the final image and mounted into the containers. The checks covered:

1. H.264/AAC MP4, HEVC 8-bit encode/decode, DNxHD 10-bit MXF, ProRes HQ/4444, and FFV1 10-bit Matroska.
2. VP8 and VP9 WebM with Opus, including VP9 10-bit encode/decode.
3. PNG-alpha to ProRes 4444 and EXR-alpha to ProRes 4444; alpha extraction confirmed non-opaque samples.
4. Numbered two-frame EXR/PNG/DPX sequences, half- and float-EXR conversion, and 10-/12-bit DPX conversion through TIFF/PNG.
5. WAV, AIFF, FLAC, Ogg, AVI, Matroska, MXF, MOV, MP4, and WebM representative read/write paths; MP3, Vorbis, AAC, Opus, FLAC, PCM WAV/AIFF outputs.
6. Crop, pad, fps, colorspace, 1D/3D LUT, overlay, alpha extraction, tone-map, trim, and concat operations.
7. Mounted file input/output and stdin pipe input; protocol inspection confirmed only `file` and `pipe`, and the device list was empty on both platforms.

Representative workflow checks ran inside the final `task4-amd64` and `task4-arm64` images against mounted generated fixtures. FFprobe confirmed the stream properties listed above, including two-frame sequence counts and numbered output files. This is manual representative validation, not an automated conformance suite; no colorimetric reference comparison or third-party application interoperability test has been performed. Do not infer support from `ffmpeg -formats`, `-codecs`, or `-pix_fmts` listings alone.

Configure options are checked against the pinned release's [FFmpeg 8.1.3 configure script](https://github.com/FFmpeg/FFmpeg/blob/n8.1.3/configure).
