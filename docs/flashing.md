# Manual Flashing

Only flash artifacts from:

```text
dist/<build-id>/manual-flash/
```

Do not flash intermediate files from `.work/android/out` directly unless you are debugging the build system.

For automated USB deployment from this host, use `docs/usb-deployment.md`. The deployment command refuses destructive operations unless a serial is explicit and `ALLOW_DESTRUCTIVE=1` is set.

## Before Flashing

Verify:

- `EMULATOR-VALIDATION.json` has `"status": "pass"`.
- `SHA256SUMS` matches every file in the manual-flash directory.
- The target tablet is the NVIDIA Shield Tablet K1 / `shieldtablet`.
- You have a known recovery path and a retained rollback image.

## First Tablet Smoke Test

After flashing, record:

- boot completes
- touch works
- Wi-Fi works
- charging status is correct
- display rotation is acceptable
- Home Assistant minimal launches
- Chromium launches
- no Google account or Play Services dependency appears
