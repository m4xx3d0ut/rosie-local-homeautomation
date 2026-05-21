#!/usr/bin/env bash
set -euo pipefail

: "${ANDROID_ROOT:?ANDROID_ROOT is required}"
: "${REPO_ROOT:?REPO_ROOT is required}"
: "${HA_MODULE:?HA_MODULE is required}"
: "${HA_PACKAGE:?HA_PACKAGE is required}"
: "${HA_APK:?HA_APK is required}"
: "${BROWSER_MODULE:?BROWSER_MODULE is required}"
: "${BROWSER_PACKAGE:?BROWSER_PACKAGE is required}"
: "${BROWSER_APK:?BROWSER_APK is required}"
: "${EMULATOR_BROWSER_MODULE:?EMULATOR_BROWSER_MODULE is required}"
: "${EMULATOR_BROWSER_APK:?EMULATOR_BROWSER_APK is required}"
HA_BROWSER_MODULE="${HA_BROWSER_MODULE:-}"
HA_BROWSER_PACKAGE="${HA_BROWSER_PACKAGE:-}"
HA_BROWSER_APK="${HA_BROWSER_APK:-}"
KIOSK_LAUNCHER_MODULE="${KIOSK_LAUNCHER_MODULE:-RosieKioskLauncher}"
KIOSK_LAUNCHER_PACKAGE="${KIOSK_LAUNCHER_PACKAGE:-local.rosie.kiosk}"
KIOSK_REMOVE_MODULES="${KIOSK_REMOVE_MODULES:-}"
KIOSK_TITLE="${KIOSK_TITLE:-Rosie Kiosk}"
KIOSK_SUBTITLE="${KIOSK_SUBTITLE:-Home Assistant and browser access}"
KIOSK_FONT_FAMILY="${KIOSK_FONT_FAMILY:-sans}"
KIOSK_BACKGROUND_TYPE="${KIOSK_BACKGROUND_TYPE:-color}"
KIOSK_BACKGROUND_PATH="${KIOSK_BACKGROUND_PATH:-}"
KIOSK_BACKGROUND_FIT="${KIOSK_BACKGROUND_FIT:-cover}"
KIOSK_BACKGROUND_LOOP="${KIOSK_BACKGROUND_LOOP:-true}"
KIOSK_BACKGROUND_FALLBACK_COLOR="${KIOSK_BACKGROUND_FALLBACK_COLOR:-#0f1216}"
KIOSK_BACKGROUND_SCRIM_COLOR="${KIOSK_BACKGROUND_SCRIM_COLOR:-#00000000}"
KIOSK_TEXT_COLOR="${KIOSK_TEXT_COLOR:-#ffffff}"
KIOSK_SUBTITLE_COLOR="${KIOSK_SUBTITLE_COLOR:-#bec6cd}"
KIOSK_TITLE_SIZE_SP="${KIOSK_TITLE_SIZE_SP:-34}"
KIOSK_SUBTITLE_SIZE_SP="${KIOSK_SUBTITLE_SIZE_SP:-18}"
KIOSK_TEXT_SHADOW_COLOR="${KIOSK_TEXT_SHADOW_COLOR:-#99000000}"
KIOSK_TEXT_SHADOW_RADIUS_DP="${KIOSK_TEXT_SHADOW_RADIUS_DP:-2}"
KIOSK_TEXT_SHADOW_DX_DP="${KIOSK_TEXT_SHADOW_DX_DP:-0}"
KIOSK_TEXT_SHADOW_DY_DP="${KIOSK_TEXT_SHADOW_DY_DP:-2}"
KIOSK_BUTTON_HA_LABEL="${KIOSK_BUTTON_HA_LABEL:-Home Assistant}"
KIOSK_BUTTON_BROWSER_LABEL="${KIOSK_BUTTON_BROWSER_LABEL:-Browser}"
KIOSK_BUTTON_BACKGROUND_COLOR="${KIOSK_BUTTON_BACKGROUND_COLOR:-#00a884}"
KIOSK_BUTTON_TEXT_COLOR="${KIOSK_BUTTON_TEXT_COLOR:-#ffffff}"
KIOSK_BUTTON_ACCENT_COLOR="${KIOSK_BUTTON_ACCENT_COLOR:-#007c61}"
KIOSK_BUTTON_BORDER_COLOR="${KIOSK_BUTTON_BORDER_COLOR:-#00a884}"
KIOSK_BUTTON_FOCUS_BORDER_COLOR="${KIOSK_BUTTON_FOCUS_BORDER_COLOR:-#007c61}"
KIOSK_BUTTON_TEXT_SIZE_SP="${KIOSK_BUTTON_TEXT_SIZE_SP:-22}"
KIOSK_BUTTON_RADIUS_DP="${KIOSK_BUTTON_RADIUS_DP:-6}"
KIOSK_BUTTON_MIN_HEIGHT_DP="${KIOSK_BUTTON_MIN_HEIGHT_DP:-68}"
KIOSK_BUTTON_WIDTH_DP="${KIOSK_BUTTON_WIDTH_DP:-520}"
KIOSK_HA_URL="${KIOSK_HA_URL:-}"
KIOSK_BROWSER_URL="${KIOSK_BROWSER_URL:-}"
KIOSK_BROWSER_LAUNCH_POLICY="${KIOSK_BROWSER_LAUNCH_POLICY:-always_new_tab}"
KIOSK_HA_BROWSER_PACKAGE="${KIOSK_HA_BROWSER_PACKAGE:-${HA_BROWSER_PACKAGE:-${BROWSER_PACKAGE}}}"
KIOSK_PINNED_APPS_JSON="${KIOSK_PINNED_APPS_JSON:-[]}"
KIOSK_EXTRA_APPS_JSON="${KIOSK_EXTRA_APPS_JSON:-[]}"
KIOSK_EXTRA_APP_MODULES="${KIOSK_EXTRA_APP_MODULES:-}"
KIOSK_EXTRA_APP_PACKAGES="${KIOSK_EXTRA_APP_PACKAGES:-}"
BROWSER_FALLBACK_PACKAGE="${BROWSER_FALLBACK_PACKAGE:-${BROWSER_PACKAGE}}"
SYSTEM_UI_NIGHT_MODE="${SYSTEM_UI_NIGHT_MODE:-auto}"
SYSTEM_UI_NIGHT_MODE_VALUE="${SYSTEM_UI_NIGHT_MODE_VALUE:-0}"
SYSTEM_AUTO_TIME="${SYSTEM_AUTO_TIME:-true}"
SYSTEM_AUTO_TIME_VALUE="${SYSTEM_AUTO_TIME_VALUE:-1}"
SYSTEM_AUTO_TIME_ZONE="${SYSTEM_AUTO_TIME_ZONE:-true}"
SYSTEM_AUTO_TIME_ZONE_VALUE="${SYSTEM_AUTO_TIME_ZONE_VALUE:-1}"
SYSTEM_TIMEZONE="${SYSTEM_TIMEZONE:-}"
SYSTEM_NTP_SERVER="${SYSTEM_NTP_SERVER:-pool.ntp.org}"
SYSTEM_LOCATION_PROVIDERS_ALLOWED="${SYSTEM_LOCATION_PROVIDERS_ALLOWED:-gps}"
APP_RUNTIME_PERMISSION_GRANTS_JSON="${APP_RUNTIME_PERMISSION_GRANTS_JSON:-[]}"
export \
  HA_PACKAGE \
  BROWSER_PACKAGE \
  HA_BROWSER_PACKAGE \
  KIOSK_LAUNCHER_PACKAGE \
  KIOSK_TITLE \
  KIOSK_SUBTITLE \
  KIOSK_FONT_FAMILY \
  KIOSK_BACKGROUND_TYPE \
  KIOSK_BACKGROUND_FIT \
  KIOSK_BACKGROUND_LOOP \
  KIOSK_BACKGROUND_FALLBACK_COLOR \
  KIOSK_BACKGROUND_SCRIM_COLOR \
  KIOSK_TEXT_COLOR \
  KIOSK_SUBTITLE_COLOR \
  KIOSK_TITLE_SIZE_SP \
  KIOSK_SUBTITLE_SIZE_SP \
  KIOSK_TEXT_SHADOW_COLOR \
  KIOSK_TEXT_SHADOW_RADIUS_DP \
  KIOSK_TEXT_SHADOW_DX_DP \
  KIOSK_TEXT_SHADOW_DY_DP \
  KIOSK_BUTTON_HA_LABEL \
  KIOSK_BUTTON_BROWSER_LABEL \
  KIOSK_BUTTON_BACKGROUND_COLOR \
  KIOSK_BUTTON_TEXT_COLOR \
  KIOSK_BUTTON_ACCENT_COLOR \
  KIOSK_BUTTON_BORDER_COLOR \
  KIOSK_BUTTON_FOCUS_BORDER_COLOR \
  KIOSK_BUTTON_TEXT_SIZE_SP \
  KIOSK_BUTTON_RADIUS_DP \
  KIOSK_BUTTON_MIN_HEIGHT_DP \
  KIOSK_BUTTON_WIDTH_DP \
  KIOSK_HA_URL \
  KIOSK_BROWSER_URL \
  KIOSK_BROWSER_LAUNCH_POLICY \
  KIOSK_HA_BROWSER_PACKAGE \
  KIOSK_PINNED_APPS_JSON \
  KIOSK_EXTRA_APPS_JSON \
  KIOSK_EXTRA_APP_MODULES \
  KIOSK_EXTRA_APP_PACKAGES \
  BROWSER_FALLBACK_PACKAGE \
  SYSTEM_AUTO_TIME \
  SYSTEM_AUTO_TIME_VALUE \
  SYSTEM_AUTO_TIME_ZONE \
  SYSTEM_AUTO_TIME_ZONE_VALUE \
  SYSTEM_TIMEZONE \
  SYSTEM_NTP_SERVER \
  SYSTEM_LOCATION_PROVIDERS_ALLOWED \
  APP_RUNTIME_PERMISSION_GRANTS_JSON

