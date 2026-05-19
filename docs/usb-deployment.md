# USB Tablet Deployment

Physical tablet automation runs on the host, not inside WorkerBee. WorkerBee still builds the runner image and performs emulator validation; host `adb` and `fastboot` handle USB because bootloader/recovery mode changes can re-enumerate the device.

## Host Prep

Install Android SDK Platform Tools so these commands work on the host:

```bash
adb --version
fastboot --version
```

If the tablet is not visible as your user, inspect it with `lsusb`, add a udev rule for the NVIDIA vendor/product ID, reload udev, and reconnect the cable.

## Tablet Prep

On the tablet:

1. Enable Developer Options.
2. Enable USB debugging.
3. Enable OEM unlocking if available.
4. Connect USB and accept the adb RSA prompt.

Bootloader unlocking is a one-time manual gate and wipes user data. If `make device-preflight` reports a locked bootloader, unlock it intentionally from fastboot before deployment.

## Safe Flow

```bash
make device-preflight SERIAL=<serial>
make deploy-tablet BUILD_DIR=dist/<build-id> SERIAL=<serial> ALLOW_DESTRUCTIVE=1
make validate-tablet BUILD_DIR=dist/<build-id> SERIAL=<serial>
```

The default `first-install` flow erases `userdata` and `cache` before sideloading the validated image. This avoids stale settings from an older LineageOS build crashing first boot. Development images also set `persist.sys.usb.config=mtp,adb`, cap the kiosk build to one Android user with `fw.max_users=1`, disable timezone updater tracking, seed setup-complete settings, default Android UI night mode to dark, and install `RosieKioskLauncher` as HOME.

To authorize ADB before the first-boot UI is usable, generate `inputs/adb/host-adbkey.pub` and opt in from an ignored local overlay:

```yaml
debug:
  adb_public_key: inputs/adb/host-adbkey.pub
```

Use a dry run before the first destructive deployment:

```bash
make deploy-tablet BUILD_DIR=dist/<build-id> SERIAL=<serial> DRY_RUN=1
```

Use `INSTALL_MODE=update` only when preserving `/data` is intentional and the currently installed build is known to be compatible with the new image.

## ADB Root For Automated Updates

LineageOS 15.1 userdebug builds require root access to be enabled before `adb root` and `adb reboot sideload` work. For local development images, enable ADB-only root in an ignored profile overlay:

```yaml
debug:
  root_access: adb
  adb_public_key: inputs/adb/host-adbkey.pub
```

Then generate the ignored host key before building:

```bash
adb pubkey ~/.android/adbkey > inputs/adb/host-adbkey.pub
```

After that image is installed once, future non-wipe updates can use `INSTALL_MODE=update`.

## Runtime Defaults

Fresh installs read `system.ui_night_mode` from the image overlay. Non-wipe updates preserve existing `/data` settings, so `deploy-tablet` also applies the configured profile value after Android boots. To apply the system defaults without flashing:

```bash
make device-apply-system-defaults SERIAL=<serial> PROFILE_OVERLAY=profiles/local/site.yaml
```

Fennec browser chrome, website color-scheme preferences, and LatinIME keyboard theme live under app data, so they require `adb root` and are applied only when configured in a local overlay. To apply the app runtime defaults without flashing:

```bash
make device-apply-app-defaults SERIAL=<serial> PROFILE_OVERLAY=profiles/local/site.yaml
```

With `debug.root_access: adb`, `deploy-tablet` applies configured system and app defaults after Android boots and after any Wi-Fi restore reboot.

## Wi-Fi Backup

Wi-Fi backups require `adb root`, so they work after installing a development image with `debug.root_access: adb`. Back up Wi-Fi secrets before destructive flashes:

```bash
make device-backup-wifi SERIAL=<serial> BUILD_DIR=dist/<build-id>
```

Restore the latest backup after boot:

```bash
make device-restore-wifi SERIAL=<serial> BUILD_DIR=dist/<build-id>
```

For destructive deploys, `WIFI_BACKUP=1` backs up before erasing and restores after the flashed image boots:

```bash
make deploy-tablet \
  BUILD_DIR=dist/<build-id> \
  SERIAL=<serial> \
  INSTALL_MODE=fastboot-image-install \
  ALLOW_DESTRUCTIVE=1 \
  WIFI_BACKUP=1
```

Wi-Fi backup tarballs contain PSKs. They are written under ignored build or work directories and must not be committed.

If the tablet is already in bootloader/fastboot mode, start the same destructive first-install flow from there:

```bash
make deploy-tablet \
  BUILD_DIR=dist/<build-id> \
  SERIAL=<serial> \
  INSTALL_MODE=fastboot-first-install \
  ALLOW_DESTRUCTIVE=1
```

If recovery sideload never appears, use the fastboot-only fallback. This flashes `boot.img`, `recovery.img`, and `system.img` from the validated bundle, then reboots:

```bash
make deploy-tablet \
  BUILD_DIR=dist/<build-id> \
  SERIAL=<serial> \
  INSTALL_MODE=fastboot-image-install \
  ALLOW_DESTRUCTIVE=1
```

If recovery boots but is not in sideload mode, select **Apply update > Apply from ADB** on the tablet, then resume:

```bash
make deploy-tablet \
  BUILD_DIR=dist/<build-id> \
  SERIAL=<serial> \
  INSTALL_MODE=resume-sideload \
  ALLOW_DESTRUCTIVE=1
```

## Evidence

Device evidence is written under:

```text
dist/<build-id>/device-validation/<serial>/
```

Expected files include preflight, deployment, validation JSON, package list, getprop summary, logcat, and screenshot.
