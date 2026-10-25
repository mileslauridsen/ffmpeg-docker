#!/usr/bin/env python3
"""Fail a builder image if its installed Debian package closure differs from the lock."""

import hashlib
import pathlib
import subprocess
import sys


def main():
    if len(sys.argv) != 2 or sys.argv[1] not in ("amd64", "arm64"):
        raise SystemExit("usage: verify_apt_lock.py amd64|arm64")

    architecture = sys.argv[1]
    lock_path = pathlib.Path(__file__).parent / "apt" / ("resolved-%s.packages" % architecture)
    expected = lock_path.read_text(encoding="utf-8").splitlines()
    result = subprocess.run(
        ["dpkg-query", "-W"], check=True, stdout=subprocess.PIPE, text=True
    )
    actual = sorted(result.stdout.splitlines())

    if actual != expected:
        expected_set = set(expected)
        actual_set = set(actual)
        missing = sorted(expected_set - actual_set)
        unexpected = sorted(actual_set - expected_set)
        raise SystemExit(
            "installed package set differs from %s\nmissing: %s\nunexpected: %s"
            % (lock_path, missing, unexpected)
        )

    digest = hashlib.sha256(("\n".join(actual) + "\n").encode("utf-8")).hexdigest()
    print("Verified %d installed packages for %s; manifest SHA-256 %s" % (
        len(actual), architecture, digest
    ))


if __name__ == "__main__":
    main()
