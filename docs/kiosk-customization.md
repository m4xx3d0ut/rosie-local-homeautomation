# Kiosk Customization

The public profile contains a neutral native launcher theme. Site-specific text, colors, and media should live in an ignored overlay under `profiles/local/`, with private assets under `inputs/kiosk-assets/`.

## Local Overlay

Copy the example overlay and replace private values:

```bash
cp profiles/local/example-site.yaml profiles/local/site.yaml
sha256sum inputs/kiosk-assets/background.png
make validate-inputs PROFILE_OVERLAY=profiles/local/site.yaml
```

Use the same overlay for build and validation:

```bash
make build-images PROFILE_OVERLAY=profiles/local/site.yaml
make validate-emulator PROFILE_OVERLAY=profiles/local/site.yaml
make publish-flash-bundle PROFILE_OVERLAY=profiles/local/site.yaml
```

## Theme Fields

`kiosk.theme` supports:

- `title`, `subtitle`, and `font_family`
- `background.type`: `color`, `image`, or `video`
- `background.path` and `background.sha256` for image/video assets
- `background.fit`: `cover`, `contain`, `stretch`, or `height` for video-only height-crop
- `background.loop`, `fallback_color`, and `scrim_color`
- `text.color`, `subtitle_color`, sizes, and optional shadow controls
- `buttons.*` labels, fill/text/border colors, text size, radius, height, and width

Media paths must be repository-relative. Images may be `.png`, `.jpg`, `.jpeg`, or `.webp`. Videos may be `.mp4`, `.m4v`, `.3gp`, or `.webm`; prefer short muted H.264 MP4 loops for the K1 tablet.

Colors accept Android `#RRGGBB` or `#AARRGGBB`, so local overlays can use translucent fills such as `#CC2c2c2c`. The public example follows the k1s docs palette: dark surfaces, muted text, and gold focus accents.

`pin-inputs` refuses overlays so private values are not written into the tracked base profile. Pin private asset hashes manually with `sha256sum`.
