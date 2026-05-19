#!/usr/bin/env python3
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import time
import zipfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

try:
    import yaml
except Exception as exc:  # noqa: BLE001
    print(f"PyYAML is required: {exc}", file=sys.stderr)
    sys.exit(2)


ROOT = Path(__file__).resolve().parents[1]
PLACEHOLDER_PREFIXES = ("REPLACE_WITH_", "<")
DEFAULT_PROFILE = "profiles/shield-k1-lineage15-dev.yaml"
COLOR_RE = re.compile(r"^#[0-9A-Fa-f]{6}([0-9A-Fa-f]{2})?$")
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
VIDEO_EXTENSIONS = {".mp4", ".m4v", ".3gp", ".webm"}
BACKGROUND_TYPES = {"color", "image", "video"}
BACKGROUND_FITS = {"cover", "contain", "height", "stretch"}
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
BROWSER_RUNTIME_THEMES = {"dark", "light", "system"}
BROWSER_WEBSITE_COLOR_SCHEME_VALUES = {
    "dark": "0",
    "light": "1",
    "system": "2",
    "browser": "3",
}
FENNEC_FAMILY_PACKAGES = {
    "org.mozilla.fennec_fdroid",
    "org.mozilla.firefox",
    "org.mozilla.fenix",
}
DEFAULT_BROWSER_RUNTIME_DEFAULTS = {
    "theme": "system",
    "website_color_scheme": "browser",
}
KEYBOARD_THEME_VALUES = {
    "default": "",
    "light": "3",
    "material_light": "3",
    "dark": "4",
    "material_dark": "4",
}
LATINIME_PACKAGE = "com.android.inputmethod.latin"
LATINIME_IME = "com.android.inputmethod.latin/.LatinIME"
LATINIME_THEME_PREF = "pref_keyboard_theme_20140509"
DEFAULT_KIOSK_THEME: dict[str, Any] = {
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


def repo_path(value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else ROOT / path


def display_path(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def root_relative(path: Path, description: str) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError as exc:
        raise ValueError(f"{description} must be inside the repository: {path}") from exc


def load_yaml_mapping(path: Path, description: str) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"{description} must be a YAML mapping: {path}")
    return data


def deep_merge(base: dict[str, Any], overlay: dict[str, Any]) -> dict[str, Any]:
    merged = copy.deepcopy(base)
    for key, value in overlay.items():
        if (
            key in merged
            and isinstance(merged[key], dict)
            and isinstance(value, dict)
        ):
            merged[key] = deep_merge(merged[key], value)
        else:
            merged[key] = copy.deepcopy(value)
    return merged


def active_profile_overlay(profile_overlay: str | Path | None = None) -> str | Path | None:
    if profile_overlay:
        return profile_overlay
    return os.environ.get("PROFILE_OVERLAY") or os.environ.get("PROFILE_OVERLAY_PATH")


def load_profile(
    path: str | Path,
    profile_overlay: str | Path | None = None,
) -> dict[str, Any]:
    profile_path = repo_path(path)
    data = load_yaml_mapping(profile_path, "profile")
    data["_profile_path"] = root_relative(profile_path, "profile")
    overlay = active_profile_overlay(profile_overlay)
    if overlay:
        overlay_path = repo_path(overlay)
        overlay_data = load_yaml_mapping(overlay_path, "profile overlay")
        data = deep_merge(data, overlay_data)
        data["_profile_path"] = root_relative(profile_path, "profile")
        data["_profile_overlay_path"] = root_relative(overlay_path, "profile overlay")
    return data


def save_profile(profile: dict[str, Any]) -> None:
    if profile.get("_profile_overlay_path"):
        raise ValueError(
            "refusing to write a merged profile overlay back to the base profile; "
            "run without PROFILE_OVERLAY to pin public inputs"
        )
    profile_path = repo_path(profile["_profile_path"])
    payload = canonical_profile(profile)
    profile_path.write_text(
        yaml.safe_dump(payload, sort_keys=False, default_flow_style=False),
        encoding="utf-8",
    )


def profile_name(profile: dict[str, Any]) -> str:
    return str(profile.get("profile") or "unnamed")


def is_placeholder(value: Any) -> bool:
    text = str(value or "")
    return not text or text.startswith(PLACEHOLDER_PREFIXES) or "REPLACE_WITH_" in text


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def apk_native_abis(path: Path) -> set[str]:
    abis: set[str] = set()
    with zipfile.ZipFile(path) as archive:
        for name in archive.namelist():
            parts = name.split("/")
            if len(parts) >= 3 and parts[0] == "lib" and parts[-1].endswith(".so"):
                abis.add(parts[1])
    return abis


def command_exists(name: str) -> bool:
    return shutil.which(name) is not None


class DeviceError(RuntimeError):
    pass


@dataclass
class CommandResult:
    argv: list[str]
    returncode: int
    stdout: str
    stderr: str


class CommandRunner:
    def run(
        self,
        argv: list[str],
        *,
        check: bool = True,
        timeout: int | None = None,
    ) -> CommandResult:
        proc = subprocess.run(
            argv,
            cwd=ROOT,
            check=False,
            text=True,
            capture_output=True,
            timeout=timeout,
        )
        result = CommandResult(
            argv=argv,
            returncode=proc.returncode,
            stdout=proc.stdout,
            stderr=proc.stderr,
        )
        if check and result.returncode != 0:
            raise DeviceError(
                f"command failed ({result.returncode}): {' '.join(shlex.quote(arg) for arg in argv)}\n"
                f"{result.stderr or result.stdout}"
            )
        return result

    def run_bytes(
        self,
        argv: list[str],
        *,
        check: bool = True,
        timeout: int | None = None,
    ) -> tuple[int, bytes, bytes]:
        proc = subprocess.run(
            argv,
            cwd=ROOT,
            check=False,
            capture_output=True,
            timeout=timeout,
        )
        if check and proc.returncode != 0:
            stderr = proc.stderr.decode("utf-8", errors="replace")
            stdout = proc.stdout.decode("utf-8", errors="replace")
            raise DeviceError(
                f"command failed ({proc.returncode}): {' '.join(shlex.quote(arg) for arg in argv)}\n"
                f"{stderr or stdout}"
            )
        return proc.returncode, proc.stdout, proc.stderr


def run(argv: list[str], *, cwd: Path = ROOT) -> None:
    print("+ " + " ".join(shlex.quote(arg) for arg in argv))
    subprocess.run(argv, cwd=cwd, check=True)


def git_value(args: list[str], default: str) -> str:
    try:
        return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()
    except Exception:  # noqa: BLE001
        return default


def canonical_profile(profile: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in profile.items() if not key.startswith("_")}


def profile_hash(profile: dict[str, Any]) -> str:
    payload = json.dumps(canonical_profile(profile), sort_keys=True).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()[:12]


def new_build_id(profile: dict[str, Any]) -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    git_sha = git_value(["rev-parse", "--short", "HEAD"], "nogit")
    return f"{profile_name(profile)}-{stamp}-{git_sha}-{profile_hash(profile)}"


def dist_root(profile: dict[str, Any]) -> Path:
    return repo_path(profile["paths"]["dist"])


def latest_build_dir(profile: dict[str, Any]) -> Path:
    root = dist_root(profile)
    prefix = profile_name(profile) + "-"
    candidates = sorted(
        [path for path in root.glob(prefix + "*") if (path / "INPUT-LOCK.json").exists()]
    )
    if not candidates:
        raise FileNotFoundError(
            f"no build output found for {profile_name(profile)} under {root}"
        )
    expected_hash = profile_hash(profile)
    matching: list[Path] = []
    for candidate in candidates:
        try:
            payload = json.loads((candidate / "INPUT-LOCK.json").read_text(encoding="utf-8"))
            locked_profile = payload.get("profile")
            if isinstance(locked_profile, dict) and profile_hash(locked_profile) == expected_hash:
                matching.append(candidate)
        except Exception:  # noqa: BLE001
            continue
    if matching:
        return matching[-1]
    if profile.get("_profile_overlay_path"):
        raise FileNotFoundError(
            f"no build output found for merged profile {profile_name(profile)} "
            f"with hash {expected_hash}; pass BUILD_DIR explicitly if reusing an older build"
        )
    return candidates[-1]


def require_mapping(root: dict[str, Any], key: str) -> dict[str, Any]:
    value = root.get(key)
    if not isinstance(value, dict):
        raise ValueError(f"missing mapping: {key}")
    return value


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def parse_adb_devices(output: str) -> list[dict[str, Any]]:
    devices: list[dict[str, Any]] = []
    for raw_line in output.splitlines():
        line = raw_line.strip()
        if (
            not line
            or line.startswith("List of devices")
            or line.startswith("* daemon")
        ):
            continue
        parts = line.split()
        if len(parts) < 2:
            continue
        details: dict[str, str] = {}
        for token in parts[2:]:
            if ":" in token:
                key, value = token.split(":", 1)
                details[key] = value
        devices.append(
            {
                "serial": parts[0],
                "state": parts[1],
                "details": details,
                "raw": raw_line,
            }
        )
    return devices


def parse_fastboot_devices(output: str) -> list[dict[str, Any]]:
    devices: list[dict[str, Any]] = []
    for raw_line in output.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        parts = line.split()
        if len(parts) < 2:
            continue
        devices.append({"serial": parts[0], "state": parts[1], "raw": raw_line})
    return devices


def parse_fastboot_getvar_all(output: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw_line in output.splitlines():
        line = raw_line.strip()
        if not line or line.lower().startswith("finished."):
            continue
        if line.startswith("(bootloader)"):
            line = line[len("(bootloader)") :].strip()
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        values[key.strip()] = value.strip()
    return values


def select_single_device(
    devices: list[dict[str, Any]],
    *,
    requested_serial: str | None,
    allowed_states: set[str],
    tool: str,
) -> dict[str, Any]:
    candidates = devices
    if requested_serial:
        candidates = [item for item in devices if item.get("serial") == requested_serial]
        if not candidates:
            raise DeviceError(f"{tool}: requested serial not found: {requested_serial}")
    if not candidates:
        raise DeviceError(f"{tool}: no connected device found")

    bad_states = [item for item in candidates if item.get("state") not in allowed_states]
    if bad_states:
        state = bad_states[0].get("state")
        serial = bad_states[0].get("serial")
        if state == "unauthorized":
            raise DeviceError(
                f"{tool}: device {serial} is unauthorized; unlock the tablet and accept the adb RSA prompt"
            )
        raise DeviceError(f"{tool}: device {serial} is in unsupported state: {state}")

    if len(candidates) > 1:
        serials = ", ".join(str(item.get("serial")) for item in candidates)
        raise DeviceError(f"{tool}: multiple devices found; pass SERIAL explicitly ({serials})")
    return candidates[0]


def profile_device_serial(profile: dict[str, Any], override: str | None) -> str | None:
    if override:
        return override
    device = profile.get("device")
    if isinstance(device, dict):
        serial = device.get("serial")
        if serial:
            return str(serial)
    return None


def expected_device_name(profile: dict[str, Any]) -> str:
    device = profile.get("device")
    if isinstance(device, dict) and device.get("expected_device"):
        return str(device["expected_device"])
    return str(profile["targets"]["tablet"].get("device") or "shieldtablet")


def deployment_config(profile: dict[str, Any]) -> dict[str, Any]:
    config = profile.get("deployment")
    return config if isinstance(config, dict) else {}


def debug_config(profile: dict[str, Any]) -> dict[str, Any]:
    config = profile.get("debug")
    return config if isinstance(config, dict) else {}


ROOT_ACCESS_VALUES = {
    "disabled": "",
    "none": "0",
    "off": "0",
    "apps": "1",
    "adb": "2",
    "all": "3",
}


def root_access_value(profile: dict[str, Any]) -> str:
    raw = debug_config(profile).get("root_access", "")
    if raw is None or raw == "":
        return ""
    value = str(raw).strip().lower()
    if value in ROOT_ACCESS_VALUES:
        return ROOT_ACCESS_VALUES[value]
    if value in {"0", "1", "2", "3"}:
        return value
    raise ValueError("debug.root_access must be one of: disabled, apps, adb, all")


def adb_root_runtime_enabled(profile: dict[str, Any]) -> bool:
    return root_access_value(profile) in {"2", "3"}


def kiosk_config(profile: dict[str, Any]) -> dict[str, Any]:
    config = profile.get("kiosk")
    return config if isinstance(config, dict) else {}


def kiosk_launcher(profile: dict[str, Any]) -> dict[str, str]:
    launcher = kiosk_config(profile).get("launcher")
    if not isinstance(launcher, dict):
        launcher = {}
    return {
        "module": str(launcher.get("module", "RosieKioskLauncher")),
        "package": str(launcher.get("package", "local.rosie.kiosk")),
    }


def kiosk_remove_modules(profile: dict[str, Any]) -> list[str]:
    return [str(module) for module in kiosk_config(profile).get("remove_modules", [])]


def kiosk_remove_packages(profile: dict[str, Any]) -> list[str]:
    return [str(package) for package in kiosk_config(profile).get("remove_packages", [])]


def system_config(profile: dict[str, Any]) -> dict[str, Any]:
    config = profile.get("system")
    return config if isinstance(config, dict) else {}


def ui_night_mode_value(profile: dict[str, Any]) -> str:
    raw = system_config(profile).get("ui_night_mode", "auto")
    value = str(raw).strip().lower()
    if value not in UI_NIGHT_MODE_VALUES:
        raise ValueError("system.ui_night_mode must be one of: auto, no, yes")
    return UI_NIGHT_MODE_VALUES[value]


def ui_night_mode_name(profile: dict[str, Any]) -> str:
    return UI_NIGHT_MODE_NAMES[ui_night_mode_value(profile)]


def keyboard_theme_value(profile: dict[str, Any]) -> str:
    raw = system_config(profile).get("keyboard_theme", "default")
    value = str(raw).strip().lower()
    if value not in KEYBOARD_THEME_VALUES:
        raise ValueError("system.keyboard_theme must be one of: default, light, dark")
    return KEYBOARD_THEME_VALUES[value]


def keyboard_theme_name(profile: dict[str, Any]) -> str:
    value = keyboard_theme_value(profile)
    if value == "3":
        return "light"
    if value == "4":
        return "dark"
    return "default"


def browser_runtime_defaults(profile: dict[str, Any], app_name: str = "browser") -> dict[str, str]:
    apps = profile.get("apps") or {}
    browser = apps.get("browser") or {}
    app = apps.get(app_name) or {}
    defaults = dict(DEFAULT_BROWSER_RUNTIME_DEFAULTS)
    if isinstance(browser, dict) and isinstance(browser.get("runtime_defaults"), dict):
        defaults.update(browser["runtime_defaults"])
    if app_name != "browser" and isinstance(app, dict) and isinstance(app.get("runtime_defaults"), dict):
        defaults.update(app["runtime_defaults"])
    theme = str(defaults.get("theme", "dark")).strip().lower()
    website_color_scheme = str(defaults.get("website_color_scheme", "dark")).strip().lower()
    if theme not in BROWSER_RUNTIME_THEMES:
        raise ValueError(f"apps.{app_name}.runtime_defaults.theme must be one of: dark, light, system")
    if website_color_scheme not in BROWSER_WEBSITE_COLOR_SCHEME_VALUES:
        raise ValueError(
            f"apps.{app_name}.runtime_defaults.website_color_scheme must be one of: "
            "dark, light, system, browser"
        )
    return {
        "theme": theme,
        "website_color_scheme": website_color_scheme,
        "website_color_scheme_value": BROWSER_WEBSITE_COLOR_SCHEME_VALUES[website_color_scheme],
    }


def browser_runtime_default_targets(profile: dict[str, Any]) -> list[dict[str, str]]:
    apps = profile.get("apps") or {}
    targets: list[dict[str, str]] = []
    seen_packages: set[str] = set()
    browser = apps.get("browser") or {}
    browser_defaults_configured = (
        isinstance(browser, dict) and isinstance(browser.get("runtime_defaults"), dict)
    )
    for app_name in ("browser", "home_assistant_browser"):
        app = apps.get(app_name)
        if not isinstance(app, dict):
            continue
        app_defaults_configured = isinstance(app.get("runtime_defaults"), dict)
        if not browser_defaults_configured and not app_defaults_configured:
            continue
        package = str(app.get("package") or "")
        if not package or package in seen_packages:
            continue
        seen_packages.add(package)
        defaults = browser_runtime_defaults(profile, app_name)
        targets.append(
            {
                "app": app_name,
                "package": package,
                **defaults,
            }
        )
    return targets


def is_fennec_family_package(package: str) -> bool:
    return package in FENNEC_FAMILY_PACKAGES


def kiosk_theme(profile: dict[str, Any]) -> dict[str, Any]:
    theme = kiosk_config(profile).get("theme")
    if theme is None:
        return copy.deepcopy(DEFAULT_KIOSK_THEME)
    if not isinstance(theme, dict):
        raise ValueError("kiosk.theme must be a mapping")
    return deep_merge(DEFAULT_KIOSK_THEME, theme)


def kiosk_launch(profile: dict[str, Any]) -> dict[str, str]:
    launch = kiosk_config(profile).get("launch")
    if launch is None:
        launch = {}
    if not isinstance(launch, dict):
        raise ValueError("kiosk.launch must be a mapping")
    apps = profile.get("apps") or {}
    ha_browser = apps.get("home_assistant_browser") or {}
    if not isinstance(ha_browser, dict):
        ha_browser = {}
    browser = apps.get("browser") or {}
    if not isinstance(browser, dict):
        browser = {}
    return {
        "home_assistant_url": str(launch.get("home_assistant_url") or ""),
        "browser_url": str(launch.get("browser_url") or ""),
        "home_assistant_browser_package": str(
            launch.get("home_assistant_browser_package")
            or ha_browser.get("package")
            or browser.get("package")
            or ""
        ),
    }


def bool_string(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    return "true" if str(value).lower() in {"1", "true", "yes", "on"} else "false"


def theme_background_path(theme: dict[str, Any]) -> str:
    background = theme["background"]
    path = str(background.get("path") or "")
    return root_relative(repo_path(path), "kiosk theme background path") if path else ""


def kiosk_theme_env(profile: dict[str, Any]) -> dict[str, str]:
    theme = kiosk_theme(profile)
    launch = kiosk_launch(profile)
    background = theme["background"]
    text = theme["text"]
    buttons = theme["buttons"]
    return {
        "KIOSK_TITLE": str(theme["title"]),
        "KIOSK_SUBTITLE": str(theme["subtitle"]),
        "KIOSK_FONT_FAMILY": str(theme["font_family"]),
        "KIOSK_BACKGROUND_TYPE": str(background["type"]),
        "KIOSK_BACKGROUND_PATH": theme_background_path(theme),
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
        "KIOSK_HA_BROWSER_PACKAGE": str(launch["home_assistant_browser_package"]),
    }


def device_validation_dir(build_dir: Path, serial: str) -> Path:
    return build_dir / "device-validation" / serial


def default_device_work_dir(serial: str) -> Path:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return ROOT / ".work" / "device" / f"{stamp}-{serial}"


def latest_manual_flash_dir(profile: dict[str, Any], build_dir: Path | None) -> Path:
    resolved = build_dir if build_dir else latest_build_dir(profile)
    manual = resolved / "manual-flash"
    if not manual.exists():
        raise FileNotFoundError(f"manual flash bundle not found: {manual}")
    return manual


def find_manual_flash_artifacts(manual: Path) -> tuple[Path, Path]:
    zips = sorted(manual.glob("lineage-*.zip"))
    if not zips:
        raise FileNotFoundError(f"missing lineage zip in {manual}")
    recovery = manual / "recovery.img"
    if not recovery.exists():
        raise FileNotFoundError(f"missing recovery.img in {manual}")
    return zips[-1], recovery


def find_manual_fastboot_images(manual: Path) -> tuple[Path, Path, Path]:
    boot = manual / "boot.img"
    system = manual / "system.img"
    recovery = manual / "recovery.img"
    missing = [path.name for path in (boot, system, recovery) if not path.exists()]
    if missing:
        raise FileNotFoundError(f"missing fastboot image(s) in {manual}: {', '.join(missing)}")
    return boot, system, recovery


def latest_target_files_image(out_dir: Path, name: str) -> Path:
    candidates = sorted(
        out_dir.glob(f"obj/PACKAGING/target_files_intermediates/lineage_*target_files-*/IMAGES/{name}"),
        key=lambda path: path.stat().st_mtime,
    )
    if not candidates:
        raise FileNotFoundError(f"missing {name} under target_files intermediates in {out_dir}")
    return candidates[-1]


def assert_emulator_validation_passed(build_dir: Path) -> None:
    validation = build_dir / "EMULATOR-VALIDATION.json"
    if not validation.exists():
        raise DeviceError(f"missing emulator validation result: {validation}")
    result = json.loads(validation.read_text(encoding="utf-8"))
    if result.get("status") != "pass":
        raise DeviceError(f"emulator validation did not pass: {result.get('status')}")


def require_destructive_gate(serial: str | None, allow: bool) -> str:
    if not serial:
        raise DeviceError("destructive deployment requires an explicit SERIAL or profile device.serial")
    if not allow:
        raise DeviceError("destructive deployment requires ALLOW_DESTRUCTIVE=1 or --allow-destructive")
    return serial


def adb_devices(runner: CommandRunner) -> list[dict[str, Any]]:
    return parse_adb_devices(runner.run(["adb", "devices", "-l"]).stdout)


def fastboot_devices(runner: CommandRunner) -> list[dict[str, Any]]:
    return parse_fastboot_devices(runner.run(["fastboot", "devices", "-l"]).stdout)


def adb_shell(
    runner: CommandRunner,
    serial: str,
    command: list[str],
    *,
    check: bool = True,
    timeout: int | None = None,
) -> CommandResult:
    return runner.run(["adb", "-s", serial, "shell", *command], check=check, timeout=timeout)


def adb_shell_script(
    runner: CommandRunner,
    serial: str,
    script: str,
    *,
    check: bool = True,
    timeout: int | None = None,
) -> CommandResult:
    return adb_shell(runner, serial, [f"sh -c {shlex.quote(script)}"], check=check, timeout=timeout)


def adb_getprop(runner: CommandRunner, serial: str, key: str) -> str:
    result = adb_shell(runner, serial, ["getprop", key], check=False)
    return result.stdout.strip().replace("\r", "")


def window_focus_references_package(text: str, package: str) -> bool:
    focus_markers = ("mCurrentFocus=", "mFocusedApp=", "mFocusedWindow=")
    for line in text.splitlines():
        if any(marker in line for marker in focus_markers) and package in line:
            return True
    return False


def send_reboot_command(
    runner: CommandRunner,
    argv: list[str],
    *,
    check: bool = True,
    timeout_seconds: int = 15,
) -> None:
    try:
        result = runner.run(argv, check=False, timeout=timeout_seconds)
    except subprocess.TimeoutExpired:
        return
    output = f"{result.stdout}\n{result.stderr}"
    if "'adb root' is required" in output or "adb root is required" in output:
        raise DeviceError(
            f"command did not switch modes: {' '.join(shlex.quote(arg) for arg in argv)}\n"
            f"{result.stderr or result.stdout}"
        )
    if check and result.returncode != 0:
        raise DeviceError(
            f"command failed ({result.returncode}): {' '.join(shlex.quote(arg) for arg in argv)}\n"
            f"{result.stderr or result.stdout}"
        )


def ensure_adb_root(runner: CommandRunner, *, serial: str) -> None:
    result = runner.run(["adb", "-s", serial, "root"], check=False, timeout=30)
    output = f"{result.stdout}\n{result.stderr}"
    if result.returncode != 0 or "cannot run as root" in output.lower():
        raise DeviceError(f"adb root failed for {serial}: {result.stderr or result.stdout}")
    wait_for_adb_state(
        runner,
        serial=serial,
        allowed_states={"device"},
        timeout_seconds=60,
    )
    uid = adb_shell(runner, serial, ["id", "-u"], check=False, timeout=15).stdout.strip()
    if uid != "0":
        root_access = adb_getprop(runner, serial, "persist.sys.root_access") or "<unset>"
        adb_root = adb_getprop(runner, serial, "lineage.service.adb.root") or "<unset>"
        raise DeviceError(
            f"adb root did not take effect for {serial}; id -u={uid or '<empty>'}, "
            f"persist.sys.root_access={root_access}, lineage.service.adb.root={adb_root}"
        )


def wait_for_adb_state(
    runner: CommandRunner,
    *,
    serial: str,
    allowed_states: set[str],
    timeout_seconds: int,
) -> dict[str, Any]:
    deadline = time.monotonic() + timeout_seconds
    last_devices: list[dict[str, Any]] = []
    while time.monotonic() < deadline:
        last_devices = adb_devices(runner)
        matches = [item for item in last_devices if item.get("serial") == serial]
        if matches and matches[0].get("state") in allowed_states:
            return matches[0]
        time.sleep(2)
    raise DeviceError(
        f"timed out waiting for adb state {sorted(allowed_states)} for {serial}; "
        f"last devices: {last_devices}"
    )


def wait_for_fastboot(
    runner: CommandRunner,
    *,
    serial: str,
    timeout_seconds: int,
) -> dict[str, Any]:
    deadline = time.monotonic() + timeout_seconds
    last_devices: list[dict[str, Any]] = []
    while time.monotonic() < deadline:
        last_devices = fastboot_devices(runner)
        matches = [item for item in last_devices if item.get("serial") == serial]
        if matches:
            return matches[0]
        time.sleep(2)
    raise DeviceError(f"timed out waiting for fastboot device {serial}; last devices: {last_devices}")


def wait_for_boot_completed(
    runner: CommandRunner,
    *,
    serial: str,
    timeout_seconds: int,
) -> None:
    wait_for_adb_state(
        runner,
        serial=serial,
        allowed_states={"device"},
        timeout_seconds=timeout_seconds,
    )
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        if adb_getprop(runner, serial, "sys.boot_completed") == "1":
            return
        time.sleep(5)
    raise DeviceError(f"timed out waiting for Android boot completion on {serial}")


def collect_basic_device_evidence(
    runner: CommandRunner,
    *,
    serial: str,
    out_dir: Path,
    profile: dict[str, Any],
) -> dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)
    props = {
        "ro.product.device": adb_getprop(runner, serial, "ro.product.device"),
        "ro.product.model": adb_getprop(runner, serial, "ro.product.model"),
        "ro.serialno": adb_getprop(runner, serial, "ro.serialno"),
        "ro.build.version.release": adb_getprop(runner, serial, "ro.build.version.release"),
        "ro.lineage.version": adb_getprop(runner, serial, "ro.lineage.version"),
        "sys.boot_completed": adb_getprop(runner, serial, "sys.boot_completed"),
    }
    (out_dir / "getprop-summary.json").write_text(
        json.dumps(props, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    packages = adb_shell(runner, serial, ["pm", "list", "packages"], check=False)
    (out_dir / "packages.txt").write_text(packages.stdout, encoding="utf-8")

    settings = {
        "device_provisioned": adb_shell(
            runner,
            serial,
            ["settings", "get", "global", "device_provisioned"],
            check=False,
        ).stdout.strip(),
        "user_setup_complete": adb_shell(
            runner,
            serial,
            ["settings", "get", "secure", "user_setup_complete"],
            check=False,
        ).stdout.strip(),
        "lockscreen_disabled": adb_shell(
            runner,
            serial,
            ["settings", "get", "secure", "lockscreen.disabled"],
            check=False,
        ).stdout.strip(),
        "screen_off_timeout": adb_shell(
            runner,
            serial,
            ["settings", "get", "system", "screen_off_timeout"],
            check=False,
        ).stdout.strip(),
        "ui_night_mode": adb_shell(
            runner,
            serial,
            ["settings", "get", "secure", "ui_night_mode"],
            check=False,
        ).stdout.strip(),
        "uimode_night": adb_shell(
            runner,
            serial,
            ["cmd", "uimode", "night"],
            check=False,
        ).stdout.strip(),
    }
    (out_dir / "settings-summary.json").write_text(
        json.dumps(settings, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    home_resolve = adb_shell(
        runner,
        serial,
        [
            "cmd",
            "package",
            "resolve-activity",
            "--brief",
            "-a",
            "android.intent.action.MAIN",
            "-c",
            "android.intent.category.HOME",
        ],
        check=False,
    )
    (out_dir / "home-resolve.txt").write_text(
        home_resolve.stdout + home_resolve.stderr,
        encoding="utf-8",
    )

    logcat = runner.run(["adb", "-s", serial, "logcat", "-d"], check=False, timeout=60)
    (out_dir / "logcat.txt").write_text(logcat.stdout + logcat.stderr, encoding="utf-8")

    code, screenshot, _ = runner.run_bytes(
        ["adb", "-s", serial, "exec-out", "screencap", "-p"],
        check=False,
        timeout=30,
    )
    if code == 0 and screenshot:
        (out_dir / "screenshot.png").write_bytes(screenshot)

    return {
        "serial": serial,
        "props": props,
        "settings": settings,
        "home_resolve": home_resolve.stdout + home_resolve.stderr,
        "expected_device": expected_device_name(profile),
    }


WIFI_BACKUP_DEVICE_PATH = "/data/local/tmp/rosie-wifi-backup.tar"
WIFI_BACKUP_EXCLUDE_DEVICE_PATH = "/data/local/tmp/rosie-wifi-backup.exclude"


def default_wifi_backup_path(build_dir: Path | None, serial: str) -> Path:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    if build_dir:
        return device_validation_dir(build_dir, serial) / f"wifi-backup-{stamp}.tar"
    return ROOT / ".work" / "device-wifi" / serial / f"wifi-backup-{stamp}.tar"


def latest_wifi_backup_path(build_dir: Path | None, serial: str) -> Path:
    candidates: list[Path] = []
    if build_dir:
        candidates.extend(device_validation_dir(build_dir, serial).glob("wifi-backup-*.tar"))
    candidates.extend((ROOT / ".work" / "device-wifi" / serial).glob("wifi-backup-*.tar"))
    if not candidates:
        raise FileNotFoundError("no Wi-Fi backup found; pass WIFI_BACKUP_PATH=<path>")
    return sorted(candidates, key=lambda path: path.stat().st_mtime)[-1]


def backup_wifi_config(
    runner: CommandRunner,
    *,
    serial: str,
    output_path: Path,
) -> Path:
    ensure_adb_root(runner, serial=serial)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    script = f"""
set -eu
exclude={shlex.quote(WIFI_BACKUP_EXCLUDE_DEVICE_PATH)}
cleanup() {{
  rm -f "$exclude"
  svc wifi enable || true
}}
trap cleanup EXIT
svc wifi disable || true
rm -f {shlex.quote(WIFI_BACKUP_DEVICE_PATH)}
printf 'data/misc/wifi/sockets\\ndata/misc/wifi/sockets/*\\n' > "$exclude"
paths=""
for p in /data/misc/wifi /data/misc_ce/0/wifi /data/misc_de/0/wifi; do
  if [ -e "$p" ]; then
    paths="$paths ${{p#/}}"
  fi
done
if [ -z "$paths" ]; then
  echo "no Wi-Fi config paths found" >&2
  exit 1
fi
cd /
tar -cpf {shlex.quote(WIFI_BACKUP_DEVICE_PATH)} -X "$exclude" $paths
chmod 0600 {shlex.quote(WIFI_BACKUP_DEVICE_PATH)}
"""
    result = adb_shell_script(runner, serial, script, check=False, timeout=60)
    if result.returncode != 0:
        raise DeviceError(f"Wi-Fi backup failed: {result.stderr or result.stdout}")
    pull = runner.run(
        ["adb", "-s", serial, "pull", WIFI_BACKUP_DEVICE_PATH, str(output_path)],
        check=False,
        timeout=60,
    )
    adb_shell(runner, serial, ["rm", "-f", WIFI_BACKUP_DEVICE_PATH], check=False, timeout=15)
    if pull.returncode != 0 or not output_path.exists():
        raise DeviceError(f"failed to pull Wi-Fi backup: {pull.stderr or pull.stdout}")
    return output_path


def restore_wifi_config(
    runner: CommandRunner,
    *,
    serial: str,
    input_path: Path,
    reboot: bool = True,
) -> None:
    if not input_path.exists():
        raise FileNotFoundError(f"Wi-Fi backup not found: {input_path}")
    ensure_adb_root(runner, serial=serial)
    push = runner.run(
        ["adb", "-s", serial, "push", str(input_path), WIFI_BACKUP_DEVICE_PATH],
        check=False,
        timeout=60,
    )
    if push.returncode != 0:
        raise DeviceError(f"failed to push Wi-Fi backup: {push.stderr or push.stdout}")
    script = f"""
set -eu
cleanup() {{
  rm -f {shlex.quote(WIFI_BACKUP_DEVICE_PATH)}
  svc wifi enable || true
}}
trap cleanup EXIT
svc wifi disable || true
cd /
tar -xpf {shlex.quote(WIFI_BACKUP_DEVICE_PATH)}
for p in /data/misc/wifi /data/misc_ce/0/wifi /data/misc_de/0/wifi; do
  if [ -e "$p" ]; then
    restorecon -RF "$p" 2>/dev/null || true
  fi
done
"""
    result = adb_shell_script(runner, serial, script, check=False, timeout=60)
    if result.returncode != 0:
        raise DeviceError(f"Wi-Fi restore failed: {result.stderr or result.stdout}")
    if reboot:
        send_reboot_command(runner, ["adb", "-s", serial, "reboot"], check=False)


def apply_runtime_system_defaults(
    runner: CommandRunner,
    *,
    serial: str,
    profile: dict[str, Any],
) -> None:
    mode = ui_night_mode_name(profile)
    result = adb_shell(
        runner,
        serial,
        ["cmd", "uimode", "night", mode],
        check=False,
        timeout=30,
    )
    if result.returncode != 0:
        raise DeviceError(f"failed to set Android UI night mode: {result.stderr or result.stdout}")


def fennec_theme_booleans(theme: str) -> dict[str, str]:
    return {
        "pref_key_light_theme": "true" if theme == "light" else "false",
        "pref_key_dark_theme": "true" if theme == "dark" else "false",
        "pref_key_follow_device_theme": "true" if theme == "system" else "false",
    }


def fennec_runtime_defaults_script(package: str, defaults: dict[str, str]) -> str:
    booleans = fennec_theme_booleans(defaults["theme"])
    content_override = defaults["website_color_scheme_value"]
    system_dark = "0" if defaults["theme"] == "light" else "1"
    return f"""
set -eu
pkg={shlex.quote(package)}
data="/data/data/$pkg"
if [ ! -d "$data" ]; then
  echo "missing package data directory: $data" >&2
  exit 1
fi
owner="$(stat -c '%u:%g' "$data")"
am force-stop "$pkg" >/dev/null 2>&1 || true
if [ ! -d "$data/files/mozilla" ] || ! find "$data/files/mozilla" -maxdepth 1 -type d -name '*.default*' 2>/dev/null | grep -q .; then
  monkey -p "$pkg" -c android.intent.category.LAUNCHER 1 >/dev/null 2>&1 || true
  sleep 6
  am force-stop "$pkg" >/dev/null 2>&1 || true
fi

prefs_dir="$data/shared_prefs"
prefs="$prefs_dir/fenix_preferences.xml"
mkdir -p "$prefs_dir"
if [ ! -f "$prefs" ]; then
  printf "%s\\n" "<?xml version='1.0' encoding='utf-8' standalone='yes' ?>" "<map>" "</map>" > "$prefs"
fi

upsert_boolean() {{
  file="$1"
  key="$2"
  value="$3"
  tmp="$file.tmp"
  if grep -q "name=\\"$key\\"" "$file"; then
    sed "s#<boolean name=\\"$key\\" value=\\"[^\\"]*\\" />#    <boolean name=\\"$key\\" value=\\"$value\\" />#" "$file" > "$tmp"
  else
    sed "/<\\/map>/i\\    <boolean name=\\"$key\\" value=\\"$value\\" />" "$file" > "$tmp"
  fi
  mv "$tmp" "$file"
}}

upsert_boolean "$prefs" "pref_key_light_theme" {shlex.quote(booleans["pref_key_light_theme"])}
upsert_boolean "$prefs" "pref_key_dark_theme" {shlex.quote(booleans["pref_key_dark_theme"])}
upsert_boolean "$prefs" "pref_key_follow_device_theme" {shlex.quote(booleans["pref_key_follow_device_theme"])}
chown "$owner" "$prefs"
chmod 0600 "$prefs"

mozilla="$data/files/mozilla"
mkdir -p "$mozilla"
profiles="$(find "$mozilla" -maxdepth 1 -type d -name '*.default*' 2>/dev/null || true)"
if [ -z "$profiles" ]; then
  profile="$mozilla/rosie.default"
  mkdir -p "$profile"
  if [ ! -f "$mozilla/profiles.ini" ]; then
    cat > "$mozilla/profiles.ini" <<'EOF_PROFILES'
[Profile0]
Name=default
IsRelative=1
Path=rosie.default
Default=1

[General]
StartWithLastProfile=1
Version=2
EOF_PROFILES
  fi
  profiles="$profile"
fi

for profile in $profiles; do
  userjs="$profile/user.js"
  tmp="$userjs.tmp"
  if [ -f "$userjs" ]; then
    grep -v -E 'layout\\.css\\.prefers-color-scheme\\.content-override|ui\\.systemUsesDarkTheme' "$userjs" > "$tmp" || true
  else
    : > "$tmp"
  fi
  cat >> "$tmp" <<EOF_USERJS
user_pref("layout.css.prefers-color-scheme.content-override", {content_override});
user_pref("ui.systemUsesDarkTheme", {system_dark});
EOF_USERJS
  mv "$tmp" "$userjs"
  chown "$owner" "$userjs"
  chmod 0600 "$userjs"
done

chown -R "$owner" "$prefs_dir" "$mozilla"
restorecon -RF "$prefs_dir" "$mozilla" >/dev/null 2>&1 || true
am force-stop "$pkg" >/dev/null 2>&1 || true
"""


def latinime_runtime_defaults_script(theme_id: str) -> str:
    return f"""
set -eu
pkg={shlex.quote(LATINIME_PACKAGE)}
ime_id={shlex.quote(LATINIME_IME)}
theme_id={shlex.quote(theme_id)}
data_dirs=""
for candidate in "/data/user_de/0/$pkg" "/data/data/$pkg"; do
  if [ -d "$candidate" ]; then
    data_dirs="$data_dirs $candidate"
  fi
done
if [ -z "$data_dirs" ]; then
  echo "missing package data directory for $pkg" >&2
  exit 1
fi
for data in $data_dirs; do
  owner="$(stat -c '%u:%g' "$data")"
  context="$(ls -Zd "$data" | awk '{{print $1}}')"
  prefs_dir="$data/shared_prefs"
  prefs="$prefs_dir/${{pkg}}_preferences.xml"
  mkdir -p "$prefs_dir"
  if [ ! -f "$prefs" ]; then
    printf "%s\\n" "<?xml version='1.0' encoding='utf-8' standalone='yes' ?>" "<map>" "</map>" > "$prefs"
  fi
  tmp="$prefs.tmp"
  if grep -q "name=\\"{LATINIME_THEME_PREF}\\"" "$prefs"; then
    sed "s#<string name=\\"{LATINIME_THEME_PREF}\\">[^<]*</string>#    <string name=\\"{LATINIME_THEME_PREF}\\">$theme_id</string>#" "$prefs" > "$tmp"
  else
    sed "/<\\/map>/i\\    <string name=\\"{LATINIME_THEME_PREF}\\">$theme_id</string>" "$prefs" > "$tmp"
  fi
  mv "$tmp" "$prefs"
  chown "$owner" "$prefs_dir" "$prefs"
  chcon "$context" "$prefs_dir" "$prefs" >/dev/null 2>&1 || true
  chmod 0600 "$prefs"
done
am force-stop "$pkg" >/dev/null 2>&1 || true
ime enable "$ime_id" >/dev/null 2>&1 || true
ime set "$ime_id" >/dev/null 2>&1 || true
"""


def apply_runtime_app_defaults(
    runner: CommandRunner,
    *,
    serial: str,
    profile: dict[str, Any],
) -> dict[str, Any]:
    if not adb_root_runtime_enabled(profile):
        return {
            "status": "skipped",
            "reason": "debug.root_access does not enable adb root",
            "targets": [],
        }
    ensure_adb_root(runner, serial=serial)
    results: list[dict[str, str]] = []
    for target in browser_runtime_default_targets(profile):
        package = target["package"]
        if not is_fennec_family_package(package):
            results.append(
                {
                    "app": target["app"],
                    "package": package,
                    "status": "skipped",
                    "reason": "unsupported browser package",
                }
            )
            continue
        result = adb_shell_script(
            runner,
            serial,
            fennec_runtime_defaults_script(package, target),
            check=False,
            timeout=60,
        )
        if result.returncode != 0:
            raise DeviceError(
                f"failed to apply browser defaults for {package}: {result.stderr or result.stdout}"
            )
        results.append(
            {
                "app": target["app"],
                "package": package,
                "status": "pass",
                "theme": target["theme"],
                "website_color_scheme": target["website_color_scheme"],
            }
        )
    keyboard_theme = keyboard_theme_value(profile)
    if keyboard_theme:
        result = adb_shell_script(
            runner,
            serial,
            latinime_runtime_defaults_script(keyboard_theme),
            check=False,
            timeout=30,
        )
        if result.returncode != 0:
            raise DeviceError(f"failed to apply keyboard defaults: {result.stderr or result.stdout}")
        results.append(
            {
                "app": "keyboard",
                "package": LATINIME_PACKAGE,
                "status": "pass",
                "theme": keyboard_theme_name(profile),
            }
        )
    return {
        "status": "pass",
        "targets": results,
    }


def collect_runtime_app_defaults_evidence(
    runner: CommandRunner,
    *,
    serial: str,
    profile: dict[str, Any],
    out_dir: Path,
) -> dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)
    if not adb_root_runtime_enabled(profile):
        evidence: dict[str, Any] = {
            "status": "skipped",
            "reason": "debug.root_access does not enable adb root",
            "targets": [],
        }
        write_json(out_dir / "app-defaults.json", evidence)
        return evidence
    ensure_adb_root(runner, serial=serial)
    targets: list[dict[str, Any]] = []
    for target in browser_runtime_default_targets(profile):
        package = target["package"]
        if not is_fennec_family_package(package):
            targets.append(
                {
                    "app": target["app"],
                    "package": package,
                    "status": "skipped",
                    "reason": "unsupported browser package",
                }
            )
            continue
        script = f"""
set -eu
pkg={shlex.quote(package)}
prefs="/data/data/$pkg/shared_prefs/fenix_preferences.xml"
if [ ! -f "$prefs" ]; then
  echo "prefs_missing=1"
else
  for key in pref_key_light_theme pref_key_dark_theme pref_key_follow_device_theme; do
    value="$(grep "name=\\"$key\\"" "$prefs" | sed 's/.*value="\\([^"]*\\)".*/\\1/' | head -1 || true)"
    echo "$key=$value"
  done
fi
found_userjs=0
for userjs in /data/data/"$pkg"/files/mozilla/*.default*/user.js /data/data/"$pkg"/files/mozilla/*.default/user.js; do
  [ -f "$userjs" ] || continue
  found_userjs=1
  echo "user_js=$userjs"
  grep -E 'layout\\.css\\.prefers-color-scheme\\.content-override|ui\\.systemUsesDarkTheme' "$userjs" || true
done
echo "user_js_found=$found_userjs"
"""
        result = adb_shell_script(runner, serial, script, check=False, timeout=30)
        text = result.stdout + result.stderr
        (out_dir / f"app-defaults-{target['app']}.txt").write_text(text, encoding="utf-8")
        prefs: dict[str, str] = {}
        user_prefs: dict[str, str] = {}
        for line in text.splitlines():
            if line.startswith("pref_key_") and "=" in line:
                key, value = line.split("=", 1)
                prefs[key] = value
            elif line.startswith("user_pref("):
                if '"layout.css.prefers-color-scheme.content-override"' in line:
                    user_prefs["layout.css.prefers-color-scheme.content-override"] = line.rsplit(",", 1)[-1].strip(" );")
                elif '"ui.systemUsesDarkTheme"' in line:
                    user_prefs["ui.systemUsesDarkTheme"] = line.rsplit(",", 1)[-1].strip(" );")
            elif "=" in line:
                key, value = line.split("=", 1)
                prefs[key] = value
        targets.append(
            {
                "app": target["app"],
                "package": package,
                "status": "pass" if result.returncode == 0 else "fail",
                "prefs": prefs,
                "user_prefs": user_prefs,
            }
        )
    keyboard_theme = keyboard_theme_value(profile)
    if keyboard_theme:
        script = f"""
set -eu
data=""
for candidate in "/data/user_de/0/{LATINIME_PACKAGE}" "/data/data/{LATINIME_PACKAGE}"; do
  if [ -d "$candidate" ]; then
    data="$candidate"
    break
  fi
done
prefs="$data/shared_prefs/{LATINIME_PACKAGE}_preferences.xml"
echo "prefs_path=$prefs"
if [ ! -f "$prefs" ]; then
  echo "prefs_missing=1"
else
  value="$(grep "name=\\"{LATINIME_THEME_PREF}\\"" "$prefs" | sed 's/.*>\\([^<]*\\)<.*/\\1/' | head -1 || true)"
  echo "{LATINIME_THEME_PREF}=$value"
fi
"""
        result = adb_shell_script(runner, serial, script, check=False, timeout=30)
        text = result.stdout + result.stderr
        (out_dir / "app-defaults-keyboard.txt").write_text(text, encoding="utf-8")
        prefs: dict[str, str] = {}
        for line in text.splitlines():
            if "=" in line:
                key, value = line.split("=", 1)
                prefs[key] = value
        targets.append(
            {
                "app": "keyboard",
                "package": LATINIME_PACKAGE,
                "status": "pass" if result.returncode == 0 else "fail",
                "prefs": prefs,
            }
        )
    evidence = {
        "status": "pass",
        "targets": targets,
    }
    write_json(out_dir / "app-defaults.json", evidence)
    return evidence


def validate_tablet_state(
    runner: CommandRunner,
    *,
    serial: str,
    profile: dict[str, Any],
    out_dir: Path,
) -> dict[str, Any]:
    evidence = collect_basic_device_evidence(
        runner,
        serial=serial,
        out_dir=out_dir,
        profile=profile,
    )
    app_defaults = collect_runtime_app_defaults_evidence(
        runner,
        serial=serial,
        profile=profile,
        out_dir=out_dir,
    )
    evidence["app_defaults"] = app_defaults
    expected = expected_device_name(profile)
    actual = evidence["props"].get("ro.product.device")
    failures: list[str] = []
    if actual and actual != expected:
        failures.append(f"expected ro.product.device={expected}, got {actual}")

    packages_text = (out_dir / "packages.txt").read_text(encoding="utf-8")
    for app_key in ("home_assistant", "browser"):
        package = profile["apps"][app_key]["package"]
        if f"package:{package}" not in packages_text:
            failures.append(f"missing package: {package}")
    if "home_assistant_browser" in profile["apps"]:
        package = str(profile["apps"]["home_assistant_browser"]["package"])
        if f"package:{package}" not in packages_text:
            failures.append(f"missing Home Assistant browser package: {package}")

    launcher_package = kiosk_launcher(profile)["package"]
    if f"package:{launcher_package}" not in packages_text:
        failures.append(f"missing kiosk launcher package: {launcher_package}")

    for package in profile["validation"].get("no_gms_packages", []):
        if f"package:{package}" in packages_text:
            failures.append(f"forbidden Google package installed: {package}")

    for package in kiosk_remove_packages(profile):
        if f"package:{package}" in packages_text:
            failures.append(f"removed package still installed: {package}")

    if evidence["settings"].get("device_provisioned") != "1":
        failures.append("device_provisioned is not set to 1")
    if evidence["settings"].get("user_setup_complete") != "1":
        failures.append("user_setup_complete is not set to 1")
    if evidence["settings"].get("lockscreen_disabled") != "1":
        failures.append("lockscreen.disabled is not set to 1")
    expected_night = ui_night_mode_name(profile)
    if evidence["settings"].get("uimode_night") != f"Night mode: {expected_night}":
        failures.append(
            "Android UI night mode is "
            f"{evidence['settings'].get('uimode_night')}, expected Night mode: {expected_night}"
        )
    if app_defaults.get("status") == "pass":
        app_default_targets = {
            str(item.get("package")): item for item in app_defaults.get("targets", []) if isinstance(item, dict)
        }
        for target in browser_runtime_default_targets(profile):
            package = target["package"]
            if not is_fennec_family_package(package):
                continue
            actual_defaults = app_default_targets.get(package)
            if not actual_defaults or actual_defaults.get("status") != "pass":
                failures.append(f"missing browser runtime-default evidence for {package}")
                continue
            expected_bools = fennec_theme_booleans(target["theme"])
            prefs = actual_defaults.get("prefs") or {}
            for key, expected_value in expected_bools.items():
                if prefs.get(key) != expected_value:
                    failures.append(f"{package} {key} is {prefs.get(key)}, expected {expected_value}")
            user_prefs = actual_defaults.get("user_prefs") or {}
            if user_prefs.get("layout.css.prefers-color-scheme.content-override") != target["website_color_scheme_value"]:
                failures.append(
                    f"{package} website color-scheme override is "
                    f"{user_prefs.get('layout.css.prefers-color-scheme.content-override')}, "
                    f"expected {target['website_color_scheme_value']}"
                )
        expected_keyboard_theme = keyboard_theme_value(profile)
        if expected_keyboard_theme:
            keyboard_defaults = next(
                (
                    item for item in app_defaults.get("targets", [])
                    if isinstance(item, dict) and item.get("app") == "keyboard"
                ),
                None,
            )
            if not keyboard_defaults or keyboard_defaults.get("status") != "pass":
                failures.append("missing keyboard runtime-default evidence")
            else:
                prefs = keyboard_defaults.get("prefs") or {}
                if prefs.get(LATINIME_THEME_PREF) != expected_keyboard_theme:
                    failures.append(
                        f"{LATINIME_PACKAGE} {LATINIME_THEME_PREF} is "
                        f"{prefs.get(LATINIME_THEME_PREF)}, expected {expected_keyboard_theme}"
                    )

    if launcher_package not in evidence.get("home_resolve", ""):
        failures.append(f"HOME intent does not resolve to kiosk launcher: {launcher_package}")

    for app_key in ("home_assistant", "browser"):
        package = str(profile["apps"][app_key]["package"])
        result = runner.run(
            ["adb", "-s", serial, "shell", "monkey", "-p", package, "-c", "android.intent.category.LAUNCHER", "1"],
            check=False,
            timeout=45,
        )
        (out_dir / f"launch-{app_key}.log").write_text(
            result.stdout + result.stderr,
            encoding="utf-8",
        )
        if result.returncode != 0:
            failures.append(f"failed to launch package: {package}")

    runner.run(
        ["adb", "-s", serial, "shell", "input", "keyevent", "KEYCODE_WAKEUP"],
        check=False,
        timeout=15,
    )
    runner.run(["adb", "-s", serial, "shell", "input", "keyevent", "KEYCODE_HOME"], check=False, timeout=15)
    time.sleep(2)
    focus = adb_shell(runner, serial, ["dumpsys", "window", "windows"], check=False, timeout=30)
    focus_text = focus.stdout + focus.stderr
    (out_dir / "home-focus.txt").write_text(focus_text, encoding="utf-8")
    if not window_focus_references_package(focus_text, launcher_package):
        failures.append(f"HOME key did not focus kiosk launcher: {launcher_package}")

    status = "pass" if not failures else "fail"
    payload = {
        "schema": "rosie-local-ha.device-validation/v1",
        "status": status,
        "serial": serial,
        "created_at": now_iso(),
        "failures": failures,
        "evidence_dir": str(out_dir),
    }
    write_json(out_dir / "DEVICE-VALIDATION.json", payload)
    return payload


def validate_profile_shape(profile: dict[str, Any]) -> list[str]:
    warnings: list[str] = []
    required_top = [
        "schema_version",
        "profile",
        "lineage",
        "targets",
        "apps",
        "blobs",
        "validation",
        "paths",
        "runner",
        "output",
    ]
    for key in required_top:
        if key not in profile:
            raise ValueError(f"missing top-level profile key: {key}")

    lineage = require_mapping(profile, "lineage")
    for key in ("branch", "repo_url", "sync_jobs"):
        if key not in lineage:
            raise ValueError(f"missing lineage.{key}")
    for project in lineage.get("extra_projects", []):
        if not isinstance(project, dict):
            raise ValueError("lineage.extra_projects entries must be mappings")
        for key in ("name", "path"):
            if key not in project:
                raise ValueError(f"missing lineage.extra_projects[].{key}")

    targets = require_mapping(profile, "targets")
    for target_name in ("tablet", "emulator"):
        target = require_mapping(targets, target_name)
        for key in ("lunch", "output_product", "product_makefile", "build_command"):
            if key not in target:
                raise ValueError(f"missing targets.{target_name}.{key}")

    apps = require_mapping(profile, "apps")
    for app_name in ("home_assistant", "browser"):
        app = require_mapping(apps, app_name)
        for key in ("module", "package", "apk", "sha256"):
            if key not in app:
                raise ValueError(f"missing apps.{app_name}.{key}")
        if is_placeholder(app["sha256"]):
            warnings.append(f"apps.{app_name}.sha256 is still a placeholder")
        validate_browser_runtime_defaults_shape(app_name, app)
    if "home_assistant_browser" in apps:
        app = require_mapping(apps, "home_assistant_browser")
        for key in ("module", "package", "apk", "sha256"):
            if key not in app:
                raise ValueError(f"missing apps.home_assistant_browser.{key}")
        if is_placeholder(app["sha256"]):
            warnings.append("apps.home_assistant_browser.sha256 is still a placeholder")
        validate_browser_runtime_defaults_shape("home_assistant_browser", app)
    for app_name, app in apps.items():
        if app_name in ("home_assistant", "browser", "home_assistant_browser"):
            continue
        if not isinstance(app, dict):
            raise ValueError(f"apps.{app_name} must be a mapping")
        for key in ("module", "package", "apk", "sha256"):
            if key not in app:
                raise ValueError(f"missing apps.{app_name}.{key}")
        if is_placeholder(app["sha256"]):
            warnings.append(f"apps.{app_name}.sha256 is still a placeholder")

    blobs = require_mapping(profile, "blobs")
    for key in ("archive", "sha256"):
        if key not in blobs:
            raise ValueError(f"missing blobs.{key}")
    if is_placeholder(blobs["sha256"]):
        warnings.append("blobs.sha256 is still a placeholder")

    paths = require_mapping(profile, "paths")
    for key in ("android_root", "ccache", "dist"):
        if key not in paths:
            raise ValueError(f"missing paths.{key}")

    runner = require_mapping(profile, "runner")
    if "image" not in runner:
        raise ValueError("missing runner.image")
    if "dockerfile" in runner and not isinstance(runner["dockerfile"], str):
        raise ValueError("runner.dockerfile must be a string when set")

    if "android" in profile:
        android = require_mapping(profile, "android")
        for key in ("api_level", "abi"):
            if key not in android:
                raise ValueError(f"missing android.{key}")

    if "device" in profile:
        device = require_mapping(profile, "device")
        if "expected_device" not in device:
            raise ValueError("missing device.expected_device")

    if "kiosk" in profile:
        kiosk = require_mapping(profile, "kiosk")
        launcher = kiosk.get("launcher")
        if not isinstance(launcher, dict):
            raise ValueError("kiosk.launcher must be a mapping")
        for key in ("module", "package"):
            if key not in launcher:
                raise ValueError(f"missing kiosk.launcher.{key}")
        for key in ("remove_modules", "remove_packages"):
            if key in kiosk and not isinstance(kiosk[key], list):
                raise ValueError(f"kiosk.{key} must be a list")
        warnings.extend(validate_kiosk_theme_shape(kiosk_theme(profile)))
        validate_kiosk_launch_shape(kiosk_launch(profile))

    if "system" in profile:
        require_mapping(profile, "system")
    ui_night_mode_value(profile)
    keyboard_theme_value(profile)

    if "deployment" in profile:
        deployment = require_mapping(profile, "deployment")
        for key in ("mode", "destructive_flags_required", "boot_timeout_seconds", "post_flash_timeout_seconds"):
            if key not in deployment:
                raise ValueError(f"missing deployment.{key}")
    if "debug" in profile:
        debug = require_mapping(profile, "debug")
        if "adb_public_key" in debug and not isinstance(debug["adb_public_key"], str):
            raise ValueError("debug.adb_public_key must be a string")
        root_access_value(profile)
    return warnings


def validate_color(value: Any, name: str) -> None:
    if not isinstance(value, str) or not COLOR_RE.match(value):
        raise ValueError(f"{name} must be #RRGGBB or #AARRGGBB")


def validate_positive_int(value: Any, name: str) -> None:
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise ValueError(f"{name} must be a positive integer")


def validate_non_negative_int(value: Any, name: str) -> None:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ValueError(f"{name} must be a non-negative integer")


def validate_kiosk_theme_shape(theme: dict[str, Any]) -> list[str]:
    warnings: list[str] = []
    for key in ("background", "text", "buttons"):
        if not isinstance(theme.get(key), dict):
            raise ValueError(f"kiosk.theme.{key} must be a mapping")
    for key in ("title", "subtitle", "font_family"):
        if not isinstance(theme.get(key), str):
            raise ValueError(f"kiosk.theme.{key} must be a string")

    background = theme["background"]
    background_type = str(background.get("type") or "")
    if background_type not in BACKGROUND_TYPES:
        raise ValueError(
            "kiosk.theme.background.type must be one of: "
            + ", ".join(sorted(BACKGROUND_TYPES))
        )
    background_fit = str(background.get("fit") or "")
    if background_fit not in BACKGROUND_FITS:
        raise ValueError(
            "kiosk.theme.background.fit must be one of: "
            + ", ".join(sorted(BACKGROUND_FITS))
        )
    if background_fit == "height" and background_type != "video":
        raise ValueError("kiosk.theme.background.fit height is only supported for video backgrounds")
    if not isinstance(background.get("loop"), bool):
        raise ValueError("kiosk.theme.background.loop must be a boolean")
    validate_color(background.get("fallback_color"), "kiosk.theme.background.fallback_color")
    validate_color(background.get("scrim_color"), "kiosk.theme.background.scrim_color")
    if background_type in {"image", "video"}:
        path = background.get("path")
        if not isinstance(path, str) or not path:
            raise ValueError("kiosk.theme.background.path is required for image/video backgrounds")
        if Path(path).is_absolute():
            raise ValueError("kiosk.theme.background.path must be repository-relative")
        root_relative(repo_path(path), "kiosk theme background path")
        expected_exts = IMAGE_EXTENSIONS if background_type == "image" else VIDEO_EXTENSIONS
        if repo_path(path).suffix.lower() not in expected_exts:
            raise ValueError(
                f"kiosk.theme.background.path has unsupported {background_type} extension: {path}"
            )
        if is_placeholder(background.get("sha256")):
            warnings.append("kiosk.theme.background.sha256 is still a placeholder")

    text = theme["text"]
    validate_color(text.get("color"), "kiosk.theme.text.color")
    validate_color(text.get("subtitle_color"), "kiosk.theme.text.subtitle_color")
    validate_positive_int(text.get("title_size_sp"), "kiosk.theme.text.title_size_sp")
    validate_positive_int(text.get("subtitle_size_sp"), "kiosk.theme.text.subtitle_size_sp")
    validate_color(text.get("shadow_color"), "kiosk.theme.text.shadow_color")
    for key in ("shadow_radius_dp", "shadow_dx_dp", "shadow_dy_dp"):
        validate_non_negative_int(text.get(key), f"kiosk.theme.text.{key}")

    buttons = theme["buttons"]
    for key in ("home_assistant_label", "browser_label"):
        if not isinstance(buttons.get(key), str):
            raise ValueError(f"kiosk.theme.buttons.{key} must be a string")
    for key in (
        "background_color",
        "text_color",
        "accent_color",
        "border_color",
        "focus_border_color",
    ):
        validate_color(buttons.get(key), f"kiosk.theme.buttons.{key}")
    for key in ("text_size_sp", "radius_dp", "min_height_dp", "width_dp"):
        validate_positive_int(buttons.get(key), f"kiosk.theme.buttons.{key}")
    return warnings


def validate_optional_http_url(value: Any, name: str) -> None:
    if not isinstance(value, str):
        raise ValueError(f"{name} must be a string")
    if not value:
        return
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError(f"{name} must be an absolute http or https URL")


def validate_kiosk_launch_shape(launch: dict[str, str]) -> None:
    validate_optional_http_url(launch["home_assistant_url"], "kiosk.launch.home_assistant_url")
    validate_optional_http_url(launch["browser_url"], "kiosk.launch.browser_url")


def validate_browser_runtime_defaults_shape(app_name: str, app: dict[str, Any]) -> None:
    defaults = app.get("runtime_defaults")
    if defaults is None:
        return
    if not isinstance(defaults, dict):
        raise ValueError(f"apps.{app_name}.runtime_defaults must be a mapping")
    theme = str(defaults.get("theme", "dark")).strip().lower()
    if theme not in BROWSER_RUNTIME_THEMES:
        raise ValueError(f"apps.{app_name}.runtime_defaults.theme must be one of: dark, light, system")
    website = str(defaults.get("website_color_scheme", "dark")).strip().lower()
    if website not in BROWSER_WEBSITE_COLOR_SCHEME_VALUES:
        raise ValueError(
            f"apps.{app_name}.runtime_defaults.website_color_scheme must be one of: "
            "dark, light, system, browser"
        )


def validate_apk_payload(profile: dict[str, Any], app_name: str, apk: Path) -> list[str]:
    errors: list[str] = []
    app = profile["apps"][app_name]
    expected_abi = str(app.get("abi") or profile.get("android", {}).get("abi") or "")
    try:
        with zipfile.ZipFile(apk) as archive:
            names = set(archive.namelist())
            if "AndroidManifest.xml" not in names:
                errors.append(f"APK is missing AndroidManifest.xml: {display_path(apk)}")
        native_abis = apk_native_abis(apk)
    except zipfile.BadZipFile:
        return [f"invalid APK/ZIP: {display_path(apk)}"]

    if native_abis and expected_abi and expected_abi not in native_abis:
        errors.append(
            f"APK native ABI mismatch for {display_path(apk)}: "
            f"expected {expected_abi}, found {', '.join(sorted(native_abis))}"
        )
    return errors


def validate_theme_inputs(profile: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    theme = kiosk_theme(profile)
    background = theme["background"]
    if background["type"] not in {"image", "video"}:
        return errors

    path = repo_path(background["path"])
    if not path.exists():
        errors.append(f"missing kiosk background asset: {display_path(path)}")
        return errors
    expected = str(background.get("sha256") or "")
    if is_placeholder(expected):
        errors.append("kiosk.theme.background.sha256 is still a placeholder")
        return errors
    actual = sha256_file(path)
    if actual.lower() != expected.lower():
        errors.append(
            f"SHA-256 mismatch for {display_path(path)}: expected {expected}, got {actual}"
        )
    return errors


def validate_concrete_inputs(profile: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    warnings = validate_profile_shape(profile)
    for warning in warnings:
        errors.append(warning)

    for app_name in profile["apps"]:
        app = profile["apps"][app_name]
        apk = repo_path(app["apk"])
        if not apk.exists():
            errors.append(f"missing APK: {apk.relative_to(ROOT)}")
            continue
        expected = str(app["sha256"])
        if is_placeholder(expected):
            continue
        actual = sha256_file(apk)
        if actual.lower() != expected.lower():
            errors.append(
                f"SHA-256 mismatch for {apk.relative_to(ROOT)}: expected {expected}, got {actual}"
            )
        errors.extend(validate_apk_payload(profile, app_name, apk))

    blob = repo_path(profile["blobs"]["archive"])
    if not blob.exists():
        errors.append(f"missing vendor blob archive: {blob.relative_to(ROOT)}")
    else:
        expected = str(profile["blobs"]["sha256"])
        if not is_placeholder(expected):
            actual = sha256_file(blob)
            if actual.lower() != expected.lower():
                errors.append(
                    f"SHA-256 mismatch for {blob.relative_to(ROOT)}: expected {expected}, got {actual}"
                )

    errors.extend(validate_theme_inputs(profile))
    return errors


def write_lock(profile: dict[str, Any], build_dir: Path) -> None:
    build_dir.mkdir(parents=True, exist_ok=True)
    lock = {
        "schema": "rosie-local-ha.input-lock/v1",
        "build_id": build_dir.name,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "git": {
            "commit": git_value(["rev-parse", "HEAD"], "uncommitted"),
            "branch": git_value(["branch", "--show-current"], "unknown"),
            "dirty": bool(git_value(["status", "--short"], "")),
        },
        "profile": canonical_profile(profile),
        "input_hashes": {},
    }
    for app_name in profile["apps"]:
        app = profile["apps"][app_name]
        apk = repo_path(app["apk"])
        lock["input_hashes"][app_name] = sha256_file(apk) if apk.exists() else None
    blob = repo_path(profile["blobs"]["archive"])
    lock["input_hashes"]["vendor_blobs"] = sha256_file(blob) if blob.exists() else None
    theme = kiosk_theme(profile)
    background = theme["background"]
    if background["type"] in {"image", "video"}:
        asset = repo_path(background["path"])
        lock["input_hashes"]["kiosk_background"] = sha256_file(asset) if asset.exists() else None
    if profile.get("_profile_overlay_path"):
        lock["profile_overlay"] = profile["_profile_overlay_path"]
    (build_dir / "INPUT-LOCK.json").write_text(
        json.dumps(lock, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def write_manifest(profile: dict[str, Any], build_dir: Path, status: str) -> None:
    manifest = {
        "schema": "rosie-local-ha.build-manifest/v1",
        "build_id": build_dir.name,
        "profile": profile_name(profile),
        "status": status,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "targets": profile["targets"],
        "runner_image": profile["runner"]["image"],
    }
    if profile.get("_profile_overlay_path"):
        manifest["profile_overlay"] = profile["_profile_overlay_path"]
    (build_dir / "BUILD-MANIFEST.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def shell_env(profile: dict[str, Any], *, container: bool) -> dict[str, str]:
    paths = profile["paths"]
    android_root = "/android" if container else str(repo_path(paths["android_root"]))
    ccache = "/ccache" if container else str(repo_path(paths["ccache"]))
    artifacts = "/artifacts" if container else str(dist_root(profile))
    emulator_browser = profile["apps"].get("emulator_browser", profile["apps"]["browser"])
    ha_browser = profile["apps"].get("home_assistant_browser", {})
    launcher = kiosk_launcher(profile)
    env = {
        "PROFILE_NAME": profile_name(profile),
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
        "KIOSK_LAUNCHER_MODULE": launcher["module"],
        "KIOSK_LAUNCHER_PACKAGE": launcher["package"],
        "KIOSK_REMOVE_MODULES": " ".join(kiosk_remove_modules(profile)),
        "KIOSK_REMOVE_PACKAGES": " ".join(kiosk_remove_packages(profile)),
        "BLOB_ARCHIVE": str(profile["blobs"]["archive"]),
        "BLOB_SHA256": str(profile["blobs"]["sha256"]),
        "ADB_PUBLIC_KEY": str(debug_config(profile).get("adb_public_key", "")),
        "ROOT_ACCESS": root_access_value(profile),
        "SYSTEM_UI_NIGHT_MODE": ui_night_mode_name(profile),
        "SYSTEM_UI_NIGHT_MODE_VALUE": ui_night_mode_value(profile),
        "ANDROID_API_LEVEL": str(profile.get("android", {}).get("api_level", "")),
        "ANDROID_ABI": str(profile.get("android", {}).get("abi", "")),
        "ANDROID_ROOT": android_root,
        "CCACHE_DIR": ccache,
        "ARTIFACT_DIR": artifacts,
        "BOOT_TIMEOUT_SECONDS": str(profile["validation"].get("boot_timeout_seconds", 600)),
        "USE_SDK_EMULATOR": "1" if profile["validation"].get("use_sdk_emulator", False) else "0",
        "NO_GMS_PACKAGES": " ".join(profile["validation"].get("no_gms_packages", [])),
    }
    env.update(kiosk_theme_env(profile))
    if container:
        env["REPO_ROOT"] = "/work/repo"
    else:
        env["REPO_ROOT"] = str(ROOT)
    return env


def render_env(profile: dict[str, Any], output: Path | None, *, container: bool) -> None:
    lines = [f"export {key}={shlex.quote(value)}" for key, value in shell_env(profile, container=container).items()]
    body = "\n".join(lines) + "\n"
    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(body, encoding="utf-8")
    else:
        print(body, end="")


def docker_runner_args(
    profile: dict[str, Any],
    artifact_dir: Path,
    command: str,
    *,
    use_host_user: bool = True,
    extra_docker_args: list[str] | None = None,
) -> list[str]:
    repo_path(profile["paths"]["android_root"]).mkdir(parents=True, exist_ok=True)
    repo_path(profile["paths"]["ccache"]).mkdir(parents=True, exist_ok=True)
    artifact_dir.mkdir(parents=True, exist_ok=True)
    args = [
        "docker",
        "run",
        "--rm",
        "-t",
    ]
    if extra_docker_args:
        args.extend(extra_docker_args)
    if use_host_user:
        args.extend(["--user", f"{os.getuid()}:{os.getgid()}"])
    args.extend([
        "-v",
        f"{ROOT}:/work/repo:ro",
        "-v",
        f"{repo_path(profile['paths']['android_root'])}:/android",
        "-v",
        f"{repo_path(profile['paths']['ccache'])}:/ccache",
        "-v",
        f"{artifact_dir}:/artifacts",
        "-e",
        f"PROFILE_PATH=/work/repo/{profile['_profile_path']}",
        "-e",
        "HOME=/artifacts/home",
    ])
    if profile.get("_profile_overlay_path"):
        args.extend(["-e", f"PROFILE_OVERLAY_PATH=/work/repo/{profile['_profile_overlay_path']}"])
    args.extend([str(profile["runner"]["image"]), command])
    return args


def workerbee_job_manifest(profile: dict[str, Any], build_dir: Path) -> str:
    image = str(profile["runner"]["image"])
    repo = str(ROOT)
    android = str(repo_path(profile["paths"]["android_root"]))
    artifacts = str(build_dir)
    overlay_env = ""
    if profile.get("_profile_overlay_path"):
        overlay_env = (
            "            - name: PROFILE_OVERLAY_PATH\n"
            f"              value: /work/repo/{profile['_profile_overlay_path']}\n"
        )
    return f"""apiVersion: batch/v1
kind: Job
metadata:
  name: emulator-validation
  labels:
    app.kubernetes.io/name: rosie-local-ha-emulator-validation
spec:
  backoffLimit: 0
  template:
    spec:
      restartPolicy: Never
      containers:
        - name: validator
          image: {image}
          imagePullPolicy: Never
          command: ["/work/repo/scripts/runner/validate-emulator.sh"]
          env:
            - name: PROFILE_PATH
              value: /work/repo/{profile["_profile_path"]}
{overlay_env.rstrip()}
          securityContext:
            privileged: true
          resources:
            requests:
              cpu: "4"
              memory: 8Gi
            limits:
              cpu: "12"
              memory: 24Gi
          volumeMounts:
            - name: repo
              mountPath: /work/repo
              readOnly: true
            - name: android
              mountPath: /android
            - name: artifacts
              mountPath: /artifacts
            - name: kvm
              mountPath: /dev/kvm
      volumes:
        - name: repo
          hostPath:
            path: {repo}
            type: Directory
        - name: android
          hostPath:
            path: {android}
            type: DirectoryOrCreate
        - name: artifacts
          hostPath:
            path: {artifacts}
            type: DirectoryOrCreate
        - name: kvm
          hostPath:
            path: /dev/kvm
            type: CharDevice
"""


def write_workerbee_manifest(profile: dict[str, Any], build_dir: Path) -> Path:
    stage = build_dir / "workerbee"
    stage.mkdir(parents=True, exist_ok=True)
    manifest = stage / "emulator-validation-job.k8s.yaml"
    manifest.write_text(workerbee_job_manifest(profile, build_dir), encoding="utf-8")
    (stage / "README.md").write_text(
        "Deploy this local-only Job with WorkerBee after `make build-images` completes.\n"
        "It mounts the Android source checkout, build artifacts, and `/dev/kvm`.\n",
        encoding="utf-8",
    )
    return manifest


def cmd_help(_: argparse.Namespace) -> int:
    print(
        """rosie-local-ha build commands

make profile-lint        Validate profile structure.
make pin-inputs          Update profile SHA-256 pins for present APK/blob inputs.
make validate-inputs     Validate APK/blob hashes and APK ABI compatibility.
make preflight           Validate host, KVM, APK inputs, and vendor blob inputs.
make build-runner        Build the Android runner image with local Docker.
make sync-sources        Sync the configured LineageOS source tree.
make extract-blobs       Extract Shield K1 blobs from an adb-connected tablet.
make build-images        Build emulator companion and Shield K1 images.
make validate-emulator   Run emulator validation and stage the WorkerBee Job.
make publish-flash-bundle
                         Publish manual-flash output after validation passes.
make device-preflight    Verify host adb/fastboot and the plugged-in tablet.
make device-snapshot     Collect non-destructive device evidence.
make device-apply-system-defaults
                         Apply runtime defaults such as Android dark mode.
make device-apply-app-defaults
                         Apply root-backed app defaults such as browser dark mode.
make deploy-tablet       Gated USB deployment to the tablet.
make validate-tablet     Collect post-flash tablet evidence.
make collect-device-logs Collect logs and package/build evidence.
make full-pipeline       Build images and validate the emulator companion image.

Set PROFILE=profiles/<name>.yaml to use a non-default profile.
Set PROFILE_OVERLAY=profiles/local/site.yaml to apply ignored local kiosk customizations.
For WorkerBee validation, build the same runner tag with WorkerBee image_build
before deploying the generated Job.
"""
    )
    return 0


def cmd_profile_lint(args: argparse.Namespace) -> int:
    profile = load_profile(args.profile)
    warnings = validate_profile_shape(profile)
    print(f"Profile OK: {profile_name(profile)}")
    for warning in warnings:
        print(f"warning: {warning}")
    return 0


def cmd_preflight(args: argparse.Namespace) -> int:
    profile = load_profile(args.profile)
    errors = validate_concrete_inputs(profile)
    warnings: list[str] = []

    if not Path("/dev/kvm").exists():
        errors.append("/dev/kvm is missing; emulator validation needs KVM")
    elif not os.access("/dev/kvm", os.R_OK | os.W_OK):
        warnings.append("/dev/kvm exists but is not readable/writable by this user")

    for command in ("docker", "python3", "make"):
        if not command_exists(command):
            errors.append(f"missing required command: {command}")

    if not command_exists("workerbee"):
        warnings.append("workerbee CLI not found; agents can still deploy via WorkerBee MCP")

    for warning in warnings:
        print(f"warning: {warning}")

    if errors:
        print("Preflight failed:")
        for error in errors:
            print(f"  - {error}")
        return 1
    print(f"Preflight OK: {profile_name(profile)}")
    return 0


def cmd_render_env(args: argparse.Namespace) -> int:
    profile = load_profile(args.profile)
    validate_profile_shape(profile)
    output = Path(args.output) if args.output else None
    render_env(profile, output, container=args.container)
    return 0


def update_profile_hash_pins(profile: dict[str, Any]) -> tuple[list[str], list[str]]:
    updated: list[str] = []
    missing: list[str] = []
    for app_name in profile["apps"]:
        app = profile["apps"][app_name]
        apk = repo_path(app["apk"])
        if apk.exists():
            app["sha256"] = sha256_file(apk)
            updated.append(f"apps.{app_name}.sha256")
        else:
            missing.append(display_path(apk))

    blob = repo_path(profile["blobs"]["archive"])
    if blob.exists():
        profile["blobs"]["sha256"] = sha256_file(blob)
        updated.append("blobs.sha256")
    else:
        missing.append(display_path(blob))

    theme = kiosk_theme(profile)
    background = theme["background"]
    if background["type"] in {"image", "video"}:
        asset = repo_path(background["path"])
        if asset.exists():
            background["sha256"] = sha256_file(asset)
            profile.setdefault("kiosk", {}).setdefault("theme", {}).setdefault(
                "background",
                {},
            )["sha256"] = background["sha256"]
            updated.append("kiosk.theme.background.sha256")
        else:
            missing.append(display_path(asset))
    return updated, missing


def cmd_pin_inputs(args: argparse.Namespace) -> int:
    profile = load_profile(args.profile)
    if profile.get("_profile_overlay_path"):
        print(
            "pin-inputs refuses PROFILE_OVERLAY to avoid writing private values into the public base profile",
            file=sys.stderr,
        )
        return 1
    validate_profile_shape(profile)
    updated, missing = update_profile_hash_pins(profile)
    save_profile(profile)
    for item in updated:
        print(f"pinned {item}")
    for item in missing:
        print(f"warning: input not present, left unchanged: {item}")
    return 0


def cmd_validate_inputs(args: argparse.Namespace) -> int:
    profile = load_profile(args.profile)
    errors = validate_concrete_inputs(profile)
    if errors:
        print("Input validation failed:")
        for error in errors:
            print(f"  - {error}")
        return 1
    print(f"Inputs OK: {profile_name(profile)}")
    return 0


def cmd_build_runner(args: argparse.Namespace) -> int:
    profile = load_profile(args.profile)
    validate_profile_shape(profile)
    if not command_exists("docker"):
        print("docker is required to build the runner image", file=sys.stderr)
        return 1
    dockerfile = str(profile["runner"].get("dockerfile") or "container/Dockerfile")
    run(
        [
            "docker",
            "build",
            "-t",
            str(profile["runner"]["image"]),
            "-f",
            dockerfile,
            ".",
        ]
    )
    return 0


def cmd_sync_sources(args: argparse.Namespace) -> int:
    profile = load_profile(args.profile)
    validate_profile_shape(profile)
    if not command_exists("docker"):
        print("docker is required to sync sources in the runner image", file=sys.stderr)
        return 1
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    artifact_dir = ROOT / ".work" / "source-sync" / f"{profile_name(profile)}-{stamp}"
    run(docker_runner_args(profile, artifact_dir, "/work/repo/scripts/runner/sync-sources.sh"))
    print(f"Source sync logs: {display_path(artifact_dir)}")
    return 0


def cmd_extract_blobs(args: argparse.Namespace) -> int:
    profile = load_profile(args.profile)
    validate_profile_shape(profile)
    missing = [command for command in ("adb", "tar", "zstd") if not command_exists(command)]
    if missing:
        print(f"missing required commands: {', '.join(missing)}", file=sys.stderr)
        return 1

    runner = CommandRunner()
    try:
        selected = select_single_device(
            adb_devices(runner),
            requested_serial=profile_device_serial(profile, args.serial),
            allowed_states={"device"},
            tool="adb",
        )
        serial = str(selected["serial"])
        actual_device = adb_getprop(runner, serial, "ro.product.device")
        expected = expected_device_name(profile)
        if actual_device and actual_device != expected:
            raise DeviceError(f"expected ro.product.device={expected}, got {actual_device}")
    except DeviceError as exc:
        print(f"blob extraction preflight failed: {exc}", file=sys.stderr)
        return 1

    android_root = repo_path(profile["paths"]["android_root"])
    device_dir = android_root / "device" / "nvidia" / "shieldtablet"
    extract_script = device_dir / "extract-files.sh"
    if not extract_script.exists():
        print(
            f"missing Lineage extractor: {display_path(extract_script)}; run make sync-sources first",
            file=sys.stderr,
        )
        return 1

    env = os.environ.copy()
    env["ANDROID_SERIAL"] = serial
    print(f"+ ANDROID_SERIAL={serial} bash {extract_script.name}")
    extract = subprocess.run(
        ["bash", str(extract_script)],
        cwd=device_dir,
        check=False,
        text=True,
        env=env,
    )
    if extract.returncode != 0:
        return extract.returncode

    vendor_dir = android_root / "vendor" / "nvidia"
    if not vendor_dir.exists():
        print(f"vendor extraction did not create {display_path(vendor_dir)}", file=sys.stderr)
        return 1

    archive = repo_path(profile["blobs"]["archive"])
    archive.parent.mkdir(parents=True, exist_ok=True)
    run(["tar", "-I", "zstd", "-cf", str(archive), "-C", str(android_root), "vendor/nvidia"])
    digest = sha256_file(archive)
    if not args.no_pin:
        profile["blobs"]["sha256"] = digest
        save_profile(profile)
        print("pinned blobs.sha256")
    print(f"Vendor blob archive: {display_path(archive)}")
    print(f"SHA-256: {digest}")
    return 0


def cmd_build_images(args: argparse.Namespace) -> int:
    profile = load_profile(args.profile)
    errors = validate_concrete_inputs(profile)
    if errors:
        for error in errors:
            print(f"error: {error}", file=sys.stderr)
        return 1

    build_dir = dist_root(profile) / new_build_id(profile)
    write_lock(profile, build_dir)
    write_manifest(profile, build_dir, "started")

    run(
        docker_runner_args(
            profile,
            build_dir,
            "/work/repo/scripts/runner/build-images.sh",
        )
    )
    write_manifest(profile, build_dir, "built")
    print(f"Build output: {build_dir.relative_to(ROOT)}")
    return 0


def cmd_validate_emulator(args: argparse.Namespace) -> int:
    profile = load_profile(args.profile)
    validate_profile_shape(profile)
    build_dir = repo_path(args.build_dir) if args.build_dir else latest_build_dir(profile)
    manifest = write_workerbee_manifest(profile, build_dir)
    print(f"WorkerBee validation manifest: {display_path(manifest)}")
    docker_args: list[str] = []
    kvm = Path("/dev/kvm")
    if kvm.exists():
        docker_args.extend(["--device", "/dev/kvm", "--group-add", str(kvm.stat().st_gid)])
    run(
        docker_runner_args(
            profile,
            build_dir,
            "/work/repo/scripts/runner/validate-emulator.sh",
            extra_docker_args=docker_args,
        )
    )
    print(f"Emulator validation result: {display_path(build_dir / 'EMULATOR-VALIDATION.json')}")
    return 0


def cmd_publish_flash_bundle(args: argparse.Namespace) -> int:
    profile = load_profile(args.profile)
    build_dir = repo_path(args.build_dir) if args.build_dir else latest_build_dir(profile)
    validation = build_dir / "EMULATOR-VALIDATION.json"
    if not validation.exists():
        print(f"missing emulator validation result: {validation}", file=sys.stderr)
        return 1
    result = json.loads(validation.read_text(encoding="utf-8"))
    if result.get("status") != "pass":
        print(f"emulator validation did not pass: {result.get('status')}", file=sys.stderr)
        return 1

    product = profile["targets"]["tablet"]["output_product"]
    out_dir = repo_path(profile["paths"]["android_root"]) / "out" / "target" / "product" / product
    zips = sorted(out_dir.glob("lineage-*.zip"))
    if not zips:
        print(f"missing Shield K1 flashable ZIP under {out_dir}", file=sys.stderr)
        return 1

    manual = build_dir / "manual-flash"
    manual.mkdir(parents=True, exist_ok=True)
    outputs = [
        zips[-1],
        out_dir / "boot.img",
        out_dir / "recovery.img",
        latest_target_files_image(out_dir, "system.img"),
    ]
    for item in outputs:
        if not item.exists():
            print(f"missing flash output: {item}", file=sys.stderr)
            return 1
        target = manual / item.name
        shutil.copy2(item, target)

    shutil.copy2(build_dir / "INPUT-LOCK.json", manual / "INPUT-LOCK.json")
    shutil.copy2(build_dir / "BUILD-MANIFEST.json", manual / "BUILD-MANIFEST.json")
    shutil.copy2(validation, manual / "EMULATOR-VALIDATION.json")
    with (manual / "SHA256SUMS").open("w", encoding="utf-8") as handle:
        for item in sorted(manual.iterdir()):
            if item.is_file() and item.name != "SHA256SUMS":
                handle.write(f"{sha256_file(item)}  {item.name}\n")
    print(f"Manual flash bundle: {manual.relative_to(ROOT)}")
    return 0


def missing_platform_tools() -> list[str]:
    return [command for command in ("adb", "fastboot") if not command_exists(command)]


def cmd_device_preflight(args: argparse.Namespace) -> int:
    profile = load_profile(args.profile)
    validate_profile_shape(profile)
    missing = missing_platform_tools()
    if missing:
        print(f"missing Android Platform Tools commands: {', '.join(missing)}", file=sys.stderr)
        return 1

    runner = CommandRunner()
    requested_serial = profile_device_serial(profile, args.serial)
    payload: dict[str, Any] = {
        "schema": "rosie-local-ha.device-preflight/v1",
        "status": "fail",
        "created_at": now_iso(),
        "requested_serial": requested_serial,
    }
    try:
        selected = select_single_device(
            adb_devices(runner),
            requested_serial=requested_serial,
            allowed_states={"device"},
            tool="adb",
        )
        serial = str(selected["serial"])
        out_dir = (
            device_validation_dir(repo_path(args.build_dir), serial)
            if args.build_dir
            else default_device_work_dir(serial)
        )
        payload["serial"] = serial
        payload["evidence_dir"] = str(out_dir)
        evidence = collect_basic_device_evidence(
            runner,
            serial=serial,
            out_dir=out_dir,
            profile=profile,
        )
        payload["props"] = evidence["props"]

        actual_device = evidence["props"].get("ro.product.device")
        expected = expected_device_name(profile)
        if actual_device and actual_device != expected:
            raise DeviceError(f"expected ro.product.device={expected}, got {actual_device}")

        send_reboot_command(runner, ["adb", "-s", serial, "reboot", "bootloader"])
        wait_for_fastboot(runner, serial=serial, timeout_seconds=120)
        getvar = runner.run(["fastboot", "-s", serial, "getvar", "all"], check=False)
        (out_dir / "fastboot-getvar-all.txt").write_text(
            getvar.stdout + getvar.stderr,
            encoding="utf-8",
        )
        fastboot_vars = parse_fastboot_getvar_all(getvar.stdout + getvar.stderr)
        payload["fastboot"] = fastboot_vars

        unlocked = fastboot_vars.get("unlocked")
        device_state = fastboot_vars.get("device-state")
        secure = fastboot_vars.get("secure")
        if unlocked == "no" or device_state == "locked":
            payload["status"] = "bootloader_locked"
            payload["next_action"] = "Unlock the bootloader manually with fastboot oem unlock; this wipes user data."
            write_json(out_dir / "DEVICE-PREFLIGHT.json", payload)
            send_reboot_command(runner, ["fastboot", "-s", serial, "reboot"], check=False)
            print(payload["next_action"], file=sys.stderr)
            return 1
        if unlocked not in {"yes", None}:
            raise DeviceError(f"unrecognized fastboot unlocked state: {unlocked}")
        if unlocked is None and device_state != "unlocked" and secure != "no":
            raise DeviceError("bootloader unlock state could not be confirmed from fastboot getvar all")

        payload["status"] = "pass"
        send_reboot_command(runner, ["fastboot", "-s", serial, "reboot"], check=False)
        wait_for_adb_state(
            runner,
            serial=serial,
            allowed_states={"device"},
            timeout_seconds=300,
        )
        write_json(out_dir / "DEVICE-PREFLIGHT.json", payload)
        print(f"Device preflight OK: {serial}")
        print(f"Evidence: {out_dir}")
        return 0
    except DeviceError as exc:
        if "serial" in payload:
            out_dir = Path(str(payload.get("evidence_dir")))
            payload["failure"] = str(exc)
            write_json(out_dir / "DEVICE-PREFLIGHT.json", payload)
        print(f"device preflight failed: {exc}", file=sys.stderr)
        return 1


def cmd_device_snapshot(args: argparse.Namespace) -> int:
    profile = load_profile(args.profile)
    validate_profile_shape(profile)
    missing = missing_platform_tools()
    if missing:
        print(f"missing Android Platform Tools commands: {', '.join(missing)}", file=sys.stderr)
        return 1

    runner = CommandRunner()
    try:
        selected = select_single_device(
            adb_devices(runner),
            requested_serial=profile_device_serial(profile, args.serial),
            allowed_states={"device"},
            tool="adb",
        )
        serial = str(selected["serial"])
        out_dir = (
            device_validation_dir(repo_path(args.build_dir), serial)
            if args.build_dir
            else default_device_work_dir(serial)
        )
        evidence = collect_basic_device_evidence(
            runner,
            serial=serial,
            out_dir=out_dir,
            profile=profile,
        )
        payload = {
            "schema": "rosie-local-ha.device-snapshot/v1",
            "status": "pass",
            "created_at": now_iso(),
            "serial": serial,
            "evidence": evidence,
        }
        write_json(out_dir / "DEVICE-SNAPSHOT.json", payload)
        print(f"Device snapshot: {out_dir}")
        return 0
    except DeviceError as exc:
        print(f"device snapshot failed: {exc}", file=sys.stderr)
        return 1


def cmd_device_backup_wifi(args: argparse.Namespace) -> int:
    profile = load_profile(args.profile)
    validate_profile_shape(profile)
    missing = missing_platform_tools()
    if missing:
        print(f"missing Android Platform Tools commands: {', '.join(missing)}", file=sys.stderr)
        return 1
    build_dir = repo_path(args.build_dir) if args.build_dir else None
    runner = CommandRunner()
    try:
        selected = select_single_device(
            adb_devices(runner),
            requested_serial=profile_device_serial(profile, args.serial),
            allowed_states={"device"},
            tool="adb",
        )
        serial = str(selected["serial"])
        output = repo_path(args.output) if args.output else default_wifi_backup_path(build_dir, serial)
        backup_wifi_config(runner, serial=serial, output_path=output)
        print(f"Wi-Fi backup: {output}")
        return 0
    except (DeviceError, FileNotFoundError) as exc:
        print(f"Wi-Fi backup failed: {exc}", file=sys.stderr)
        return 1


def cmd_device_restore_wifi(args: argparse.Namespace) -> int:
    profile = load_profile(args.profile)
    validate_profile_shape(profile)
    missing = missing_platform_tools()
    if missing:
        print(f"missing Android Platform Tools commands: {', '.join(missing)}", file=sys.stderr)
        return 1
    build_dir = repo_path(args.build_dir) if args.build_dir else None
    runner = CommandRunner()
    try:
        selected = select_single_device(
            adb_devices(runner),
            requested_serial=profile_device_serial(profile, args.serial),
            allowed_states={"device"},
            tool="adb",
        )
        serial = str(selected["serial"])
        input_path = repo_path(args.input) if args.input else latest_wifi_backup_path(build_dir, serial)
        restore_wifi_config(runner, serial=serial, input_path=input_path, reboot=not args.no_reboot)
        print(f"Wi-Fi restored from: {input_path}")
        return 0
    except (DeviceError, FileNotFoundError) as exc:
        print(f"Wi-Fi restore failed: {exc}", file=sys.stderr)
        return 1


def cmd_device_apply_system_defaults(args: argparse.Namespace) -> int:
    profile = load_profile(args.profile)
    validate_profile_shape(profile)
    missing = missing_platform_tools()
    if missing:
        print(f"missing Android Platform Tools commands: {', '.join(missing)}", file=sys.stderr)
        return 1
    runner = CommandRunner()
    try:
        selected = select_single_device(
            adb_devices(runner),
            requested_serial=profile_device_serial(profile, args.serial),
            allowed_states={"device"},
            tool="adb",
        )
        serial = str(selected["serial"])
        apply_runtime_system_defaults(runner, serial=serial, profile=profile)
        print(f"Applied system defaults to {serial}: ui_night_mode={ui_night_mode_name(profile)}")
        return 0
    except DeviceError as exc:
        print(f"apply system defaults failed: {exc}", file=sys.stderr)
        return 1


def cmd_device_apply_app_defaults(args: argparse.Namespace) -> int:
    profile = load_profile(args.profile)
    validate_profile_shape(profile)
    missing = missing_platform_tools()
    if missing:
        print(f"missing Android Platform Tools commands: {', '.join(missing)}", file=sys.stderr)
        return 1
    runner = CommandRunner()
    try:
        selected = select_single_device(
            adb_devices(runner),
            requested_serial=profile_device_serial(profile, args.serial),
            allowed_states={"device"},
            tool="adb",
        )
        serial = str(selected["serial"])
        result = apply_runtime_app_defaults(runner, serial=serial, profile=profile)
        if result["status"] == "skipped":
            print(f"Skipped app defaults for {serial}: {result['reason']}")
        else:
            print(f"Applied app defaults to {serial}: {len(result['targets'])} target(s)")
        return 0
    except DeviceError as exc:
        print(f"apply app defaults failed: {exc}", file=sys.stderr)
        return 1


def deployment_mode(profile: dict[str, Any], override: str | None) -> str:
    if override:
        return override
    configured = str(deployment_config(profile).get("mode") or "recovery_sideload")
    return "first-install" if configured == "recovery_sideload" else configured


def print_dry_run(commands: list[list[str]]) -> None:
    print("Dry run command sequence:")
    for command in commands:
        print("  " + " ".join(shlex.quote(part) for part in command))


def deployment_command_sequence(
    *,
    mode: str,
    serial: str,
    recovery: Path,
    lineage_zip: Path,
    boot_img: Path | None = None,
    system_img: Path | None = None,
) -> list[list[str]]:
    if mode == "first-install":
        return [
            ["adb", "-s", serial, "reboot", "bootloader"],
            ["fastboot", "-s", serial, "erase", "userdata"],
            ["fastboot", "-s", serial, "erase", "cache"],
            ["fastboot", "-s", serial, "flash", "recovery", str(recovery)],
            ["fastboot", "-s", serial, "reboot", "recovery"],
            ["adb", "-s", serial, "sideload", str(lineage_zip)],
            ["adb", "-s", serial, "reboot"],
        ]
    if mode == "fastboot-image-install":
        if boot_img is None or system_img is None:
            raise ValueError("fastboot-image-install requires boot.img and system.img")
        return [
            ["fastboot", "-s", serial, "erase", "userdata"],
            ["fastboot", "-s", serial, "erase", "cache"],
            ["fastboot", "-s", serial, "flash", "boot", str(boot_img)],
            ["fastboot", "-s", serial, "flash", "recovery", str(recovery)],
            ["fastboot", "-s", serial, "flash", "system", str(system_img)],
            ["fastboot", "-s", serial, "reboot"],
        ]
    if mode == "fastboot-first-install":
        return [
            ["fastboot", "-s", serial, "erase", "userdata"],
            ["fastboot", "-s", serial, "erase", "cache"],
            ["fastboot", "-s", serial, "flash", "recovery", str(recovery)],
            ["fastboot", "-s", serial, "reboot", "recovery"],
            ["adb", "-s", serial, "sideload", str(lineage_zip)],
            ["adb", "-s", serial, "reboot"],
        ]
    if mode == "update":
        return [
            ["adb", "-s", serial, "reboot", "sideload"],
            ["adb", "-s", serial, "sideload", str(lineage_zip)],
            ["adb", "-s", serial, "reboot"],
        ]
    if mode == "resume-sideload":
        return [
            ["adb", "-s", serial, "sideload", str(lineage_zip)],
            ["adb", "-s", serial, "reboot"],
        ]
    raise ValueError(f"unknown install mode: {mode}")


def sideload_zip(
    runner: CommandRunner,
    *,
    serial: str,
    zip_path: Path,
    out_dir: Path,
    timeout_seconds: int,
) -> None:
    state = wait_for_adb_state(
        runner,
        serial=serial,
        allowed_states={"sideload", "recovery"},
        timeout_seconds=timeout_seconds,
    )
    if state.get("state") == "recovery":
        raise DeviceError(
            "device is in recovery but not sideload mode; select Apply update > Apply from ADB, "
            "then rerun deploy-tablet with --install-mode resume-sideload"
        )
    result = runner.run(["adb", "-s", serial, "sideload", str(zip_path)], check=False, timeout=1800)
    (out_dir / "adb-sideload.log").write_text(result.stdout + result.stderr, encoding="utf-8")
    if result.returncode != 0:
        raise DeviceError(f"adb sideload failed with exit code {result.returncode}")


def cmd_deploy_tablet(args: argparse.Namespace) -> int:
    profile = load_profile(args.profile)
    validate_profile_shape(profile)
    build_dir = repo_path(args.build_dir) if args.build_dir else latest_build_dir(profile)
    manual = latest_manual_flash_dir(profile, build_dir)
    lineage_zip, recovery = find_manual_flash_artifacts(manual)
    assert_emulator_validation_passed(build_dir)

    allow = args.allow_destructive or os.environ.get("ALLOW_DESTRUCTIVE") == "1"
    configured_serial = profile_device_serial(profile, args.serial)
    serial = configured_serial or ("<serial>" if args.dry_run else None)
    mode = deployment_mode(profile, args.install_mode)
    destructive_mode = mode in {"first-install", "fastboot-first-install", "fastboot-image-install"}
    boot_img = system_img = None
    if mode == "fastboot-image-install":
        boot_img, system_img, recovery = find_manual_fastboot_images(manual)
    try:
        commands = deployment_command_sequence(
            mode=mode,
            serial=serial or "<serial>",
            recovery=recovery,
            lineage_zip=lineage_zip,
            boot_img=boot_img,
            system_img=system_img,
        )
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    if args.dry_run:
        print_dry_run(commands)
        return 0

    try:
        serial = require_destructive_gate(configured_serial, allow)
        missing = missing_platform_tools()
        if missing:
            raise DeviceError(f"missing Android Platform Tools commands: {', '.join(missing)}")

        runner = CommandRunner()
        out_dir = device_validation_dir(build_dir, serial)
        out_dir.mkdir(parents=True, exist_ok=True)
        wifi_backup_path: Path | None = None
        if args.wifi_backup and destructive_mode:
            wifi_backup_path = repo_path(args.wifi_backup_path) if args.wifi_backup_path else default_wifi_backup_path(build_dir, serial)
            select_single_device(
                adb_devices(runner),
                requested_serial=serial,
                allowed_states={"device"},
                tool="adb",
            )
            backup_wifi_config(runner, serial=serial, output_path=wifi_backup_path)
        elif args.wifi_backup:
            print(f"Wi-Fi backup skipped for non-destructive install mode: {mode}")
        payload = {
            "schema": "rosie-local-ha.device-deployment/v1",
            "status": "started",
            "created_at": now_iso(),
            "serial": serial,
            "mode": mode,
            "lineage_zip": str(lineage_zip),
            "recovery": str(recovery),
            "wifi_backup": str(wifi_backup_path) if wifi_backup_path else None,
        }
        write_json(out_dir / "DEVICE-DEPLOYMENT.json", payload)

        timeouts = deployment_config(profile)
        boot_timeout = int(timeouts.get("boot_timeout_seconds", 600))
        post_flash_timeout = int(timeouts.get("post_flash_timeout_seconds", 900))
        post_install_adb_reboot = True

        if mode == "first-install":
            select_single_device(
                adb_devices(runner),
                requested_serial=serial,
                allowed_states={"device"},
                tool="adb",
            )
            send_reboot_command(runner, ["adb", "-s", serial, "reboot", "bootloader"])
            wait_for_fastboot(runner, serial=serial, timeout_seconds=120)
            runner.run(["fastboot", "-s", serial, "erase", "userdata"])
            runner.run(["fastboot", "-s", serial, "erase", "cache"])
            runner.run(["fastboot", "-s", serial, "flash", "recovery", str(recovery)])
            send_reboot_command(runner, ["fastboot", "-s", serial, "reboot", "recovery"], check=False)
            sideload_zip(
                runner,
                serial=serial,
                zip_path=lineage_zip,
                out_dir=out_dir,
                timeout_seconds=boot_timeout,
            )
        elif mode == "fastboot-first-install":
            select_single_device(
                fastboot_devices(runner),
                requested_serial=serial,
                allowed_states={"fastboot"},
                tool="fastboot",
            )
            runner.run(["fastboot", "-s", serial, "erase", "userdata"])
            runner.run(["fastboot", "-s", serial, "erase", "cache"])
            runner.run(["fastboot", "-s", serial, "flash", "recovery", str(recovery)])
            send_reboot_command(runner, ["fastboot", "-s", serial, "reboot", "recovery"], check=False)
            sideload_zip(
                runner,
                serial=serial,
                zip_path=lineage_zip,
                out_dir=out_dir,
                timeout_seconds=boot_timeout,
            )
        elif mode == "fastboot-image-install":
            if boot_img is None or system_img is None:
                raise DeviceError("fastboot-image-install requires boot.img and system.img")
            select_single_device(
                fastboot_devices(runner),
                requested_serial=serial,
                allowed_states={"fastboot"},
                tool="fastboot",
            )
            runner.run(["fastboot", "-s", serial, "erase", "userdata"])
            runner.run(["fastboot", "-s", serial, "erase", "cache"])
            runner.run(["fastboot", "-s", serial, "flash", "boot", str(boot_img)])
            runner.run(["fastboot", "-s", serial, "flash", "recovery", str(recovery)])
            runner.run(["fastboot", "-s", serial, "flash", "system", str(system_img)])
            send_reboot_command(runner, ["fastboot", "-s", serial, "reboot"], check=False)
            post_install_adb_reboot = False
        elif mode == "update":
            select_single_device(
                adb_devices(runner),
                requested_serial=serial,
                allowed_states={"device"},
                tool="adb",
            )
            ensure_adb_root(runner, serial=serial)
            send_reboot_command(runner, ["adb", "-s", serial, "reboot", "sideload"])
            sideload_zip(
                runner,
                serial=serial,
                zip_path=lineage_zip,
                out_dir=out_dir,
                timeout_seconds=boot_timeout,
            )
        else:
            sideload_zip(
                runner,
                serial=serial,
                zip_path=lineage_zip,
                out_dir=out_dir,
                timeout_seconds=30,
            )

        if post_install_adb_reboot:
            send_reboot_command(runner, ["adb", "-s", serial, "reboot"], check=False)
        wait_for_boot_completed(runner, serial=serial, timeout_seconds=post_flash_timeout)
        apply_runtime_system_defaults(runner, serial=serial, profile=profile)
        apply_runtime_app_defaults(runner, serial=serial, profile=profile)
        if wifi_backup_path:
            restore_wifi_config(runner, serial=serial, input_path=wifi_backup_path, reboot=True)
            wait_for_boot_completed(runner, serial=serial, timeout_seconds=post_flash_timeout)
            apply_runtime_system_defaults(runner, serial=serial, profile=profile)
            apply_runtime_app_defaults(runner, serial=serial, profile=profile)
        payload["status"] = "pass"
        payload["finished_at"] = now_iso()
        write_json(out_dir / "DEVICE-DEPLOYMENT.json", payload)
        print(f"Tablet deployment completed: {serial}")
        return 0
    except DeviceError as exc:
        if configured_serial:
            out_dir = device_validation_dir(build_dir, configured_serial)
            payload = {
                "schema": "rosie-local-ha.device-deployment/v1",
                "status": "fail",
                "created_at": now_iso(),
                "serial": configured_serial,
                "mode": mode,
                "failure": str(exc),
            }
            write_json(out_dir / "DEVICE-DEPLOYMENT.json", payload)
        print(f"tablet deployment failed: {exc}", file=sys.stderr)
        return 1


def cmd_validate_tablet(args: argparse.Namespace) -> int:
    profile = load_profile(args.profile)
    validate_profile_shape(profile)
    missing = missing_platform_tools()
    if missing:
        print(f"missing Android Platform Tools commands: {', '.join(missing)}", file=sys.stderr)
        return 1
    build_dir = repo_path(args.build_dir) if args.build_dir else latest_build_dir(profile)
    runner = CommandRunner()
    try:
        selected = select_single_device(
            adb_devices(runner),
            requested_serial=profile_device_serial(profile, args.serial),
            allowed_states={"device"},
            tool="adb",
        )
        serial = str(selected["serial"])
        timeout = int(deployment_config(profile).get("post_flash_timeout_seconds", 900))
        wait_for_boot_completed(runner, serial=serial, timeout_seconds=timeout)
        result = validate_tablet_state(
            runner,
            serial=serial,
            profile=profile,
            out_dir=device_validation_dir(build_dir, serial),
        )
        if result["status"] != "pass":
            print(f"tablet validation failed: {result['failures']}", file=sys.stderr)
            return 1
        print(f"Tablet validation OK: {serial}")
        return 0
    except DeviceError as exc:
        print(f"tablet validation failed: {exc}", file=sys.stderr)
        return 1


def cmd_collect_device_logs(args: argparse.Namespace) -> int:
    profile = load_profile(args.profile)
    validate_profile_shape(profile)
    missing = missing_platform_tools()
    if missing:
        print(f"missing Android Platform Tools commands: {', '.join(missing)}", file=sys.stderr)
        return 1
    build_dir = repo_path(args.build_dir) if args.build_dir else latest_build_dir(profile)
    runner = CommandRunner()
    try:
        selected = select_single_device(
            adb_devices(runner),
            requested_serial=profile_device_serial(profile, args.serial),
            allowed_states={"device"},
            tool="adb",
        )
        serial = str(selected["serial"])
        out_dir = device_validation_dir(build_dir, serial)
        collect_basic_device_evidence(
            runner,
            serial=serial,
            out_dir=out_dir,
            profile=profile,
        )
        print(f"Device logs collected: {out_dir}")
        return 0
    except DeviceError as exc:
        print(f"collect device logs failed: {exc}", file=sys.stderr)
        return 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="kioskctl")
    sub = parser.add_subparsers(dest="command", required=True)

    help_cmd = sub.add_parser("help")
    help_cmd.set_defaults(func=cmd_help)

    for name, func in (
        ("profile-lint", cmd_profile_lint),
        ("pin-inputs", cmd_pin_inputs),
        ("validate-inputs", cmd_validate_inputs),
        ("preflight", cmd_preflight),
        ("build-runner", cmd_build_runner),
        ("sync-sources", cmd_sync_sources),
        ("extract-blobs", cmd_extract_blobs),
        ("build-images", cmd_build_images),
        ("validate-emulator", cmd_validate_emulator),
        ("publish-flash-bundle", cmd_publish_flash_bundle),
        ("device-preflight", cmd_device_preflight),
        ("device-snapshot", cmd_device_snapshot),
        ("device-backup-wifi", cmd_device_backup_wifi),
        ("device-restore-wifi", cmd_device_restore_wifi),
        ("device-apply-system-defaults", cmd_device_apply_system_defaults),
        ("device-apply-app-defaults", cmd_device_apply_app_defaults),
        ("deploy-tablet", cmd_deploy_tablet),
        ("validate-tablet", cmd_validate_tablet),
        ("collect-device-logs", cmd_collect_device_logs),
    ):
        cmd = sub.add_parser(name)
        cmd.add_argument("--profile", default=DEFAULT_PROFILE)
        cmd.add_argument("--profile-overlay")
        if name in {
            "validate-emulator",
            "publish-flash-bundle",
            "device-preflight",
            "device-snapshot",
            "device-backup-wifi",
            "device-restore-wifi",
            "device-apply-app-defaults",
            "deploy-tablet",
            "validate-tablet",
            "collect-device-logs",
        }:
            cmd.add_argument("--build-dir")
        if name in {
            "device-preflight",
            "device-snapshot",
            "extract-blobs",
            "device-backup-wifi",
            "device-restore-wifi",
            "device-apply-system-defaults",
            "device-apply-app-defaults",
            "deploy-tablet",
            "validate-tablet",
            "collect-device-logs",
        }:
            cmd.add_argument("--serial")
        if name == "deploy-tablet":
            cmd.add_argument("--allow-destructive", action="store_true")
            cmd.add_argument("--dry-run", action="store_true")
            cmd.add_argument("--wifi-backup", action="store_true")
            cmd.add_argument("--wifi-backup-path")
            cmd.add_argument(
                "--install-mode",
                choices=[
                    "first-install",
                    "fastboot-first-install",
                    "fastboot-image-install",
                    "update",
                    "resume-sideload",
                ],
            )
        if name == "device-backup-wifi":
            cmd.add_argument("--output")
        if name == "device-restore-wifi":
            cmd.add_argument("--input")
            cmd.add_argument("--no-reboot", action="store_true")
        if name == "extract-blobs":
            cmd.add_argument("--no-pin", action="store_true")
        cmd.set_defaults(func=func)

    render = sub.add_parser("render-env")
    render.add_argument("--profile", default=DEFAULT_PROFILE)
    render.add_argument("--profile-overlay")
    render.add_argument("--output")
    render.add_argument("--container", action="store_true")
    render.set_defaults(func=cmd_render_env)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    if getattr(args, "profile_overlay", None):
        os.environ["PROFILE_OVERLAY"] = args.profile_overlay
    try:
        return int(args.func(args))
    except subprocess.CalledProcessError as exc:
        return exc.returncode
    except Exception as exc:  # noqa: BLE001
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
