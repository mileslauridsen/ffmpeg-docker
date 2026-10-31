#!/usr/bin/env python3
"""Run deterministic, redistributable media checks against a built image."""

import argparse
import json
import pathlib
import struct
import subprocess
import sys
import tempfile
import zlib

from generate_test_media import generate as generate_fixtures


ROOT = pathlib.Path(__file__).resolve().parents[1]
WIDTH, HEIGHT, FRAMES, RATE, SAMPLE_RATE = 64, 64, 24, "24/1", 48_000


def generate(directory):
    metadata = generate_fixtures(directory)
    expected = {
        "video_rgb_pixels": "bb4be6cfb38d87fc081de63b7042fc3c8b575bcdcaf6abf66b01087f84677cc7",
        "alpha_rgba_pixels": "0990d6243dc534a603c072a89605db3d98dc80eb101edb09228b45e724b9708d",
        "audio_pcm_s16le": "5b3f02c6c97b7db26cbea63612d03ef01e34e105e71ac026a416ca71dd18f8b8",
        "identity_lut_cube": "566f34b56d12fd94ff4426c5a46a0f579724f05f4909511052d7186a99d5dc2e",
    }
    if metadata["sha256"] != expected:
        raise RuntimeError("fixture identity changed: expected %s; generated %s" % (expected, metadata["sha256"]))
    return metadata


