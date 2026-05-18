# Local Profile Overlays

Put private kiosk customization overlays in this directory. Git ignores local overlay files by default, except for the checked-in example.

Use an overlay with any command:

```bash
make build-images PROFILE_OVERLAY=profiles/local/site.yaml
make validate-emulator PROFILE_OVERLAY=profiles/local/site.yaml
```

Overlays are deep-merged over the selected public profile. Keep private media under `inputs/kiosk-assets/` and pin each asset with `sha256sum`.
