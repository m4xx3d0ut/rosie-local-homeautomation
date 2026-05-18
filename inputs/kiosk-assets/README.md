# Kiosk Asset Inputs

Place private kiosk background media here for local builds.

Supported background asset types:

- Images: `.png`, `.jpg`, `.jpeg`, `.webp`
- Videos: `.mp4`, `.m4v`, `.3gp`, `.webm`

Files in this directory are ignored by git. Reference them from an ignored profile overlay such as `profiles/local/site.yaml`, then run:

```bash
sha256sum inputs/kiosk-assets/<file>
make validate-inputs PROFILE_OVERLAY=profiles/local/site.yaml
```
