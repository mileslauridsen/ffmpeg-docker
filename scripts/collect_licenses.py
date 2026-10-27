#!/usr/bin/env python3
"""Copy upstream license and notice files while preserving their source paths."""

import os
import shutil
import sys


NOTICE_PREFIXES = ("COPYING", "LICENSE", "COPYRIGHT", "NOTICE")


def collect(source_root, destination):
    source_root = os.path.abspath(source_root)
    copied = 0

    for current, directories, filenames in os.walk(source_root):
        relative_directory = os.path.relpath(current, source_root)
        depth = 0 if relative_directory == "." else len(relative_directory.split(os.sep))
        if depth >= 2:
            directories[:] = []

        for filename in filenames:
            upper_name = filename.upper()
            if not upper_name.startswith(NOTICE_PREFIXES) and upper_name != "PATENTS":
                continue

            source_path = os.path.join(current, filename)
            relative_path = os.path.relpath(source_path, source_root)
            destination_path = os.path.join(destination, relative_path)
            os.makedirs(os.path.dirname(destination_path), exist_ok=True)
            shutil.copy2(source_path, destination_path)
            copied += 1

    if copied == 0:
        raise RuntimeError("no license or notice files found in " + source_root)

    print("Copied {0} notice files from {1}".format(copied, source_root))


def main(argv):
    if len(argv) != 3:
        raise SystemExit("usage: collect_licenses.py SOURCE_DIR OUTPUT_DIR")
    collect(argv[1], argv[2])


if __name__ == "__main__":
    try:
        main(sys.argv)
    except (OSError, RuntimeError) as error:
        print("license collection error: {0}".format(error), file=sys.stderr)
        raise SystemExit(1)