def docker(args, *command, input_bytes=None):
    cmd = ["docker", "run", "--rm"]
    if input_bytes is not None:
        cmd.append("-i")
    cmd.extend(["--platform", args.platform, "--volume", "%s:/media" % args.fixtures, args.image])
    cmd.extend(command)
    result = subprocess.run(cmd, input=input_bytes, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if result.returncode:
        raise RuntimeError("command failed (%s):\n%s" %
                           (" ".join(cmd), result.stderr.decode("utf-8", "replace")))
    return result.stdout


def ffmpeg(args, *options):
    docker(args, "ffmpeg", "-hide_banner", "-loglevel", "error", "-y", *options)


def probe(args, path):
    data = docker(args, "ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", path)
    return json.loads(data)


def stream(probe_data, codec):
    matches = [item for item in probe_data["streams"] if item.get("codec_type") == codec]
    if len(matches) != 1:
        raise AssertionError("expected one %s stream, found %s" % (codec, len(matches)))
    return matches[0]


def check_video(data, codec, width=WIDTH, height=HEIGHT, pix_fmt=None, duration_range=(0.95, 1.05)):
    item = stream(data, "video")
    assert item["codec_name"] == codec, item
    assert item["width"] == width and item["height"] == height, item
    assert item["r_frame_rate"] == RATE, item
    if pix_fmt:
        assert item["pix_fmt"] == pix_fmt, item
    duration = float(data["format"]["duration"])
    assert duration_range[0] <= duration <= duration_range[1], duration


def check_audio(data, codec):
    item = stream(data, "audio")
    assert item["codec_name"] == codec, item
    assert item["sample_rate"] == str(SAMPLE_RATE), item
    assert item["channels"] == 1, item


def grayscale_png_pixels(path):
    data = path.read_bytes()
    if not data.startswith(b"\x89PNG\r\n\x1a\n"):
        raise AssertionError("alpha extraction did not produce a PNG")
    offset, compressed, dimensions = 8, [], None
    while offset < len(data):
        length = struct.unpack(">I", data[offset:offset + 4])[0]
        kind = data[offset + 4:offset + 8]
        chunk = data[offset + 8:offset + 8 + length]
        if kind == b"IHDR":
            width, height, bit_depth, color_type, _, _, _ = struct.unpack(">IIBBBBB", chunk)
            dimensions = width, height
            if bit_depth != 8 or color_type != 0:
                raise AssertionError("alpha extraction PNG is not 8-bit grayscale")
        elif kind == b"IDAT":
            compressed.append(chunk)
        elif kind == b"IEND":
            break
        offset += length + 12
    width, height = dimensions
    encoded = zlib.decompress(b"".join(compressed))
    stride, position = width, 0
    previous = bytearray(stride)
    pixels = bytearray()

    def paeth(a, b, c):
        p = a + b - c
        pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
        return a if pa <= pb and pa <= pc else (b if pb <= pc else c)

    for _ in range(height):
        filter_type = encoded[position]
        source = encoded[position + 1:position + 1 + stride]
        position += stride + 1
        row = bytearray(stride)
        for x, value in enumerate(source):
            left = row[x - 1] if x else 0
            up = previous[x]
            upper_left = previous[x - 1] if x else 0
            if filter_type == 0:
                predictor = 0
            elif filter_type == 1:
                predictor = left
            elif filter_type == 2:
                predictor = up
            elif filter_type == 3:
                predictor = (left + up) // 2
            elif filter_type == 4:
                predictor = paeth(left, up, upper_left)
            else:
                raise AssertionError("unsupported PNG filter %s" % filter_type)
            row[x] = (value + predictor) & 255
        pixels.extend(row)
        previous = row
    return pixels


def run_checks(args):
    directory = args.fixtures
    fixture_metadata = generate(directory)
    checks = []

    # Review MP4: deterministic raw RGB and PCM inputs, H.264/AAC output.
    ffmpeg(args, "-framerate", RATE, "-start_number", "1", "-i", "/media/video-%02d.png",
           "-i", "/media/audio.wav", "-frames:v", str(FRAMES), "-shortest",
           "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "96k", "/media/review.mp4")
    review = probe(args, "/media/review.mp4")
    check_video(review, "h264", pix_fmt="yuv420p")
    check_audio(review, "aac")
    checks.append({"name": "h264-aac-mp4", "video": stream(review, "video"), "audio": stream(review, "audio")})

    # A second lossy family and the 10-bit VP9 WebM profile.
    ffmpeg(args, "-i", "/media/review.mp4", "-an", "-c:v", "libx265", "-pix_fmt", "yuv420p",
           "-x265-params", "log-level=error", "/media/hevc.mp4")
    hevc = probe(args, "/media/hevc.mp4")
    check_video(hevc, "hevc", pix_fmt="yuv420p")
    checks.append({"name": "hevc-8bit-mp4", "video": stream(hevc, "video")})
    ffmpeg(args, "-i", "/media/review.mp4", "-c:v", "libvpx-vp9", "-pix_fmt", "yuv420p10le",
           "-deadline", "good", "-cpu-used", "5", "-c:a", "libopus", "/media/web-vp9.webm")
    webm = probe(args, "/media/web-vp9.webm")
    check_video(webm, "vp9", pix_fmt="yuv420p10le")
    check_audio(webm, "opus")
    checks.append({"name": "vp9-10bit-opus-webm", "video": stream(webm, "video"), "audio": stream(webm, "audio")})
    ffmpeg(args, "-i", "/media/review.mp4", "-c:v", "libvpx", "-pix_fmt", "yuv420p",
           "-deadline", "good", "-cpu-used", "5", "-c:a", "libopus", "/media/web-vp8.webm")
    vp8 = probe(args, "/media/web-vp8.webm")
    check_video(vp8, "vp8", pix_fmt="yuv420p")
    check_audio(vp8, "opus")
    checks.append({"name": "vp8-opus-webm", "video": stream(vp8, "video"), "audio": stream(vp8, "audio")})

    # High-quality 10-bit DNxHD and ProRes 4444 with a variable alpha channel.
    ffmpeg(args, "-i", "/media/review.mp4", "-frames:v", "1", "-vf",
           "scale=1920:1080,format=yuv422p10le", "-an", "-c:v", "dnxhd", "-b:v", "185M",
           "-f", "mxf", "/media/dnxhd.mxf")
    dnxhd = probe(args, "/media/dnxhd.mxf")
    check_video(dnxhd, "dnxhd", 1920, 1080, "yuv422p10le", (0.0, 0.1))
    checks.append({"name": "dnxhd-10bit-mxf", "video": stream(dnxhd, "video")})
    ffmpeg(args, "-i", "/media/dnxhd.mxf", "-frames:v", "1", "-c:v", "png", "/media/dnxhd.png")
    checks.append({"name": "dnxhd-mxf-decode", "video": stream(probe(args, "/media/dnxhd.png"), "video")})
    ffmpeg(args, "-i", "/media/review.mp4", "-an", "-c:v", "prores_ks", "-profile:v", "3",
           "-pix_fmt", "yuv422p10le", "/media/prores-hq.mov")
    prores = probe(args, "/media/prores-hq.mov")
    check_video(prores, "prores", pix_fmt="yuv422p10le")
    checks.append({"name": "prores-422-hq", "video": stream(prores, "video")})
    ffmpeg(args, "-framerate", RATE, "-start_number", "1", "-i", "/media/alpha-%02d.png",
           "-frames:v", "1", "-an", "-c:v", "prores_ks",
           "-profile:v", "4", "-pix_fmt", "yuva444p10le", "/media/alpha.mov")
    alpha = probe(args, "/media/alpha.mov")
    check_video(alpha, "prores", pix_fmt="yuva444p12le", duration_range=(0.0, 0.1))
    docker(args, "ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", "/media/alpha.mov",
           "-frames:v", "1", "-vf", "alphaextract", "-pix_fmt", "gray", "/media/alpha.png")
    alpha_bytes = grayscale_png_pixels(directory / "alpha.png")
    assert alpha_bytes and min(alpha_bytes) < max(alpha_bytes), "ProRes alpha was not preserved"
    checks.append({"name": "prores-4444-alpha", "video": stream(alpha, "video"),
                   "alpha_min": min(alpha_bytes), "alpha_max": max(alpha_bytes)})

    # Audio encoders, image sequences, and common conform filters.
    for encoder, output, codec in (("flac", "audio.flac", "flac"),
                                   ("libmp3lame", "audio.mp3", "mp3"),
                                   ("libvorbis", "audio.ogg", "vorbis")):
        ffmpeg(args, "-i", "/media/audio.wav", "-c:a", encoder, "/media/" + output)
        audio_probe = probe(args, "/media/" + output)
        check_audio(audio_probe, codec)
        checks.append({"name": "audio-" + codec, "audio": stream(audio_probe, "audio")})
    ffmpeg(args, "-i", "/media/audio.wav", "-c:a", "pcm_s16be", "/media/audio.aiff")
    aiff = probe(args, "/media/audio.aiff")
    check_audio(aiff, "pcm_s16be")
    ffmpeg(args, "-i", "/media/audio.aiff", "-c:a", "pcm_s16le", "/media/aiff-roundtrip.wav")
    check_audio(probe(args, "/media/aiff-roundtrip.wav"), "pcm_s16le")
    checks.append({"name": "aiff-big-endian-pcm-roundtrip", "audio": stream(aiff, "audio")})
    ffmpeg(args, "-i", "/media/review.mp4", "-frames:v", "2", "/media/frame-%02d.png")
    assert all((directory / ("frame-%02d.png" % index)).is_file() for index in (1, 2))
    checks.append({"name": "two-frame-png-sequence", "files": ["frame-01.png", "frame-02.png"]})
    for encoder, output, codec, extra in (
            ("tiff", "frame.tiff", "tiff", ()),
            ("dpx", "frame.dpx", "dpx", ("-pix_fmt", "rgb48le")),
            ("mjpeg", "frame.jpg", "mjpeg", ("-q:v", "2"))):
        ffmpeg(args, "-i", "/media/review.mp4", "-frames:v", "1", "-c:v", encoder, *extra,
               "/media/" + output)
        still = probe(args, "/media/" + output)
        assert stream(still, "video")["codec_name"] == codec, still
        checks.append({"name": "image-" + codec, "video": stream(still, "video")})
    ffmpeg(args, "-i", "/media/review.mp4", "-frames:v", "1", "-vf", "format=gbrpf32le",
           "-c:v", "exr", "/media/frame.exr")
    exr = probe(args, "/media/frame.exr")
    assert stream(exr, "video")["codec_name"] == "exr", exr
    checks.append({"name": "openexr-float", "video": stream(exr, "video")})
    ffmpeg(args, "-i", "/media/frame.exr", "-frames:v", "1", "-c:v", "exr", "-format", "half",
           "/media/frame-half.exr")
    half_exr = probe(args, "/media/frame-half.exr")
    assert stream(half_exr, "video")["pix_fmt"] == "gbrpf16le", half_exr
    checks.append({"name": "openexr-float-to-half", "video": stream(half_exr, "video")})
    ffmpeg(args, "-i", "/media/review.mp4", "-frames:v", "2", "-c:v", "dpx", "-pix_fmt", "rgb48le",
           "/media/dpx-%02d.dpx")
    assert all((directory / ("dpx-%02d.dpx" % index)).is_file() for index in (1, 2))
    checks.append({"name": "two-frame-dpx-sequence", "files": ["dpx-01.dpx", "dpx-02.dpx"]})
    ffmpeg(args, "-i", "/media/review.mp4", "-frames:v", "2", "-vf", "format=gbrpf32le", "-c:v", "exr",
           "/media/exr-%02d.exr")
    assert all((directory / ("exr-%02d.exr" % index)).is_file() for index in (1, 2))
    checks.append({"name": "two-frame-openexr-sequence", "files": ["exr-01.exr", "exr-02.exr"]})
    ffmpeg(args, "-i", "/media/review.mp4", "-c:v", "ffv1", "-pix_fmt", "yuv420p", "/media/lossless.mkv")
    ffv1 = probe(args, "/media/lossless.mkv")
    assert stream(ffv1, "video")["codec_name"] == "ffv1", ffv1
    checks.append({"name": "ffv1-matroska", "video": stream(ffv1, "video")})
    ffmpeg(args, "-i", "/media/review.mp4", "-vf", "setparams=colorspace=bt709:color_primaries=bt709:color_trc=bt709,colorspace=iall=bt709:all=bt709",
           "-an", "-c:v", "libx264", "-pix_fmt", "yuv420p", "/media/colorspace.mp4")
    checks.append({"name": "colorspace-conversion", "video": stream(probe(args, "/media/colorspace.mp4"), "video")})
    ffmpeg(args, "-i", "/media/review.mp4", "-vf", "lut=y='val'", "-an", "-c:v", "libx264",
           "-pix_fmt", "yuv420p", "/media/lut.mp4")
    checks.append({"name": "lut-filter", "video": stream(probe(args, "/media/lut.mp4"), "video")})
    ffmpeg(args, "-i", "/media/review.mp4", "-vf", "lut3d=file=/media/identity.cube", "-an",
           "-c:v", "libx264", "-pix_fmt", "yuv420p", "/media/lut3d.mp4")
    checks.append({"name": "lut3d-filter", "video": stream(probe(args, "/media/lut3d.mp4"), "video")})
    ffmpeg(args, "-i", "/media/review.mp4", "-i", "/media/alpha-01.png", "-filter_complex",
           "[0:v][1:v]overlay=0:0", "-frames:v", "1", "-an", "-c:v", "libx264", "-pix_fmt", "yuv420p",
           "/media/overlay.mp4")
    checks.append({"name": "overlay-filter", "video": stream(probe(args, "/media/overlay.mp4"), "video")})
    ffmpeg(args, "-i", "/media/frame.exr", "-vf",
           "setparams=colorspace=bt709:color_primaries=bt709:color_trc=linear,tonemap=tonemap=hable:desat=0,format=yuv420p",
           "-frames:v", "1", "-c:v", "libx264", "/media/tonemap.mp4")
    checks.append({"name": "tonemap-filter", "video": stream(probe(args, "/media/tonemap.mp4"), "video")})
    ffmpeg(args, "-i", "/media/review.mp4", "-i", "/media/review.mp4", "-filter_complex",
           "[0:v][0:a][1:v][1:a]concat=n=2:v=1:a=1[v][a]", "-map", "[v]", "-map", "[a]",
           "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "/media/concat.mp4")
    concat = probe(args, "/media/concat.mp4")
    assert 1.9 <= float(concat["format"]["duration"]) <= 2.1, concat["format"]
    checks.append({"name": "concat-filter", "format": concat["format"]})
    ffmpeg(args, "-i", "/media/review.mp4", "-vf", "scale=48:48,crop=40:40,pad=64:64,fps=12,trim=duration=0.5",
           "-an", "-c:v", "libx264", "-pix_fmt", "yuv420p", "/media/conform.mp4")
    conform = probe(args, "/media/conform.mp4")
    item = stream(conform, "video")
    assert (item["width"], item["height"], item["r_frame_rate"]) == (64, 64, "12/1"), item
    assert float(conform["format"]["duration"]) <= 0.6, conform["format"]
    checks.append({"name": "scale-crop-pad-fps-trim", "video": item, "duration": conform["format"]["duration"]})

    # The application contract permits files and pipes, and excludes devices/network.
    protocols = docker(args, "ffmpeg", "-hide_banner", "-protocols").decode("utf-8")
    indevices = docker(args, "ffmpeg", "-hide_banner", "-devices").decode("utf-8")
    assert "\n  file\n" in protocols and "\n  pipe\n" in protocols, protocols
    assert "http" not in protocols and "tcp" not in protocols, protocols
    assert indevices.strip().endswith("---"), indevices

    # Verify standard-input pipe decode and standard-output encode.
    mp4 = (directory / "review.mp4").read_bytes()
    pipe_png = docker(args, "ffmpeg", "-hide_banner", "-loglevel", "error", "-i", "pipe:0",
                      "-frames:v", "1", "-f", "image2pipe", "-vcodec", "png", "pipe:1", input_bytes=mp4)
    assert pipe_png.startswith(b"\x89PNG\r\n\x1a\n"), "pipe output is not PNG"
    checks.append({"name": "mounted-files-and-pipes", "pipe_output": "png"})
    print("Media checks passed for %s (%s)" % (args.image, args.platform))
    return {
        "schema_version": 1,
        "image": args.image,
        "platform": args.platform,
        "result": "passed",
        "fixtures": fixture_metadata,
        "checks": checks,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image", required=True)
    parser.add_argument("--platform", required=True, choices=("linux/amd64", "linux/arm64"))
    parser.add_argument("--fixtures", type=pathlib.Path)
    parser.add_argument("--metadata", type=pathlib.Path)
    args = parser.parse_args()
    if args.fixtures is None:
        args.fixtures = pathlib.Path(tempfile.mkdtemp(prefix="ffmpeg-media-")).resolve()
    args.fixtures.mkdir(parents=True, exist_ok=True)
    try:
        metadata = run_checks(args)
        if args.metadata:
            args.metadata.parent.mkdir(parents=True, exist_ok=True)
            args.metadata.write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    except (AssertionError, OSError, RuntimeError, subprocess.SubprocessError, ValueError) as error:
        print("media validation failed: %s" % error, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
