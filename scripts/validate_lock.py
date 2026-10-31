#!/usr/bin/env python3
"""Validate source/build locks and prove a bad archive is rejected pre-extraction."""

import json
import pathlib
import re
import subprocess
import sys
import tempfile


ROOT = pathlib.Path(__file__).resolve().parents[1]
EXPECTED_DEPENDENCIES = {
    "ffmpeg", "nasm", "x264", "x265", "fdk-aac", "lame",
    "opus", "libogg", "libvorbis", "libvpx",
}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def validate_source_lock():
    path = ROOT / "build/dependencies.lock.json"
    lock = json.loads(path.read_text(encoding="utf-8"))
    require(lock.get("lock_version") == 1, "unsupported dependency lock version")
    dependencies = lock.get("dependencies")
    require(isinstance(dependencies, list), "dependencies must be a list")
    by_name = {}
    archives = set()
    for item in dependencies:
        name = item.get("name")
        require(name and name not in by_name, "dependency names must be unique")
        require(item.get("version"), "%s has no version" % name)
        require(item.get("url", "").startswith("https://"), "%s URL is not HTTPS" % name)
        require(item.get("source_root"), "%s has no source_root" % name)
        archive = item.get("archive", "")
        require(pathlib.PurePosixPath(archive).name == archive, "%s archive is not a filename" % name)
        require(archive not in archives, "%s archive is duplicated" % name)
        require(re.fullmatch(r"[0-9a-f]{64}", item.get("sha256", "")) is not None,
                "%s has an invalid SHA-256" % name)
        require(item.get("checksum_provenance"), "%s has no checksum provenance" % name)
        archives.add(archive)
        by_name[name] = item
        for signature in item.get("signatures", []):
            key_file = ROOT / "build" / signature.get("key_file", "")
            require(key_file.is_file(), "%s signing key is missing" % name)
            require(signature.get("url", "").startswith("https://"), "%s signature URL is not HTTPS" % name)
            require(re.fullmatch(r"[0-9A-Fa-f]{40}", signature.get("fingerprint", "")) is not None,
                    "%s signature fingerprint is invalid" % name)
    require(set(by_name) == EXPECTED_DEPENDENCIES,
            "source dependency set differs: expected %s; got %s" %
            (sorted(EXPECTED_DEPENDENCIES), sorted(by_name)))
    require(by_name["ffmpeg"]["version"] == "8.1.3", "FFmpeg lock version changed")

    # The helper itself must reject corrupted bytes before it can create extracted sources.
    with tempfile.TemporaryDirectory(prefix="ffmpeg-lock-check-") as temporary:
        directory = pathlib.Path(temporary)
        bad_archive = directory / "corrupt.tar.xz"
        bad_archive.write_bytes(b"deliberately incorrect archive\n")
        extraction = directory / "extracted"
        result = subprocess.run(
            [sys.executable, str(ROOT / "build/fetch_sources.py"),
             "--verify-archive", "ffmpeg", "--archive", str(bad_archive),
             "--extract-dir", str(extraction)],
            text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        require(result.returncode != 0, "corrupt archive was accepted")
        require("SHA-256 mismatch" in result.stdout, "corrupt archive failed for an unexpected reason: %s" % result.stdout)
        require(not extraction.exists(), "source extraction started before checksum rejection")
    print("Verified %d source identities and checksum rejection before extraction" % len(by_name))


def validate_toolchain_lock():
    path = ROOT / "build/toolchain.lock.json"
    lock = json.loads(path.read_text(encoding="utf-8"))
    require(lock.get("schema_version") == 1, "unsupported toolchain lock version")
    require(re.fullmatch(r"sha256:[0-9a-f]{64}", lock["base_image"]["index_digest"]) is not None,
            "base image is not pinned by digest")
    for platform in ("linux/amd64", "linux/arm64"):
        require(platform in lock["base_image"]["platform_manifests"], "%s base manifest is missing" % platform)
        resolved = ROOT / lock["apt"]["resolved_package_manifests"][platform]
        requested = ROOT / lock["apt"]["requested_and_transitive_packages"][platform]
        resolved_lines = resolved.read_text(encoding="utf-8").splitlines()
        requested_lines = requested.read_text(encoding="utf-8").splitlines()
        require(resolved_lines and all(len(line.split("\t")) == 2 and line.split("\t")[1]
                                       for line in resolved_lines),
                "%s has incomplete package pins" % resolved)
        require(requested_lines and all("=" in line for line in requested_lines),
                "%s has incomplete package pins" % requested)
        require(len(resolved_lines) == len(set(resolved_lines)), "%s contains duplicate pins" % resolved)
        require(len(requested_lines) == len(set(requested_lines)), "%s contains duplicate pins" % requested)
    dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")
    for name in EXPECTED_DEPENDENCIES:
        require("~/ffmpeg_sources/%s" % name in dockerfile,
                "locked dependency %s is not referenced by the Dockerfile" % name)
    require("debian:trixie-slim@" + lock["base_image"]["index_digest"] in dockerfile,
            "Dockerfile base digest differs from toolchain lock")
    actions = lock["docker_build_tools"].get("github_actions", {})
    require(actions.get("runners") == {"linux/amd64": "ubuntu-24.04", "linux/arm64": "ubuntu-24.04-arm"},
            "GitHub-hosted runner mapping is missing or differs from the target platforms")
    workflow = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
    pinned_uses = re.findall(r"^\s*uses:\s*([^\s]+)@([0-9a-f]{40})\b", workflow, re.MULTILINE)
    all_uses = re.findall(r"^\s*uses:\s*([^\s]+)@([^\s]+)", workflow, re.MULTILINE)
    require(pinned_uses and len(all_uses) == len(pinned_uses),
            "every GitHub Action must be pinned to a full commit SHA")
    for action_name, lock_key in (("actions/checkout", "checkout"),
                                  ("docker/setup-buildx-action", "setup_buildx"),
                                  ("actions/upload-artifact", "upload_artifact")):
        require(any(name == action_name for name, _ in pinned_uses), "CI does not use %s" % action_name)
        sha = next(value for name, value in pinned_uses if name == action_name)
        require(action_name + "@" + sha in actions.get(lock_key, ""),
                "%s SHA differs from the toolchain lock" % action_name)
    require("moby/buildkit:v0.33.1@" + lock["docker_build_tools"]["buildkit"]["index_digest"] in workflow,
            "CI BuildKit image digest differs from the toolchain lock")
    print("Verified toolchain image, package, and per-platform manifest locks")


if __name__ == "__main__":
    try:
        validate_source_lock()
        validate_toolchain_lock()
    except (KeyError, OSError, ValueError, json.JSONDecodeError) as error:
        print("lock validation failed: %s" % error, file=sys.stderr)
        sys.exit(1)
