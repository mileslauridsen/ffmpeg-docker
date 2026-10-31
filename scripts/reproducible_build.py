#!/usr/bin/env python3
"""Compare two isolated cold builds: runtime content, binary hashes, and image identity."""

import argparse
import hashlib
import json
import pathlib
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile


ROOT = pathlib.Path(__file__).resolve().parents[1]
IGNORED = shutil.ignore_patterns(".git", ".idea", "__pycache__", ".pytest_cache")
CONTAINER_RUNTIME_PATHS = (
    ".dockerenv", "dev", "proc", "sys", "run", "etc/hostname", "etc/hosts",
    "etc/resolv.conf", "etc/mtab", "root/.cache/rosetta",
)


def run(command, check=True, **kwargs):
    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, **kwargs)
    if check and result.returncode:
        raise RuntimeError("command failed (%s):\n%s" % (" ".join(command), result.stdout))
    return result


def image_id(image):
    return run(["docker", "image", "inspect", "--format", "{{.Id}}", image]).stdout.strip()


def image_digests(image):
    """Read the config digest from the saved config JSON and the manifest digest from inspect."""
    inspected = json.loads(run(["docker", "image", "inspect", image]).stdout)[0]
    manifest_digest = inspected.get("Descriptor", {}).get("digest")
    with tempfile.TemporaryDirectory(prefix="ffmpeg-image-config-") as temporary:
        archive_path = pathlib.Path(temporary) / "image.tar"
        run(["docker", "image", "save", "--output", str(archive_path), image])
        with tarfile.open(archive_path, mode="r:") as archive:
            manifest = json.load(archive.extractfile("manifest.json"))
            if not manifest or "Config" not in manifest[0]:
                raise RuntimeError("docker image save did not include its config JSON")
            config = archive.extractfile(manifest[0]["Config"])
            if config is None:
                raise RuntimeError("docker image save referenced a missing config JSON")
            config_digest = "sha256:" + hashlib.sha256(config.read()).hexdigest()
    return config_digest, manifest_digest


def file_hashes(image, platform):
    # List shared runtime libraries resolved by the two executables.
    result = run(["docker", "run", "--rm", "--platform", platform, image,
                  "bash", "-euc", "ldd /root/bin/ffmpeg; ldd /root/bin/ffprobe"])
    libraries = set()
    for line in result.stdout.splitlines():
        if "=>" in line:
            match = re.search(r"=>\s+(/\S+)", line)
            if match:
                libraries.add(match.group(1))
        elif line.lstrip().startswith("/"):
            libraries.add(line.strip().split()[0])
        elif "not found" in line:
            raise RuntimeError("unresolved runtime library: %s" % line)
    paths = ["/root/bin/ffmpeg", "/root/bin/ffprobe"] + sorted(libraries)
    checksums = run(["docker", "run", "--rm", "--platform", platform, image, "sha256sum"] + paths)
    result_map = {}
    for line in checksums.stdout.splitlines():
        digest, path = line.split(None, 1)
        result_map[path.strip()] = digest
    if set(result_map) != set(paths):
        raise RuntimeError("could not hash every runtime executable and shared library: %s" % checksums.stdout)
    return result_map


