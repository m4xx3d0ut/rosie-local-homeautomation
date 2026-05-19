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

`kiosk.launch` supports optional local URLs:

- `home_assistant_url`: when set, the Home Assistant button opens this URL in the browser instead of launching the Companion app. With the default Fennec package shared by both buttons, HA opens in a Fennec Custom Tab so normal Browser tabs do not leak into the HA view.
- `browser_url`: when set, the Browser button opens this URL as a new normal Fennec/Firefox-compatible browser tab instead of opening a blank browser session. Use `https://duckduckgo.com/` for a neutral general-browsing start page.
- `home_assistant_browser_package`: optional override for the browser package used only by the Home Assistant button.

`system.ui_night_mode` controls the Android default night mode and accepts `'yes'`, `'no'`, or `'auto'`. Quote the value because YAML otherwise treats `yes` and `no` as booleans. The public profile uses `'yes'`.

To isolate Home Assistant tabs from general browser tabs, add a second browser APK under `apps.home_assistant_browser`:

```yaml
apps:
  home_assistant_browser:
    module: FirefoxFocus
    package: org.mozilla.focus
    apk: inputs/apks/FirefoxFocus.apk
    sha256: REPLACE_WITH_FIREFOX_FOCUS_APK_SHA256
```

When present, the tablet image installs that APK and the Home Assistant button targets it instead of using the shared-browser Custom Tab path. The Browser button still targets `apps.browser`.

Media paths must be repository-relative. Images may be `.png`, `.jpg`, `.jpeg`, or `.webp`. Videos may be `.mp4`, `.m4v`, `.3gp`, or `.webm`; prefer short muted H.264 MP4 loops for the K1 tablet.

Colors accept Android `#RRGGBB` or `#AARRGGBB`, so local overlays can use translucent fills such as `#CC2c2c2c`. The public example follows the k1s docs palette: dark surfaces, muted text, and gold focus accents.

`pin-inputs` refuses overlays so private values are not written into the tracked base profile. Pin private asset hashes manually with `sha256sum`.
