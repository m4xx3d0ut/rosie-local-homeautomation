# APK Inputs

Place pinned APK inputs here before running `make preflight`.

Expected initial files:

- `HomeAssistantMinimal.apk`
- `FennecFdroid.apk`
- `PrivacyBrowser.apk`

The Shield K1 tablet image uses Fennec F-Droid. The x86 emulator companion uses Privacy Browser because current Fennec F-Droid APKs are ARM-only and cannot launch on the x86 emulator. The default Lineage 15.1 profile pins the expected SHA-256 hashes for these files. Use `make validate-inputs` to verify the APKs before building. Do not commit APK binaries unless the repository policy explicitly allows it.

Kiosk background media belongs in `inputs/kiosk-assets/`, not this directory.
