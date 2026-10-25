#!/usr/bin/env python
"""Fetch locked source archives and verify them before build extraction."""

from __future__ import print_function

import argparse
import hashlib
import json
import os
import posixpath
import re
import shutil
import subprocess
import sys
import tempfile
import time

try:
    from urllib.request import Request, urlopen
except ImportError:  # Python 2 on the legacy CentOS 7 builder.
    from urllib2 import Request, urlopen


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_LOCKFILE = os.path.join(SCRIPT_DIR, "dependencies.lock.json")
KEY_DIR = SCRIPT_DIR
CHUNK_SIZE = 1024 * 1024


def find_executable(name):
    try:
        from shutil import which
        return which(name)
    except ImportError:  # Python 2 on the legacy CentOS 7 builder.
        import distutils.spawn
        return distutils.spawn.find_executable(name)


def load_lock(path):
    with open(path, "r") as lock_file:
        lock = json.load(lock_file)
    if lock.get("lock_version") != 1:
        raise ValueError("unsupported lock_version: {0}".format(lock.get("lock_version")))
    dependencies = lock.get("dependencies")
    if not isinstance(dependencies, list) or not dependencies:
        raise ValueError("lockfile must contain a non-empty dependencies list")
    seen = set()
    archives = set()
    for dependency in dependencies:
        name = dependency.get("name")
        if not name or name in seen:
            raise ValueError("dependency names must be present and unique")
        seen.add(name)
        if not re.match(r"^[0-9a-fA-F]{64}$", dependency.get("sha256", "")):
            raise ValueError("{0}: sha256 must contain 64 hexadecimal characters".format(name))
        archive = dependency.get("archive", "")
        if os.path.basename(archive) != archive or archive in archives:
            raise ValueError("{0}: archive must be a filename".format(name))
        archives.add(archive)
        if not dependency.get("url", "").startswith("https://"):
            raise ValueError("{0}: source URL must use HTTPS".format(name))
        if not dependency.get("source_root"):
            raise ValueError("{0}: source_root is required".format(name))
    return dependencies


def download(url, destination):
    temporary = destination + ".part"
    for attempt in range(3):
        try:
            request = Request(url, headers={"User-Agent": "ffmpeg-docker-locked-source-fetcher/1"})
            response = urlopen(request, timeout=120)
            try:
                if not response.geturl().startswith("https://"):
                    raise ValueError("download redirected away from HTTPS: {0}".format(response.geturl()))
                with open(temporary, "wb") as output:
                    while True:
                        chunk = response.read(CHUNK_SIZE)
                        if not chunk:
                            break
                        output.write(chunk)
            finally:
                response.close()
            os.rename(temporary, destination)
            return
        except Exception:
            if os.path.exists(temporary):
                os.unlink(temporary)
            if attempt == 2:
                raise
            time.sleep(2 ** attempt)


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as source:
        while True:
            chunk = source.read(CHUNK_SIZE)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def verify_archive(dependency, archive_path):
    actual = sha256_file(archive_path)
    expected = dependency["sha256"].lower()
    if actual.lower() != expected:
        raise ValueError(
            "{0}: SHA-256 mismatch for {1}: expected {2}, got {3}".format(
                dependency["name"], archive_path, expected, actual
            )
        )
    print("{0}: SHA-256 verified ({1})".format(dependency["name"], actual))


def dependency_signatures(dependency):
    signatures = dependency.get("signatures", [])
    if not signatures and dependency.get("signature"):
        signatures = [dependency["signature"]]
    return signatures


