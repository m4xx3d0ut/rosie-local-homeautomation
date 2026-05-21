# APK Inputs

Place pinned APK inputs here before running `make preflight`.

Expected initial files:

- `HomeAssistantMinimal.apk`
- `FennecFdroid.apk`
- `PrivacyBrowser.apk`
- `NewPipe.apk`
- `Kreate.apk`
- `Joplin.apk`
- `BreezyWeather.apk`

Download the public default app set from F-Droid:

```bash
curl -L https://f-droid.org/repo/org.schabi.newpipe_1010.apk -o inputs/apks/NewPipe.apk
curl -L https://f-droid.org/repo/me.knighthat.kreate_135.apk -o inputs/apks/Kreate.apk
curl -L https://f-droid.org/repo/net.cozic.joplin_2097806.apk -o inputs/apks/Joplin.apk
curl -L https://f-droid.org/repo/org.breezyweather_60200.apk -o inputs/apks/BreezyWeather.apk
make pin-inputs
```

The Shield K1 tablet image uses Fennec F-Droid. The x86 emulator companion uses Privacy Browser because current Fennec F-Droid APKs are ARM-only and cannot launch on the x86 emulator. The default Lineage 15.1 profile pins the expected SHA-256 hashes for these files. Use `make validate-inputs` to verify the APKs before building. Do not commit APK binaries unless the repository policy explicitly allows it.

Kiosk background media belongs in `inputs/kiosk-assets/`, not this directory.
