from __future__ import annotations

import tempfile
import unittest
import zipfile
import subprocess
import sys
from copy import deepcopy
from pathlib import Path

from tools import kioskctl


PROFILE = "profiles/shield-k1-lineage15-dev.yaml"
LINEAGE18_PROFILE = "profiles/shield-k1-lineage18-dev.yaml"


class KioskCtlTests(unittest.TestCase):
    def test_default_profile_shape_is_valid(self) -> None:
        profile = kioskctl.load_profile(PROFILE)

        warnings = kioskctl.validate_profile_shape(profile)

        self.assertEqual(profile["profile"], "shield-k1-lineage15-dev")
        self.assertEqual(profile["lineage"]["branch"], "lineage-15.1")
        self.assertEqual(profile["targets"]["emulator"]["lunch"], "sdk_phone_x86-userdebug")
        self.assertEqual(profile["apps"]["browser"]["package"], "org.mozilla.fennec_fdroid")
        self.assertEqual(profile["apps"]["emulator_browser"]["package"], "com.stoutner.privacybrowser.standard")
        self.assertEqual(profile["kiosk"]["launcher"]["package"], "local.rosie.kiosk")
        self.assertEqual(profile["kiosk"]["theme"]["background"]["type"], "color")
        self.assertEqual(profile["kiosk"]["theme"]["buttons"]["radius_dp"], 6)
        self.assertEqual(profile["kiosk"]["theme"]["text"]["shadow_radius_dp"], 2)
        self.assertIn("LineageSetupWizard", profile["kiosk"]["remove_modules"])
        self.assertIn("org.lineageos.trebuchet", profile["kiosk"]["remove_packages"])
        self.assertEqual([], warnings)

    def test_shell_env_exports_kiosk_controls_and_theme(self) -> None:
        profile = kioskctl.load_profile(PROFILE)

        env = kioskctl.shell_env(profile, container=True)

        self.assertEqual(env["KIOSK_LAUNCHER_MODULE"], "RosieKioskLauncher")
        self.assertEqual(env["KIOSK_LAUNCHER_PACKAGE"], "local.rosie.kiosk")
        self.assertIn("Trebuchet", env["KIOSK_REMOVE_MODULES"])
        self.assertIn("org.lineageos.setupwizard", env["KIOSK_REMOVE_PACKAGES"])
        self.assertEqual(env["KIOSK_TITLE"], "Rosie Kiosk")
        self.assertEqual(env["KIOSK_BACKGROUND_TYPE"], "color")
        self.assertEqual(env["KIOSK_BUTTON_BORDER_COLOR"], "#00a884")
        self.assertEqual(env["KIOSK_BUTTON_TEXT_SIZE_SP"], "22")
        self.assertEqual(env["KIOSK_BUTTON_RADIUS_DP"], "6")
        self.assertEqual(env["KIOSK_TEXT_SHADOW_COLOR"], "#99000000")

    def test_profile_overlay_deep_merges_private_theme(self) -> None:
        work = kioskctl.ROOT / ".work" / "tests"
        work.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=work) as temp:
            overlay = Path(temp) / "site.yaml"
            overlay.write_text(
                "kiosk:\n"
                "  theme:\n"
                "    title: Kitchen\n"
                "    background:\n"
                "      scrim_color: '#66000000'\n",
                encoding="utf-8",
            )

            profile = kioskctl.load_profile(PROFILE, overlay)

        self.assertEqual(profile["kiosk"]["theme"]["title"], "Kitchen")
        self.assertEqual(profile["kiosk"]["theme"]["background"]["scrim_color"], "#66000000")
        self.assertEqual(profile["kiosk"]["theme"]["buttons"]["radius_dp"], 6)
        self.assertEqual(profile["_profile_overlay_path"].split("/")[-1], "site.yaml")

    def test_overlay_pin_inputs_is_rejected(self) -> None:
        work = kioskctl.ROOT / ".work" / "tests"
        work.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=work) as temp:
            overlay = Path(temp) / "site.yaml"
            overlay.write_text("kiosk:\n  theme:\n    title: Private\n", encoding="utf-8")
            profile = kioskctl.load_profile(PROFILE, overlay)

        with self.assertRaisesRegex(ValueError, "refusing to write"):
            kioskctl.save_profile(profile)

    def test_latest_build_dir_requires_overlay_hash_match(self) -> None:
        work = kioskctl.ROOT / ".work" / "tests"
        work.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=work) as temp:
            dist = Path(temp)
            profile = deepcopy(kioskctl.load_profile(PROFILE))
            profile["paths"]["dist"] = str(dist.relative_to(kioskctl.ROOT))
            profile["_profile_overlay_path"] = "profiles/local/site.yaml"
            stale = dist / f"{kioskctl.profile_name(profile)}-20260101T000000Z-old-deadbeef"
            stale.mkdir()
            kioskctl.write_json(
                stale / "INPUT-LOCK.json",
                {"profile": {"profile": kioskctl.profile_name(profile)}},
            )

            with self.assertRaisesRegex(FileNotFoundError, "merged profile"):
                kioskctl.latest_build_dir(profile)

            fresh = dist / f"{kioskctl.profile_name(profile)}-20260102T000000Z-new-feedface"
            fresh.mkdir()
            kioskctl.write_json(
                fresh / "INPUT-LOCK.json",
                {"profile": kioskctl.canonical_profile(profile)},
            )

            selected = kioskctl.latest_build_dir(profile)

        self.assertEqual(fresh.name, selected.name)

    def test_lineage18_profile_remains_valid_as_future_experiment(self) -> None:
        profile = kioskctl.load_profile(LINEAGE18_PROFILE)

        warnings = kioskctl.validate_profile_shape(profile)

        self.assertEqual(profile["profile"], "shield-k1-lineage18-dev")
        self.assertIn("apps.home_assistant.sha256 is still a placeholder", warnings)

    def test_preflight_reports_missing_concrete_inputs(self) -> None:
        profile = deepcopy(kioskctl.load_profile(PROFILE))
        profile["apps"]["home_assistant"]["apk"] = "inputs/apks/__missing_ha__.apk"
        profile["apps"]["browser"]["apk"] = "inputs/apks/__missing_browser__.apk"
        profile["blobs"]["archive"] = "inputs/vendor-blobs/__missing_blobs__.tar.zst"

        errors = kioskctl.validate_concrete_inputs(profile)

        self.assertIn("missing APK: inputs/apks/__missing_ha__.apk", errors)
        self.assertIn("missing APK: inputs/apks/__missing_browser__.apk", errors)
        self.assertIn(
            "missing vendor blob archive: inputs/vendor-blobs/__missing_blobs__.tar.zst",
            errors,
        )

    def test_validate_inputs_reports_missing_kiosk_background(self) -> None:
        profile = deepcopy(kioskctl.load_profile(PROFILE))
        profile["kiosk"]["theme"]["background"] = {
            "type": "image",
            "path": "inputs/kiosk-assets/missing.png",
            "sha256": "0" * 64,
            "fit": "cover",
            "loop": True,
            "fallback_color": "#0f1216",
            "scrim_color": "#66000000",
        }

        errors = kioskctl.validate_concrete_inputs(profile)

        self.assertIn("missing kiosk background asset: inputs/kiosk-assets/missing.png", errors)

    def test_validate_inputs_accepts_hashed_kiosk_background(self) -> None:
        work = kioskctl.ROOT / ".work" / "tests"
        work.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=work) as temp:
            asset = Path(temp) / "background.png"
            asset.write_bytes(b"not-a-real-png-but-hashable")
            profile = deepcopy(kioskctl.load_profile(PROFILE))
            profile["kiosk"]["theme"]["background"] = {
                "type": "image",
                "path": str(asset.relative_to(kioskctl.ROOT)),
                "sha256": kioskctl.sha256_file(asset),
                "fit": "cover",
                "loop": True,
                "fallback_color": "#0f1216",
                "scrim_color": "#66000000",
            }

            errors = kioskctl.validate_theme_inputs(profile)

        self.assertEqual([], errors)

    def test_validate_inputs_accepts_video_height_fit_and_argb_theme(self) -> None:
        work = kioskctl.ROOT / ".work" / "tests"
        work.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=work) as temp:
            asset = Path(temp) / "background.mp4"
            asset.write_bytes(b"not-a-real-mp4-but-hashable")
            profile = deepcopy(kioskctl.load_profile(PROFILE))
            profile["kiosk"]["theme"]["background"] = {
                "type": "video",
                "path": str(asset.relative_to(kioskctl.ROOT)),
                "sha256": kioskctl.sha256_file(asset),
                "fit": "height",
                "loop": True,
                "fallback_color": "#121212",
                "scrim_color": "#B8070A0E",
            }
            profile["kiosk"]["theme"]["text"]["shadow_color"] = "#B8000000"
            profile["kiosk"]["theme"]["buttons"]["background_color"] = "#CC2c2c2c"
            profile["kiosk"]["theme"]["buttons"]["accent_color"] = "#33fbc02d"
            profile["kiosk"]["theme"]["buttons"]["border_color"] = "#99404040"

            warnings = kioskctl.validate_profile_shape(profile)
            errors = kioskctl.validate_theme_inputs(profile)

        self.assertEqual([], warnings)
        self.assertEqual([], errors)

    def test_height_fit_is_video_only(self) -> None:
        profile = deepcopy(kioskctl.load_profile(PROFILE))
        profile["kiosk"]["theme"]["background"] = {
            "type": "image",
            "path": "inputs/kiosk-assets/background.png",
            "sha256": "0" * 64,
            "fit": "height",
            "loop": True,
            "fallback_color": "#0f1216",
            "scrim_color": "#66000000",
        }

        with self.assertRaisesRegex(ValueError, "height is only supported"):
            kioskctl.validate_profile_shape(profile)

    def test_workerbee_manifest_uses_local_kvm_job(self) -> None:
        profile = kioskctl.load_profile(PROFILE)
        manifest = kioskctl.workerbee_job_manifest(profile, Path("/tmp/build-id"))

        self.assertIn("kind: Job", manifest)
        self.assertIn("path: /dev/kvm", manifest)
        self.assertIn("privileged: true", manifest)
        self.assertIn("/work/repo/scripts/runner/validate-emulator.sh", manifest)
        self.assertIn("rosie-local-ha/android-runner:lineage15", manifest)

    def test_apk_payload_rejects_wrong_native_abi(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            apk = Path(temp) / "Browser.apk"
            with zipfile.ZipFile(apk, "w") as archive:
                archive.writestr("AndroidManifest.xml", b"manifest")
                archive.writestr("lib/arm64-v8a/libexample.so", b"binary")
            profile = deepcopy(kioskctl.load_profile(PROFILE))

            errors = kioskctl.validate_apk_payload(profile, "browser", apk)

        self.assertIn("expected armeabi-v7a, found arm64-v8a", errors[0])

    def test_prune_missing_optional_vendor_apps_removes_absent_apk_modules(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            device_root = root / "device/nvidia/shieldtablet"
            vendor_root = root / "vendor/nvidia/shieldtablet"
            (device_root).mkdir(parents=True)
            (vendor_root / "proprietary/vendor/app/NvCPLSvc").mkdir(parents=True)
            (device_root / "proprietary-files.txt").write_text(
                "-vendor/app/ConsoleUI/ConsoleUI.apk\n"
                "-vendor/app/NvCPLSvc/NvCPLSvc.apk\n"
            )
            (vendor_root / "proprietary/vendor/app/NvCPLSvc/NvCPLSvc.apk").write_bytes(b"apk")
            (vendor_root / "proprietary/vendor/bin").mkdir(parents=True)
            (vendor_root / "proprietary/vendor/bin/existingd").write_bytes(b"bin")
            (vendor_root / "Android.mk").write_text(
                "include $(CLEAR_VARS)\n"
                "LOCAL_MODULE := ConsoleUI\n"
                "LOCAL_SRC_FILES := proprietary/vendor/app/ConsoleUI/ConsoleUI.apk\n"
                "include $(BUILD_PREBUILT)\n\n"
                "include $(CLEAR_VARS)\n"
                "LOCAL_MODULE := NvCPLSvc\n"
                "LOCAL_SRC_FILES := proprietary/vendor/app/NvCPLSvc/NvCPLSvc.apk\n"
                "include $(BUILD_PREBUILT)\n"
            )
            (vendor_root / "shieldtablet-vendor.mk").write_text(
                "PRODUCT_COPY_FILES += \\\n"
                "    vendor/nvidia/shieldtablet/proprietary/vendor/bin/ussrd:$(TARGET_COPY_OUT_VENDOR)/bin/ussrd \\\n"
                "    vendor/nvidia/shieldtablet/proprietary/vendor/bin/existingd:$(TARGET_COPY_OUT_VENDOR)/bin/existingd\n\n"
                "PRODUCT_PACKAGES += \\\n"
                "    ConsoleUI \\\n"
                "    NvCPLSvc\n"
            )

            subprocess.run(
                [
                    sys.executable,
                    "scripts/runner/prune-missing-optional-vendor-apps.py",
                    "--android-root",
                    str(root),
                ],
                check=True,
            )

            self.assertNotIn("ConsoleUI", (vendor_root / "Android.mk").read_text())
            self.assertIn("NvCPLSvc", (vendor_root / "Android.mk").read_text())
            vendor_mk = (vendor_root / "shieldtablet-vendor.mk").read_text()
            self.assertNotIn("ConsoleUI", vendor_mk)
            self.assertNotIn("ussrd", vendor_mk)
            self.assertIn("existingd", vendor_mk)
            self.assertIn("NvCPLSvc", vendor_mk)

    def test_parse_adb_devices_with_authorized_and_unauthorized(self) -> None:
        devices = kioskctl.parse_adb_devices(
            """List of devices attached
abc123 device product:shieldtablet model:SHIELD_Tablet device:shieldtablet transport_id:1
def456 unauthorized usb:1-1
"""
        )

        self.assertEqual(devices[0]["serial"], "abc123")
        self.assertEqual(devices[0]["state"], "device")
        self.assertEqual(devices[0]["details"]["device"], "shieldtablet")
        self.assertEqual(devices[1]["state"], "unauthorized")

    def test_select_single_device_rejects_multiple_without_serial(self) -> None:
        devices = [
            {"serial": "one", "state": "device"},
            {"serial": "two", "state": "device"},
        ]

        with self.assertRaises(kioskctl.DeviceError):
            kioskctl.select_single_device(
                devices,
                requested_serial=None,
                allowed_states={"device"},
                tool="adb",
            )

    def test_select_single_device_rejects_unauthorized(self) -> None:
        with self.assertRaisesRegex(kioskctl.DeviceError, "RSA prompt"):
            kioskctl.select_single_device(
                [{"serial": "one", "state": "unauthorized"}],
                requested_serial="one",
                allowed_states={"device"},
                tool="adb",
            )

    def test_parse_fastboot_getvar_all_detects_locked_state(self) -> None:
        values = kioskctl.parse_fastboot_getvar_all(
            """(bootloader) unlocked: no
(bootloader) device-state: locked
finished. total time: 0.001s
"""
        )

        self.assertEqual(values["unlocked"], "no")
        self.assertEqual(values["device-state"], "locked")

    def test_destructive_gate_requires_serial_and_allow_flag(self) -> None:
        with self.assertRaises(kioskctl.DeviceError):
            kioskctl.require_destructive_gate(None, True)

        with self.assertRaises(kioskctl.DeviceError):
            kioskctl.require_destructive_gate("abc123", False)

        self.assertEqual(kioskctl.require_destructive_gate("abc123", True), "abc123")

    def test_first_install_sequence_wipes_userdata_before_sideload(self) -> None:
        commands = kioskctl.deployment_command_sequence(
            mode="first-install",
            serial="abc123",
            recovery=Path("/tmp/recovery.img"),
            lineage_zip=Path("/tmp/lineage.zip"),
        )

        self.assertEqual(commands[0], ["adb", "-s", "abc123", "reboot", "bootloader"])
        self.assertIn(["fastboot", "-s", "abc123", "erase", "userdata"], commands)
        self.assertIn(["fastboot", "-s", "abc123", "erase", "cache"], commands)
        self.assertLess(
            commands.index(["fastboot", "-s", "abc123", "erase", "userdata"]),
            commands.index(["adb", "-s", "abc123", "sideload", "/tmp/lineage.zip"]),
        )

    def test_fastboot_first_install_starts_from_bootloader(self) -> None:
        commands = kioskctl.deployment_command_sequence(
            mode="fastboot-first-install",
            serial="abc123",
            recovery=Path("/tmp/recovery.img"),
            lineage_zip=Path("/tmp/lineage.zip"),
        )

        self.assertEqual(commands[0], ["fastboot", "-s", "abc123", "erase", "userdata"])
        self.assertNotIn(["adb", "-s", "abc123", "reboot", "bootloader"], commands)
        self.assertLess(
            commands.index(["fastboot", "-s", "abc123", "flash", "recovery", "/tmp/recovery.img"]),
            commands.index(["adb", "-s", "abc123", "sideload", "/tmp/lineage.zip"]),
        )

    def test_fastboot_image_install_flashes_system_without_recovery_sideload(self) -> None:
        commands = kioskctl.deployment_command_sequence(
            mode="fastboot-image-install",
            serial="abc123",
            recovery=Path("/tmp/recovery.img"),
            lineage_zip=Path("/tmp/lineage.zip"),
            boot_img=Path("/tmp/boot.img"),
            system_img=Path("/tmp/system.img"),
        )

        self.assertIn(["fastboot", "-s", "abc123", "flash", "boot", "/tmp/boot.img"], commands)
        self.assertIn(["fastboot", "-s", "abc123", "flash", "system", "/tmp/system.img"], commands)
        self.assertNotIn(["adb", "-s", "abc123", "sideload", "/tmp/lineage.zip"], commands)
        self.assertEqual(commands[-1], ["fastboot", "-s", "abc123", "reboot"])

    def test_window_focus_references_package_requires_focus_line(self) -> None:
        dump = """
          Window #1 Window{abc u0 local.rosie.kiosk/local.rosie.kiosk.LauncherActivity}
          mFocusedApp=AppWindowToken{def token=Token{ghi ActivityRecord{jkl org.mozilla.fennec_fdroid/.App}}}
        """

        self.assertFalse(kioskctl.window_focus_references_package(dump, "local.rosie.kiosk"))

    def test_window_focus_references_package_accepts_focused_app(self) -> None:
        dump = """
          Window #1 Window{abc u0 org.mozilla.fennec_fdroid/org.mozilla.fennec_fdroid.App}
          mFocusedApp=AppWindowToken{def token=Token{ghi ActivityRecord{jkl local.rosie.kiosk/.LauncherActivity}}}
        """

        self.assertTrue(kioskctl.window_focus_references_package(dump, "local.rosie.kiosk"))


if __name__ == "__main__":
    unittest.main()
