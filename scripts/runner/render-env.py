#!/usr/bin/env python3
import argparse
import copy
import os
import shlex
from pathlib import Path

import yaml


DEFAULT_THEME = {
    "title": "Rosie Kiosk",
    "subtitle": "Home Assistant and browser access",
    "font_family": "sans",
    "background": {
        "type": "color",
        "fit": "cover",
        "loop": True,
        "fallback_color": "#0f1216",
        "scrim_color": "#00000000",
    },
    "text": {
        "color": "#ffffff",
        "subtitle_color": "#bec6cd",
        "title_size_sp": 34,
        "subtitle_size_sp": 18,
        "shadow_color": "#99000000",
        "shadow_radius_dp": 2,
        "shadow_dx_dp": 0,
        "shadow_dy_dp": 2,
    },
    "buttons": {
        "home_assistant_label": "Home Assistant",
        "browser_label": "Browser",
        "background_color": "#00a884",
        "text_color": "#ffffff",
        "accent_color": "#007c61",
        "border_color": "#00a884",
        "focus_border_color": "#007c61",
        "text_size_sp": 22,
        "radius_dp": 6,
        "min_height_dp": 68,
        "width_dp": 520,
    },
}


def load_mapping(path):
    with open(path, "r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    if not isinstance(data, dict):
        raise ValueError("profile must be a YAML mapping: {}".format(path))
    return data


def deep_merge(base, overlay):
    merged = copy.deepcopy(base)
    for key, value in overlay.items():
        if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
            merged[key] = deep_merge(merged[key], value)
        else:
            merged[key] = copy.deepcopy(value)
    return merged


def load_profile(path, overlay_path):
    profile = load_mapping(path)
    if overlay_path:
        profile = deep_merge(profile, load_mapping(overlay_path))
    return profile


def bool_string(value):
    if isinstance(value, bool):
        return "true" if value else "false"
    return "true" if str(value).lower() in ("1", "true", "yes", "on") else "false"


def theme_for(profile):
    kiosk = profile.get("kiosk") or {}
    theme = kiosk.get("theme") or {}
    return deep_merge(DEFAULT_THEME, theme)


def env_for(profile, repo_root, container):
    paths = profile["paths"]
    android_root = "/android" if container else str((repo_root / paths["android_root"]).resolve())
    ccache = "/ccache" if container else str((repo_root / paths["ccache"]).resolve())
    artifacts = "/artifacts" if container else str((repo_root / paths["dist"]).resolve())
    emulator_browser = profile["apps"].get("emulator_browser", profile["apps"]["browser"])
    kiosk = profile.get("kiosk", {})
    kiosk_launcher = kiosk.get("launcher", {})
    theme = theme_for(profile)
    background = theme["background"]
    text = theme["text"]
    buttons = theme["buttons"]
    env = {
        "PROFILE_NAME": str(profile.get("profile") or "unnamed"),
        "LINEAGE_REPO_URL": str(profile["lineage"]["repo_url"]),
        "LINEAGE_BRANCH": str(profile["lineage"]["branch"]),
        "LINEAGE_SYNC_JOBS": str(profile["lineage"]["sync_jobs"]),
        "TABLET_LUNCH": str(profile["targets"]["tablet"]["lunch"]),
        "TABLET_OUTPUT_PRODUCT": str(profile["targets"]["tablet"]["output_product"]),
        "TABLET_PRODUCT_MK": str(profile["targets"]["tablet"]["product_makefile"]),
        "TABLET_BUILD_COMMAND": str(profile["targets"]["tablet"]["build_command"]),
        "EMULATOR_LUNCH": str(profile["targets"]["emulator"]["lunch"]),
        "EMULATOR_OUTPUT_PRODUCT": str(profile["targets"]["emulator"]["output_product"]),
        "EMULATOR_PRODUCT_MK": str(profile["targets"]["emulator"]["product_makefile"]),
        "EMULATOR_BUILD_COMMAND": str(profile["targets"]["emulator"]["build_command"]),
        "EMULATOR_SYSTEM_IMAGE_SIZE": str(profile["targets"]["emulator"].get("system_image_size", "")),
        "HA_MODULE": str(profile["apps"]["home_assistant"]["module"]),
        "HA_PACKAGE": str(profile["apps"]["home_assistant"]["package"]),
        "HA_APK": str(profile["apps"]["home_assistant"]["apk"]),
        "HA_SHA256": str(profile["apps"]["home_assistant"]["sha256"]),
        "BROWSER_MODULE": str(profile["apps"]["browser"]["module"]),
        "BROWSER_PACKAGE": str(profile["apps"]["browser"]["package"]),
        "BROWSER_APK": str(profile["apps"]["browser"]["apk"]),
        "BROWSER_SHA256": str(profile["apps"]["browser"]["sha256"]),
        "EMULATOR_BROWSER_MODULE": str(emulator_browser["module"]),
        "EMULATOR_BROWSER_PACKAGE": str(emulator_browser["package"]),
        "EMULATOR_BROWSER_APK": str(emulator_browser["apk"]),
        "EMULATOR_BROWSER_SHA256": str(emulator_browser["sha256"]),
        "KIOSK_LAUNCHER_MODULE": str(kiosk_launcher.get("module", "RosieKioskLauncher")),
        "KIOSK_LAUNCHER_PACKAGE": str(kiosk_launcher.get("package", "local.rosie.kiosk")),
        "KIOSK_REMOVE_MODULES": " ".join(kiosk.get("remove_modules", [])),
        "KIOSK_REMOVE_PACKAGES": " ".join(kiosk.get("remove_packages", [])),
        "KIOSK_TITLE": str(theme["title"]),
        "KIOSK_SUBTITLE": str(theme["subtitle"]),
        "KIOSK_FONT_FAMILY": str(theme["font_family"]),
        "KIOSK_BACKGROUND_TYPE": str(background["type"]),
        "KIOSK_BACKGROUND_PATH": str(background.get("path") or ""),
        "KIOSK_BACKGROUND_FIT": str(background["fit"]),
        "KIOSK_BACKGROUND_LOOP": bool_string(background["loop"]),
        "KIOSK_BACKGROUND_FALLBACK_COLOR": str(background["fallback_color"]),
        "KIOSK_BACKGROUND_SCRIM_COLOR": str(background["scrim_color"]),
        "KIOSK_TEXT_COLOR": str(text["color"]),
        "KIOSK_SUBTITLE_COLOR": str(text["subtitle_color"]),
        "KIOSK_TITLE_SIZE_SP": str(text["title_size_sp"]),
        "KIOSK_SUBTITLE_SIZE_SP": str(text["subtitle_size_sp"]),
        "KIOSK_TEXT_SHADOW_COLOR": str(text["shadow_color"]),
        "KIOSK_TEXT_SHADOW_RADIUS_DP": str(text["shadow_radius_dp"]),
        "KIOSK_TEXT_SHADOW_DX_DP": str(text["shadow_dx_dp"]),
        "KIOSK_TEXT_SHADOW_DY_DP": str(text["shadow_dy_dp"]),
        "KIOSK_BUTTON_HA_LABEL": str(buttons["home_assistant_label"]),
        "KIOSK_BUTTON_BROWSER_LABEL": str(buttons["browser_label"]),
        "KIOSK_BUTTON_BACKGROUND_COLOR": str(buttons["background_color"]),
        "KIOSK_BUTTON_TEXT_COLOR": str(buttons["text_color"]),
        "KIOSK_BUTTON_ACCENT_COLOR": str(buttons["accent_color"]),
        "KIOSK_BUTTON_BORDER_COLOR": str(buttons["border_color"]),
        "KIOSK_BUTTON_FOCUS_BORDER_COLOR": str(buttons["focus_border_color"]),
        "KIOSK_BUTTON_TEXT_SIZE_SP": str(buttons["text_size_sp"]),
        "KIOSK_BUTTON_RADIUS_DP": str(buttons["radius_dp"]),
        "KIOSK_BUTTON_MIN_HEIGHT_DP": str(buttons["min_height_dp"]),
        "KIOSK_BUTTON_WIDTH_DP": str(buttons["width_dp"]),
        "BLOB_ARCHIVE": str(profile["blobs"]["archive"]),
        "BLOB_SHA256": str(profile["blobs"]["sha256"]),
        "ADB_PUBLIC_KEY": str(profile.get("debug", {}).get("adb_public_key", "")),
        "ANDROID_API_LEVEL": str(profile.get("android", {}).get("api_level", "")),
        "ANDROID_ABI": str(profile.get("android", {}).get("abi", "")),
        "ANDROID_ROOT": android_root,
        "CCACHE_DIR": ccache,
        "ARTIFACT_DIR": artifacts,
        "BOOT_TIMEOUT_SECONDS": str(profile["validation"].get("boot_timeout_seconds", 600)),
        "USE_SDK_EMULATOR": "1" if profile["validation"].get("use_sdk_emulator", False) else "0",
        "NO_GMS_PACKAGES": " ".join(profile["validation"].get("no_gms_packages", [])),
        "REPO_ROOT": "/work/repo" if container else str(repo_root),
    }
    return env


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", required=True)
    parser.add_argument("--profile-overlay")
    parser.add_argument("--output", required=True)
    parser.add_argument("--container", action="store_true")
    args = parser.parse_args()

    profile_path = Path(args.profile)
    overlay_path = (
        args.profile_overlay
        or os.environ.get("PROFILE_OVERLAY_PATH")
        or os.environ.get("PROFILE_OVERLAY")
    )
    repo_root = Path("/work/repo") if args.container else profile_path.resolve().parents[1]
    profile = load_profile(profile_path, overlay_path)
    lines = []
    for key, value in env_for(profile, repo_root, args.container).items():
        lines.append("export {}={}".format(key, shlex.quote(value)))
    Path(args.output).write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
