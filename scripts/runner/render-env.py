#!/usr/bin/env python3
import argparse
import copy
import json
import os
import re
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
DEFAULT_PINNED_APPS = [
    {"app": "home_assistant", "label": "Home Assistant"},
    {"app": "browser", "label": "Browser"},
]


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


def launch_for(profile):
    kiosk = profile.get("kiosk") or {}
    launch = kiosk.get("launch") or {}
    apps = profile.get("apps") or {}
    ha_browser = apps.get("home_assistant_browser") or {}
    browser = apps.get("browser") or {}
    return {
        "home_assistant_url": str(launch.get("home_assistant_url") or ""),
        "browser_url": str(launch.get("browser_url") or ""),
        "browser_launch_policy": str(launch.get("browser_launch_policy") or "always_new_tab"),
        "home_assistant_browser_package": str(
            launch.get("home_assistant_browser_package")
            or ha_browser.get("package")
            or browser.get("package")
            or ""
        ),
    }


def pinned_apps_for(profile):
    kiosk = profile.get("kiosk") or {}
    pinned = kiosk.get("pinned_apps")
    if pinned is None:
        theme = theme_for(profile)
        buttons = theme["buttons"]
        pinned = [
            {"app": "home_assistant", "label": str(buttons["home_assistant_label"])},
            {"app": "browser", "label": str(buttons["browser_label"])},
        ]
    apps = profile.get("apps") or {}
    result = []
    for item in pinned:
        app_key = str(item["app"])
        app = apps[app_key]
        result.append(
            {
                "app": app_key,
                "label": str(item["label"]),
                "package": str(app["package"]),
            }
        )
    return result


def extra_pinned_app_keys(profile):
    special = {"home_assistant", "browser", "home_assistant_browser", "emulator_browser"}
    keys = []
    for item in pinned_apps_for(profile):
        key = item["app"]
        if key not in special and key not in keys:
            keys.append(key)
    return keys


def extra_pinned_apps_json(profile):
    payload = []
    for key in extra_pinned_app_keys(profile):
        app = profile["apps"][key]
        payload.append(
            {
                "app": key,
                "module": str(app["module"]),
                "package": str(app["package"]),
                "apk": str(app["apk"]),
            }
        )
    return json.dumps(payload, sort_keys=True)


def module_list(profile, keys):
    return " ".join(str(profile["apps"][key]["module"]) for key in keys)


ROOT_ACCESS_VALUES = {
    "disabled": "",
    "none": "0",
    "off": "0",
    "apps": "1",
    "adb": "2",
    "all": "3",
}
UI_NIGHT_MODE_VALUES = {
    "auto": "0",
    "0": "0",
    "no": "1",
    "light": "1",
    "off": "1",
    "1": "1",
    "yes": "2",
    "dark": "2",
    "on": "2",
    "true": "2",
    "2": "2",
    "false": "1",
}
UI_NIGHT_MODE_NAMES = {
    "0": "auto",
    "1": "no",
    "2": "yes",
}
BOOLEAN_CONFIG_VALUES = {
    True: True,
    False: False,
    "1": True,
    "true": True,
    "yes": True,
    "on": True,
    "0": False,
    "false": False,
    "no": False,
    "off": False,
}
LOCATION_PROVIDER_VALUES = {"gps", "network"}
RUNTIME_PERMISSION_RE = re.compile(r"^android\.permission\.[A-Z0-9_]+$")


def root_access_value(profile):
    raw = (profile.get("debug") or {}).get("root_access", "")
    if raw is None or raw == "":
        return ""
    value = str(raw).strip().lower()
    if value in ROOT_ACCESS_VALUES:
        return ROOT_ACCESS_VALUES[value]
    return value


def ui_night_mode_value(profile):
    raw = (profile.get("system") or {}).get("ui_night_mode", "auto")
    value = str(raw).strip().lower()
    if value not in UI_NIGHT_MODE_VALUES:
        raise ValueError("system.ui_night_mode must be one of: auto, no, yes")
    return UI_NIGHT_MODE_VALUES[value]


def ui_night_mode_name(profile):
    return UI_NIGHT_MODE_NAMES[ui_night_mode_value(profile)]


def bool_config_value(value, name, default):
    raw = default if value is None else value
    key = raw if isinstance(raw, bool) else str(raw).strip().lower()
    if key not in BOOLEAN_CONFIG_VALUES:
        raise ValueError("{} must be a boolean".format(name))
    return BOOLEAN_CONFIG_VALUES[key]


def bool_setting_value(value):
    return "1" if value else "0"


def bool_xml_value(value):
    return "true" if value else "false"


def system_time_config(profile):
    config = (profile.get("system") or {}).get("time")
    return config if isinstance(config, dict) else {}


def system_auto_time(profile):
    return bool_config_value(system_time_config(profile).get("auto_time"), "system.time.auto_time", True)


def system_auto_time_zone(profile):
    return bool_config_value(
        system_time_config(profile).get("auto_time_zone"),
        "system.time.auto_time_zone",
        True,
    )


def system_timezone(profile):
    value = str(system_time_config(profile).get("timezone") or "").strip()
    if not value:
        return ""
    if value not in ("UTC", "GMT") and not re.match(r"^[A-Za-z_]+/[A-Za-z0-9_+./-]+$", value):
        raise ValueError("system.time.timezone must be an IANA timezone such as America/Los_Angeles")
    return value


