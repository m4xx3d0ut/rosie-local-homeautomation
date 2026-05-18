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

The default `first-install` flow erases `userdata` and `cache` before sideloading the validated image. This avoids stale settings from an older LineageOS build crashing first boot. Development images also set `persist.sys.usb.config=mtp,adb`, cap the kiosk build to one Android user with `fw.max_users=1`, disable timezone updater tracking, seed setup-complete settings, and install `RosieKioskLauncher` as HOME.

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
