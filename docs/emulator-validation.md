# Emulator Validation

The default validation command runs the local runner container and writes a WorkerBee-compatible Kubernetes Job for repeatable automation:

```bash
make validate-emulator BUILD_DIR=dist/<build-id>
```

The generated WorkerBee manifest is written to:

```text
dist/<build-id>/workerbee/emulator-validation-job.k8s.yaml
```

The local container and WorkerBee Job mount:

- the repo at `/work/repo`
- the Android source/build tree at `/android`
- the current build artifact directory at `/artifacts`
- `/dev/kvm` for emulator acceleration

This is intentionally local-only. The WorkerBee Job uses privileged mode because KVM-backed Android Emulator execution needs host device access. The local Docker path passes `/dev/kvm` and the device group into the container when `/dev/kvm` is present.

## Checks

The validator cold-boots the `sdk_phone_x86` companion target with the pinned SDK emulator, waits for `sys.boot_completed=1`, and checks:

- Home Assistant minimal package is installed and launchable.
- The emulator-compatible browser package is installed and launchable.
- Profile-pinned apps are installed.
- The generated `RosieKioskLauncher` package is installed and owns the HOME intent.
- First-run setup is already marked complete.
- Profile time, timezone, NTP, location-provider, and runtime permission defaults are present.
- Profile-listed Lineage setup/home packages are absent.
- Google Play Services and Play Store packages are absent.
- Logs, package list, a kiosk home screenshot, and a final screenshot are captured.

The Shield K1 tablet image still uses the ARM Fennec F-Droid APK. The emulator companion uses `apps.emulator_browser` from the profile because current Fennec F-Droid APKs are ARM-only.

When `PROFILE_OVERLAY` is set, emulator validation uses the same merged kiosk theme and private assets as the tablet build. Review `dist/<build-id>/screenshots/kiosk-home.png` for app-row layout and scale; `final.png` remains secondary evidence after launch smoke checks.

The result is written to `EMULATOR-VALIDATION.json`. `make publish-flash-bundle` refuses to publish if this file is missing or does not contain `"status": "pass"`.
