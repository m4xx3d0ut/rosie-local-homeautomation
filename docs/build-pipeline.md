# Build Pipeline

The initial build system produces two Android outputs from one locked profile:

1. A LineageOS 15.1 `sdk_phone_x86` companion image for automated validation.
2. A LineageOS 15.1 Shield Tablet K1 flashable artifact for manual tablet testing.

The emulator does not boot the Tegra Shield image. It validates the shared build inputs, generated kiosk launcher, removed Lineage setup/home apps, and product-app injection with Home Assistant minimal plus an emulator-compatible browser APK on the tree's SDK x86 emulator target. The Shield K1 output remains pinned to the ARM Fennec F-Droid APK.

## Commands

```bash
make profile-lint
make pin-inputs
make validate-inputs
make preflight
make build-runner
make sync-sources
make extract-blobs SERIAL=<serial>
make build-images
make validate-emulator
make publish-flash-bundle
make device-preflight SERIAL=<serial>
make deploy-tablet BUILD_DIR=dist/<build-id> SERIAL=<serial> ALLOW_DESTRUCTIVE=1
make validate-tablet BUILD_DIR=dist/<build-id> SERIAL=<serial>
```

Use a different profile with:

```bash
make build-images PROFILE=profiles/my-profile.yaml
```

Use private kiosk customization without committing it by adding an ignored overlay:

```bash
make build-images PROFILE_OVERLAY=profiles/local/site.yaml
make validate-emulator PROFILE_OVERLAY=profiles/local/site.yaml
```

See `docs/kiosk-customization.md` for supported theme fields and asset rules.

## Required Inputs

Before `make preflight` can pass, provide:

- `inputs/apks/HomeAssistantMinimal.apk`
- `inputs/apks/FennecFdroid.apk`
- `inputs/apks/PrivacyBrowser.apk`
- `inputs/vendor-blobs/vendor-nvidia-shieldtablet-lineage15.tar.zst`
- optional private kiosk media under `inputs/kiosk-assets/`

The default profile already pins the downloaded APK hashes. Run `make sync-sources`, then `make extract-blobs SERIAL=<serial>` against an adb-authorized Shield Tablet K1 to generate and pin the vendor blob archive.

`make build-images` expects the LineageOS checkout to already exist under `.work/android-lineage15`. Re-run `make sync-sources` when you intentionally want to refresh upstream sources.

## WorkerBee Runner Image

`make build-runner` builds the Lineage 15.1 runner with local Docker from `container/lineage15/Dockerfile`. `make validate-emulator` runs that image locally and also writes a WorkerBee Job manifest. For WorkerBee-only validation, build the same tag with WorkerBee's image build facility so the image is available to the WorkerBee runtime before deploying the generated Job.

## Output Contract

Build outputs are written under `dist/<build-id>/`. The final manual-flash bundle is published only after emulator validation passes:

```text
dist/<build-id>/manual-flash/
  BUILD-MANIFEST.json
  EMULATOR-VALIDATION.json
  INPUT-LOCK.json
  SHA256SUMS
  lineage-*-shieldtablet.zip
  recovery.img
  boot.img
  system.img
```

Physical deployment is intentionally separate from publishing. See `docs/usb-deployment.md` before flashing a connected tablet.
