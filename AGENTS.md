# Repository Guidelines

## Project Structure & Module Organization

This repository contains the `rosie-local-ha` build, validation, and USB deployment pipeline for a LineageOS-derived Home Assistant kiosk image on the NVIDIA Shield Tablet K1. Start with `README.md`, then use `docs/build-pipeline.md` for command details.

- `tools/kioskctl.py`: command dispatcher for profiles, input locking, build orchestration, WorkerBee validation manifests, and USB deployment gates.
- `profiles/`: YAML build profiles. The default first-build target is `shield-k1-lineage15-dev.yaml`; the Lineage 18.1 profile remains a future experiment.
- `scripts/runner/`: container-side source sync, prebuilt APK injection, image build, and emulator validation scripts.
- `container/`: Docker build environments, including `container/lineage15/Dockerfile` for the Android 8.1/Lineage 15.1 build.
- `inputs/apks/`: pinned Home Assistant minimal and Fennec F-Droid APKs; binaries are ignored by Git.
- `inputs/vendor-blobs/`: locally generated Shield K1 proprietary blob archives; binaries are ignored by Git.
- `docs/`: build, emulator validation, flashing, and USB deployment instructions.
- `dist/`: generated ROM artifacts and manifests; keep output out of Git.

## Build, Test, and Development Commands

Use `make` as the guaranteed local entrypoint. `Taskfile.yml` exists only as a convenience wrapper for systems with `task` installed.

- `make profile-lint`: validate profile structure.
- `make pin-inputs`: update profile SHA-256 pins for present APK/blob inputs.
- `make validate-inputs`: verify APK hashes, ABI compatibility, and blob archive hash.
- `make preflight`: verify host tools, KVM, APK inputs, blob archive, and hashes.
- `make test`: run lightweight Python tests for profile and manifest behavior.
- `make build-runner`: build the Android runner container with local Docker; use WorkerBee image build for WorkerBee validation.
- `make sync-sources`: sync the configured LineageOS tree into `.work/`.
- `make extract-blobs`: extract vendor blobs from the adb-connected Shield K1 and pin the blob archive hash.
- `make build-images`: build the emulator companion image and Shield K1 image.
- `make validate-emulator`: generate the WorkerBee emulator validation Job.
- `make publish-flash-bundle`: publish manual-flash artifacts after validation passes.
- `make device-preflight`: verify host adb/fastboot and the plugged-in tablet.
- `make device-snapshot`: collect non-destructive device evidence.
- `make deploy-tablet`: gated USB deployment; requires explicit serial and `ALLOW_DESTRUCTIVE=1`.
- `make validate-tablet`: collect post-flash tablet evidence.
- `make collect-device-logs`: collect logs and package/build evidence from a booted tablet.
- `make full-pipeline`: run build through WorkerBee emulator job staging; publish only after validation evidence exists.

## Coding Style & Naming Conventions

Use small, explicit shell scripts with `set -euo pipefail`. Prefer YAML for profiles and lowercase kebab-case names, for example `shield-k1-ha-kiosk-release`. Use two-space indentation for YAML and four spaces for Python if added.

Keep generated Android artifacts, proprietary blobs, and signing material separate from source-controlled build logic. Commit checksums and manifests, not large binary inputs.

## Testing Guidelines

Focus tests on reproducibility and device safety. Add coverage for profile parsing, APK checksum verification, package injection, and manifest generation before automating flashable builds. Name tests after behavior, such as `test_verify_apk_hashes.py` or `verify-apks.bats`.

For ROM work, record smoke-test results in manifests: boot status, Wi-Fi, touch, display rotation, charging, Home Assistant launch, and browser launch.

## Commit & Pull Request Guidelines

Use concise imperative messages with an optional scope, following the existing history, for example `Add APK verification script` or `device-config: add kiosk product makefile`.

Pull requests should include purpose, changed build/profile paths, validation performed, and device-flashing impact. Include screenshots or logs for UI, boot, or kiosk changes.

## Security & Configuration Tips

Do not commit proprietary vendor blobs, private signing keys, Home Assistant secrets, Wi-Fi credentials, or release artifacts containing secrets. Keep dev and release builds separate, and avoid long-term images signed only with public Android test keys.