def rootfs_manifest(image, platform):
    container = run(["docker", "create", "--platform", platform, image]).stdout.strip()
    try:
        with tempfile.TemporaryDirectory(prefix="ffmpeg-rootfs-") as temporary:
            archive_path = pathlib.Path(temporary) / "rootfs.tar"
            run(["docker", "export", "--output", str(archive_path), container])
            manifest = {}
            with tarfile.open(archive_path, mode="r:") as archive:
                for member in archive:
                    name = member.name[2:] if member.name.startswith("./") else member.name
                    name = name.lstrip("/")
                    # docker export updates this directory's mtime when it mounts /etc/hosts,
                    # /etc/hostname, and /etc/resolv.conf into the container.
                    if name == "etc":
                        continue
                    if any(name == prefix or name.startswith(prefix + "/")
                           for prefix in CONTAINER_RUNTIME_PATHS):
                        continue
                    if member.isfile():
                        source = archive.extractfile(member)
                        digest = hashlib.sha256()
                        while True:
                            block = source.read(1024 * 1024)
                            if not block:
                                break
                            digest.update(block)
                        manifest[name] = {
                            "type": "file", "sha256": digest.hexdigest(), "mode": member.mode & 0o7777,
                            "mtime": member.mtime, "uid": member.uid, "gid": member.gid,
                        }
                    elif member.issym():
                        manifest[name] = {
                            "type": "symlink", "target": member.linkname, "mtime": member.mtime,
                            "uid": member.uid, "gid": member.gid,
                        }
                    elif member.isdir():
                        manifest[name] = {
                            "type": "directory", "mode": member.mode & 0o7777, "mtime": member.mtime,
                            "uid": member.uid, "gid": member.gid,
                        }
                    elif member.islnk():
                        manifest[name] = {
                            "type": "hardlink", "target": member.linkname, "mtime": member.mtime,
                            "uid": member.uid, "gid": member.gid,
                        }
                    else:
                        manifest[name] = {"type": "other", "mode": member.mode & 0o7777}
            return manifest
    finally:
        run(["docker", "rm", container], check=False)


def context_digest(directory):
    digest = hashlib.sha256()
    for path in sorted(directory.rglob("*")):
        if path.is_file():
            relative = path.relative_to(directory).as_posix().encode("utf-8")
            digest.update(relative + b"\0")
            content = path.read_bytes()
            digest.update(hashlib.sha256(content).digest())
            digest.update((path.stat().st_mode & 0o7777).to_bytes(2, "big"))
    return digest.hexdigest()


def differences(left, right):
    """Return path-level differences with both sides preserved for diagnosis."""
    return [
        {"path": path, "build_a": left.get(path), "build_b": right.get(path)}
        for path in sorted(set(left) | set(right))
        if left.get(path) != right.get(path)
    ]