ROSIE_VENDOR="${ANDROID_ROOT}/vendor/rosie"
APP_DIR="${ROSIE_VENDOR}/prebuilt_apps"
KIOSK_DIR="${ROSIE_VENDOR}/kiosk_launcher"
PRODUCT_DIR="${ROSIE_VENDOR}/product"
ADB_DIR="${ROSIE_VENDOR}/adb"
DEFAULT_PERMISSIONS_DIR="${ROSIE_VENDOR}/default-permissions"
OVERLAY_VALUES_DIR="${ROSIE_VENDOR}/overlay/frameworks/base/core/res/res/values"
SETTINGS_OVERLAY_VALUES_DIR="${ROSIE_VENDOR}/overlay/frameworks/base/packages/SettingsProvider/res/values"
ROOT_ACCESS="${ROOT_ACCESS:-}"

mkdir -p \
  "${APP_DIR}/${HA_MODULE}" \
  "${APP_DIR}/${BROWSER_MODULE}" \
  "${APP_DIR}/${EMULATOR_BROWSER_MODULE}" \
  "${KIOSK_DIR}/res/values" \
  "${KIOSK_DIR}/res/drawable-nodpi" \
  "${KIOSK_DIR}/res/raw" \
  "${KIOSK_DIR}/src/${KIOSK_LAUNCHER_PACKAGE//.//}" \
  "${PRODUCT_DIR}" \
  "${ADB_DIR}" \
  "${DEFAULT_PERMISSIONS_DIR}" \
  "${OVERLAY_VALUES_DIR}" \
  "${SETTINGS_OVERLAY_VALUES_DIR}"
if [[ -n "${HA_BROWSER_MODULE}" && "${HA_BROWSER_MODULE}" != "${BROWSER_MODULE}" && "${HA_BROWSER_MODULE}" != "${EMULATOR_BROWSER_MODULE}" ]]; then
  mkdir -p "${APP_DIR}/${HA_BROWSER_MODULE}"
fi
python3 - "${APP_DIR}" <<'PY'
import json
import os
import sys
from pathlib import Path

app_dir = Path(sys.argv[1])
for app in json.loads(os.environ.get("KIOSK_EXTRA_APPS_JSON", "[]")):
    module = app["module"]
    (app_dir / module).mkdir(parents=True, exist_ok=True)
PY
cp "${REPO_ROOT}/${HA_APK}" "${APP_DIR}/${HA_MODULE}/${HA_MODULE}.apk"
cp "${REPO_ROOT}/${BROWSER_APK}" "${APP_DIR}/${BROWSER_MODULE}/${BROWSER_MODULE}.apk"
if [[ "${EMULATOR_BROWSER_MODULE}" != "${BROWSER_MODULE}" ]]; then
  cp "${REPO_ROOT}/${EMULATOR_BROWSER_APK}" "${APP_DIR}/${EMULATOR_BROWSER_MODULE}/${EMULATOR_BROWSER_MODULE}.apk"
fi
if [[ -n "${HA_BROWSER_MODULE}" && "${HA_BROWSER_MODULE}" != "${BROWSER_MODULE}" && "${HA_BROWSER_MODULE}" != "${EMULATOR_BROWSER_MODULE}" ]]; then
  if [[ -z "${HA_BROWSER_APK}" || ! -f "${REPO_ROOT}/${HA_BROWSER_APK}" ]]; then
    echo "missing Home Assistant browser APK: ${REPO_ROOT}/${HA_BROWSER_APK}" >&2
    exit 1
  fi
  cp "${REPO_ROOT}/${HA_BROWSER_APK}" "${APP_DIR}/${HA_BROWSER_MODULE}/${HA_BROWSER_MODULE}.apk"
fi
python3 - "${APP_DIR}" <<'PY'
import json
import os
import shutil
import sys
from pathlib import Path

app_dir = Path(sys.argv[1])
repo_root = Path(os.environ["REPO_ROOT"])
for app in json.loads(os.environ.get("KIOSK_EXTRA_APPS_JSON", "[]")):
    module = app["module"]
    apk = repo_root / app["apk"]
    if not apk.is_file():
        print(f"missing pinned app APK: {apk}", file=sys.stderr)
        raise SystemExit(1)
    shutil.copy2(apk, app_dir / module / f"{module}.apk")
PY
if [[ -n "${ADB_PUBLIC_KEY:-}" ]]; then
  if [[ ! -f "${REPO_ROOT}/${ADB_PUBLIC_KEY}" ]]; then
    echo "missing adb public key: ${REPO_ROOT}/${ADB_PUBLIC_KEY}" >&2
    exit 1
  fi
  cp "${REPO_ROOT}/${ADB_PUBLIC_KEY}" "${ADB_DIR}/adb_keys"
fi

rm -f \
  "${KIOSK_DIR}/res/drawable-nodpi/kiosk_background".* \
  "${KIOSK_DIR}/res/raw/kiosk_background".*
if [[ "${KIOSK_BACKGROUND_TYPE}" == "image" || "${KIOSK_BACKGROUND_TYPE}" == "video" ]]; then
  if [[ -z "${KIOSK_BACKGROUND_PATH}" || ! -f "${REPO_ROOT}/${KIOSK_BACKGROUND_PATH}" ]]; then
    echo "missing kiosk background asset: ${REPO_ROOT}/${KIOSK_BACKGROUND_PATH}" >&2
    exit 1
  fi
  background_ext="${KIOSK_BACKGROUND_PATH##*.}"
  background_ext="${background_ext,,}"
  if [[ "${KIOSK_BACKGROUND_TYPE}" == "image" ]]; then
    if [[ "${background_ext}" == "jpeg" ]]; then
      background_ext="jpg"
    fi
    cp "${REPO_ROOT}/${KIOSK_BACKGROUND_PATH}" "${KIOSK_DIR}/res/drawable-nodpi/kiosk_background.${background_ext}"
  else
    cp "${REPO_ROOT}/${KIOSK_BACKGROUND_PATH}" "${KIOSK_DIR}/res/raw/kiosk_background.${background_ext}"
  fi
