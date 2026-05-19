# Rosie's Local Home Assistant

A reproducible Android image build, validation, and USB deployment pipeline for an NVIDIA Shield Tablet K1 home kiosk.

The repository builds a LineageOS 15.1 based development image with no Google services, preloads Home Assistant Companion minimal, preloads a browser APK, installs a small native kiosk launcher as HOME, validates the image with an emulator companion build, and can deploy the validated tablet image over USB with explicit destructive gates.

This is not an official LineageOS, Home Assistant, NVIDIA, or browser project. Why then? I have a good K1 tablet and wanted a custom kiosk image for home assistant. Reduce, reuse, recycle, right? :-)

Who is Rosie? She is a [WorkerBee](https://github.com/the-cm-collective/k1s-workerbee), I'm building some "exploratory" HA integrations for her. If they prove useful, I'll make them public as well.

Regardless of your target device, you can likely adapt the build pipeline to your needs. Hopefully you find it helpful!

## Current Scope

The supported target is the NVIDIA Shield Tablet K1 / `shieldtablet` using the LineageOS 15.1 tree. The default public profile is:

```text
profiles/shield-k1-lineage15-dev.yaml
```

The public profile uses neutral default kiosk text and styling only:

```text
Title:    Rosie Kiosk
Subtitle: Home Assistant and browser access
Theme:    dark neutral background, light text, simple buttons
```

Local site-specific text, colors, background images, videos, Wi-Fi details, Home Assistant URLs, and any private media are intentionally excluded from the public repository.

## What Gets Built

The pipeline produces two Android outputs from one locked profile:

- A Shield Tablet K1 ARM image for physical flashing.
- An x86 emulator companion image for automated validation of shared kiosk logic, APK injection, package removal, and default HOME behavior.

The tablet image includes:

- LineageOS 15.1 / Android 8.1 base for `shieldtablet`
- Home Assistant Companion minimal APK
- Fennec F-Droid browser APK by default for the ARM tablet target
- Privacy Browser APK by default for the x86 emulator target
- `RosieKioskLauncher`, a native launcher with two buttons: Home Assistant and Browser
- Development defaults for ADB, setup completion, disabled lockscreen, dark UI mode, and kiosk HOME selection

The repository does not commit APK binaries, vendor blobs, private assets, host ADB keys, or generated images.

## Repository Layout

```text
container/                 Android build runner Dockerfiles
docs/                      Detailed build, emulator, kiosk, and USB docs
inputs/apks/               Ignored APK input directory plus README
inputs/kiosk-assets/       Ignored local media asset directory plus README
inputs/vendor-blobs/       Ignored proprietary blob archive directory
profiles/                  Public build profiles and ignored local overlays
scripts/runner/            Container-side Android build and validation scripts
tests/                     Python unit tests for safety-critical helpers
tools/kioskctl.py          Main command dispatcher and build/deploy orchestrator
dist/                      Ignored generated build artifacts and evidence
```

## Prerequisites

Use a Linux host with enough disk and RAM for Android source builds. The pipeline expects:

- Docker or a compatible local container runtime for the Android runner image
- Python 3 with PyYAML
- Android SDK Platform Tools: `adb` and `fastboot`
- KVM available for emulator validation
- `repo`, Git, and Android build dependencies inside the runner image
- An unlocked NVIDIA Shield Tablet K1 for physical deployment

Run the lightweight checks first:

```bash
make test
make profile-lint
```

## Required Inputs

Place these files locally before a full build:

```text
inputs/apks/HomeAssistantMinimal.apk
inputs/apks/FennecFdroid.apk
inputs/apks/PrivacyBrowser.apk
inputs/vendor-blobs/vendor-nvidia-shieldtablet-lineage15.tar.zst
```

The default profile pins expected hashes for the current APK inputs. Validate all inputs with:

```bash
make validate-inputs
```

If you need to generate the vendor blob archive from an adb-authorized tablet:

```bash
make sync-sources
make extract-blobs SERIAL=<tablet-serial>
```

## Build Workflow

The normal local flow is:

```bash
make build-runner
make sync-sources
make preflight
make build-images
make validate-emulator
make publish-flash-bundle
```

Build outputs are written to:

```text
dist/<build-id>/
```

The flashable output is only published after emulator validation passes:

```text
dist/<build-id>/manual-flash/
  BUILD-MANIFEST.json
  EMULATOR-VALIDATION.json
  INPUT-LOCK.json
  SHA256SUMS
  lineage-*-shieldtablet.zip
  boot.img
  recovery.img
  system.img
```

Use an explicit build directory for later steps:

```bash
make validate-emulator BUILD_DIR=dist/<build-id>
make publish-flash-bundle BUILD_DIR=dist/<build-id>
```

## Emulator Validation

The emulator validation boots the x86 companion image and checks that:

- Home Assistant minimal is installed
- the emulator browser package is installed
- `RosieKioskLauncher` is installed
- HOME resolves to `local.rosie.kiosk/.LauncherActivity`
- removed setup/home packages are absent
- logs, packages, settings, and a final screenshot are captured

Evidence is written under the selected build directory, including:

```text
EMULATOR-VALIDATION.json
screenshots/final.png
logs/validate-emulator.log
```

WorkerBee users can also use the generated validation Job manifest under:

```text
dist/<build-id>/workerbee/emulator-validation-job.k8s.yaml
```

## USB Tablet Deployment

Physical deployment is intentionally separate from build and emulator validation. It is destructive by default for first installs and requires both an explicit serial and `ALLOW_DESTRUCTIVE=1`.

First confirm the connected tablet:

```bash
adb devices -l
make device-preflight BUILD_DIR=dist/<build-id> SERIAL=<tablet-serial>
```

Then deploy a validated build:

```bash
make deploy-tablet \
  BUILD_DIR=dist/<build-id> \
  SERIAL=<tablet-serial> \
  INSTALL_MODE=fastboot-image-install \
  ALLOW_DESTRUCTIVE=1
```

Validate the booted tablet:

```bash
make validate-tablet BUILD_DIR=dist/<build-id> SERIAL=<tablet-serial>
```

Device evidence is written to:

```text
dist/<build-id>/device-validation/<tablet-serial>/
```

Expected evidence includes deployment JSON, validation JSON, package list, build properties, logcat, HOME focus output, launch logs, and a screenshot.

## Local Customization

Public defaults should stay generic. Site-specific customization belongs in ignored local overlays:

```bash
cp profiles/local/example-site.yaml profiles/local/site.yaml
make validate-inputs PROFILE_OVERLAY=profiles/local/site.yaml
make build-images PROFILE_OVERLAY=profiles/local/site.yaml
```

The overlay system supports local text, colors, button sizing, image or video backgrounds, Android UI night mode, opt-in browser and keyboard theme defaults, launch URLs, and Android ARGB colors such as `#CC2c2c2c`. Private assets belong under `inputs/kiosk-assets/` and should be pinned in the overlay with `sha256sum`.

When `kiosk.launch.home_assistant_url` and `kiosk.launch.browser_url` both target the default Fennec browser, the Home Assistant button opens HA in a Fennec Custom Tab while the Browser button opens the configured URL as a fresh normal Fennec tab. This keeps Browser tabs, such as `https://duckduckgo.com/`, out of the HA view while preserving the normal browser session. For stronger process-level separation, configure an optional `apps.home_assistant_browser` APK; the Home Assistant button then targets that package instead.

If a local development profile uses `debug.root_access: adb` and configures runtime theme defaults, deployment also applies those app-data settings under `/data`, such as Fennec chrome theme, website `prefers-color-scheme`, and the built-in LatinIME keyboard theme.

Do not commit local overlays, private media, Home Assistant secrets, Wi-Fi credentials, vendor blobs, APK binaries, or release signing keys.

## Safety Notes

Flashing custom Android images can wipe data or leave a device unbootable. Keep a known-good recovery path, verify the serial before deployment, and prefer emulator validation plus `device-preflight` before every flash.

The default development images use public Android test keys and development-friendly ADB settings. They are suitable for local testing, not production security.

## More Documentation

- [Build pipeline](docs/build-pipeline.md)
- [Emulator validation](docs/emulator-validation.md)
- [Kiosk customization](docs/kiosk-customization.md)
- [USB deployment](docs/usb-deployment.md)
- [Flashing notes](docs/flashing.md)