def verify_signature(dependency, signature, archive_path, signature_path):
    key_path = os.path.join(KEY_DIR, signature["key_file"])
    if not os.path.isfile(key_path):
        raise ValueError("pinned signing key is missing: {0}".format(key_path))

    home = tempfile.mkdtemp(prefix="ffmpeg-gpg-")
    try:
        keyring = os.path.join(home, "trustedkeys.gpg")
        gpg = find_executable("gpg2") or find_executable("gpg")
        gpgv = find_executable("gpgv2") or find_executable("gpgv")
        if not gpg or not gpgv:
            raise ValueError("FFmpeg signature verification requires gpg and gpgv")
        with open(key_path, "rb") as key_input, open(keyring, "wb") as keyring_output:
            subprocess.check_call([gpg, "--no-options", "--batch", "--dearmor"], stdin=key_input, stdout=keyring_output)

        process = subprocess.Popen(
            [gpgv, "--status-fd=1", "--keyring", keyring, signature_path, archive_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        output = process.communicate()[0]
        if not isinstance(output, str):
            output = output.decode("utf-8", "replace")
        if process.returncode != 0:
            raise ValueError("{0}: detached signature verification failed\n{1}".format(dependency["name"], output))

        expected = signature["fingerprint"].replace(" ", "").upper()
        valid_fingerprints = []
        for line in output.splitlines():
            fields = line.split()
            if len(fields) > 2 and fields[0] == "[GNUPG:]" and fields[1] == "VALIDSIG":
                valid_fingerprints.extend(value.upper() for value in fields[2:] if len(value) == 40)
        if expected not in valid_fingerprints:
            raise ValueError(
                "{0}: signature is valid but not from pinned fingerprint {1}\n{2}".format(
                    dependency["name"], expected, output
                )
            )
        print("{0}: detached signature verified with {1}".format(dependency["name"], expected))
    finally:
        shutil.rmtree(home)


def select_dependency(dependencies, name):
    for dependency in dependencies:
        if dependency["name"] == name:
            return dependency
    raise ValueError("unknown dependency: {0}".format(name))


def extract_source(dependency, archive_path, extract_dir):
    if not os.path.isdir(extract_dir):
        os.makedirs(extract_dir)
    target = os.path.join(extract_dir, dependency["name"])
    if os.path.exists(target):
        shutil.rmtree(target)
    temporary = tempfile.mkdtemp(prefix="source-extract-", dir=extract_dir)
    try:
        subprocess.check_call(["tar", "-xf", archive_path, "-C", temporary])
        source_root = dependency["source_root"]
        normalized = posixpath.normpath(source_root)
        if normalized.startswith("../") or normalized.startswith("/") or normalized != source_root:
            raise ValueError("{0}: invalid source_root".format(dependency["name"]))
        extracted = os.path.join(temporary, source_root)
        if not os.path.isdir(extracted):
            raise ValueError("{0}: archive did not contain expected root {1}".format(dependency["name"], source_root))
        shutil.move(extracted, target)
        print("{0}: extracted verified source to {1}".format(dependency["name"], target))
    finally:
        shutil.rmtree(temporary)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lockfile", default=DEFAULT_LOCKFILE)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--all", action="store_true", help="fetch and verify every locked source")
    modes.add_argument("--name", help="fetch and verify one named source")
    modes.add_argument("--verify-archive", help="verify a local archive without downloading it")
    parser.add_argument("--output-dir", default="/root/ffmpeg_sources/downloads")
    parser.add_argument("--extract-dir", help="also extract each verified archive into a directory named for its dependency")
    parser.add_argument("--archive", help="archive path for --verify-archive")
    parser.add_argument("--signature-file", action="append", help="local detached signature for --verify-archive; repeat in lock order")
    args = parser.parse_args()

    try:
        dependencies = load_lock(args.lockfile)
        if args.verify_archive:
            if not args.archive:
                parser.error("--verify-archive requires --archive")
            dependency = select_dependency(dependencies, args.verify_archive)
            verify_archive(dependency, args.archive)
            signatures = dependency_signatures(dependency)
            signature_files = args.signature_file or []
            if len(signature_files) != len(signatures):
                parser.error("{0} requires {1} --signature-file value(s) in lock order".format(args.verify_archive, len(signatures)))
            for signature, signature_path in zip(signatures, signature_files):
                verify_signature(dependency, signature, args.archive, signature_path)
            if args.extract_dir:
                if not os.path.isdir(args.extract_dir):
                    os.makedirs(args.extract_dir)
                extract_source(dependency, args.archive, args.extract_dir)
            return 0

        selected = dependencies if args.all else [select_dependency(dependencies, args.name)]
        if not os.path.isdir(args.output_dir):
            os.makedirs(args.output_dir)
        for dependency in selected:
            archive_path = os.path.join(args.output_dir, dependency["archive"])
            if not os.path.isfile(archive_path):
                print("Fetching {0} {1}".format(dependency["name"], dependency["version"]))
                download(dependency["url"], archive_path)
            verify_archive(dependency, archive_path)
            for signature in dependency_signatures(dependency):
                signature_name = signature.get("file", dependency["archive"] + ".asc")
                signature_path = os.path.join(args.output_dir, signature_name)
                if not os.path.isfile(signature_path):
                    download(signature["url"], signature_path)
                verify_signature(dependency, signature, archive_path, signature_path)
            if args.extract_dir:
                extract_source(dependency, archive_path, args.extract_dir)
        return 0
    except Exception as error:
        print("source lock error: {0}".format(error), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