def build(builder, platform, context, tag, metadata_path):
    command = ["docker", "buildx", "build", "--progress=plain", "--builder", builder,
               "--pull", "--no-cache", "--platform", platform, "--target", "runtime-image",
               "--build-arg", "ENABLE_SMALL=1", "--build-arg", "SOURCE_DATE_EPOCH=0",
               "--metadata-file", str(metadata_path),
               "--load", "-t", tag, str(context)]
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                               text=True, bufsize=1)
    for line in process.stdout:
        sys.stdout.write(line)
        sys.stdout.flush()
    status = process.wait()
    if status:
        raise RuntimeError("cold Docker build failed with exit code %s" % status)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--platform", required=True, choices=("linux/amd64", "linux/arm64"))
    parser.add_argument("--builder", required=True)
    parser.add_argument("--metadata", type=pathlib.Path)
    parser.add_argument("--baseline-image", help="reuse a previously completed cold build as build A")
    parser.add_argument("--keep-images", action="store_true")
    args = parser.parse_args()

    tags = []
    try:
        with tempfile.TemporaryDirectory(prefix="ffmpeg-repro-") as temporary:
            root = pathlib.Path(temporary)
            contexts = [root / "build-a", root / "build-b"]
            for context in contexts:
                shutil.copytree(ROOT, context, ignore=IGNORED)
            digests = [context_digest(context) for context in contexts]
            if digests[0] != digests[1]:
                raise RuntimeError("isolated build contexts differ: %s" % digests)

            records = []
            start_number = 1
            if args.baseline_image:
                baseline_id = image_id(args.baseline_image)
                baseline_config_digest, baseline_manifest_digest = image_digests(args.baseline_image)
                records.append({
                    "tag": args.baseline_image,
                    "image_id": baseline_id,
                    "config_digest": baseline_config_digest,
                    "manifest_digest": baseline_manifest_digest,
                    "runtime_artifact_sha256": file_hashes(args.baseline_image, args.platform),
                    "rootfs_content": rootfs_manifest(args.baseline_image, args.platform),
                })
                start_number = 2

            for number, context in enumerate(contexts[start_number - 1:], start_number):
                suffix = "amd64" if args.platform.endswith("amd64") else "arm64"
                tag = "ffmpeg-docker-repro:%s-%d" % (suffix, number)
                tags.append(tag)
                build_metadata = root / ("build-metadata-%d.json" % number)
                print("Starting independent cold build %d for %s" % (number, args.platform), flush=True)
                build(args.builder, args.platform, context, tag, build_metadata)
                metadata = json.loads(build_metadata.read_text(encoding="utf-8"))
                loaded_image_id = image_id(tag)
                saved_config_digest, inspected_manifest_digest = image_digests(tag)
                descriptor = metadata.get("containerimage.descriptor", {})
                metadata_config_digest = (metadata.get("containerimage.config.digest")
                                          or descriptor.get("annotations", {}).get("config.digest"))
                config_digest = saved_config_digest
                manifest_digest = (metadata.get("containerimage.digest") or descriptor.get("digest")
                                   or inspected_manifest_digest)
                if metadata_config_digest and metadata_config_digest != config_digest:
                    raise RuntimeError("Buildx config digest differs from saved image config JSON")
                records.append({
                    "tag": tag,
                    "image_id": loaded_image_id,
                    "manifest_digest": manifest_digest,
                    "config_digest": config_digest,
                    "runtime_artifact_sha256": file_hashes(tag, args.platform),
                    "rootfs_content": rootfs_manifest(tag, args.platform),
                })

            binary_equal = records[0]["runtime_artifact_sha256"] == records[1]["runtime_artifact_sha256"]
            binary_differences = differences(records[0]["runtime_artifact_sha256"],
                                             records[1]["runtime_artifact_sha256"])
            rootfs_equal = records[0]["rootfs_content"] == records[1]["rootfs_content"]
            rootfs_differences = differences(records[0]["rootfs_content"], records[1]["rootfs_content"])
            image_id_equal = records[0]["image_id"] == records[1]["image_id"]
            config_digest_equal = records[0]["config_digest"] == records[1]["config_digest"]
            manifest_equal = (records[0]["manifest_digest"] == records[1]["manifest_digest"]
                              if records[0]["manifest_digest"] and records[1]["manifest_digest"] else None)
            report = {
                "schema_version": 1,
                "platform": args.platform,
                "builder": args.builder,
                "source_date_epoch": 0,
                "context_sha256": digests[0],
                "runtime_binaries_and_libraries_equal": binary_equal,
                "runtime_artifact_differences": binary_differences,
                "rootfs_content_and_metadata_equal": rootfs_equal,
                "rootfs_differences": rootfs_differences,
                "docker_image_id_equal": image_id_equal,
                "docker_config_digest_equal": config_digest_equal,
                "docker_manifest_digest_equal": manifest_equal,
                "docker_manifest_digest_comparison_available": manifest_equal is not None,
                "baseline_image_reused": args.baseline_image,
                "builds": [{key: value for key, value in record.items() if key != "rootfs_content"}
                           for record in records],
            }
            print(json.dumps(report, indent=2, sort_keys=True))
            if args.metadata:
                args.metadata.parent.mkdir(parents=True, exist_ok=True)
                args.metadata.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            if not binary_equal or not rootfs_equal:
                raise RuntimeError("cold builds differed in runtime binaries/libraries or canonical rootfs content")
            if config_digest_equal:
                print("Docker image config digests match")
            else:
                print("Runtime/rootfs content matches; Docker image config digests differ and are reported separately")
            if manifest_equal is True:
                print("Docker image manifest digests also match")
            elif manifest_equal is False:
                print("Docker image manifest digests differ and are reported separately")
            else:
                print("Docker manifest digest comparison unavailable for one or both builds")
        return 0
    except (OSError, RuntimeError, subprocess.SubprocessError, ValueError) as error:
        print("reproducibility validation failed: %s" % error, file=sys.stderr)
        return 1
    finally:
        if not args.keep_images:
            for tag in tags:
                run(["docker", "image", "rm", "-f", tag], check=False)


if __name__ == "__main__":
    sys.exit(main())