fi

write_if_changed() {
  local path="$1"
  local tmp="${path}.rosie-tmp"
  cat > "${tmp}"
  if [[ ! -f "${path}" ]] || ! cmp -s "${tmp}" "${path}"; then
    mv "${tmp}" "${path}"
  else
    rm "${tmp}"
  fi
}

replace_once() {
  local path="$1"
  local from="$2"
  local to="$3"

  if [[ ! -f "${path}" ]]; then
    echo "missing patch target: ${path}" >&2
    return 1
  fi
  if grep -Fq "${to}" "${path}"; then
    return 0
  fi
  if ! grep -Fq "${from}" "${path}"; then
    echo "patch target did not contain expected text: ${path}" >&2
    return 1
  fi
  sed -i "s|${from}|${to}|g" "${path}"
}

replace_block_once() {
  local path="$1"
  local from="$2"
  local to="$3"

  if [[ ! -f "${path}" ]]; then
    echo "missing patch target: ${path}" >&2
    return 1
  fi
  python3 - "${path}" "${from}" "${to}" <<'PY'
import sys

path, source, replacement = sys.argv[1:4]
with open(path, "r", encoding="utf-8") as handle:
    content = handle.read()
if replacement in content:
    raise SystemExit(0)
if source not in content:
    print(f"patch target did not contain expected text: {path}", file=sys.stderr)
    raise SystemExit(1)
with open(path, "w", encoding="utf-8") as handle:
    handle.write(content.replace(source, replacement))
PY
}

replace_once \
  "${ANDROID_ROOT}/device/nvidia/shield-common/system_prop.mk" \
  "persist.sys.usb.config=mtp" \
  "persist.sys.usb.config=mtp,adb"

replace_once \
  "${ANDROID_ROOT}/device/nvidia/shieldtablet/initfiles/init.tn8_common.rc" \
  "setprop persist.sys.usb.config mtp" \
  "setprop persist.sys.usb.config mtp,adb"

