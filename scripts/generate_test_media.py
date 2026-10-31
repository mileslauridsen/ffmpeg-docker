#!/usr/bin/env python3
"""Generate deterministic PNG, WAV, alpha, and LUT fixtures for FFmpeg checks."""

import argparse
import hashlib
import json
import binascii
import pathlib
import struct
import wave
import zlib


WIDTH = 64
HEIGHT = 64
FRAMES = 24
SAMPLE_RATE = 48_000


def video_frames(rgba=False):
    channels = 4 if rgba else 3
    for frame in range(FRAMES):
        data = bytearray()
        for y in range(HEIGHT):
            for x in range(WIDTH):
                data.extend(((x * 3 + frame * 7) % 256,
                             (y * 5 + frame * 11) % 256,
                             (x + y + frame * 13) % 256))
                if rgba:
                    data.append((x * 4 + y * 2 + frame * 3) % 256)
        assert len(data) == WIDTH * HEIGHT * channels
        yield data


def digest_chunks(chunks):
    digest = hashlib.sha256()
    for chunk in chunks:
        digest.update(chunk)
    return digest.hexdigest()


def png_chunk(kind, data):
    content = kind + data
    return struct.pack(">I", len(data)) + content + struct.pack(">I", binascii.crc32(content) & 0xffffffff)


def write_png(path, pixels, rgba=False):
    channels = 4 if rgba else 3
    rows = b"".join(b"\0" + pixels[y * WIDTH * channels:(y + 1) * WIDTH * channels]
                    for y in range(HEIGHT))
    header = struct.pack(">IIBBBBB", WIDTH, HEIGHT, 8, 6 if rgba else 2, 0, 0, 0)
    data = b"\x89PNG\r\n\x1a\n" + png_chunk(b"IHDR", header)
    data += png_chunk(b"IDAT", zlib.compress(rows, 9)) + png_chunk(b"IEND", b"")
    path.write_bytes(data)


def audio_samples():
    for sample in range(SAMPLE_RATE):
        phase = sample * 440 % SAMPLE_RATE
        value = 8000 if phase < SAMPLE_RATE // 2 else -8000
        yield struct.pack("<h", value)


def generate(directory):
    directory.mkdir(parents=True, exist_ok=True)
    rgb_frames = list(video_frames())
    rgba_frames = list(video_frames(rgba=True))
    for number, pixels in enumerate(rgb_frames, 1):
        write_png(directory / ("video-%02d.png" % number), pixels)
    for number, pixels in enumerate(rgba_frames, 1):
        write_png(directory / ("alpha-%02d.png" % number), pixels, rgba=True)
    pcm = b"".join(audio_samples())
    with wave.open(str(directory / "audio.wav"), "wb") as output:
        output.setnchannels(1)
        output.setsampwidth(2)
        output.setframerate(SAMPLE_RATE)
        output.writeframes(pcm)
    cube = ("TITLE \"Identity LUT\"\nLUT_3D_SIZE 2\n"
            "0 0 0\n1 0 0\n0 1 0\n1 1 0\n"
            "0 0 1\n1 0 1\n0 1 1\n1 1 1\n").encode("ascii")
    (directory / "identity.cube").write_bytes(cube)
    video_hash = digest_chunks(rgb_frames)
    rgba_hash = digest_chunks(rgba_frames)
    audio_hash = hashlib.sha256(pcm).hexdigest()
    return {
        "width": WIDTH,
        "height": HEIGHT,
        "frames": FRAMES,
        "frame_rate": "24/1",
        "audio_sample_rate": SAMPLE_RATE,
        "audio_channels": 1,
        "sha256": {
            "video_rgb_pixels": video_hash,
            "alpha_rgba_pixels": rgba_hash,
            "audio_pcm_s16le": audio_hash,
            "identity_lut_cube": hashlib.sha256(cube).hexdigest(),
        },
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=pathlib.Path)
    args = parser.parse_args()
    print(json.dumps(generate(args.directory), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