def system_ntp_server(profile):
    value = str(system_time_config(profile).get("ntp_server") or "pool.ntp.org").strip()
    if not value or re.search(r"\s", value):
        raise ValueError("system.time.ntp_server must be a hostname or IP address")
    return value


def location_providers_allowed(profile):
    raw = ((profile.get("system") or {}).get("location") or {}).get("providers_allowed", ["gps"])
    if isinstance(raw, str):
        values = [item.strip().lower() for item in raw.split(",")]
    elif isinstance(raw, list):
        values = [str(item).strip().lower() for item in raw]
    else:
        raise ValueError("system.location.providers_allowed must be a list or comma-separated string")
    providers = []
    for provider in values:
        if not provider:
            continue
        if provider not in LOCATION_PROVIDER_VALUES:
            raise ValueError("system.location.providers_allowed entries must be one of: gps, network")
        if provider not in providers:
            providers.append(provider)
    return providers


def runtime_permission_grants(profile):
    grants = []
    for app_name, app in (profile.get("apps") or {}).items():
        if not isinstance(app, dict):
            continue
        raw = app.get("runtime_permissions", [])
        if raw is None:
            continue
        if not isinstance(raw, list):
            raise ValueError("apps.{}.runtime_permissions must be a list".format(app_name))
        permissions = []
        for index, item in enumerate(raw):
            permission = str(item).strip()
            if not permission or not RUNTIME_PERMISSION_RE.match(permission):
                raise ValueError(
                    "apps.{}.runtime_permissions[{}] must be an android.permission.* name".format(
                        app_name,
                        index,
                    )
                )
            if permission not in permissions:
                permissions.append(permission)
        if permissions:
            grants.append(
                {
                    "app": str(app_name),
                    "package": str(app.get("package") or ""),
                    "permissions": permissions,
                }
            )
    return grants


def env_for(profile, repo_root, container):
    paths = profile["paths"]
    android_root = "/android" if container else str((repo_root / paths["android_root"]).resolve())
    ccache = "/ccache" if container else str((repo_root / paths["ccache"]).resolve())
    artifacts = "/artifacts" if container else str((repo_root / paths["dist"]).resolve())
    emulator_browser = profile["apps"].get("emulator_browser", profile["apps"]["browser"])
    ha_browser = profile["apps"].get("home_assistant_browser", {})
    extra_app_keys = extra_pinned_app_keys(profile)
    kiosk = profile.get("kiosk", {})
    kiosk_launcher = kiosk.get("launcher", {})
    theme = theme_for(profile)
    launch = launch_for(profile)
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
        "HA_BROWSER_MODULE": str(ha_browser.get("module", "")),
        "HA_BROWSER_PACKAGE": str(ha_browser.get("package", "")),
        "HA_BROWSER_APK": str(ha_browser.get("apk", "")),
        "HA_BROWSER_SHA256": str(ha_browser.get("sha256", "")),
        "EMULATOR_BROWSER_MODULE": str(emulator_browser["module"]),
        "EMULATOR_BROWSER_PACKAGE": str(emulator_browser["package"]),
        "EMULATOR_BROWSER_APK": str(emulator_browser["apk"]),
        "EMULATOR_BROWSER_SHA256": str(emulator_browser["sha256"]),
        "BROWSER_FALLBACK_PACKAGE": str(emulator_browser["package"]),
        "KIOSK_EXTRA_APPS_JSON": extra_pinned_apps_json(profile),
        "KIOSK_EXTRA_APP_MODULES": module_list(profile, extra_app_keys),
        "KIOSK_EXTRA_APP_PACKAGES": " ".join(str(profile["apps"][key]["package"]) for key in extra_app_keys),
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
        "KIOSK_HA_URL": str(launch["home_assistant_url"]),
        "KIOSK_BROWSER_URL": str(launch["browser_url"]),
        "KIOSK_BROWSER_LAUNCH_POLICY": str(launch["browser_launch_policy"]),
        "KIOSK_HA_BROWSER_PACKAGE": str(launch["home_assistant_browser_package"]),
        "KIOSK_PINNED_APPS_JSON": json.dumps(pinned_apps_for(profile), sort_keys=True),
        "BLOB_ARCHIVE": str(profile["blobs"]["archive"]),
        "BLOB_SHA256": str(profile["blobs"]["sha256"]),
        "ADB_PUBLIC_KEY": str((profile.get("debug") or {}).get("adb_public_key", "")),
        "ROOT_ACCESS": root_access_value(profile),
        "SYSTEM_UI_NIGHT_MODE": ui_night_mode_name(profile),
        "SYSTEM_UI_NIGHT_MODE_VALUE": ui_night_mode_value(profile),
        "SYSTEM_AUTO_TIME": bool_xml_value(system_auto_time(profile)),
        "SYSTEM_AUTO_TIME_VALUE": bool_setting_value(system_auto_time(profile)),
        "SYSTEM_AUTO_TIME_ZONE": bool_xml_value(system_auto_time_zone(profile)),
        "SYSTEM_AUTO_TIME_ZONE_VALUE": bool_setting_value(system_auto_time_zone(profile)),
        "SYSTEM_TIMEZONE": system_timezone(profile),
        "SYSTEM_NTP_SERVER": system_ntp_server(profile),
        "SYSTEM_LOCATION_PROVIDERS_ALLOWED": ",".join(location_providers_allowed(profile)),
        "APP_RUNTIME_PERMISSION_GRANTS_JSON": json.dumps(runtime_permission_grants(profile), sort_keys=True),
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