replace_block_once \
  "${ANDROID_ROOT}/frameworks/base/services/core/java/com/android/server/display/DisplayManagerService.java" \
  "        if (mContext.getResources().getBoolean(
                com.android.internal.R.bool.config_enableWifiDisplay)
                || SystemProperties.getInt(FORCE_WIFI_DISPLAY_ENABLE, -1) == 1) {" \
  "        if ((mContext.getResources().getBoolean(
                com.android.internal.R.bool.config_enableWifiDisplay)
                || SystemProperties.getInt(FORCE_WIFI_DISPLAY_ENABLE, -1) == 1)
                && mContext.getSystemService(Context.WIFI_P2P_SERVICE) != null) {"

remove_product_package_entries() {
  local path="$1"
  local module

  if [[ ! -f "${path}" || -z "${KIOSK_REMOVE_MODULES}" ]]; then
    return 0
  fi

  for module in ${KIOSK_REMOVE_MODULES}; do
    sed -i -E \
      -e "/^[[:space:]]*${module}[[:space:]]*\\\\?[[:space:]]*(#.*)?$/d" \
      -e "/^[[:space:]]*PRODUCT_PACKAGES[[:space:]]*\\+=[[:space:]]*${module}[[:space:]]*(#.*)?$/d" \
      "${path}"
  done
}

for product_makefile in \
  build/target/product/core.mk \
  build/target/product/core_base.mk \
  build/target/product/sdk_base.mk \
  vendor/lineage/config/common.mk \
  vendor/lineage/config/common_full.mk \
  device/nvidia/shieldtablet/device.mk; do
  remove_product_package_entries "${ANDROID_ROOT}/${product_makefile}"
done

prune_staged_product_packages() {
  local product="$1"
  local product_out="${ANDROID_ROOT}/out/target/product/${product}"
  local module

  if [[ ! -d "${product_out}" || -z "${KIOSK_REMOVE_MODULES}" ]]; then
    return 0
  fi

  for module in ${KIOSK_REMOVE_MODULES}; do
    rm -rf \
      "${product_out}/system/app/${module}" \
      "${product_out}/system/priv-app/${module}" \
      "${product_out}/data/app/${module}" \
      "${product_out}/obj/APPS/${module}_intermediates"
  done
}

prune_staged_product_packages "${EMULATOR_OUTPUT_PRODUCT}"
prune_staged_product_packages "${TABLET_OUTPUT_PRODUCT}"

{
cat <<EOF_MK
LOCAL_PATH := \$(call my-dir)

include \$(CLEAR_VARS)
LOCAL_MODULE := ${HA_MODULE}
LOCAL_SRC_FILES := ${HA_MODULE}/${HA_MODULE}.apk
LOCAL_MODULE_CLASS := APPS
LOCAL_MODULE_SUFFIX := \$(COMMON_ANDROID_PACKAGE_SUFFIX)
LOCAL_CERTIFICATE := PRESIGNED
LOCAL_MODULE_TAGS := optional
LOCAL_PRODUCT_MODULE := true
include \$(BUILD_PREBUILT)

include \$(CLEAR_VARS)
LOCAL_MODULE := ${BROWSER_MODULE}
LOCAL_SRC_FILES := ${BROWSER_MODULE}/${BROWSER_MODULE}.apk
LOCAL_MODULE_CLASS := APPS
LOCAL_MODULE_SUFFIX := \$(COMMON_ANDROID_PACKAGE_SUFFIX)
LOCAL_CERTIFICATE := PRESIGNED
LOCAL_MODULE_TAGS := optional
LOCAL_PRODUCT_MODULE := true
include \$(BUILD_PREBUILT)
EOF_MK

if [[ -n "${HA_BROWSER_MODULE}" && "${HA_BROWSER_MODULE}" != "${BROWSER_MODULE}" && "${HA_BROWSER_MODULE}" != "${EMULATOR_BROWSER_MODULE}" ]]; then
cat <<EOF_MK

include \$(CLEAR_VARS)
LOCAL_MODULE := ${HA_BROWSER_MODULE}
LOCAL_SRC_FILES := ${HA_BROWSER_MODULE}/${HA_BROWSER_MODULE}.apk
LOCAL_MODULE_CLASS := APPS
LOCAL_MODULE_SUFFIX := \$(COMMON_ANDROID_PACKAGE_SUFFIX)
LOCAL_CERTIFICATE := PRESIGNED
LOCAL_MODULE_TAGS := optional
LOCAL_PRODUCT_MODULE := true
include \$(BUILD_PREBUILT)
EOF_MK
fi

if [[ "${EMULATOR_BROWSER_MODULE}" != "${BROWSER_MODULE}" ]]; then
cat <<EOF_MK
include \$(CLEAR_VARS)
LOCAL_MODULE := ${EMULATOR_BROWSER_MODULE}
LOCAL_SRC_FILES := ${EMULATOR_BROWSER_MODULE}/${EMULATOR_BROWSER_MODULE}.apk
LOCAL_MODULE_CLASS := APPS
LOCAL_MODULE_SUFFIX := \$(COMMON_ANDROID_PACKAGE_SUFFIX)
LOCAL_CERTIFICATE := PRESIGNED
LOCAL_MODULE_TAGS := optional
LOCAL_PRODUCT_MODULE := true
include \$(BUILD_PREBUILT)
EOF_MK
fi
python3 - <<'PY'
import json
import os

for app in json.loads(os.environ.get("KIOSK_EXTRA_APPS_JSON", "[]")):
    module = app["module"]
    print(
        f"""
include $(CLEAR_VARS)
LOCAL_MODULE := {module}
LOCAL_SRC_FILES := {module}/{module}.apk
LOCAL_MODULE_CLASS := APPS
LOCAL_MODULE_SUFFIX := $(COMMON_ANDROID_PACKAGE_SUFFIX)
LOCAL_CERTIFICATE := PRESIGNED
LOCAL_MODULE_TAGS := optional
LOCAL_DEX_PREOPT := false
LOCAL_PRODUCT_MODULE := true
include $(BUILD_PREBUILT)""".rstrip()
    )
PY
} | write_if_changed "${APP_DIR}/Android.mk"

write_if_changed "${KIOSK_DIR}/Android.mk" <<EOF_MK
LOCAL_PATH := \$(call my-dir)

include \$(CLEAR_VARS)
LOCAL_PACKAGE_NAME := ${KIOSK_LAUNCHER_MODULE}
LOCAL_MODULE_TAGS := optional
LOCAL_CERTIFICATE := platform
LOCAL_PRIVILEGED_MODULE := true
LOCAL_OVERRIDES_PACKAGES := ${KIOSK_REMOVE_MODULES}
LOCAL_SRC_FILES := \$(call all-java-files-under, src)
LOCAL_RESOURCE_DIR := \$(LOCAL_PATH)/res
LOCAL_PROGUARD_ENABLED := disabled
include \$(BUILD_PACKAGE)
EOF_MK

write_if_changed "${KIOSK_DIR}/AndroidManifest.xml" <<EOF_XML
<?xml version="1.0" encoding="utf-8"?>
<manifest xmlns:android="http://schemas.android.com/apk/res/android"
    package="${KIOSK_LAUNCHER_PACKAGE}"
    android:versionCode="1"
    android:versionName="1.0">

    <uses-sdk android:minSdkVersion="23" android:targetSdkVersion="27" />

    <application
        android:theme="@style/AppTheme"
        android:label="@string/app_name"
        android:allowBackup="false"
        android:resizeableActivity="false">
        <activity
            android:name=".LauncherActivity"
            android:clearTaskOnLaunch="true"
            android:excludeFromRecents="true"
            android:launchMode="singleTask"
            android:stateNotNeeded="true">
            <intent-filter>
                <action android:name="android.intent.action.MAIN" />
                <category android:name="android.intent.category.HOME" />
                <category android:name="android.intent.category.DEFAULT" />
                <category android:name="android.intent.category.LAUNCHER" />
            </intent-filter>
        </activity>
    </application>
</manifest>
EOF_XML

write_if_changed "${KIOSK_DIR}/res/values/strings.xml" <<EOF_XML
<?xml version="1.0" encoding="utf-8"?>
<resources>
    <string name="app_name">Rosie Kiosk</string>
</resources>
EOF_XML

write_if_changed "${KIOSK_DIR}/res/values/styles.xml" <<EOF_XML
<?xml version="1.0" encoding="utf-8"?>
<resources>
    <style name="AppTheme" parent="@android:style/Theme.Material.NoActionBar">
        <item name="android:windowNoTitle">true</item>
        <item name="android:windowActionBar">false</item>
        <item name="android:windowFullscreen">true</item>
        <item name="android:fontFamily">sans</item>
        <item name="android:colorAccent">#00a884</item>
    </style>
</resources>
EOF_XML

python3 - "${KIOSK_DIR}/src/${KIOSK_LAUNCHER_PACKAGE//.//}/LauncherActivity.java" <<'PY'
import json
import os
import sys
from pathlib import Path


def j(value):
    return json.dumps(str(value))


def i(name):
    return int(os.environ[name])


path = Path(sys.argv[1])
package_name = os.environ["KIOSK_LAUNCHER_PACKAGE"]
background_type = os.environ["KIOSK_BACKGROUND_TYPE"]
background_loop = "true" if os.environ["KIOSK_BACKGROUND_LOOP"].lower() in ("1", "true", "yes", "on") else "false"
if background_type == "image":
    background_method = """    private View backgroundView() {
        ImageView image = new ImageView(this);
        image.setImageResource(R.drawable.kiosk_background);
        image.setScaleType(imageScaleType());
        return image;
    }
"""
elif background_type == "video":
    background_method = """    private View backgroundView() {
        FrameLayout container = new FrameLayout(this);
        container.setClipChildren(true);
        final AspectVideoView video = new AspectVideoView(this, BACKGROUND_FIT);
        Uri uri = Uri.parse(\"android.resource://\" + getPackageName() + \"/\" + R.raw.kiosk_background);
        video.setVideoURI(uri);
        video.setOnPreparedListener(new MediaPlayer.OnPreparedListener() {
            @Override
            public void onPrepared(MediaPlayer player) {
                player.setLooping(BACKGROUND_LOOP);
                player.setVolume(0f, 0f);
                video.setVideoSize(player.getVideoWidth(), player.getVideoHeight());
                video.start();
            }
        });
        container.addView(video, new FrameLayout.LayoutParams(
                FrameLayout.LayoutParams.MATCH_PARENT,
                FrameLayout.LayoutParams.MATCH_PARENT,
                Gravity.CENTER));
        return container;
    }
"""
else:
    background_method = """    private View backgroundView() {
        return null;
    }
"""
pinned_apps = json.loads(os.environ.get("KIOSK_PINNED_APPS_JSON", "[]"))
if not pinned_apps:
    pinned_apps = [
        {"app": "home_assistant", "label": os.environ["KIOSK_BUTTON_HA_LABEL"], "package": os.environ["HA_PACKAGE"]},
        {"app": "browser", "label": os.environ["KIOSK_BUTTON_BROWSER_LABEL"], "package": os.environ["BROWSER_PACKAGE"]},
    ]


def java_array(values):
    return "new String[] {" + ", ".join(j(value) for value in values) + "}"


pinned_keys = java_array([app["app"] for app in pinned_apps])
pinned_labels = java_array([app["label"] for app in pinned_apps])
pinned_packages = java_array([app["package"] for app in pinned_apps])
content = f"""package {package_name};

import android.app.Activity;
import android.content.Context;
import android.content.Intent;
import android.content.SharedPreferences;
import android.content.pm.PackageManager;
import android.graphics.Color;
import android.graphics.Typeface;
import android.graphics.drawable.Drawable;
import android.graphics.drawable.GradientDrawable;
import android.graphics.drawable.StateListDrawable;
import android.media.MediaPlayer;
import android.net.Uri;
import android.os.Bundle;
import android.provider.Browser;
import android.view.Gravity;
import android.view.View;
import android.view.Window;
import android.view.WindowManager;
import android.widget.FrameLayout;
import android.widget.ImageView;
import android.widget.LinearLayout;
import android.widget.TextView;
import android.widget.Toast;
import android.widget.VideoView;

public class LauncherActivity extends Activity {{
    private static final String HA_PACKAGE = {j(os.environ["HA_PACKAGE"])};
    private static final String BROWSER_PACKAGE = {j(os.environ["BROWSER_PACKAGE"])};
    private static final String BROWSER_FALLBACK_PACKAGE = {j(os.environ["BROWSER_FALLBACK_PACKAGE"])};
    private static final String HA_BROWSER_PACKAGE = {j(os.environ["KIOSK_HA_BROWSER_PACKAGE"])};
    private static final String[] PINNED_APP_KEYS = {pinned_keys};
    private static final String[] PINNED_APP_LABELS = {pinned_labels};
    private static final String[] PINNED_APP_PACKAGES = {pinned_packages};
    private static final String TITLE = {j(os.environ["KIOSK_TITLE"])};
    private static final String SUBTITLE = {j(os.environ["KIOSK_SUBTITLE"])};
    private static final String FONT_FAMILY = {j(os.environ["KIOSK_FONT_FAMILY"])};
    private static final String BACKGROUND_TYPE = {j(os.environ["KIOSK_BACKGROUND_TYPE"])};
    private static final String BACKGROUND_FIT = {j(os.environ["KIOSK_BACKGROUND_FIT"])};
    private static final boolean BACKGROUND_LOOP = {background_loop};
    private static final String BACKGROUND_COLOR = {j(os.environ["KIOSK_BACKGROUND_FALLBACK_COLOR"])};
    private static final String SCRIM_COLOR = {j(os.environ["KIOSK_BACKGROUND_SCRIM_COLOR"])};
    private static final String TEXT_COLOR = {j(os.environ["KIOSK_TEXT_COLOR"])};
    private static final String SUBTITLE_COLOR = {j(os.environ["KIOSK_SUBTITLE_COLOR"])};
    private static final int TITLE_SIZE_SP = {i("KIOSK_TITLE_SIZE_SP")};
    private static final int SUBTITLE_SIZE_SP = {i("KIOSK_SUBTITLE_SIZE_SP")};
    private static final String TEXT_SHADOW_COLOR = {j(os.environ["KIOSK_TEXT_SHADOW_COLOR"])};
    private static final int TEXT_SHADOW_RADIUS_DP = {i("KIOSK_TEXT_SHADOW_RADIUS_DP")};
    private static final int TEXT_SHADOW_DX_DP = {i("KIOSK_TEXT_SHADOW_DX_DP")};
    private static final int TEXT_SHADOW_DY_DP = {i("KIOSK_TEXT_SHADOW_DY_DP")};
    private static final String HA_LABEL = {j(os.environ["KIOSK_BUTTON_HA_LABEL"])};
    private static final String BROWSER_LABEL = {j(os.environ["KIOSK_BUTTON_BROWSER_LABEL"])};
    private static final String BUTTON_BACKGROUND_COLOR = {j(os.environ["KIOSK_BUTTON_BACKGROUND_COLOR"])};
    private static final String BUTTON_TEXT_COLOR = {j(os.environ["KIOSK_BUTTON_TEXT_COLOR"])};
    private static final String BUTTON_ACCENT_COLOR = {j(os.environ["KIOSK_BUTTON_ACCENT_COLOR"])};
    private static final String BUTTON_BORDER_COLOR = {j(os.environ["KIOSK_BUTTON_BORDER_COLOR"])};
    private static final String BUTTON_FOCUS_BORDER_COLOR = {j(os.environ["KIOSK_BUTTON_FOCUS_BORDER_COLOR"])};
    private static final int BUTTON_TEXT_SIZE_SP = {i("KIOSK_BUTTON_TEXT_SIZE_SP")};
    private static final int BUTTON_RADIUS_DP = {i("KIOSK_BUTTON_RADIUS_DP")};
    private static final int BUTTON_MIN_HEIGHT_DP = {i("KIOSK_BUTTON_MIN_HEIGHT_DP")};
    private static final int BUTTON_WIDTH_DP = {i("KIOSK_BUTTON_WIDTH_DP")};
    private static final String HA_URL = {j(os.environ["KIOSK_HA_URL"])};
    private static final String BROWSER_URL = {j(os.environ["KIOSK_BROWSER_URL"])};
    private static final String BROWSER_LAUNCH_POLICY = {j(os.environ["KIOSK_BROWSER_LAUNCH_POLICY"])};
    private static final String PREFS_NAME = "launcher_state";
    private static final String PREF_BROWSER_URL_SEEDED = "browser_url_seeded";

    @Override
    protected void onCreate(Bundle savedInstanceState) {{
        super.onCreate(savedInstanceState);
        requestWindowFeature(Window.FEATURE_NO_TITLE);
        getWindow().addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);
        setContentView(createContent());
        hideSystemUi();
    }}

    @Override
    protected void onResume() {{
        super.onResume();
        hideSystemUi();
    }}

    @Override
    public void onWindowFocusChanged(boolean hasFocus) {{
        super.onWindowFocusChanged(hasFocus);
        if (hasFocus) {{
            hideSystemUi();
        }}
    }}

    private View createContent() {{
        FrameLayout root = new FrameLayout(this);
        root.setBackgroundColor(Color.parseColor(BACKGROUND_COLOR));

        View background = backgroundView();
        if (background != null) {{
            root.addView(background, new FrameLayout.LayoutParams(
                    FrameLayout.LayoutParams.MATCH_PARENT,
                    FrameLayout.LayoutParams.MATCH_PARENT));
        }}

        View scrim = new View(this);
        scrim.setBackgroundColor(Color.parseColor(SCRIM_COLOR));
        root.addView(scrim, new FrameLayout.LayoutParams(
                FrameLayout.LayoutParams.MATCH_PARENT,
                FrameLayout.LayoutParams.MATCH_PARENT));

        LinearLayout content = new LinearLayout(this);
        content.setOrientation(LinearLayout.VERTICAL);
        content.setGravity(Gravity.CENTER);
        int horizontalPadding = dp(contentHorizontalPaddingDp());
        content.setPadding(horizontalPadding, dp(48), horizontalPadding, dp(48));

        Typeface typeface = Typeface.create(FONT_FAMILY, Typeface.NORMAL);
        Typeface titleTypeface = Typeface.create(FONT_FAMILY, Typeface.BOLD);
        TextView title = new TextView(this);
        title.setText(TITLE);
        title.setTextColor(Color.parseColor(TEXT_COLOR));
        title.setTextSize(TITLE_SIZE_SP);
        title.setTypeface(titleTypeface);
        title.setGravity(Gravity.CENTER);
        title.setIncludeFontPadding(false);
        applyTextShadow(title);
        content.addView(title, new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,
                LinearLayout.LayoutParams.WRAP_CONTENT));

        TextView subtitle = new TextView(this);
        subtitle.setText(SUBTITLE);
        subtitle.setTextColor(Color.parseColor(SUBTITLE_COLOR));
        subtitle.setTextSize(SUBTITLE_SIZE_SP);
        subtitle.setTypeface(typeface);
        subtitle.setGravity(Gravity.CENTER);
        subtitle.setIncludeFontPadding(false);
        applyTextShadow(subtitle);
        LinearLayout.LayoutParams subtitleParams = new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,
                LinearLayout.LayoutParams.WRAP_CONTENT);
        subtitleParams.setMargins(0, dp(10), 0, dp(36));
        content.addView(subtitle, subtitleParams);

        content.addView(pinnedAppRow(), new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,
                LinearLayout.LayoutParams.WRAP_CONTENT));
        FrameLayout.LayoutParams contentParams = new FrameLayout.LayoutParams(
                FrameLayout.LayoutParams.MATCH_PARENT,
                FrameLayout.LayoutParams.WRAP_CONTENT,
                Gravity.CENTER);
        root.addView(content, contentParams);
        return root;
    }}

{background_method}

    private ImageView.ScaleType imageScaleType() {{
        if ("contain".equals(BACKGROUND_FIT)) {{
            return ImageView.ScaleType.FIT_CENTER;
        }}
        if ("stretch".equals(BACKGROUND_FIT)) {{
            return ImageView.ScaleType.FIT_XY;
        }}
        return ImageView.ScaleType.CENTER_CROP;
    }}

    private static class AspectVideoView extends VideoView {{
        private final String fit;
        private int videoWidth = 0;
        private int videoHeight = 0;

        public AspectVideoView(Context context, String fit) {{
            super(context);
            this.fit = fit;
        }}

        public void setVideoSize(int width, int height) {{
            videoWidth = width;
            videoHeight = height;
            requestLayout();
        }}

        @Override
        protected void onMeasure(int widthMeasureSpec, int heightMeasureSpec) {{
            int viewWidth = MeasureSpec.getSize(widthMeasureSpec);
            int viewHeight = MeasureSpec.getSize(heightMeasureSpec);
            if (viewWidth <= 0 || viewHeight <= 0 || videoWidth <= 0 || videoHeight <= 0) {{
                setMeasuredDimension(viewWidth, viewHeight);
                return;
            }}
            if ("stretch".equals(fit)) {{
                setMeasuredDimension(viewWidth, viewHeight);
                return;
            }}

            float videoRatio = (float) videoWidth / (float) videoHeight;
            float viewRatio = (float) viewWidth / (float) viewHeight;
            int measuredWidth = viewWidth;
            int measuredHeight = viewHeight;

            if ("height".equals(fit)) {{
                measuredHeight = viewHeight;
                measuredWidth = Math.round(viewHeight * videoRatio);
            }} else if ("contain".equals(fit)) {{
                if (videoRatio > viewRatio) {{
                    measuredWidth = viewWidth;
                    measuredHeight = Math.round(viewWidth / videoRatio);
                }} else {{
                    measuredHeight = viewHeight;
                    measuredWidth = Math.round(viewHeight * videoRatio);
                }}
            }} else {{
                if (videoRatio > viewRatio) {{
                    measuredHeight = viewHeight;
                    measuredWidth = Math.round(viewHeight * videoRatio);
                }} else {{
                    measuredWidth = viewWidth;
                    measuredHeight = Math.round(viewWidth / videoRatio);
                }}
            }}

            setMeasuredDimension(measuredWidth, measuredHeight);
        }}
    }}

    private void applyTextShadow(TextView textView) {{
        textView.setShadowLayer(
                dp(TEXT_SHADOW_RADIUS_DP),
                dp(TEXT_SHADOW_DX_DP),
                dp(TEXT_SHADOW_DY_DP),
                Color.parseColor(TEXT_SHADOW_COLOR));
    }}

    private View pinnedAppRow() {{
        LinearLayout shelf = new LinearLayout(this);
        shelf.setOrientation(LinearLayout.VERTICAL);
        shelf.setGravity(Gravity.CENTER);
        shelf.setPadding(dp(4), 0, dp(4), 0);

        int columns = pinnedColumnCount();
        LinearLayout row = null;
        for (int i = 0; i < PINNED_APP_KEYS.length; i++) {{
            if (i % columns == 0) {{
                row = new LinearLayout(this);
                row.setOrientation(LinearLayout.HORIZONTAL);
                row.setGravity(Gravity.CENTER);
                shelf.addView(row, new LinearLayout.LayoutParams(
                        LinearLayout.LayoutParams.MATCH_PARENT,
                        LinearLayout.LayoutParams.WRAP_CONTENT));
            }}
            row.addView(appTile(
                    PINNED_APP_LABELS[i],
                    PINNED_APP_KEYS[i],
                    PINNED_APP_PACKAGES[i]));
        }}
        return shelf;
    }}

    private View appTile(String label, final String action, final String packageName) {{
        FrameLayout tile = new FrameLayout(this);
        tile.setContentDescription(label);
        tile.setClickable(true);
        tile.setFocusable(true);
        tile.setPadding(dp(12), dp(10), dp(12), dp(10));
        tile.setMinimumHeight(dp(BUTTON_MIN_HEIGHT_DP));
        tile.setElevation(dp(2));
        tile.setBackground(buttonBackground());
        tile.setOnClickListener(new View.OnClickListener() {{
            @Override
            public void onClick(View view) {{
                if ("home_assistant".equals(action)) {{
                    launchHomeAssistant();
                }} else if ("browser".equals(action)) {{
                    launchBrowser();
                }} else {{
                    launchPackage(packageName);
                }}
            }}
        }});

        ImageView icon = new ImageView(this);
        icon.setImageDrawable(appIcon(packageName));
        icon.setScaleType(ImageView.ScaleType.FIT_CENTER);
        icon.setAdjustViewBounds(true);
        icon.setContentDescription(null);
        int iconSize = pinnedIconSize();
        FrameLayout.LayoutParams iconParams = new FrameLayout.LayoutParams(
                iconSize,
                iconSize,
                Gravity.CENTER);
        tile.addView(icon, iconParams);

        int targetWidth = pinnedButtonWidth();
        LinearLayout.LayoutParams params = new LinearLayout.LayoutParams(
                targetWidth,
                pinnedButtonHeight());
        int horizontalMargin = dp(pinnedButtonHorizontalMarginDp());
        params.setMargins(horizontalMargin, dp(10), horizontalMargin, dp(10));
        tile.setLayoutParams(params);
        return tile;
    }}

    private int pinnedButtonWidth() {{
        int screenWidth = getResources().getDisplayMetrics().widthPixels;
        int columns = pinnedColumnCount();
        int horizontalPadding = dp(contentHorizontalPaddingDp() * 2);
        int shelfPadding = dp(8);
        int buttonMargins = columns * dp(pinnedButtonHorizontalMarginDp() * 2);
        int available = Math.max(dp(72), screenWidth - horizontalPadding - shelfPadding - buttonMargins);
        int rowWidth = Math.max(dp(84), available / columns);
        return Math.min(dp(BUTTON_WIDTH_DP), rowWidth);
    }}

    private int pinnedButtonHeight() {{
        int width = pinnedButtonWidth();
        return Math.max(dp(BUTTON_MIN_HEIGHT_DP), Math.min(dp(112), width));
    }}

    private int pinnedIconSize() {{
        int width = pinnedButtonWidth();
        return Math.max(dp(44), Math.min(dp(72), width - dp(48)));
    }}

    private Drawable appIcon(String packageName) {{
        PackageManager packageManager = getPackageManager();
        try {{
            return packageManager.getApplicationIcon(packageName);
        }} catch (PackageManager.NameNotFoundException firstError) {{
            if (packageName.equals(BROWSER_PACKAGE) && !BROWSER_FALLBACK_PACKAGE.equals(BROWSER_PACKAGE)) {{
                try {{
                    return packageManager.getApplicationIcon(BROWSER_FALLBACK_PACKAGE);
                }} catch (PackageManager.NameNotFoundException ignored) {{
                    // Use the launcher icon fallback below.
                }}
            }}
            try {{
                return packageManager.getApplicationIcon(getPackageName());
            }} catch (PackageManager.NameNotFoundException ignored) {{
                return getResources().getDrawable(android.R.drawable.sym_def_app_icon);
            }}
        }}
    }}

    private int contentHorizontalPaddingDp() {{
        int screenWidthDp = getResources().getConfiguration().screenWidthDp;
        if (screenWidthDp < 480) {{
            return 24;
        }}
        if (screenWidthDp < 720) {{
            return 40;
        }}
        return 64;
    }}

    private int pinnedButtonHorizontalMarginDp() {{
        return pinnedColumnCount() >= 4 ? 6 : 4;
    }}

    private int pinnedColumnCount() {{
        int screenWidthDp = getResources().getConfiguration().screenWidthDp;
        int appCount = Math.max(PINNED_APP_KEYS.length, 1);
        if (screenWidthDp >= 720) {{
            return Math.min(appCount, 6);
        }}
        if (screenWidthDp >= 600) {{
            return Math.min(appCount, 4);
        }}
        return Math.min(appCount, 3);
    }}

    private StateListDrawable buttonBackground() {{
        StateListDrawable states = new StateListDrawable();
        states.addState(new int[] {{ android.R.attr.state_pressed }}, roundedButton(BUTTON_ACCENT_COLOR, BUTTON_FOCUS_BORDER_COLOR, 2));
        states.addState(new int[] {{ android.R.attr.state_focused }}, roundedButton(BUTTON_ACCENT_COLOR, BUTTON_FOCUS_BORDER_COLOR, 2));
        states.addState(new int[] {{}}, roundedButton(BUTTON_BACKGROUND_COLOR, BUTTON_BORDER_COLOR, 1));
        return states;
    }}

    private GradientDrawable roundedButton(String color, String borderColor, int strokeDp) {{
        GradientDrawable drawable = new GradientDrawable();
        drawable.setColor(Color.parseColor(color));
        drawable.setStroke(dp(strokeDp), Color.parseColor(borderColor));
        drawable.setCornerRadius(dp(BUTTON_RADIUS_DP));
        return drawable;
    }}

    private void launchPackage(String packageName) {{
        Intent intent = getPackageManager().getLaunchIntentForPackage(packageName);
        if (intent == null && packageName.equals(BROWSER_PACKAGE) && !BROWSER_FALLBACK_PACKAGE.equals(BROWSER_PACKAGE)) {{
            intent = getPackageManager().getLaunchIntentForPackage(BROWSER_FALLBACK_PACKAGE);
        }}
        if (intent == null) {{
            Toast.makeText(this, "App is not available", Toast.LENGTH_SHORT).show();
            return;
        }}
        intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_ACTIVITY_CLEAR_TOP);
        startActivity(intent);
    }}

    private void launchHomeAssistant() {{
        if (HA_URL.length() > 0) {{
            boolean isolatedBrowser = shouldIsolateHomeAssistantBrowser();
            launchUrl(HA_URL, HA_BROWSER_PACKAGE, isolatedBrowser, false, !isolatedBrowser);
            return;
        }}
        launchPackage(HA_PACKAGE);
    }}

    private void launchBrowser() {{
        if (BROWSER_URL.length() == 0 || "resume".equals(BROWSER_LAUNCH_POLICY)) {{
            launchPackage(BROWSER_PACKAGE);
            return;
        }}
        if ("seed_once".equals(BROWSER_LAUNCH_POLICY)) {{
            SharedPreferences prefs = getSharedPreferences(PREFS_NAME, MODE_PRIVATE);
            String seedKey = PREF_BROWSER_URL_SEEDED + ":" + BROWSER_URL;
            if (!prefs.getBoolean(seedKey, false)) {{
                if (launchUrl(BROWSER_URL, BROWSER_PACKAGE, false, true, false)) {{
                    prefs.edit().putBoolean(seedKey, true).apply();
                }}
                return;
            }}
            launchPackage(BROWSER_PACKAGE);
            return;
        }}
        if ("always_url".equals(BROWSER_LAUNCH_POLICY)) {{
            launchUrl(BROWSER_URL, BROWSER_PACKAGE, false, false, false);
            return;
        }}
        launchUrl(BROWSER_URL, BROWSER_PACKAGE, false, true, false);
    }}

    private boolean shouldIsolateHomeAssistantBrowser() {{
        return HA_BROWSER_PACKAGE.length() > 0 && !HA_BROWSER_PACKAGE.equals(BROWSER_PACKAGE);
    }}

    private boolean launchUrl(String url, String preferredPackage, boolean isolatedTask, boolean createNewTab, boolean customTab) {{
        if (customTab && launchFennecCustomTab(url, preferredPackage)) {{
            return true;
        }}

        if (createNewTab && launchFennecNewTab(url, preferredPackage)) {{
            return true;
        }}

        Intent intent = new Intent(Intent.ACTION_VIEW, Uri.parse(url));
        intent.addCategory(Intent.CATEGORY_BROWSABLE);
        int flags = Intent.FLAG_ACTIVITY_NEW_TASK;
        if (isolatedTask) {{
            flags |= Intent.FLAG_ACTIVITY_CLEAR_TASK;
        }} else if (!createNewTab) {{
            flags |= Intent.FLAG_ACTIVITY_CLEAR_TOP;
        }}
        intent.addFlags(flags);
        if (createNewTab) {{
            intent.putExtra(Browser.EXTRA_CREATE_NEW_TAB, true);
        }}
        if (preferredPackage.length() > 0) {{
            intent.setPackage(preferredPackage);
        }}
        try {{
            startActivity(intent);
            return true;
        }} catch (Exception firstError) {{
            if (preferredPackage.equals(BROWSER_PACKAGE) && !BROWSER_FALLBACK_PACKAGE.equals(BROWSER_PACKAGE)) {{
                Intent browserFallback = new Intent(Intent.ACTION_VIEW, Uri.parse(url));
                browserFallback.addCategory(Intent.CATEGORY_BROWSABLE);
                browserFallback.addFlags(flags);
                browserFallback.setPackage(BROWSER_FALLBACK_PACKAGE);
                if (createNewTab) {{
                    browserFallback.putExtra(Browser.EXTRA_CREATE_NEW_TAB, true);
                }}
                try {{
                    startActivity(browserFallback);
                    return true;
                }} catch (Exception ignored) {{
                    // Fall through to the unscoped fallback below.
                }}
            }}
            if (preferredPackage.length() > 0) {{
                Intent fallback = new Intent(Intent.ACTION_VIEW, Uri.parse(url));
                fallback.addCategory(Intent.CATEGORY_BROWSABLE);
                fallback.addFlags(flags);
                if (createNewTab) {{
                    fallback.putExtra(Browser.EXTRA_CREATE_NEW_TAB, true);
                }}
                try {{
                    startActivity(fallback);
                    return true;
                }} catch (Exception ignored) {{
                    // Fall through to the user-visible error below.
                }}
            }}
            Toast.makeText(this, "URL is not available", Toast.LENGTH_SHORT).show();
            return false;
        }}
    }}

    private boolean launchFennecCustomTab(String url, String preferredPackage) {{
        if (!isFenixBrowserPackage(preferredPackage)) {{
            return false;
        }}

        Intent intent = new Intent(Intent.ACTION_VIEW, Uri.parse(url));
        intent.addCategory(Intent.CATEGORY_BROWSABLE);
        intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
        intent.setPackage(preferredPackage);
        Bundle customTabsExtras = new Bundle();
        customTabsExtras.putBinder("android.support.customtabs.extra.SESSION", null);
        intent.putExtras(customTabsExtras);
        intent.putExtra("android.support.customtabs.extra.SHARE_MENU_ITEM", false);
        intent.putExtra("android.support.customtabs.extra.TITLE_VISIBILITY", 1);
        intent.putExtra("android.support.customtabs.extra.ENABLE_URLBAR_HIDING", true);
        try {{
            startActivity(intent);
            return true;
        }} catch (Exception ignored) {{
            return false;
        }}
    }}

    private boolean launchFennecNewTab(String url, String preferredPackage) {{
        if (!isFenixBrowserPackage(preferredPackage)) {{
            return false;
        }}

        String encodedUrl = Uri.encode(url);
        String[] deepLinks = new String[] {{
                "fenix://open?url=" + encodedUrl,
                "firefox://open?url=" + encodedUrl,
        }};
        for (String deepLink : deepLinks) {{
            Intent intent = new Intent(Intent.ACTION_VIEW, Uri.parse(deepLink));
            intent.addCategory(Intent.CATEGORY_BROWSABLE);
            intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
            intent.setPackage(preferredPackage);
            try {{
                startActivity(intent);
                return true;
            }} catch (Exception ignored) {{
                // Try the next Firefox-family deep link before falling back.
            }}
        }}
        return false;
    }}

    private boolean isFenixBrowserPackage(String packageName) {{
        return "org.mozilla.fennec_fdroid".equals(packageName)
                || "org.mozilla.firefox".equals(packageName)
                || "org.mozilla.fenix".equals(packageName);
    }}

    private void hideSystemUi() {{
        getWindow().getDecorView().setSystemUiVisibility(
                View.SYSTEM_UI_FLAG_IMMERSIVE_STICKY
                        | View.SYSTEM_UI_FLAG_FULLSCREEN
                        | View.SYSTEM_UI_FLAG_HIDE_NAVIGATION
                        | View.SYSTEM_UI_FLAG_LAYOUT_FULLSCREEN
                        | View.SYSTEM_UI_FLAG_LAYOUT_HIDE_NAVIGATION
                        | View.SYSTEM_UI_FLAG_LAYOUT_STABLE);
    }}

    private int dp(int value) {{
        return (int) (value * getResources().getDisplayMetrics().density + 0.5f);
    }}
}}
"""

tmp = path.with_suffix(path.suffix + ".rosie-tmp")
tmp.write_text(content, encoding="utf-8")
if not path.exists() or tmp.read_bytes() != path.read_bytes():
    tmp.replace(path)
else:
    tmp.unlink()
PY

write_if_changed "${OVERLAY_VALUES_DIR}/config.xml" <<EOF_XML
<?xml version="1.0" encoding="utf-8"?>
<resources>
    <!-- Kiosk images rely on bundled tzdata and do not ship a timezone updater app pair. -->
    <bool name="config_timeZoneRulesUpdateTrackingEnabled">false</bool>
    <bool name="config_enableWifiDisplay">false</bool>
    <bool name="config_disableLockscreenByDefault">true</bool>
    <integer name="config_defaultNightMode">${SYSTEM_UI_NIGHT_MODE_VALUE}</integer>
    <string name="config_ntpServer" translatable="false">${SYSTEM_NTP_SERVER}</string>
    <string name="config_timeZoneRulesUpdaterPackage" translatable="false">com.android.timezone.updater</string>
    <string name="config_timeZoneRulesDataPackage" translatable="false">com.android.timezone.data</string>
</resources>
EOF_XML

write_if_changed "${SETTINGS_OVERLAY_VALUES_DIR}/defaults.xml" <<EOF_XML
<?xml version="1.0" encoding="utf-8"?>
<resources>
    <bool name="def_device_provisioned">true</bool>
    <bool name="def_user_setup_complete">true</bool>
    <bool name="def_lockscreen_disabled">true</bool>
    <bool name="def_auto_time">${SYSTEM_AUTO_TIME}</bool>
    <bool name="def_auto_time_zone">${SYSTEM_AUTO_TIME_ZONE}</bool>
    <string name="def_location_providers_allowed" translatable="false">${SYSTEM_LOCATION_PROVIDERS_ALLOWED}</string>
    <integer name="def_screen_off_timeout">2147483647</integer>
    <string name="def_immersive_mode_confirmations" translatable="false">confirmed</string>
</resources>
EOF_XML

python3 - "${DEFAULT_PERMISSIONS_DIR}/rosie-kiosk.xml" <<'PY'
import json
import os
import sys
import xml.etree.ElementTree as ET

path = sys.argv[1]
root = ET.Element("exceptions")
for grant in json.loads(os.environ.get("APP_RUNTIME_PERMISSION_GRANTS_JSON", "[]")):
    package = grant["package"]
    if not package:
        continue
    exception = ET.SubElement(root, "exception", {"package": package})
    for permission in grant.get("permissions", []):
        ET.SubElement(exception, "permission", {"name": permission, "fixed": "false"})
tree = ET.ElementTree(root)
tmp = path + ".rosie-tmp"
tree.write(tmp, encoding="utf-8", xml_declaration=True)
with open(tmp, "a", encoding="utf-8") as handle:
    handle.write("\n")
if not os.path.exists(path) or open(tmp, "rb").read() != open(path, "rb").read():
    os.replace(tmp, path)
else:
    os.unlink(tmp)
PY

{
cat <<EOF_MK
# Rosie local Home Assistant kiosk additions for Shield K1.
DEVICE_PACKAGE_OVERLAYS += vendor/rosie/overlay

PRODUCT_PROPERTY_OVERRIDES += \\
    persist.sys.usb.config=mtp,adb \\
    persist.service.adb.enable=1 \\
    persist.debug.wfd.enable=0 \\
    ro.lockscreen.disable.default=1 \\
    fw.max_users=1 \\
    fw.show_multiuserui=0 \\
    ro.setupwizard.mode=DISABLED

EOF_MK

if [[ -n "${SYSTEM_TIMEZONE:-}" ]]; then
cat <<EOF_MK
PRODUCT_PROPERTY_OVERRIDES += \\
    persist.sys.timezone=${SYSTEM_TIMEZONE}

EOF_MK
fi

if [[ -n "${ROOT_ACCESS:-}" ]]; then
cat <<EOF_MK
PRODUCT_PROPERTY_OVERRIDES += \\
    persist.sys.root_access=${ROOT_ACCESS}

EOF_MK
fi

if [[ -n "${ADB_PUBLIC_KEY:-}" ]]; then
cat <<EOF_MK
PRODUCT_COPY_FILES += \\
    vendor/rosie/adb/adb_keys:root/adb_keys

EOF_MK
fi

cat <<EOF_MK
PRODUCT_COPY_FILES += \\
    vendor/rosie/default-permissions/rosie-kiosk.xml:system/etc/default-permissions/rosie-kiosk.xml

PRODUCT_PACKAGES += \\
    ${HA_MODULE} \\
    ${BROWSER_MODULE} \\
EOF_MK
if [[ -n "${HA_BROWSER_MODULE}" && "${HA_BROWSER_MODULE}" != "${BROWSER_MODULE}" ]]; then
cat <<EOF_MK
    ${HA_BROWSER_MODULE} \\
EOF_MK
fi
for module in ${KIOSK_EXTRA_APP_MODULES}; do
cat <<EOF_MK
    ${module} \\
EOF_MK
done
cat <<EOF_MK
    ${KIOSK_LAUNCHER_MODULE}

PRODUCT_PACKAGES := \$(filter-out ${KIOSK_REMOVE_MODULES},\$(PRODUCT_PACKAGES))
EOF_MK
} | write_if_changed "${PRODUCT_DIR}/rosie_kiosk_tablet.mk"

{
cat <<EOF_MK
# Rosie local Home Assistant kiosk additions for emulator validation.
\$(call inherit-product-if-exists, vendor/lineage/config/lineage_sdk_common.mk)
DEVICE_PACKAGE_OVERLAYS += vendor/lineage/overlay/common vendor/rosie/overlay

PRODUCT_PROPERTY_OVERRIDES += \\
    persist.sys.usb.config=mtp,adb \\
    persist.service.adb.enable=1 \\
    persist.debug.wfd.enable=0 \\
    ro.lockscreen.disable.default=1 \\
    fw.max_users=1 \\
    fw.show_multiuserui=0 \\
    ro.setupwizard.mode=DISABLED

EOF_MK
if [[ -n "${SYSTEM_TIMEZONE:-}" ]]; then
cat <<EOF_MK
PRODUCT_PROPERTY_OVERRIDES += \\
    persist.sys.timezone=${SYSTEM_TIMEZONE}

EOF_MK
fi
cat <<EOF_MK
PRODUCT_COPY_FILES += \\
    vendor/rosie/default-permissions/rosie-kiosk.xml:system/etc/default-permissions/rosie-kiosk.xml

PRODUCT_PACKAGES += \\
    LineageSettingsProvider \\
    ${HA_MODULE} \\
    ${EMULATOR_BROWSER_MODULE} \\
EOF_MK
for module in ${KIOSK_EXTRA_APP_MODULES}; do
cat <<EOF_MK
    ${module} \\
EOF_MK
done
cat <<EOF_MK
    ${KIOSK_LAUNCHER_MODULE}

PRODUCT_PACKAGES := \$(filter-out ${KIOSK_REMOVE_MODULES},\$(PRODUCT_PACKAGES))
EOF_MK
} | write_if_changed "${PRODUCT_DIR}/rosie_kiosk_emulator.mk"

append_product_include() {
  local makefile="$1"
  local product_include="$2"
  local path="${ANDROID_ROOT}/${makefile}"
  local include_line="\$(call inherit-product-if-exists, ${product_include})"
  local legacy_include="\$(call inherit-product-if-exists, vendor/rosie/product/rosie_kiosk.mk)"

  if [[ ! -f "${path}" ]]; then
    echo "missing product makefile: ${makefile}" >&2
    return 1
  fi

  if grep -Fq "${legacy_include}" "${path}"; then
    grep -Fvx "${legacy_include}" "${path}" > "${path}.rosie-tmp"
    mv "${path}.rosie-tmp" "${path}"
  fi

  if ! grep -Fq "${include_line}" "${path}"; then
    {
      printf '\n# Rosie kiosk product additions.\n'
      printf '%s\n' "${include_line}"
    } >> "${path}"
  fi
}

append_product_include "${TABLET_PRODUCT_MK}" "vendor/rosie/product/rosie_kiosk_tablet.mk"
append_product_include "${EMULATOR_PRODUCT_MK}" "vendor/rosie/product/rosie_kiosk_emulator.mk"
