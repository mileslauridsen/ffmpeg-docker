# Locked Source Provenance

`build/dependencies.lock.json` is the authoritative list of source archive URLs, versions or immutable revisions, and expected SHA-256 digests. `build/fetch_sources.py` checks each archive against its digest before extracting it. The Dockerfile does not resolve source branches or moving snapshots.

The lock was assembled from the source recipe's enabled integrations, upstream releases, and installed source inputs. It retains the configured codec set while replacing the moving FFmpeg snapshot and floating repository heads. All locked sources compiled into both `linux/amd64` and `linux/arm64` images using Debian 13 Trixie and GCC 14.2.0. The configured external codec encoders were present, and an H.264 encode/probe passed on both architectures. The project has not defined broader VFX media profiles; those are scheduled for Task 4.

## Verification Evidence

- FFmpeg 8.1.3: archive digest was calculated locally; the detached signature verified with the FFmpeg release signing key fingerprint `FCF986EA15E6E293A5644F10B4322F04D67658D8`.
- libvorbis 1.3.7: archive digest matches the Xiph `SHA256SUMS` file, and its detached signature verified with Ralph Giles's key fingerprint `B7B00AEE1F960EEA0FED66FB9259A8F2D2D44C84`. The signing key is expired; verification establishes the signature against that key, not current key validity.
- x264: pinned to commit `31e19f92f00c7003fa115047ce50978bc98c3a0d`, resolved from the stable branch of the `mirror/x264` repository; the commit archive digest was calculated locally.
- x265 4.1: archive digest matches the VideoLAN x265 download page.
- Opus 1.6.1: archive digest matches the Opus release page.
- libogg 1.3.6: archive digest matches the Xiph `SHA256SUMS` file.
- NASM 3.02, FDK AAC 2.0.3, LAME 3.100, and libvpx 1.17.0: archive digests were calculated locally from the pinned HTTPS source URLs.

Locally calculated hashes protect later builds from changed or corrupted downloads. They establish the exact downloaded archive but do not act as independent upstream signatures. Publisher checksums and detached signatures are recorded where available; the remaining inputs rely on pinned HTTPS URLs and locally calculated hashes. A hash mismatch fails closed. The fetch helper also rejects a source URL that redirects away from HTTPS.

The FFmpeg and Xiph public keys are stored in `build/ffmpeg-release-key.asc` and `build/xiph-rillian-release-key.asc`; the helper checks each signing fingerprint recorded in the lock before accepting a signature. Update the archive, digest, signature, and reviewed key fingerprint together when changing a signed release.

## Lock Update Procedure

1. Update the dependency's version or immutable commit, HTTPS URL, archive filename, expected source root, and SHA-256 in `build/dependencies.lock.json`. For signed releases, also update the signature URL, pinned key file, and reviewed fingerprint.
2. Run `python3 build/fetch_sources.py --all --output-dir /tmp/ffmpeg-lock-downloads --extract-dir /tmp/ffmpeg-lock-sources` and review the resulting identity and signature checks.
3. Build each supported target with `docker build --platform=linux/amd64 --progress=plain -t vfx/ffmpeg:locked-amd64 .` and `docker build --platform=linux/arm64 --progress=plain -t vfx/ffmpeg:locked-arm64 .`; confirm the changed library configures, compiles, and appears in FFmpeg's encoder or decoder list on each target.
4. Run the affected media workflows and probe their output. Update this record and the implementation log with the new evidence before accepting the lock change.
5. Verify the failure path by changing the dependency's digest in a temporary copy of the lock and confirming the helper exits before extraction.
