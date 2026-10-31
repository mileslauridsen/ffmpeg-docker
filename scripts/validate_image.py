#!/usr/bin/env python3
"""Check runtime identity, linkage, image contents, and the per-platform size budget."""

import argparse
import hashlib
import json
import pathlib
import re
import subprocess
import sys


ROOT = pathlib.Path(__file__).resolve().parents[1]
FORBIDDEN_TOOLS = ("gcc", "g++", "make", "cmake", "nasm", "ndisasm", "x264", "lame", "pkg-config")


def run(command, check=True):
    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    if check and result.returncode:
        raise RuntimeError("command failed (%s):\n%s" % (" ".join(command), result.stdout))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image", required=True)
    parser.add_argument("--platform", required=True, choices=("linux/amd64", "linux/arm64"))
    parser.add_argument("--metadata", type=pathlib.Path)
    parser.add_argument("--revision")
    args = parser.parse_args()

    try:
        dockerfile = (ROOT / "Dockerfile").read_bytes()
        source_lock = (ROOT / "build/dependencies.lock.json").read_bytes()
        toolchain_lock = (ROOT / "build/toolchain.lock.json").read_bytes()
        support_doc = (ROOT / "docs/MEDIA_SUPPORT.md").read_bytes()
        budget_lock = (ROOT / "build/image-size-budgets.json").read_bytes()
        lock = json.loads(source_lock)
        ffmpeg_version = next(item["version"] for item in lock["dependencies"] if item["name"] == "ffmpeg")
        budgets = json.loads((ROOT / "build/image-size-budgets.json").read_text(encoding="utf-8"))
        budget = budgets["budgets"][args.platform]

        inspected = run(["docker", "image", "inspect", "--format", "{{.Id}} {{.Size}}", args.image]).stdout.strip().split()
        if len(inspected) != 2:
            raise RuntimeError("unexpected docker image inspect result: %r" % inspected)
        image_id, size = inspected[0], int(inspected[1])
        architecture = run(["docker", "image", "inspect", "--format", "{{.Architecture}}", args.image]).stdout.strip()
        expected_arch = args.platform.split("/")[1]
        if architecture != expected_arch:
            raise RuntimeError("image architecture %s does not match requested %s" % (architecture, expected_arch))
        if size > budget:
            raise RuntimeError("image size %d exceeds %s budget %d" % (size, args.platform, budget))

        version = run(["docker", "run", "--rm", "--platform", args.platform, args.image,
                       "ffmpeg", "-version"]).stdout
        if not re.search(r"^ffmpeg version %s(?:\s|$)" % re.escape(ffmpeg_version), version, re.MULTILINE):
            raise RuntimeError("runtime FFmpeg version does not match locked version %s" % ffmpeg_version)

        buildconf = run(["docker", "run", "--rm", "--platform", args.platform, args.image,
                         "ffmpeg", "-buildconf"]).stdout
        for option in ("--disable-everything", "--disable-network", "--enable-small",
                       "--enable-libx264", "--enable-libx265", "--enable-libvpx",
                       "--enable-libfdk_aac", "--enable-libopus", "--enable-libvorbis", "--enable-libmp3lame"):
            if option not in buildconf:
                raise RuntimeError("runtime build configuration is missing %s" % option)

        runtime = r'''set -eu
command -v ffmpeg
command -v ffprobe
test -x /bin/bash
ldd /root/bin/ffmpeg
ldd /root/bin/ffprobe
for tool in %s; do
  if command -v "$tool" >/dev/null 2>&1; then
    echo "unexpected build tool in runtime: $tool" >&2
    exit 1
  fi
done
''' % " ".join(FORBIDDEN_TOOLS)
        linkage = run(["docker", "run", "--rm", "--platform", args.platform, args.image,
                       "bash", "-euc", runtime]).stdout
        if "not found" in linkage:
            raise RuntimeError("runtime has an unresolved shared library:\n%s" % linkage)
        print("Runtime identity and tools passed for %s: %s" % (args.platform, image_id))
        print("Image size %d / %d bytes" % (size, budget))

        if args.metadata:
            record = {
                "schema_version": 1,
                "source_revision": args.revision,
                "platform": args.platform,
                "image": args.image,
                "image_id": image_id,
                "image_size_bytes": size,
                "image_size_budget_bytes": budget,
                "ffmpeg_version": ffmpeg_version,
                "configure_arguments": [line.strip() for line in buildconf.splitlines() if line.strip().startswith("--")],
                "sha256": {
                    "Dockerfile": hashlib.sha256(dockerfile).hexdigest(),
                    "dependencies_lock": hashlib.sha256(source_lock).hexdigest(),
                    "toolchain_lock": hashlib.sha256(toolchain_lock).hexdigest(),
                    "media_support": hashlib.sha256(support_doc).hexdigest(),
                    "image_size_budgets": hashlib.sha256(budget_lock).hexdigest(),
                },
            }
            args.metadata.parent.mkdir(parents=True, exist_ok=True)
            args.metadata.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return 0
    except (KeyError, OSError, RuntimeError, StopIteration, ValueError) as error:
        print("image validation failed: %s" % error, file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
